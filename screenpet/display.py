"""Tüm monitörleri kaplayan şeffaf pencere ve monitör geometrisi.

Pencere sanal ekranın (tüm monitörlerin birleşimi) tamamını kaplar. Oyun
koordinatları pencere koordinatıdır: masaüstü koordinatı - pencere başlangıcı.
"""

import os
from dataclasses import dataclass

import pygame

from . import theme, winapi


@dataclass
class Monitor:
    rect: pygame.Rect      # pencere koordinatında monitör alanı
    work: pygame.Rect      # görev çubuğu hariç alan
    scale: float           # DPI ölçeği (1.0 = %100)
    primary: bool


class Display:
    def __init__(self):
        self.origin = (0, 0)
        self.size = (800, 600)
        self.monitors = []
        self.screen = None
        self.hwnd = None
        self.overlay = False
        self.visible = True

    # --- Kurulum -----------------------------------------------------------

    def create(self):
        bounds = self._query_bounds()
        x, y, w, h = bounds
        os.environ["SDL_VIDEO_WINDOW_POS"] = f"{x},{y}"
        try:
            self.screen = pygame.display.set_mode((w, h), pygame.NOFRAME)
        except pygame.error as e:
            print(f"Çerçevesiz pencere açılamadı ({e}), normal pencere kullanılıyor.")
            bounds = (0, 0, 800, 600)
            self.screen = pygame.display.set_mode(bounds[2:])
        self._apply_bounds(bounds)
        try:
            self.hwnd = pygame.display.get_wm_info().get("window")
        except pygame.error:
            self.hwnd = None
        self.overlay = winapi.make_overlay(self.hwnd, theme.KEY_COLOR, bounds)
        self._load_monitors()

    @property
    def background(self):
        return theme.KEY_COLOR if self.overlay else theme.FALLBACK_BG

    def _query_bounds(self):
        vs = winapi.virtual_screen()
        if vs:
            return vs
        info = pygame.display.Info()
        return 0, 0, info.current_w, info.current_h

    def _apply_bounds(self, bounds):
        x, y, w, h = bounds
        self.origin = (x, y)
        self.size = (w, h)

    def _load_monitors(self):
        ox, oy = self.origin
        result = []
        for m in winapi.monitors():
            l, t, r, b = m["rect"]
            wl, wt, wr, wb = m["work"]
            result.append(Monitor(
                rect=pygame.Rect(l - ox, t - oy, r - l, b - t),
                work=pygame.Rect(wl - ox, wt - oy, wr - wl, wb - wt),
                scale=m["scale"],
                primary=m["primary"],
            ))
        if not result:
            full = pygame.Rect(0, 0, *self.size)
            result = [Monitor(full, full.copy(), winapi.system_scale(), True)]
        result.sort(key=lambda mon: not mon.primary)
        self.monitors = result

    def refresh(self):
        """Monitör eklendi/çıkarıldı ya da çözünürlük değiştiyse pencereyi yeniden boyutlandırır.

        Pencere başlangıcı değiştiyse (dx, dy) kayması döner, değişmediyse None.
        """
        if not self.overlay:
            return None
        bounds = self._query_bounds()
        old_origin = self.origin
        old_monitors = [(m.rect, m.work, m.scale) for m in self.monitors]
        if bounds != (*self.origin, *self.size):
            x, y, w, h = bounds
            os.environ["SDL_VIDEO_WINDOW_POS"] = f"{x},{y}"
            self.screen = pygame.display.set_mode((w, h), pygame.NOFRAME)
            self._apply_bounds(bounds)
            self.overlay = winapi.make_overlay(self.hwnd, theme.KEY_COLOR, bounds)
        self._load_monitors()
        if old_monitors == [(m.rect, m.work, m.scale) for m in self.monitors] and old_origin == self.origin:
            return None
        return old_origin[0] - self.origin[0], old_origin[1] - self.origin[1]

    def set_visible(self, visible):
        self.visible = visible
        winapi.show_window(self.hwnd, visible)

    # --- Koordinat yardımcıları ---------------------------------------------

    @property
    def primary(self):
        return self.monitors[0]

    def to_desktop(self, pos):
        return pos[0] + self.origin[0], pos[1] + self.origin[1]

    def from_desktop(self, pos):
        return pos[0] - self.origin[0], pos[1] - self.origin[1]

    def monitor_at(self, pos):
        for m in self.monitors:
            if m.rect.collidepoint(pos):
                return m
        return None

    def nearest_monitor(self, pos):
        found = self.monitor_at(pos)
        if found:
            return found
        x, y = pos

        def distance(m):
            cx = min(max(x, m.rect.left), m.rect.right - 1)
            cy = min(max(y, m.rect.top), m.rect.bottom - 1)
            return (cx - x) ** 2 + (cy - y) ** 2

        return min(self.monitors, key=distance)

    def scale_at(self, pos):
        return self.nearest_monitor(pos).scale

    def is_visible_point(self, pos):
        return self.monitor_at(pos) is not None

    def clamp_rect(self, rect):
        """Dikdörtgeni merkezine en yakın monitörün çalışma alanına sığdırır."""
        work = self.nearest_monitor(rect.center).work
        return rect.clamp(work)
