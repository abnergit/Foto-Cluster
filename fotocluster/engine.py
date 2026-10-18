"""Motor de detecção, reconhecimento e agrupamento de rostos.

Usa apenas OpenCV (modelos YuNet + SFace em ONNX), NumPy e Pillow.
"""

import os
import re
import shutil
import sys
import urllib.request
from dataclasses import dataclass, field

import cv2
import numpy as np
from PIL import Image, ImageOps

try:
    cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_ERROR)
except AttributeError:
    pass

IMAGE_EXTS ={".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}

_ZOO = "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models"
MODELS = {
    "detector": (
        "face_detection_yunet_2023mar.onnx",
        f"{_ZOO}/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    ),
    "recognizer": (
        "face_recognition_sface_2021dec.onnx",
        f"{_ZOO}/face_recognition_sface/face_recognition_sface_2021dec.onnx",
    ),
}


# --------------------------------------------------------------------------- #
# Modelos
# --------------------------------------------------------------------------- #
def _model_dirs():
    """Locais onde os modelos podem estar (o primeiro é onde baixamos)."""
    dirs = []
    if getattr(sys, "frozen", False):
        dirs.append(os.path.join(os.path.dirname(sys.executable), "models"))
        if hasattr(sys, "_MEIPASS"):
            dirs.append(os.path.join(sys._MEIPASS, "models"))
    project = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dirs.append(os.path.join(project, "models"))
    return dirs


def ensure_models(log=None):
    """Garante que os modelos existem localmente, baixando se necessário."""
    paths = {}
    dirs = _model_dirs()
    for key, (filename, url) in MODELS.items():
        found = next(
            (os.path.join(d, filename) for d in dirs
             if os.path.isfile(os.path.join(d, filename))),
            None,
        )
        if found is None:
            target_dir = dirs[0]
            os.makedirs(target_dir, exist_ok=True)
            found = os.path.join(target_dir, filename)
            if log:
                log(f"Baixando modelo {filename} (somente na primeira vez)...")
            tmp = found + ".part"
            urllib.request.urlretrieve(url, tmp)
            os.replace(tmp, found)
        paths[key] = found
    return paths


# --------------------------------------------------------------------------- #
# Estruturas
# --------------------------------------------------------------------------- #
@dataclass
class Face:
    photo: str
    embedding: np.ndarray
    thumb: Image.Image  # rosto alinhado 112x112 (RGB)
    score: float


@dataclass
class Group:
    name: str
    faces: list
    photos: list = field(default_factory=list)  # caminhos únicos, em ordem
    cover: Image.Image = None


# --------------------------------------------------------------------------- #
# Leitura de fotos
# --------------------------------------------------------------------------- #
def list_photos(folder, recursive=True, exclude_dir=None):
    exclude = os.path.normcase(os.path.abspath(exclude_dir)) if exclude_dir else None
    result = []
    for root, dirs, files in os.walk(folder):
        if exclude:
            dirs[:] = [
                d for d in dirs
                if os.path.normcase(os.path.abspath(os.path.join(root, d))) != exclude
            ]
        for name in sorted(files):
            if os.path.splitext(name)[1].lower() in IMAGE_EXTS:
                result.append(os.path.join(root, name))
        if not recursive:
            break
    return result


def load_image(path, max_side=1280):
    """Abre a imagem respeitando a orientação EXIF e reduz para max_side (BGR)."""
    try:
        with Image.open(path) as im:
            im.draft("RGB", (max_side, max_side))  # decodificação JPEG acelerada
            im = ImageOps.exif_transpose(im).convert("RGB")
            im.thumbnail((max_side, max_side))
            return np.asarray(im)[:, :, ::-1].copy()
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# Análise
# --------------------------------------------------------------------------- #
class FaceAnalyzer:
    def __init__(self, model_paths, score_threshold=0.85, min_face=40):
        self.min_face = min_face
        self.detector = cv2.FaceDetectorYN.create(
            model_paths["detector"], "", (320, 320), score_threshold, 0.3, 5000
        )
        self.recognizer = cv2.FaceRecognizerSF.create(model_paths["recognizer"], "")

    def analyze(self, path):
        img = load_image(path)
        if img is None:
            return None
        h, w = img.shape[:2]
        self.detector.setInputSize((w, h))
        _, detections = self.detector.detect(img)
        faces = []
        if detections is None:
            return faces
        for det in detections:
            if min(det[2], det[3]) < self.min_face:
                continue
            aligned = self.recognizer.alignCrop(img, det)
            feat = self.recognizer.feature(aligned).flatten().astype(np.float32)
            feat /= np.linalg.norm(feat) + 1e-9
            thumb = Image.fromarray(aligned[:, :, ::-1].copy())
            faces.append(Face(path, feat, thumb, float(det[-1])))
        return faces


# --------------------------------------------------------------------------- #
# Agrupamento (Chinese Whispers sobre grafo de similaridade de cosseno)
# --------------------------------------------------------------------------- #
def chinese_whispers(embeddings, threshold, iterations=30, seed=0):
    n = len(embeddings)
    if n == 0:
        return np.array([], dtype=int)
    neighbors, weights = [], []
    for start in range(0, n, 1024):
        sims = embeddings[start:start + 1024] @ embeddings.T
        for row, i in enumerate(range(start, min(start + 1024, n))):
            idx = np.nonzero(sims[row] >= threshold)[0]
            idx = idx[idx != i]
            neighbors.append(idx)
            weights.append(sims[row, idx])

    labels = np.arange(n)
    rng = np.random.default_rng(seed)
    for _ in range(iterations):
        changed = False
        for i in rng.permutation(n):
            nb = neighbors[i]
            if len(nb) == 0:
                continue
            uniq, inv = np.unique(labels[nb], return_inverse=True)
            best = uniq[np.argmax(np.bincount(inv, weights=weights[i]))]
            if best != labels[i]:
                labels[i] = best
                changed = True
        if not changed:
            break
    return labels


def cluster_faces(faces, threshold=0.40, min_photos=2):
    """Retorna (grupos ordenados por tamanho, fotos com rostos não agrupados)."""
    if not faces:
        return [], []
    emb = np.stack([f.embedding for f in faces])
    labels = chinese_whispers(emb, threshold)

    buckets = {}
    for face, label in zip(faces, labels):
        buckets.setdefault(int(label), []).append(face)

    groups, leftover = [], []
    for members in buckets.values():
        photos = list(dict.fromkeys(f.photo for f in members))
        if len(photos) < min_photos:
            leftover.extend(photos)
            continue
        centroid = np.mean([f.embedding for f in members], axis=0)
        cover = max(members, key=lambda f: float(f.embedding @ centroid) + 0.1 * f.score)
        groups.append(Group("", members, photos, cover.thumb))

    groups.sort(key=lambda g: len(g.photos), reverse=True)
    for i, g in enumerate(groups, 1):
        g.name = f"Pessoa {i:02d}"

    grouped = {p for g in groups for p in g.photos}
    leftover = [p for p in dict.fromkeys(leftover) if p not in grouped]
    return groups, leftover


# --------------------------------------------------------------------------- #
# Exportação
# --------------------------------------------------------------------------- #
def safe_folder_name(name):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip().rstrip(". ")
    return name or "Sem nome"


def export(folders, out_dir, progress=None, cancel=None):
    """folders: dict {nome da pasta: [caminhos]}. Copia as fotos (nunca move)."""
    total = sum(len(v) for v in folders.values())
    done = 0
    for folder_name, photos in folders.items():
        target = os.path.join(out_dir, safe_folder_name(folder_name))
        os.makedirs(target, exist_ok=True)
        used = {n.lower() for n in os.listdir(target)}
        for src in dict.fromkeys(photos):
            if cancel and cancel.is_set():
                return done
            base, ext = os.path.splitext(os.path.basename(src))
            name, k = base + ext, 1
            while name.lower() in used:
                k += 1
                name = f"{base} ({k}){ext}"
            used.add(name.lower())
            shutil.copy2(src, os.path.join(target, name))
            done += 1
            if progress:
                progress(done, total)
    return done
