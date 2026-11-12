"""Sistem tepsisi simgesi.

pystray kendi iş parçacığında çalışır. Menü eylemleri doğrudan oyun durumunu
değiştirmez, bir kuyruğa yazılır ve ana döngü bunları sırayla işler.
Menü metinleri her açılışta geçerli dilden okunur, dil değişince menü yenilenir.
"""

import queue
import threading

from . import APP_NAME, __version__, i18n

try:
    from PIL import Image
    from pystray import Icon, Menu, MenuItem
    HAS_TRAY = True
except Exception as e:  # pystray bazı ortamlarda içe aktarılırken farklı hatalar verir
    print(f"Tepsi simgesi kullanılamıyor: {e}")
    HAS_TRAY = False


class Tray:
    def __init__(self, icon_path):
        self.actions = queue.Queue()
        self._icon = None
        self._icon_path = icon_path
        self._ready = threading.Event()

    def start(self):
        if not HAS_TRAY:
            return False
        try:
            image = Image.open(self._icon_path)
        except OSError:
            image = Image.new("RGBA", (64, 64), (226, 135, 51, 255))
        menu = Menu(
            MenuItem(lambda _item: i18n.t("tray_show_hide"), self._post("toggle"), default=True),
            MenuItem(lambda _item: i18n.t("settings"), self._post("settings")),
            Menu.SEPARATOR,
            MenuItem(lambda _item: i18n.t("quit"), self._post("quit")),
        )
        self._icon = Icon(APP_NAME, image, self._title(), menu)
        threading.Thread(target=self._run, name="tray", daemon=True).start()
        return True

    def _run(self):
        try:
            self._icon.run(setup=self._setup)
        except Exception as e:
            print(f"Tepsi simgesi çalıştırılamadı: {e}")
            self._ready.set()

    def _setup(self, icon):
        icon.visible = True
        self._ready.set()

    def _post(self, action):
        return lambda _icon, _item: self.actions.put(action)

    @staticmethod
    def _title():
        return f"{APP_NAME} {__version__}"

    def poll(self):
        """Bekleyen menü eylemlerini döndürür (ana iş parçacığından çağrılır)."""
        items = []
        while True:
            try:
                items.append(self.actions.get_nowait())
            except queue.Empty:
                return items

    def refresh(self):
        """Dil değişince menüyü yeniden oluşturur."""
        if self._icon:
            try:
                self._icon.update_menu()
            except Exception as e:
                print(f"Tepsi menüsü yenilenemedi: {e}")

    def notify(self, message, title=APP_NAME):
        if self._icon and self._ready.wait(timeout=2):
            try:
                self._icon.notify(message, title)
            except Exception as e:
                print(f"Bildirim gösterilemedi: {e}")

    def stop(self):
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass
