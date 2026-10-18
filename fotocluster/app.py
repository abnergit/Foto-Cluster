"""Foto Cluster — interface gráfica (Tkinter)."""

import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import ImageTk

from . import auth, engine

APP_NAME = "Foto Cluster"
BG = "#f4f5f7"
CARD = "#ffffff"
ACCENT = "#2f6fed"
MUTED = "#6b7280"

THUMB = 110
MINI = 34
CARD_W = 200


class ScrollFrame(ttk.Frame):
    """Frame com rolagem vertical (inclusive pela roda do mouse)."""

    def __init__(self, master):
        super().__init__(master)
        self.canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        bar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=BG)
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=bar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(
            self._win, width=e.width))
        self.bind_all("<MouseWheel>", self._wheel, add="+")

    def _wheel(self, event):
        widget = self.winfo_containing(event.x_root, event.y_root)
        while widget is not None:
            if widget is self.canvas:
                self.canvas.yview_scroll(int(-event.delta / 120), "units")
                return
            widget = widget.master


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("980x760")
        self.minsize(760, 560)
        self.configure(bg=BG)
        self._set_icon()

        self.events = queue.Queue()
        self.cancel = threading.Event()
        self.worker = None

        self.faces = []
        self.no_face = []
        self.groups = []
        self.leftover = []
        self.cards = []
        self._images = []

        self.src_var = tk.StringVar()
        self.dst_var = tk.StringVar()
        self.recursive_var = tk.BooleanVar(value=True)
        self.precision_var = tk.DoubleVar(value=0.40)
        self.min_photos_var = tk.IntVar(value=2)
        self.keep_others_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Escolha a pasta com suas fotos para começar.")

        self._style()
        self._build()
        self.after(100, self._poll)

    # ------------------------------------------------------------------ UI --
    def _set_icon(self):
        base = getattr(sys, "_MEIPASS",
                       os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        icon = os.path.join(base, "assets", "icon.ico")
        if os.path.isfile(icon):
            self.iconbitmap(default=icon)  # vale para todas as janelas, inclusive a de senha

    def _style(self):
        s = ttk.Style(self)
        if "vista" in s.theme_names():
            s.theme_use("vista")
        s.configure("TFrame", background=BG)
        s.configure("Card.TFrame", background=CARD)
        s.configure("TLabel", background=BG, font=("Segoe UI", 10))
        s.configure("Card.TLabel", background=CARD)
        s.configure("Muted.TLabel", background=CARD, foreground=MUTED, font=("Segoe UI", 9))
        s.configure("Title.TLabel", font=("Segoe UI Semibold", 18))
        s.configure("Sub.TLabel", foreground=MUTED)
        s.configure("Section.TLabel", background=CARD, font=("Segoe UI Semibold", 11))
        s.configure("TCheckbutton", background=CARD)
        s.configure("Accent.TButton", font=("Segoe UI Semibold", 10), padding=(16, 6))

    def _build(self):
        header = ttk.Frame(self, padding=(20, 16, 20, 4))
        header.pack(fill="x")
        ttk.Label(header, text=APP_NAME, style="Title.TLabel").pack(anchor="w")
        ttk.Label(header, style="Sub.TLabel",
                  text="Organize suas fotos em pastas, uma para cada pessoa.").pack(anchor="w")

        # --- Configurações ---
        card = ttk.Frame(self, style="Card.TFrame", padding=16)
        card.pack(fill="x", padx=20, pady=10)
        card.columnconfigure(1, weight=1)

        ttk.Label(card, text="1. Pasta com as fotos", style="Section.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 4))
        ttk.Entry(card, textvariable=self.src_var).grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Button(card, text="Procurar...", command=self._pick_src).grid(row=0, column=2)
        ttk.Checkbutton(card, text="Incluir subpastas", variable=self.recursive_var).grid(
            row=1, column=1, sticky="w", padx=8, pady=(0, 8))

        ttk.Label(card, text="2. Salvar em", style="Section.TLabel").grid(
            row=2, column=0, sticky="w")
        ttk.Entry(card, textvariable=self.dst_var).grid(row=2, column=1, sticky="ew", padx=8)
        ttk.Button(card, text="Procurar...", command=self._pick_dst).grid(row=2, column=2)

        opts = ttk.Frame(card, style="Card.TFrame")
        opts.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(12, 0))
        ttk.Label(opts, text="Rigor na comparação:", style="Card.TLabel").pack(side="left")
        ttk.Label(opts, text="tolerante", style="Muted.TLabel").pack(side="left", padx=(8, 2))
        ttk.Scale(opts, from_=0.30, to=0.55, variable=self.precision_var,
                  length=160).pack(side="left")
        ttk.Label(opts, text="rigoroso", style="Muted.TLabel").pack(side="left", padx=(2, 20))
        ttk.Label(opts, text="Mín. de fotos por pessoa:", style="Card.TLabel").pack(side="left")
        ttk.Spinbox(opts, from_=1, to=20, width=4,
                    textvariable=self.min_photos_var).pack(side="left", padx=8)
        ttk.Checkbutton(card, variable=self.keep_others_var,
                        text="Copiar também as fotos sem pessoa identificada "
                             "(pastas \"Não identificados\" e \"Sem rostos\")").grid(
            row=4, column=0, columnspan=3, sticky="w", pady=(8, 0))

        # --- Barra de ações / progresso ---
        bar = ttk.Frame(self, padding=(20, 0))
        bar.pack(fill="x")
        self.analyze_btn = ttk.Button(bar, text="Analisar fotos", style="Accent.TButton",
                                      command=self._start_analysis)
        self.analyze_btn.pack(side="left")
        self.regroup_btn = ttk.Button(bar, text="Reagrupar", command=self._regroup,
                                      state="disabled")
        self.regroup_btn.pack(side="left", padx=6)
        self.cancel_btn = ttk.Button(bar, text="Cancelar", command=self.cancel.set,
                                     state="disabled")
        self.cancel_btn.pack(side="left")
        self.export_btn = ttk.Button(bar, text="Criar pastas", style="Accent.TButton",
                                     command=self._start_export, state="disabled")
        self.export_btn.pack(side="right")
        self.open_btn = ttk.Button(bar, text="Abrir destino", command=self._open_dst,
                                   state="disabled")
        self.open_btn.pack(side="right", padx=6)

        prog = ttk.Frame(self, padding=(20, 8, 20, 0))
        prog.pack(fill="x")
        self.progress = ttk.Progressbar(prog, mode="determinate")
        self.progress.pack(fill="x")
        ttk.Label(prog, textvariable=self.status_var, foreground=MUTED).pack(
            anchor="w", pady=(4, 0))

        # --- Resultados ---
        res_head = ttk.Frame(self, padding=(20, 10, 20, 4))
        res_head.pack(fill="x")
        ttk.Label(res_head, text="Pessoas encontradas",
                  font=("Segoe UI Semibold", 12)).pack(side="left")
        ttk.Label(res_head, style="Sub.TLabel",
                  text="Renomeie os grupos. Nomes iguais juntam os grupos na mesma pasta; "
                       "desmarque para ignorar.").pack(side="left", padx=12)

        self.results = ScrollFrame(self)
        self.results.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        self.results.canvas.bind("<Configure>", lambda e: self._layout_cards(), add="+")
        self._show_placeholder("Os grupos de rostos aparecerão aqui depois da análise.")

    def _show_placeholder(self, text):
        for w in self.results.inner.winfo_children():
            w.destroy()
        tk.Label(self.results.inner, text=text, bg=BG, fg=MUTED,
                 font=("Segoe UI", 10)).grid(row=0, column=0, padx=10, pady=30, sticky="w")

    # ------------------------------------------------------------- Pastas --
    def _pick_src(self):
        path = filedialog.askdirectory(title="Escolha a pasta com as fotos")
        if path:
            path = os.path.normpath(path)
            self.src_var.set(path)
            if not self.dst_var.get():
                self.dst_var.set(os.path.join(path, "Fotos por pessoa"))

    def _pick_dst(self):
        path = filedialog.askdirectory(title="Escolha onde salvar as pastas")
        if path:
            self.dst_var.set(os.path.normpath(path))

    def _open_dst(self):
        path = self.dst_var.get()
        if os.path.isdir(path):
            os.startfile(path)

    # ------------------------------------------------------------ Análise --
    def _set_busy(self, busy):
        state = "disabled" if busy else "normal"
        self.analyze_btn.configure(state=state)
        self.cancel_btn.configure(state="normal" if busy else "disabled")
        has_data = bool(self.faces or self.no_face)
        self.regroup_btn.configure(state="disabled" if busy or not self.faces else "normal")
        self.export_btn.configure(state="disabled" if busy or not has_data else "normal")

    def _start_analysis(self):
        src = self.src_var.get().strip()
        if not os.path.isdir(src):
            messagebox.showwarning(APP_NAME, "Escolha uma pasta de fotos válida.")
            return
        self.cancel.clear()
        self.faces, self.no_face, self.groups = [], [], []
        self._show_placeholder("Analisando...")
        self._set_busy(True)
        self.worker = threading.Thread(
            target=self._analysis_worker,
            args=(src, self.recursive_var.get(), self.dst_var.get().strip()),
            daemon=True,
        )
        self.worker.start()

    def _analysis_worker(self, src, recursive, dst):
        emit = self.events.put
        try:
            models = engine.ensure_models(log=lambda m: emit(("status", m)))
            analyzer = engine.FaceAnalyzer(models)
            emit(("status", "Procurando fotos..."))
            photos = engine.list_photos(src, recursive, exclude_dir=dst or None)
            if not photos:
                emit(("error", "Nenhuma foto encontrada nessa pasta."))
                return
            faces, no_face, unreadable = [], [], 0
            for i, path in enumerate(photos, 1):
                if self.cancel.is_set():
                    emit(("status", "Análise cancelada."))
                    break
                found = analyzer.analyze(path)
                if found is None:
                    unreadable += 1
                elif found:
                    faces.extend(found)
                else:
                    no_face.append(path)
                emit(("progress", i, len(photos),
                      f"Analisando {i} de {len(photos)} — {len(faces)} rostos encontrados"))
            emit(("analysis_done", faces, no_face, unreadable))
        except Exception as exc:  # erro inesperado (ex.: sem internet p/ baixar modelos)
            emit(("error", f"Ocorreu um erro: {exc}"))

    def _regroup(self):
        self.groups, self.leftover = engine.cluster_faces(
            self.faces, self.precision_var.get(), max(1, self.min_photos_var.get()))
        self._render_groups()
        self.status_var.set(
            f"{len(self.groups)} pessoas encontradas em {len({f.photo for f in self.faces})} "
            f"fotos com rostos ({len(self.no_face)} fotos sem rostos).")

    # ------------------------------------------------------------ Grupos --
    def _render_groups(self):
        for w in self.results.inner.winfo_children():
            w.destroy()
        self.cards, self._images = [], []
        if not self.groups:
            self._show_placeholder("Nenhum grupo encontrado. Tente um rigor mais tolerante "
                                   "ou diminua o mínimo de fotos por pessoa.")
            return
        for group in self.groups:
            self.cards.append(self._make_card(group))
        self._layout_cards()

    def _make_card(self, group):
        card = tk.Frame(self.results.inner, bg=CARD, padx=10, pady=10,
                        highlightbackground="#e3e5e8", highlightthickness=1)
        img = ImageTk.PhotoImage(group.cover.resize((THUMB, THUMB)))
        self._images.append(img)
        tk.Label(card, image=img, bg=CARD).pack()

        strip = tk.Frame(card, bg=CARD)
        strip.pack(pady=(6, 4))
        others = [f for f in group.faces if f.thumb is not group.cover][:4]
        for f in others:
            mini = ImageTk.PhotoImage(f.thumb.resize((MINI, MINI)))
            self._images.append(mini)
            tk.Label(strip, image=mini, bg=CARD).pack(side="left", padx=1)

        name_var = tk.StringVar(value=group.name)
        ttk.Entry(card, textvariable=name_var, width=20, justify="center").pack(pady=2)
        use_var = tk.BooleanVar(value=True)
        n = len(group.photos)
        ttk.Checkbutton(card, text=f"{n} foto{'s' if n != 1 else ''}",
                        variable=use_var).pack()
        card.name_var, card.use_var, card.group = name_var, use_var, group
        return card

    def _layout_cards(self):
        if not self.cards:
            return
        width = max(self.results.canvas.winfo_width(), CARD_W)
        cols = max(1, width // (CARD_W + 12))
        for i, card in enumerate(self.cards):
            card.grid(row=i // cols, column=i % cols, padx=6, pady=6, sticky="n")

    # ---------------------------------------------------------- Exportar --
    def _start_export(self):
        dst = self.dst_var.get().strip()
        if not dst:
            messagebox.showwarning(APP_NAME, "Escolha a pasta onde as fotos serão salvas.")
            return
        folders = {}
        for card in self.cards:
            if card.use_var.get():
                name = card.name_var.get().strip() or card.group.name
                folders.setdefault(name, []).extend(card.group.photos)
        if self.keep_others_var.get():
            if self.leftover:
                folders.setdefault("Não identificados", []).extend(self.leftover)
            if self.no_face:
                folders.setdefault("Sem rostos", []).extend(self.no_face)
        if not folders:
            messagebox.showinfo(APP_NAME, "Nada para salvar.")
            return
        total = sum(len(set(v)) for v in folders.values())
        if not messagebox.askyesno(
                APP_NAME, f"Copiar {total} fotos para {len(folders)} pastas em:\n{dst}\n\n"
                          "As fotos originais não serão alteradas."):
            return
        self.cancel.clear()
        self._set_busy(True)
        threading.Thread(target=self._export_worker, args=(folders, dst), daemon=True).start()

    def _export_worker(self, folders, dst):
        emit = self.events.put
        try:
            done = engine.export(
                folders, dst,
                progress=lambda d, t: emit(("progress", d, t, f"Copiando {d} de {t} fotos...")),
                cancel=self.cancel,
            )
            emit(("export_done", done))
        except Exception as exc:
            emit(("error", f"Erro ao copiar fotos: {exc}"))

    # ------------------------------------------------------ Fila de eventos --
    def _poll(self):
        try:
            while True:
                self._handle(self.events.get_nowait())
        except queue.Empty:
            pass
        self.after(100, self._poll)

    def _handle(self, ev):
        kind = ev[0]
        if kind == "status":
            self.status_var.set(ev[1])
        elif kind == "progress":
            _, done, total, text = ev
            self.progress.configure(maximum=total, value=done)
            self.status_var.set(text)
        elif kind == "analysis_done":
            _, self.faces, self.no_face, unreadable = ev
            self._set_busy(False)
            self._regroup()
            if unreadable:
                msg = ("1 arquivo não pôde ser lido." if unreadable == 1
                       else f"{unreadable} arquivos não puderam ser lidos.")
                self.status_var.set(f"{self.status_var.get()} {msg}")
        elif kind == "export_done":
            self._set_busy(False)
            self.open_btn.configure(state="normal")
            self.status_var.set(f"Pronto! {ev[1]} fotos copiadas.")
            if messagebox.askyesno(APP_NAME, "Fotos organizadas! Abrir a pasta de destino?"):
                self._open_dst()
        elif kind == "error":
            self._set_busy(False)
            self.status_var.set(ev[1])
            messagebox.showerror(APP_NAME, ev[1])


def main():
    try:  # textos nítidos em telas com escala (Windows)
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    app = App()
    app.withdraw()
    try:  # fecha a tela de abertura do executável
        import pyi_splash
        pyi_splash.close()
    except ImportError:
        pass
    if not auth.ask_password(app, APP_NAME):
        app.destroy()
        return
    app.deiconify()
    app.lift()
    app.focus_force()
    app.mainloop()
