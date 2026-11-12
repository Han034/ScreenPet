"""Uygulama: başlatma, ana döngü, olay yönlendirme ve kullanıcı eylemleri."""

import os
import subprocess
import sys
import time
import traceback

import pygame

from . import APP_NAME, __version__, i18n, paths, winapi
from .assets import SUPPORTED_IMAGE_TYPES, TINTS, AssetStore
from .display import Display
from .pet import apply_offline_time
from .settings import Settings
from .tray import Tray
from .ui.menus import HouseMenu, PetMenu
from .ui.settings_panel import SettingsPanel
from .world import World

FPS = 60
HIDDEN_FPS = 10
MAX_DT = 0.1
AUTOSAVE_SECONDS = 30
DISPLAY_CHECK_SECONDS = 2


class App:
    def __init__(self):
        winapi.enable_dpi_awareness()
        i18n.load()
        self.settings = Settings(paths.settings_path())
        i18n.set_language(self.settings["language"])

        pygame.init()
        pygame.display.set_caption(i18n.t("app_title"))
        try:
            pygame.display.set_icon(pygame.image.load(paths.icon_path()))
        except (pygame.error, FileNotFoundError):
            pass
        self.display = Display()
        self.display.create()
        pygame.key.start_text_input()

        self.assets = AssetStore({group: self.settings[f"{group}_tint"] for group in TINTS})
        last_seen = self.settings["last_seen"]
        offline = time.time() - last_seen if isinstance(last_seen, (int, float)) else 0
        stats = apply_offline_time(self.settings["stats"], offline)
        self.world = World(self.display, stats, self.settings["pet_pos"], self.settings["house_pos"])

        self.pet_menu = PetMenu()
        self.house_menu = HouseMenu([
            ("get_ball", self.spawn_ball),
            ("feed", self.world.feed),
            ("settings", self.open_settings),
            ("hide_app", self.hide),
            ("quit", self.quit),
        ])
        self.panel = SettingsPanel(self)

        self.tray = Tray(paths.icon_path())
        self.has_tray = self.tray.start()
        self._sync_startup()

        self.running = True
        self.clock = pygame.time.Clock()
        self._drag = None
        self._drag_offset = (0, 0)
        self._hide_hint_shown = False
        self._restart_requested = False
        self._last_save = time.monotonic()
        self._last_display_check = time.monotonic()
        self.save()

    # --- Ana döngü ------------------------------------------------------------

    def run(self):
        while self.running:
            dt = min(MAX_DT, self.clock.tick(FPS if self.display.visible else HIDDEN_FPS) / 1000.0)
            for action in self.tray.poll():
                self._tray_action(action)
            for event in pygame.event.get():
                self._handle(event)
            if not self.running:
                break

            if self.panel.visible:
                self.world.update_effects(dt)
            else:
                self.world.update(dt)

            self._periodic()
            if self.display.visible:
                self._draw()

    def shutdown(self):
        self.save()
        self.tray.stop()
        pygame.quit()
        if self._restart_requested:
            self._spawn_new_instance()

    def _periodic(self):
        now = time.monotonic()
        if now - self._last_display_check >= DISPLAY_CHECK_SECONDS:
            self._last_display_check = now
            shift = self.display.refresh()
            if shift is not None:
                self.world.shift(*shift)
                self.world.clamp_all()
                self.pet_menu.close()
                self.house_menu.close()
                if self.panel.visible:
                    self.panel.open(self.display.nearest_monitor(self.panel.rect.center))
        if now - self._last_save >= AUTOSAVE_SECONDS:
            self.save()

    def _draw(self):
        screen = self.display.screen
        mouse = pygame.mouse.get_pos()
        screen.fill(self.display.background)
        self.world.draw(screen, self.assets, self.settings["pet_name"], self.settings["show_object_names"])
        if not self.panel.visible:
            self.pet_menu.draw(screen, self.display, self.world.pet, mouse)
            self.house_menu.draw(screen, self.display, mouse)
        self.panel.draw(screen, mouse)
        pygame.display.flip()

    # --- Olaylar --------------------------------------------------------------

    def _handle(self, event):
        if event.type == pygame.QUIT:
            # Alt+F4 uygulamayı kapatmaz, gizler. Tepsi yoksa geri getirilemeyeceği için kapatır.
            if self.has_tray:
                self.hide()
            else:
                self.quit()
            return
        if event.type == pygame.WINDOWFOCUSLOST:
            self.pet_menu.close()
            self.house_menu.close()
            self._end_drag(pygame.time.get_ticks())
        if self.panel.visible:
            self.panel.handle_event(event)
            return

        now = pygame.time.get_ticks()
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if self.pet_menu.click(event.pos) or self.house_menu.click(event.pos):
                    return
                self._press(event.pos, now)
            elif event.button == 3:
                self._context_menu(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._end_drag(now)
        elif event.type == pygame.MOUSEMOTION and self._drag:
            self._drag_to(event.pos, now)
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.pet_menu.close()
            self.house_menu.close()

    def _press(self, pos, now):
        world = self.world
        ball, pet, house = world.ball, world.pet, world.house
        if ball.active and ball.rect.collidepoint(pos):
            self._begin_drag("ball", pos, ball.center)
            ball.start_drag(now)
        elif pet.rect.collidepoint(pos):
            world.pet_clicked(now)
            pet.start_drag()
            self._begin_drag("pet", pos, pet.center)
        elif house.rect.collidepoint(pos):
            world.house_clicked(now)
            house.dragging = True
            self._begin_drag("house", pos, house.center)

    def _begin_drag(self, kind, pos, center):
        self._drag = kind
        self._drag_offset = (center[0] - pos[0], center[1] - pos[1])

    def _drag_to(self, pos, now):
        target = (pos[0] + self._drag_offset[0], pos[1] + self._drag_offset[1])
        if self._drag == "pet":
            self.world.pet.move_to(target)
        elif self._drag == "house":
            self.world.house.move_to(target)
        elif self._drag == "ball":
            self.world.ball.drag_to(target, now)

    def _end_drag(self, now):
        kind, self._drag = self._drag, None
        world = self.world
        if kind == "pet":
            world.pet.stop_drag()
        elif kind == "house":
            world.house.dragging = False
        elif kind == "ball":
            world.ball.release(now)
        if kind:
            world.clamp_all()

    def _context_menu(self, pos):
        self.pet_menu.close()
        self.house_menu.close()
        scale = self.display.scale_at(pos)
        if self.world.pet.rect.collidepoint(pos):
            self.pet_menu.show(pos, scale)
        elif self.world.house.rect.collidepoint(pos):
            self.house_menu.show(pos, scale)

    def _tray_action(self, action):
        if action == "toggle":
            if self.display.visible:
                self.hide()
            else:
                self.show()
        elif action == "settings":
            self.show()
            self.open_settings()
        elif action == "quit":
            self.quit()

    # --- Kayıt ----------------------------------------------------------------

    def save(self):
        pet_pos, house_pos = self.world.desktop_positions()
        self.settings["stats"] = self.world.pet.stats()
        self.settings["pet_pos"] = pet_pos
        self.settings["house_pos"] = house_pos
        self.settings.save()
        self._last_save = time.monotonic()

    def _sync_startup(self):
        """Windows ile başlatma açıksa ve kayıt eksik ya da artık var olmayan bir dosyayı gösteriyorsa
        (EXE taşınmış olabilir) kaydı bu kopyaya yönlendirir. Çalışan başka bir kopyanın kaydını ezmez."""
        if not self.settings["start_with_windows"]:
            return
        entry = winapi.startup_entry()
        target = entry.split('"')[1] if entry and entry.startswith('"') else (entry or "").split(" ")[0]
        if not entry or not os.path.exists(target):
            winapi.set_startup(True)

    # --- Kullanıcı eylemleri --------------------------------------------------

    def spawn_ball(self):
        self.world.spawn_ball(pygame.mouse.get_pos())

    def show(self):
        if not self.display.visible:
            self.display.set_visible(True)

    def hide(self):
        self.pet_menu.close()
        self.house_menu.close()
        self.panel.close()
        self._end_drag(pygame.time.get_ticks())
        self.display.set_visible(False)
        if not self._hide_hint_shown:
            self._hide_hint_shown = True
            self.tray.notify(i18n.t("hidden_hint"), i18n.t("hidden_title"))

    def quit(self):
        self.running = False

    def restart(self):
        self._restart_requested = True
        self.running = False

    def _spawn_new_instance(self):
        env = dict(os.environ)
        try:
            if paths.is_frozen():
                # PyInstaller'ın yeni sürecin kendi geçici klasörünü açmasını sağlar.
                env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
                subprocess.Popen([sys.executable], env=env, close_fds=True)
            else:
                subprocess.Popen([sys.executable, os.path.join(paths.app_dir(), "start.py")],
                                 env=env, close_fds=True)
        except OSError as e:
            winapi.message_box(APP_NAME, i18n.t("restart_failed", e=e), error=True)

    def open_settings(self):
        self.pet_menu.close()
        self.house_menu.close()
        self.panel.open(self.display.nearest_monitor(pygame.mouse.get_pos()))

    def close_settings(self):
        self.panel.close()

    def rename_pet(self, name):
        self.settings["pet_name"] = name
        self.settings.save()

    def set_language(self, code):
        if code == i18n.get_language():
            return
        self.settings["language"] = code
        i18n.set_language(code)
        pygame.display.set_caption(i18n.t("app_title"))
        self.tray.refresh()
        self.settings.save()

    def set_tint(self, group, name):
        self.settings[f"{group}_tint"] = name
        self.assets.set_tint(group, name)
        self.settings.save()

    def toggle_show_names(self):
        self.settings["show_object_names"] = not self.settings["show_object_names"]
        self.settings.save()

    def toggle_startup(self):
        enable = not self.settings["start_with_windows"]
        if winapi.set_startup(enable):
            self.settings["start_with_windows"] = enable
            self.settings.save()
            self.panel.toast(i18n.t("start_win_enabled" if enable else "start_win_disabled"))
        else:
            self.panel.toast(i18n.t("start_win_failed"))

    def reset_settings(self):
        had_startup = self.settings["start_with_windows"]
        self.settings.reset_preferences()
        if had_startup and not self.settings["start_with_windows"]:
            winapi.set_startup(False)
        i18n.set_language(self.settings["language"])
        for group in TINTS:
            self.assets.set_tint(group, self.settings[f"{group}_tint"])
        pygame.display.set_caption(i18n.t("app_title"))
        self.tray.refresh()
        self.settings.save()
        self.panel.toast(i18n.t("settings_reset"))

    def choose_asset(self, key):
        path = _open_file_dialog(i18n.t("choose_image", name=i18n.t(f"asset_{key}")))
        self.clock.tick()  # Pencere açıkken geçen süre bir sonraki karede sıçramaya yol açmasın.
        if not path:
            return
        if self.assets.replace(key, path):
            self.panel.toast(i18n.t("image_updated"))
        else:
            self.panel.toast(i18n.t("image_invalid"))

    def reset_asset(self, key):
        if self.assets.reset(key):
            self.panel.toast(i18n.t("image_reset"))


def _open_file_dialog(title):
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        winapi.message_box(APP_NAME, i18n.t("tkinter_missing", folder=os.path.join(paths.data_dir(), "Assets")))
        return None
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askopenfilename(parent=root, title=title, filetypes=SUPPORTED_IMAGE_TYPES)
        root.destroy()
        return path or None
    except tk.TclError as e:
        print(f"Dosya seçme penceresi açılamadı: {e}")
        return None


def _redirect_output():
    """Paketlenmiş (konsolsuz) sürümde çıktıları bir günlük dosyasına yazar."""
    if paths.is_frozen() or sys.stdout is None:
        try:
            log = open(os.path.join(paths.data_dir(), "screenpet.log"), "w", encoding="utf-8", buffering=1)
            sys.stdout = sys.stderr = log
        except OSError:
            pass


def main():
    _redirect_output()
    print(f"{APP_NAME} {__version__}")
    app = None
    try:
        app = App()
        app.run()
    except Exception:
        details = traceback.format_exc()
        print(details)
        winapi.message_box(APP_NAME, details[-1500:], error=True)
    finally:
        if app is not None:
            app.shutdown()
        else:
            pygame.quit()
