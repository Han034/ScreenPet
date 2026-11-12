"""Sağ tık menüleri: hayvanın durumu ve evin eylem menüsü."""

import pygame

from .. import i18n, theme
from .widgets import HitMap, bar, button, text


class Popup:
    def __init__(self):
        self.visible = False
        self.anchor = (0, 0)
        self.scale = 1.0
        self.rect = None
        self.hits = HitMap()

    def show(self, pos, scale):
        self.visible = True
        self.anchor = pos
        self.scale = scale
        self.rect = None

    def close(self):
        self.visible = False
        self.rect = None
        self.hits.clear()

    def click(self, pos):
        """Menü açıkken tıklama: içerideyse eylem, dışarıdaysa menüyü kapatır. Hep tüketir."""
        if not self.visible:
            return False
        if self.rect and self.rect.collidepoint(pos):
            self.hits.click(pos)
        else:
            self.close()
        return True

    def _place(self, width, height, display):
        """Menüyü imlecin yanına, bulunduğu monitörün dışına taşmayacak şekilde yerleştirir."""
        rect = pygame.Rect(self.anchor[0], self.anchor[1], width, height)
        return rect.clamp(display.nearest_monitor(self.anchor).work)


class PetMenu(Popup):
    def draw(self, surface, display, pet, mouse_pos):
        if not self.visible:
            return
        sc = self.scale
        pad = theme.s(12, sc)
        f = theme.font(14, sc)
        line = theme.s(36, sc)
        width = theme.s(200, sc)
        rows = (("happiness", pet.happiness, theme.BAR_HAPPINESS),
                ("hunger", pet.hunger, theme.BAR_HUNGER),
                ("sleep", pet.energy, theme.BAR_ENERGY))
        self.rect = self._place(width, pad * 2 + line * len(rows) - theme.s(6, sc), display)
        pygame.draw.rect(surface, theme.MENU_BG, self.rect, border_radius=theme.s(8, sc))
        pygame.draw.rect(surface, theme.MENU_BORDER, self.rect, width=1, border_radius=theme.s(8, sc))
        y = self.rect.top + pad
        for key, value, color in rows:
            label = f"{i18n.t(key)}"
            text(surface, label, f, theme.TEXT, (self.rect.left + pad, y))
            text(surface, str(int(round(value))), f, theme.TEXT, (self.rect.right - pad, y), "topright")
            bar_rect = pygame.Rect(self.rect.left + pad, y + f.get_height() + theme.s(2, sc),
                                   width - 2 * pad, theme.s(6, sc))
            bar(surface, bar_rect, value, color)
            y += line


class HouseMenu(Popup):
    def __init__(self, actions):
        super().__init__()
        # [(dil anahtarı, fonksiyon)]
        self.actions = actions

    def draw(self, surface, display, mouse_pos):
        if not self.visible:
            return
        self.hits.clear()
        sc = self.scale
        pad = theme.s(8, sc)
        gap = theme.s(4, sc)
        f = theme.font(14, sc)
        btn_h = f.get_height() + theme.s(10, sc)
        labels = [i18n.t(key) for key, _ in self.actions]
        btn_w = max(theme.s(150, sc), max(f.size(lbl)[0] for lbl in labels) + theme.s(28, sc))
        height = pad * 2 + btn_h * len(labels) + gap * (len(labels) - 1)
        self.rect = self._place(btn_w + 2 * pad, height, display)
        pygame.draw.rect(surface, theme.MENU_BG, self.rect, border_radius=theme.s(8, sc))
        pygame.draw.rect(surface, theme.MENU_BORDER, self.rect, width=1, border_radius=theme.s(8, sc))
        y = self.rect.top + pad
        for label, (key, action) in zip(labels, self.actions):
            rect = pygame.Rect(self.rect.left + pad, y, btn_w, btn_h)
            danger = key == "quit"
            button(surface, rect, label, f, mouse_pos,
                   fg=theme.BUTTON_DANGER if danger else theme.TEXT, radius=theme.s(4, sc))
            self.hits.add(rect, self._run, action)
            y += btn_h + gap

    def _run(self, action):
        self.close()
        action()
