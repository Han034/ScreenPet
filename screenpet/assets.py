"""Görsellerin yüklenmesi, renklendirilmesi ve kullanıcı görselleriyle değiştirilmesi."""

import os
import shutil
from dataclasses import dataclass

import pygame
from PIL import Image, ImageChops

from . import paths

PET_SIZE = 80
HOUSE_SIZE = 150
BALL_RADIUS = 15


@dataclass(frozen=True)
class AssetSpec:
    key: str            # kod içi ad, dil anahtarı "asset_<key>"
    group: str          # "pet", "house", "ball" (renk ayarı gruba uygulanır)
    folder: str         # Assets altındaki klasör
    default_file: str
    user_file: str      # UserSchema içindeki dosya adı (eski sürümle uyumlu)
    base_size: int      # mantıksal piksel, kare


_PET = [
    ("idle", "cat.PNG", "user_cat.png"),
    ("sit_left", "left_sit_cat.PNG", "user_sit_left.png"),
    ("sit_right", "right_sit_cat.PNG", "user_sit_right.png"),
    ("back", "back_cat.PNG", "user_back.png"),
    ("sleep", "right_sleep_cat.PNG", "user_sleep.png"),
    ("trigger_left", "left_trigger_cat.PNG", "user_trigger_left.png"),
    ("trigger_right", "right_trigger_cat.PNG", "user_trigger_right.png"),
    ("sad", "sad_cat.PNG", "user_sad.png"),
    ("angry", "angry_cat.PNG", "user_angry.png"),
    ("happy", "happy_cat.PNG", "user_happy.png"),
    ("smile", "smile_cat.PNG", "user_smile.png"),
    ("kips", "kips_cat.PNG", "user_kips.png"),
    ("smile2", "smile_cat_2.PNG", "user_smile2.png"),
    ("walk_1", "cat_walk.PNG", "user_walk_1.png"),
] + [(f"walk_{i}", f"cat_walk_{i}.PNG", f"user_walk_{i}.png") for i in range(2, 7)]

SPECS = (
    [AssetSpec("pet_idle", "pet", "Animal", "cat.PNG", "user_cat.png", PET_SIZE),
     AssetSpec("house", "house", "House", "house.png", "user_house.png", HOUSE_SIZE),
     AssetSpec("ball", "ball", "Ball", "ball.png", "user_ball.png", BALL_RADIUS * 2)]
    + [AssetSpec(f"pet_{k}", "pet", "Animal", d, u, PET_SIZE) for k, d, u in _PET[1:]]
)
SPEC_BY_KEY = {spec.key: spec for spec in SPECS}
WALK_KEYS = [spec.key for spec in SPECS if spec.key.startswith("pet_walk_")]

# Renk seçenekleri. "hue": renk tonu kaydırma (0-255), "sat": doygunluk çarpanı,
# "mult": renkle çarpma (beyaz/açık renkli görseller için).
TINTS = {
    "pet": {
        "original": None,
        "gray": {"sat": 0.08},
        "blue": {"hue": 138, "sat": 0.85},
        "purple": {"hue": 180, "sat": 0.8},
        "pink": {"hue": 216, "sat": 0.7},
    },
    "house": {
        "original": None,
        "green": {"mult": (170, 235, 170)},
        "orange": {"mult": (255, 205, 140)},
        "brown": {"mult": (205, 165, 125)},
        "blue": {"mult": (175, 200, 255)},
    },
    "ball": {
        "original": None,
        "red": {"hue": 238},
        "blue": {"hue": 140},
        "green": {"hue": 70},
        "purple": {"hue": 185},
    },
}

SUPPORTED_IMAGE_TYPES = (("PNG", "*.png"), ("Images", "*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.webp"))


def apply_tint(image, tint):
    """PIL RGBA görseline renk ayarı uygular."""
    if not tint:
        return image
    alpha = image.getchannel("A")
    rgb = image.convert("RGB")
    if "mult" in tint:
        rgb = ImageChops.multiply(rgb, Image.new("RGB", rgb.size, tint["mult"]))
    else:
        h, s, v = rgb.convert("HSV").split()
        shift = tint.get("hue", 0)
        sat = tint.get("sat", 1.0)
        if shift:
            h = h.point(lambda x: (x + shift) % 256)
        if sat != 1.0:
            s = s.point(lambda x: max(0, min(255, round(x * sat))))
        rgb = Image.merge("HSV", (h, s, v)).convert("RGB")
    rgb.putalpha(alpha)
    return rgb


def fit(image, size):
    """En-boy oranını koruyarak tuvale sığdırır; alt ortaya (zemine) oturtur.

    Kare olmayan görseller eskiden kareye geriliyordu; bu yüzden kedi pozdan poza
    şişip basıklaşıyordu.
    """
    w, h = size
    ratio = min(w / image.width, h / image.height)
    new = (max(1, round(image.width * ratio)), max(1, round(image.height * ratio)))
    resample = Image.Resampling.BOX if ratio < 1 else Image.Resampling.NEAREST
    image = image.resize(new, resample)
    if new == size:
        return image
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    canvas.paste(image, ((w - new[0]) // 2, h - new[1]))
    return canvas


def prepare(image, size, tint=None):
    """Renklendirir, boyutlandırır ve yarı saydam pikselleri ayıklar.

    Pencere şeffaflığı tek bir renk anahtarıyla çalışır, yarı saydamlık yoktur.
    Yarı saydam kenar pikselleri arka planla karışıp kirli bir hale bırakır.
    Bu yüzden alfa kanalı 0 ya da 255 olacak şekilde eşiklenir.
    """
    image = apply_tint(image.convert("RGBA"), tint)
    if image.size != size:
        image = fit(image, size)
    alpha = image.getchannel("A").point(lambda a: 255 if a >= 128 else 0)
    image.putalpha(alpha)
    surf = pygame.image.frombytes(image.tobytes(), image.size, "RGBA")
    return surf.convert_alpha() if pygame.display.get_surface() else surf


class AssetStore:
    def __init__(self, tints=None):
        self.tints = dict(tints or {})
        self._raw = {}      # key -> PIL.Image
        self._cache = {}    # (key, px, tint_name) -> Surface
        for spec in SPECS:
            self._load_raw(spec)

    # --- Yükleme ------------------------------------------------------------

    def user_path(self, key):
        spec = SPEC_BY_KEY[key]
        return paths.user_asset_path(spec.folder, spec.user_file)

    def has_override(self, key):
        return os.path.exists(self.user_path(key))

    def _load_raw(self, spec):
        candidates = [paths.user_asset_path(spec.folder, spec.user_file),
                      paths.default_asset_path(spec.folder, spec.default_file)]
        self._raw.pop(spec.key, None)
        for path in candidates:
            if not os.path.exists(path):
                continue
            try:
                with Image.open(path) as img:
                    self._raw[spec.key] = img.convert("RGBA")
                return True
            except (OSError, ValueError) as e:
                print(f"Görsel okunamadı ({path}): {e}")
        print(f"Görsel bulunamadı: {spec.key}")
        return False

    def _invalidate(self, predicate):
        for cache_key in [k for k in self._cache if predicate(k[0])]:
            del self._cache[cache_key]

    # --- Erişim -------------------------------------------------------------

    def surface(self, key, scale=1.0, tint_name=None):
        spec = SPEC_BY_KEY[key]
        tint_name = tint_name if tint_name is not None else self.tints.get(spec.group, "original")
        px = max(4, round(spec.base_size * scale))
        cache_key = (key, px, tint_name)
        surf = self._cache.get(cache_key)
        if surf is None:
            raw = self._raw.get(key)
            if raw is None:
                return None
            surf = prepare(raw, (px, px), TINTS[spec.group].get(tint_name))
            self._cache[cache_key] = surf
        return surf

    def thumbnail(self, key, px, tint_name=None):
        spec = SPEC_BY_KEY[key]
        return self.surface(key, px / spec.base_size, tint_name)

    def set_tint(self, group, tint_name):
        if tint_name not in TINTS.get(group, {}):
            return
        self.tints[group] = tint_name

    # --- Kullanıcı görselleri -----------------------------------------------

    def replace(self, key, source_path):
        """Seçilen dosyayı kalıcı kullanıcı klasörüne kopyalar ve hemen yükler."""
        spec = SPEC_BY_KEY[key]
        try:
            with Image.open(source_path) as img:
                img.verify()
        except (OSError, ValueError, SyntaxError) as e:
            print(f"Geçersiz görsel ({source_path}): {e}")
            return False
        target = self.user_path(key)
        try:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            # Seçilen dosya hedefin kendisiyse kopyalama hata verir.
            if os.path.abspath(source_path) != os.path.abspath(target):
                shutil.copyfile(source_path, target)
        except OSError as e:
            print(f"Görsel kopyalanamadı: {e}")
            return False
        self._invalidate(lambda k: k == key)
        return self._load_raw(spec)

    def reset(self, key):
        target = self.user_path(key)
        try:
            if os.path.exists(target):
                os.remove(target)
        except OSError as e:
            print(f"Kullanıcı görseli silinemedi: {e}")
            return False
        self._invalidate(lambda k: k == key)
        return self._load_raw(SPEC_BY_KEY[key])
