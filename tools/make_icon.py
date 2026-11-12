"""Uygulama ikonunu üretir: Assets/Icon/screenpet.ico ve screenpet.png.

16x16 piksel sanat bir kedi yüzü, tam sayı katlarla büyütülür. Böylece her
boyutta keskin kalır ve oyundaki piksel sanat görsellerle uyumlu olur.

Kullanım: python tools/make_icon.py
"""

import os

from PIL import Image

GRID = [
    "................",
    "................",
    ".KK..........KK.",
    ".KOK........KOK.",
    ".KPOK......KOPK.",
    ".KPOOKKKKKKOOPK.",
    ".KOOODODDODOOOK.",
    "KOOOOODOODOOOOOK",
    "KOOWEOOOOOOWEOOK",
    "KOOEEOOOOOOEEOOK",
    "KOOOOOONNOOOOOOK",
    "KOOCCCCKKCCCCOOK",
    ".KCCCCKCCKCCCCK.",
    "..KKCCCCCCCCKK..",
    "....KKKKKKKK....",
    "................",
]

PALETTE = {
    ".": (0, 0, 0, 0),
    "K": (62, 36, 22, 255),      # kontur
    "O": (230, 138, 52, 255),    # turuncu tüy
    "D": (186, 98, 34, 255),     # çizgiler
    "P": (244, 166, 160, 255),   # kulak içi
    "E": (34, 24, 20, 255),      # göz
    "W": (255, 255, 255, 255),   # göz parıltısı
    "N": (232, 112, 120, 255),   # burun
    "C": (252, 230, 190, 255),   # ağız çevresi
}

SIZES = (16, 32, 48, 64, 128, 256)


def base_image():
    img = Image.new("RGBA", (16, 16))
    for y, row in enumerate(GRID):
        assert len(row) == 16, f"satır {y} 16 karakter değil"
        for x, ch in enumerate(row):
            img.putpixel((x, y), PALETTE[ch])
    return img


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(root, "Assets", "Icon")
    os.makedirs(out_dir, exist_ok=True)
    base = base_image()
    frames = [base.resize((s, s), Image.Resampling.NEAREST) for s in SIZES]
    frames[-1].save(os.path.join(out_dir, "screenpet.ico"), sizes=[(s, s) for s in SIZES],
                    append_images=frames[:-1])
    frames[SIZES.index(64)].save(os.path.join(out_dir, "screenpet.png"))
    frames[-1].save(os.path.join(out_dir, "screenpet_256.png"))
    print(f"İkon yazıldı: {out_dir}")


if __name__ == "__main__":
    main()
