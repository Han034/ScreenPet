"""Temel testler. Çalıştırma: python -m unittest discover -s tests"""

import json
import os
import re
import sys
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pygame  # noqa: E402

from screenpet import assets, i18n, pet as petmod, settings  # noqa: E402


class LanguageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(ROOT, "languages.json"), encoding="utf-8") as f:
            cls.langs = json.load(f)

    def test_languages_have_same_keys(self):
        self.assertEqual(set(self.langs["tr"]), set(self.langs["en"]))

    def test_every_key_used_in_code_exists(self):
        used = set()
        pattern = re.compile(r'(?:i18n\.tn?|t)\(\s*"([a-z0-9_]+)"')
        pairs = re.compile(r'\(\s*"([a-z0-9_]+)",\s*(?:self|app)\.')
        for folder, _, files in os.walk(os.path.join(ROOT, "screenpet")):
            for name in files:
                if name.endswith(".py"):
                    with open(os.path.join(folder, name), encoding="utf-8") as f:
                        source = f.read()
                    used.update(pattern.findall(source))
                    used.update(pairs.findall(source))
        used.update(f"asset_{spec.key}" for spec in assets.SPECS)
        used.update(("pet", "house", "ball", "assets", "game_settings", "turkish", "english",
                     "happiness", "hunger", "sleep", "start_win_disabled"))
        # Kod içi sözlük anahtarları (dil anahtarı değil)
        used -= {"hue", "sat", "stats", "energy", "birth_date", "hayvan_yas", "window", "toggle"}
        missing = sorted(k for k in used if k not in self.langs["tr"])
        self.assertEqual(missing, [])

    def test_fallback_and_plural(self):
        i18n.load(os.path.join(ROOT, "languages.json"))
        i18n.set_language("en")
        self.assertEqual(i18n.tn("age_value", 1), "1 day old")
        self.assertEqual(i18n.tn("age_value", 3), "3 days old")
        self.assertEqual(i18n.t("does_not_exist"), "does_not_exist")
        i18n.set_language("xx")
        self.assertEqual(i18n.get_language(), "tr")


class SettingsTests(unittest.TestCase):
    def test_migrates_legacy_file(self):
        legacy = {"hayvan_ismi": "Usman", "hayvan_yas": 3, "hayvan_color": [255, 255, 0],
                  "language": "en", "start_with_windows": True}
        data = settings.migrate(dict(legacy))
        self.assertEqual(data["pet_name"], "Usman")
        self.assertNotIn("hayvan_ismi", data)
        self.assertNotIn("hayvan_color", data)
        self.assertEqual(data["language"], "en")
        self.assertEqual(data["stats"]["hunger"], 100.0)

    def test_save_load_roundtrip_and_age(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "ayarlar.json")
            s = settings.Settings(path)
            s["pet_name"] = "Pamuk"
            s["stats"] = {"happiness": 40, "hunger": 55, "energy": 70}
            s["birth_date"] = "2020-01-01"
            self.assertTrue(s.save())
            again = settings.Settings(path)
            self.assertEqual(again["pet_name"], "Pamuk")
            self.assertEqual(again["stats"]["hunger"], 55.0)
            self.assertGreater(again.age_days(), 365)

    def test_reset_keeps_pet_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = settings.Settings(os.path.join(tmp, "a.json"))
            s["pet_name"] = "X"
            s["stats"] = {"happiness": 10, "hunger": 10, "energy": 10}
            s.reset_preferences()
            self.assertEqual(s["pet_name"], settings.PREFERENCE_DEFAULTS["pet_name"])
            self.assertEqual(s["stats"]["happiness"], 10)


class _Monitor:
    def __init__(self, rect):
        self.rect = rect
        self.work = rect
        self.scale = 1.0


class _Display:
    def __init__(self):
        self.monitors = [_Monitor(pygame.Rect(0, 0, 1920, 1080))]

    def scale_at(self, pos):
        return 1.0

    def nearest_monitor(self, pos):
        return self.monitors[0]


class _World:
    def __init__(self):
        from screenpet.ball import Ball
        self.display = _Display()
        self.house_rect = pygame.Rect(1500, 800, 150, 150)
        self.house_dragging = False
        self.ball = Ball()
        self.caught = 0

    def on_ball_caught(self):
        self.caught += 1
        self.ball.remove()
        self.pet.caught_ball()


class PetTests(unittest.TestCase):
    def test_stats_decay_slowly(self):
        p = petmod.Pet({"happiness": 100, "hunger": 100, "energy": 100}, (500, 900))
        w = _World()
        for _ in range(60 * 60):  # bir dakika
            p.update(1 / 60, w)
        self.assertGreater(p.hunger, 99.5)
        self.assertGreater(p.happiness, 99.5)
        self.assertLess(p.energy, 100)

    def test_tired_pet_goes_home_sleeps_and_recovers(self):
        p = petmod.Pet({"happiness": 100, "hunger": 100, "energy": 5}, (500, 900))
        w = _World()
        for _ in range(60 * 30):
            p.update(1 / 60, w)
            if p.state == petmod.SLEEPING:
                break
        self.assertEqual(p.state, petmod.SLEEPING)
        self.assertTrue(w.house_rect.collidepoint(p.center))
        for _ in range(60 * 60 * 15):
            p.update(1 / 60, w)
            if p.state != petmod.SLEEPING:
                break
        self.assertNotEqual(p.state, petmod.SLEEPING)
        self.assertGreaterEqual(p.energy, 99.9)

    def test_catching_ball_makes_pet_happy(self):
        p = petmod.Pet({"happiness": 50, "hunger": 100, "energy": 100}, (500, 900))
        w = _World()
        w.pet = p
        w.ball.active = True
        w.ball.x, w.ball.y = 700, 900
        for _ in range(60 * 10):
            p.update(1 / 60, w)
            if w.caught:
                break
        self.assertEqual(w.caught, 1)
        self.assertGreater(p.happiness, 50 + petmod.BALL_HAPPINESS - 1)

    def test_offline_time(self):
        out = petmod.apply_offline_time({"happiness": 90, "hunger": 90, "energy": 10}, 3 * 24 * 3600)
        self.assertEqual(out["hunger"], petmod.OFFLINE_FLOOR)
        self.assertEqual(out["energy"], 100)
        low = petmod.apply_offline_time({"happiness": 10, "hunger": 10, "energy": 50}, 3600)
        self.assertEqual(low["hunger"], 10)


class AssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        from screenpet import paths
        self.paths = paths
        self._old = paths._data_dir
        paths._data_dir = self.tmp.name

    def tearDown(self):
        self.paths._data_dir = self._old
        self.tmp.cleanup()

    def test_all_default_assets_load_with_binary_alpha(self):
        store = assets.AssetStore()
        for spec in assets.SPECS:
            surf = store.surface(spec.key, 1.0)
            self.assertIsNotNone(surf, spec.key)
            alphas = {surf.get_at((x, y)).a for x in range(0, surf.get_width(), 3)
                      for y in range(0, surf.get_height(), 3)}
            self.assertTrue(alphas <= {0, 255}, spec.key)

    def test_replace_goes_to_persistent_dir_and_reset(self):
        store = assets.AssetStore()
        src = os.path.join(self.tmp.name, "red.png")
        from PIL import Image
        Image.new("RGBA", (10, 10), (255, 0, 0, 255)).save(src)
        self.assertTrue(store.replace("ball", src))
        self.assertTrue(store.user_path("ball").startswith(self.tmp.name))
        self.assertTrue(store.has_override("ball"))
        self.assertEqual(tuple(store.surface("ball", 1.0).get_at((15, 15)))[:3], (255, 0, 0))
        self.assertTrue(store.reset("ball"))
        self.assertFalse(store.has_override("ball"))

    def test_rejects_non_image(self):
        store = assets.AssetStore()
        bad = os.path.join(self.tmp.name, "bad.png")
        with open(bad, "w") as f:
            f.write("not an image")
        self.assertFalse(store.replace("house", bad))
        self.assertFalse(store.has_override("house"))

    def test_tints_change_pixels(self):
        store = assets.AssetStore()
        original = store.surface("pet_idle", 1.0, "original")
        blue = store.surface("pet_idle", 1.0, "blue")
        self.assertNotEqual(pygame.image.tobytes(original, "RGBA"), pygame.image.tobytes(blue, "RGBA"))


if __name__ == "__main__":
    unittest.main()
