"""Basit arayüz parçaları.

Arayüz her karede yeniden çizilir. Çizim sırasında tıklanabilir alanlar bir
HitMap'e kaydedilir, sonraki tıklama bu kayıtlardan çözülür.
"""

import pygame

from .. import theme


class HitMap:
    def __init__(self):
        self._items = []

    def clear(self):
        self._items = []

    def add(self, rect, action, *args):
        self._items.append((pygame.Rect(rect), action, args))

    def click(self, pos):
        """Üstteki (en son eklenen) alanın eylemini çalıştırır. Tıklandıysa True."""
        for rect, action, args in reversed(self._items):
            if rect.collidepoint(pos):
                action(*args)
                return True
        return False

    def hovering(self, pos):
        return any(rect.collidepoint(pos) for rect, _, _ in self._items)


def text(surface, value, font, color, pos, anchor="topleft"):
    surf = font.render(value, True, color)
    rect = surf.get_rect(**{anchor: pos})
    surface.blit(surf, rect)
    return rect


def fit_text(value, font, max_width):
    if font.size(value)[0] <= max_width:
        return value
    while value and font.size(value + "…")[0] > max_width:
        value = value[:-1]
    return value + "…"


def button(surface, rect, label, font, mouse_pos, *, bg=theme.BUTTON_BG, fg=theme.TEXT,
           hover=theme.BUTTON_HOVER, radius=4, border=None):
    rect = pygame.Rect(rect)
    color = hover if hover and rect.collidepoint(mouse_pos) else bg
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    if border:
        pygame.draw.rect(surface, border, rect, width=1, border_radius=radius)
    text(surface, fit_text(label, font, rect.width - 8), font, fg, rect.center, "center")
    return rect


def checkbox_button(surface, rect, label, checked, font, mouse_pos, scale):
    rect = button(surface, rect, "", font, mouse_pos)
    box = pygame.Rect(0, 0, theme.s(16, scale), theme.s(16, scale))
    box.midleft = (rect.left + theme.s(12, scale), rect.centery)
    pygame.draw.rect(surface, theme.TEXT, box, width=max(1, theme.s(1.5, scale)), border_radius=3)
    if checked:
        inner = box.inflate(-theme.s(6, scale), -theme.s(6, scale))
        pygame.draw.rect(surface, theme.PANEL_ACCENT, inner, border_radius=2)
    text(surface, label, font, theme.TEXT, (box.right + theme.s(10, scale), rect.centery), "midleft")
    return rect


def bar(surface, rect, value, color):
    rect = pygame.Rect(rect)
    pygame.draw.rect(surface, theme.BAR_BG, rect, border_radius=rect.height // 2)
    filled = rect.copy()
    filled.width = max(0, round(rect.width * max(0.0, min(100.0, value)) / 100))
    if filled.width:
        pygame.draw.rect(surface, color, filled, border_radius=rect.height // 2)
