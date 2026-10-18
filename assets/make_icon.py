"""Gera assets/icon.ico (câmera fotográfica) e assets/icon.png."""
from PIL import Image, ImageDraw

S = 1024
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
body, dark, accent = (47, 111, 237), (24, 40, 82), (255, 255, 255)

d.rounded_rectangle((330, 170, 620, 300), 50, fill=body)            # topo do visor
d.rounded_rectangle((70, 240, 954, 860), 130, fill=body)            # corpo
d.rounded_rectangle((690, 320, 830, 390), 30, fill=(255, 210, 80))  # flash
cx, cy = 512, 560
for r, c in [(250, accent), (205, dark), (140, (60, 90, 170)), (70, dark)]:
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=c)
d.ellipse((cx - 115, cy - 115, cx - 55, cy - 55), fill=(255, 255, 255, 200))  # brilho
d.ellipse((150, 330, 220, 400), fill=accent)                        # botão

img = img.resize((256, 256), Image.LANCZOS)
img.save("assets/icon.png")
img.save("assets/icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

# Tela de abertura (exibida enquanto o executável carrega)
from PIL import ImageFont

splash = Image.new("RGB", (420, 220), (244, 245, 247))
sd = ImageDraw.Draw(splash)
splash.paste(img.resize((96, 96), Image.LANCZOS), (30, 50), img.resize((96, 96), Image.LANCZOS))
try:
    title = ImageFont.truetype("C:/Windows/Fonts/seguisb.ttf", 30)
    sub = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 15)
except OSError:
    title = sub = ImageFont.load_default()
sd.text((145, 68), "Foto Cluster", fill=(17, 24, 39), font=title)
sd.text((147, 112), "Abrindo, aguarde um instante...", fill=(107, 114, 128), font=sub)
sd.rectangle((0, 214, 420, 220), fill=(47, 111, 237))
splash.save("assets/splash.png")
