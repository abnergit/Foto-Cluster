# Configuração do PyInstaller: gera FotoCluster.exe (arquivo único) na raiz do projeto.
# Uso: Gerar_EXE.bat  (ou: pyinstaller FotoCluster.spec --distpath .)

a = Analysis(
    ["main.py"],
    datas=[("assets/icon.ico", "assets"), ("models", "models")],
    excludes=["PIL._avif"],
)

# Partes não usadas pelo app (suporte a vídeo do OpenCV), deixam o .exe menor e mais rápido.
a.binaries = [b for b in a.binaries if "opencv_videoio_ffmpeg" not in b[0]]

pyz = PYZ(a.pure)

splash = Splash("assets/splash.png", binaries=a.binaries, datas=a.datas)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    splash,
    splash.binaries,
    name="FotoCluster",
    icon="assets/icon.ico",
    console=False,
    upx=False,
)
