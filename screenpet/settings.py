"""Ayarların ve hayvan durumunun kalıcı olarak saklanması (ayarlar.json)."""

import copy
import datetime as dt
import json
import os
import time

DEFAULT_STATS = {"happiness": 100.0, "hunger": 100.0, "energy": 100.0}

# Kullanıcı tercihleri: "Ayarları Sıfırla" bunları varsayılana döndürür.
PREFERENCE_DEFAULTS = {
    "pet_name": "Maviş",
    "language": "tr",
    "start_with_windows": False,
    "show_object_names": True,
    "pet_tint": "original",
    "house_tint": "original",
    "ball_tint": "original",
}

# Hayvanın durumu: sıfırlamada korunur.
STATE_DEFAULTS = {
    "birth_date": None,       # ISO tarih, yaş buradan hesaplanır
    "stats": DEFAULT_STATS,
    "last_seen": None,        # epoch saniye, kapalıyken geçen süre için
    "pet_pos": None,          # masaüstü koordinatı [x, y]
    "house_pos": None,
}

DEFAULTS = {**PREFERENCE_DEFAULTS, **STATE_DEFAULTS}

# Eski sürümlerdeki anahtarlar
_LEGACY_RENAMES = {"hayvan_ismi": "pet_name"}
_LEGACY_DROPPED = ("hayvan_yas", "hayvan_color", "ev_color", "top_color")


def _today():
    return dt.date.today()


def migrate(data):
    """Eski ayar dosyalarını yeni biçime çevirir. Yerinde değiştirir ve döndürür."""
    for old, new in _LEGACY_RENAMES.items():
        if old in data and new not in data:
            data[new] = data[old]
        data.pop(old, None)

    if not data.get("birth_date"):
        try:
            old_age = max(1, int(data.get("hayvan_yas", 1)))
        except (TypeError, ValueError):
            old_age = 1
        data["birth_date"] = (_today() - dt.timedelta(days=old_age - 1)).isoformat()

    for key in _LEGACY_DROPPED:
        data.pop(key, None)

    stats = data.get("stats")
    if not isinstance(stats, dict):
        stats = {}
    clean = {}
    for name, default in DEFAULT_STATS.items():
        try:
            clean[name] = max(0.0, min(100.0, float(stats.get(name, default))))
        except (TypeError, ValueError):
            clean[name] = default
    data["stats"] = clean

    for key, default in DEFAULTS.items():
        if key not in data:
            data[key] = copy.deepcopy(default)
    return data


class Settings:
    def __init__(self, path):
        self.path = path
        self.data = self._load()

    def _load(self):
        data = {}
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    data = loaded
            except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
                print(f"Ayar dosyası okunamadı, varsayılanlar kullanılıyor: {e}")
        return migrate(data)

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value

    def get(self, key, default=None):
        return self.data.get(key, default)

    def save(self):
        """Önce geçici dosyaya yazar, sonra yerine taşır. Yarım kalan yazma dosyayı bozmaz."""
        self.data["last_seen"] = time.time()
        tmp = self.path + ".tmp"
        try:
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
            os.replace(tmp, self.path)
            return True
        except (OSError, TypeError) as e:
            print(f"Ayarlar kaydedilemedi: {e}")
            return False

    def reset_preferences(self):
        for key, value in PREFERENCE_DEFAULTS.items():
            self.data[key] = copy.deepcopy(value)

    def age_days(self):
        """Hayvanın kaçıncı gününde olduğu (ilk gün = 1)."""
        try:
            born = dt.date.fromisoformat(self.data["birth_date"])
        except (TypeError, ValueError):
            return 1
        return max(1, (_today() - born).days + 1)
