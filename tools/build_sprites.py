"""Google Flow'da üretilen sprite sayfalarından kedi görsellerini üretir.

Kullanım:
    python tools/build_sprites.py poses.jpg walk.jpg [--preview out.png]

İki sayfa da aynı referansla, aynı ölçekte üretildi (duruş sayfası 4x3 poz,
yürüme sayfası 4x3 kare). Bu araç:
  * yeşil arka planı ve JPEG'in yeşile kayan kenar piksellerini ayıklar,
  * kopuk küçük lekeleri atar,
  * tüm pozları tek bir ortak palete eşler (JPEG gürültüsü gider, renkler pozdan poza kaymaz),
  * hepsini ölçeklemeden aynı kare tuvale, aynı zemin çizgisine oturtur
    (eskiden her görsel kendi kutusuna gerilip boyu pozdan poza değişiyordu),
  * yürüme karelerini kafaya göre hizalar (yürürken ileri geri titremez),
  * sonucu Assets/Animal/Default altına aynı dosya adlarıyla yazar.
"""

import argparse
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "Assets", "Animal", "Default")

CANVAS = 324         # kaynak pikseli; en geniş poz (yürüyen kedi) ~292 px
BASELINE_PAD = 6     # ayakların altında bırakılan boşluk
PALETTE_SIZE = 24
MIN_BLOB = 120       # bundan küçük kopuk lekeler (JPEG kiri) atılır

# (satır, sütun) -> [(dosya adı, yatay çevir)]
POSE_MAP = {
    (0, 0): [("cat.PNG", False)],
    (0, 1): [("happy_cat.PNG", False)],
    (0, 2): [("smile_cat.PNG", False)],
    (0, 3): [("kips_cat.PNG", False)],
    (1, 0): [("smile_cat_2.PNG", False)],
    (1, 1): [("sad_cat.PNG", False)],
    (1, 2): [("angry_cat.PNG", False)],
    (1, 3): [("back_cat.PNG", False)],
    (2, 0): [("right_sit_cat.PNG", False), ("left_sit_cat.PNG", True)],
    (2, 1): [("right_trigger_cat.PNG", False), ("left_trigger_cat.PNG", True)],
    (2, 2): [("right_sleep_cat.PNG", False)],
}
# Yürüme sayfasından seçilen kareler, oynatma sırasıyla
WALK_CELLS = [(0, 0), (0, 1), (0, 2), (0, 3), (1, 3), (2, 3)]
WALK_FILES = ["cat_walk.PNG"] + [f"cat_walk_{i}.PNG" for i in range(2, 7)]


def load(path):
    rgb = np.asarray(Image.open(path).convert("RGB")).astype(np.int32)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    # Kedinin hiçbir rengi (turuncu, kahve, krem, mavi gözyaşı) yeşil baskın değildir.
    background = (g > 70) & (g - np.maximum(r, b) > 15)
    return rgb, ~background


def runs(mask):
    out, start = [], None
    for i, v in enumerate(mask):
        if v and start is None:
            start = i
        elif not v and start is not None:
            out.append((start, i))
            start = None
    if start is not None:
        out.append((start, len(mask)))
    return out


def grid_cells(fg):
    """Satır/sütun boşluklarından hücre sınırlarını bulur."""
    rows = [r for r in runs(fg.sum(1) > 2) if r[1] - r[0] > 60]
    cols = [c for c in runs(fg.sum(0) > 2) if c[1] - c[0] > 60]
    return rows, cols


def clean_mask(mask):
    """Küçük kopuk lekeleri atar (4-komşuluk)."""
    h, w = mask.shape
    seen = np.zeros_like(mask)
    keep = np.zeros_like(mask)
    for y in range(h):
        for x in range(w):
            if mask[y, x] and not seen[y, x]:
                stack, comp = [(y, x)], []
                seen[y, x] = True
                while stack:
                    cy, cx = stack.pop()
                    comp.append((cy, cx))
                    for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
                        if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                            seen[ny, nx] = True
                            stack.append((ny, nx))
                if len(comp) >= MIN_BLOB:
                    for cy, cx in comp:
                        keep[cy, cx] = True
    return keep


def crop(rgb, mask):
    ys, xs = np.nonzero(mask)
    sl = (slice(ys.min(), ys.max() + 1), slice(xs.min(), xs.max() + 1))
    return rgb[sl], mask[sl]


def extract(path, cells):
    rgb, fg = load(path)
    rows, cols = grid_cells(fg)
    print(f"{os.path.basename(path)}: {len(rows)}x{len(cols)} hücre")
    out = {}
    for (r, c) in cells:
        (y0, y1), (x0, x1) = rows[r], cols[c]
        out[(r, c)] = crop(rgb[y0:y1, x0:x1], clean_mask(fg[y0:y1, x0:x1]))
    return out


def build_palette(samples, k):
    """Basit k-ortalama; tüm pozlar aynı paleti kullansın diye."""
    data = np.concatenate(samples).astype(float)
    rng = np.random.default_rng(0)
    data = data[rng.choice(len(data), min(len(data), 60000), replace=False)]
    centers = data[rng.choice(len(data), k, replace=False)]
    for _ in range(25):
        label = ((data[:, None, :] - centers[None]) ** 2).sum(2).argmin(1)
        for c in range(k):
            pts = data[label == c]
            if len(pts):
                centers[c] = pts.mean(0)
    return centers.round().astype(np.int32)


def quantize(color, palette):
    flat = color.reshape(-1, 3)
    out = np.empty_like(flat)
    for i in range(0, len(flat), 50000):
        part = flat[i:i + 50000]
        out[i:i + 50000] = palette[((part[:, None, :] - palette[None]) ** 2).sum(-1).argmin(-1)]
    return out.reshape(color.shape)


def place(color, alpha, x_offset=None):
    """Tuvale, ortak zemin çizgisine oturtur."""
    h, w = alpha.shape
    if h > CANVAS - BASELINE_PAD or w > CANVAS:
        raise SystemExit(f"Poz tuvale sığmıyor: {w}x{h}")
    out = np.zeros((CANVAS, CANVAS, 4), np.uint8)
    y0 = CANVAS - BASELINE_PAD - h
    x0 = (CANVAS - w) // 2 if x_offset is None else x_offset
    x0 = max(0, min(CANVAS - w, x0))
    out[y0:y0 + h, x0:x0 + w, :3] = color
    out[y0:y0 + h, x0:x0 + w, 3] = alpha * 255
    return out


def head_x(alpha):
    """Üst %40'taki (kafa) piksellerin yatay ağırlık merkezi."""
    rows = max(1, int(alpha.shape[0] * 0.4))
    xs = np.nonzero(alpha[:rows])[1]
    return xs.mean() if len(xs) else alpha.shape[1] / 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("poses")
    ap.add_argument("walk")
    ap.add_argument("--preview")
    args = ap.parse_args()

    poses = extract(args.poses, POSE_MAP.keys())
    walk = extract(args.walk, WALK_CELLS)
    palette = build_palette([c[a] for c, a in list(poses.values()) + list(walk.values())],
                            PALETTE_SIZE)

    sprites = {}
    for cell, targets in POSE_MAP.items():
        color, alpha = poses[cell]
        rgba = place(quantize(color, palette), alpha)
        for name, flip in targets:
            sprites[name] = rgba[:, ::-1] if flip else rgba

    frames = [walk[c] for c in WALK_CELLS]
    target = round(np.mean([(CANVAS - a.shape[1]) / 2 + head_x(a) for _, a in frames]))
    for name, (color, alpha) in zip(WALK_FILES, frames):
        sprites[name] = place(quantize(color, palette), alpha, round(target - head_x(alpha)))

    os.makedirs(OUT_DIR, exist_ok=True)
    for name, rgba in sprites.items():
        Image.fromarray(np.ascontiguousarray(rgba), "RGBA").save(os.path.join(OUT_DIR, name))
    print(f"{len(sprites)} görsel yazıldı: {OUT_DIR}")

    if args.preview:
        names = sorted(sprites)
        cell = CANVAS // 2
        sheet = Image.new("RGBA", (cell * 6, cell * ((len(names) + 5) // 6)), (205, 210, 225, 255))
        for i, name in enumerate(names):
            img = Image.fromarray(np.ascontiguousarray(sprites[name]), "RGBA")
            img = img.resize((cell, cell), Image.Resampling.BOX)
            sheet.alpha_composite(img, ((i % 6) * cell, (i // 6) * cell))
        sheet.save(args.preview)


if __name__ == "__main__":
    sys.exit(main())
