"""Renkler, yazı tipleri ve metin çizim yardımcıları."""

import pygame

# Şeffaflık anahtarı. Bu renkteki pikseller görünmez olur.
# Saf siyah (0, 0, 0) kullanılınca görsellerdeki siyah çizgiler delik gibi
# görünüyordu. Görsellerde neredeyse hiç geçmeyen bir renk seçildi.
KEY_COLOR = (1, 0, 1)
FALLBACK_BG = (225, 225, 225)  # Şeffaflık yoksa (Windows dışı) arka plan

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
TEXT = (40, 40, 40)
LABEL_FG = (255, 255, 255)
LABEL_OUTLINE = (30, 30, 30)

MENU_BG = (236, 236, 236)
MENU_BORDER = (150, 150, 150)
BUTTON_BG = (250, 250, 250)
BUTTON_HOVER = (214, 228, 250)
BUTTON_DANGER = (200, 60, 60)

PANEL_BG = (52, 52, 56)
PANEL_TABS_BG = (36, 36, 40)
PANEL_TAB_ACTIVE = (72, 72, 78)
PANEL_TEXT = (232, 232, 232)
PANEL_MUTED = (160, 160, 168)
PANEL_FIELD = (70, 70, 76)
PANEL_ACCENT = (110, 170, 255)

BAR_HAPPINESS = (240, 180, 60)
BAR_HUNGER = (110, 200, 110)
BAR_ENERGY = (110, 160, 240)
BAR_BG = (80, 80, 86)

PARTICLE_HEARTS = ((235, 70, 90), (255, 160, 190))
PARTICLE_BLUE = (100, 120, 255)

_FONT_NAMES = "segoeui,arial,dejavusans"
_font_cache = {}


def font(size, scale=1.0, bold=False):
    """Ölçeğe göre önbellekli yazı tipi. `size` mantıksal piksel."""
    px = max(8, round(size * scale))
    key = (px, bold)
    cached = _font_cache.get(key)
    if cached is None:
        try:
            cached = pygame.font.SysFont(_FONT_NAMES, px, bold=bold)
        except (pygame.error, OSError):
            cached = pygame.font.Font(None, round(px * 1.35))
        _font_cache[key] = cached
    return cached


def s(value, scale):
    """Mantıksal pikseli ölçeklenmiş tam sayıya çevirir."""
    return max(1, round(value * scale))


_label_cache = {}


def outlined_label(text, size, scale):
    """Masaüstünün her renginde okunabilen, kenarlıklı etiket."""
    key = (text, size, round(scale, 2))
    surf = _label_cache.get(key)
    if surf is None:
        f = font(size, scale, bold=True)
        fg = f.render(text, False, LABEL_FG)
        outline = f.render(text, False, LABEL_OUTLINE)
        w = max(1, round(scale))
        surf = pygame.Surface((fg.get_width() + 2 * w, fg.get_height() + 2 * w), pygame.SRCALPHA)
        for dx in (-w, 0, w):
            for dy in (-w, 0, w):
                if dx or dy:
                    surf.blit(outline, (w + dx, w + dy))
        surf.blit(fg, (w, w))
        if len(_label_cache) > 64:
            _label_cache.clear()
        _label_cache[key] = surf
    return surf
