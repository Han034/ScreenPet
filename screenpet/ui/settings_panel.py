"""Ayarlar paneli: hayvan, ev, top, görseller ve oyun ayarları sekmeleri."""

import math

import pygame

from .. import __version__, i18n, theme
from ..assets import SPECS, TINTS
from .widgets import HitMap, bar, button, checkbox_button, fit_text, text

TABS = ("pet", "house", "ball", "assets", "game_settings")
PANEL_W, PANEL_H = 720, 470
NAME_MAX = 20
TOAST_MS = 2500


class SettingsPanel:
    def __init__(self, app):
        self.app = app
        self.visible = False
        self.tab = "pet"
        self.scale = 1.0
        self.rect = pygame.Rect(0, 0, PANEL_W, PANEL_H)
        self.hits = HitMap()
        self.editing_name = False
        self.name_buffer = ""
        self.scroll = 0
        self._content_h = 0
        self._view = None
        self._scrollbar = None
        self._handle = None
        self._dragging_handle = None
        self._toast = None
        self._name_rect = None

    # --- Açma/kapama ----------------------------------------------------------

    def open(self, monitor):
        self.visible = True
        self.scale = monitor.scale
        self.rect = pygame.Rect(0, 0, theme.s(PANEL_W, self.scale), theme.s(PANEL_H, self.scale))
        self.rect.center = monitor.work.center
        self.rect.clamp_ip(monitor.work)
        self.editing_name = False
        self.scroll = 0

    def close(self):
        self.visible = False
        self.editing_name = False
        self._dragging_handle = None
        self.hits.clear()

    def toast(self, message):
        self._toast = (message, pygame.time.get_ticks() + TOAST_MS)

    def set_tab(self, tab):
        if tab != self.tab:
            self.tab = tab
            self.scroll = 0
        self.editing_name = False

    # --- Olaylar --------------------------------------------------------------

    def handle_event(self, event):
        """Panel açıkken tüm fare ve klavye olaylarını tüketir (diğer nesnelere ulaşmaz)."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._handle and self._handle.collidepoint(event.pos):
                self._dragging_handle = event.pos[1] - self._handle.y
                return True
            was_editing = self.editing_name
            if not self.hits.click(event.pos) and was_editing:
                self.editing_name = False
            elif was_editing and self.editing_name and not self._name_hit(event.pos):
                self.editing_name = False
            return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._dragging_handle = None
            return True
        if event.type == pygame.MOUSEMOTION and self._dragging_handle is not None:
            self._drag_scroll(event.pos[1])
            return True
        if event.type == pygame.MOUSEWHEEL:
            if self.tab == "assets" and self._view and self._view.collidepoint(pygame.mouse.get_pos()):
                self._scroll_by(-event.y * theme.s(40, self.scale))
            return True
        if event.type == pygame.TEXTINPUT and self.editing_name:
            for ch in event.text:
                if ch.isprintable() and len(self.name_buffer) < NAME_MAX:
                    self.name_buffer += ch
            return True
        if event.type == pygame.KEYDOWN:
            if self.editing_name:
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self._commit_name()
                elif event.key == pygame.K_BACKSPACE:
                    self.name_buffer = self.name_buffer[:-1]
                elif event.key == pygame.K_ESCAPE:
                    self.editing_name = False
            elif event.key == pygame.K_ESCAPE:
                self.app.close_settings()
            return True
        return event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION)

    def _name_hit(self, pos):
        return self._name_rect is not None and self._name_rect.collidepoint(pos)

    def _start_name_edit(self):
        if self.editing_name:
            self._commit_name()
            return
        self.editing_name = True
        self.name_buffer = self.app.settings["pet_name"]

    def _commit_name(self):
        name = self.name_buffer.strip()
        self.editing_name = False
        if name:
            self.app.rename_pet(name)
            self.toast(i18n.t("name_updated", name=name))

    def _scroll_by(self, delta):
        view_h = self._view.height if self._view else 0
        self.scroll = max(0, min(self.scroll + delta, max(0, self._content_h - view_h)))

    def _drag_scroll(self, mouse_y):
        if not (self._scrollbar and self._handle):
            return
        track = self._scrollbar.height - self._handle.height
        if track <= 0:
            return
        ratio = (mouse_y - self._dragging_handle - self._scrollbar.y) / track
        max_scroll = max(0, self._content_h - self._view.height)
        self.scroll = max(0, min(max_scroll, ratio * max_scroll))

    # --- Çizim ----------------------------------------------------------------

    def draw(self, surface, mouse_pos):
        if not self.visible:
            return
        self.hits.clear()
        self._name_rect = None
        sc = self.scale
        radius = theme.s(14, sc)
        pygame.draw.rect(surface, theme.PANEL_BG, self.rect, border_radius=radius)

        tab_h = theme.s(42, sc)
        tabs_rect = pygame.Rect(self.rect.left, self.rect.top, self.rect.width, tab_h)
        pygame.draw.rect(surface, theme.PANEL_TABS_BG, tabs_rect,
                         border_top_left_radius=radius, border_top_right_radius=radius)
        close_w = theme.s(44, sc)
        tab_w = (self.rect.width - close_w) // len(TABS)
        tab_font = theme.font(14, sc, bold=True)
        for i, key in enumerate(TABS):
            r = pygame.Rect(self.rect.left + i * tab_w, self.rect.top, tab_w, tab_h)
            active = key == self.tab
            if active or r.collidepoint(mouse_pos):
                kwargs = {"border_top_left_radius": radius} if i == 0 else {}
                pygame.draw.rect(surface, theme.PANEL_TAB_ACTIVE if active else theme.PANEL_FIELD, r, **kwargs)
            color = theme.PANEL_TEXT if active else theme.PANEL_MUTED
            text(surface, fit_text(i18n.t(key), tab_font, tab_w - 8), tab_font, color, r.center, "center")
            self.hits.add(r, self.set_tab, key)

        close_rect = pygame.Rect(self.rect.right - close_w, self.rect.top, close_w, tab_h)
        hover = close_rect.collidepoint(mouse_pos)
        if hover:
            pygame.draw.rect(surface, theme.BUTTON_DANGER, close_rect, border_top_right_radius=radius)
        cx, cy, arm = close_rect.centerx, close_rect.centery, theme.s(7, sc)
        width = max(2, theme.s(2, sc))
        pygame.draw.line(surface, theme.PANEL_TEXT, (cx - arm, cy - arm), (cx + arm, cy + arm), width)
        pygame.draw.line(surface, theme.PANEL_TEXT, (cx - arm, cy + arm), (cx + arm, cy - arm), width)
        self.hits.add(close_rect, self.app.close_settings)

        content = pygame.Rect(self.rect.left, tabs_rect.bottom, self.rect.width, self.rect.height - tab_h)
        inner = content.inflate(-theme.s(48, sc), -theme.s(40, sc))
        getattr(self, f"_draw_{self.tab}")(surface, inner, mouse_pos)
        self._draw_toast(surface, content)

    def _draw_toast(self, surface, content):
        if not self._toast:
            return
        message, until = self._toast
        if pygame.time.get_ticks() > until:
            self._toast = None
            return
        sc = self.scale
        f = theme.font(13, sc)
        surf = f.render(message, True, theme.WHITE)
        box = surf.get_rect().inflate(theme.s(24, sc), theme.s(12, sc))
        box.midbottom = (content.centerx, content.bottom - theme.s(12, sc))
        pygame.draw.rect(surface, (30, 110, 70), box, border_radius=box.height // 2)
        surface.blit(surf, surf.get_rect(center=box.center))

    # --- Ortak parçalar -------------------------------------------------------

    def _preview(self, surface, rect, key, tint=None):
        sc = self.scale
        pygame.draw.rect(surface, theme.PANEL_FIELD, rect, border_radius=theme.s(10, sc))
        img = self.app.assets.thumbnail(key, rect.width - theme.s(16, sc), tint)
        if img:
            surface.blit(img, img.get_rect(center=rect.center))

    def _tint_row(self, surface, x, y, group, preview_key):
        sc = self.scale
        size = theme.s(52, sc)
        gap = theme.s(10, sc)
        current = self.app.settings[f"{group}_tint"]
        for name in TINTS[group]:
            r = pygame.Rect(x, y, size, size)
            pygame.draw.rect(surface, theme.PANEL_FIELD, r, border_radius=theme.s(8, sc))
            img = self.app.assets.thumbnail(preview_key, size - theme.s(10, sc), name)
            if img:
                surface.blit(img, img.get_rect(center=r.center))
            if name == current:
                pygame.draw.rect(surface, theme.PANEL_ACCENT, r, width=max(2, theme.s(3, sc)),
                                 border_radius=theme.s(8, sc))
            elif r.collidepoint(pygame.mouse.get_pos()):
                pygame.draw.rect(surface, theme.PANEL_MUTED, r, width=1, border_radius=theme.s(8, sc))
            self.hits.add(r, self.app.set_tint, group, name)
            x += size + gap
        return y + size

    def _section_label(self, surface, label, pos):
        return text(surface, label, theme.font(14, self.scale, bold=True), theme.PANEL_TEXT, pos)

    # --- Sekmeler -------------------------------------------------------------

    def _draw_pet(self, surface, area, mouse_pos):
        sc = self.scale
        preview = pygame.Rect(area.left, area.top, theme.s(130, sc), theme.s(130, sc))
        self._preview(surface, preview, "pet_idle")
        x = preview.right + theme.s(28, sc)
        y = area.top
        f = theme.font(15, sc)
        label_f = theme.font(14, sc, bold=True)
        label_w = theme.s(90, sc)

        # İsim
        text(surface, i18n.t("name"), label_f, theme.PANEL_TEXT, (x, y + theme.s(6, sc)))
        field = pygame.Rect(x + label_w, y, theme.s(220, sc), theme.s(32, sc))
        pygame.draw.rect(surface, theme.PANEL_FIELD, field, border_radius=theme.s(5, sc))
        if self.editing_name:
            pygame.draw.rect(surface, theme.PANEL_ACCENT, field, width=max(1, theme.s(1.5, sc)),
                             border_radius=theme.s(5, sc))
        shown = self.name_buffer if self.editing_name else self.app.settings["pet_name"]
        name_rect = text(surface, fit_text(shown, f, field.width - theme.s(16, sc)), f, theme.WHITE,
                         (field.left + theme.s(8, sc), field.centery), "midleft")
        if self.editing_name and (pygame.time.get_ticks() // 500) % 2 == 0:
            cx = name_rect.right + theme.s(2, sc)
            pygame.draw.line(surface, theme.WHITE, (cx, field.top + theme.s(7, sc)),
                             (cx, field.bottom - theme.s(7, sc)), max(1, theme.s(1, sc)))
        edit_rect = pygame.Rect(field.right + theme.s(8, sc), y, theme.s(90, sc), field.height)
        button(surface, edit_rect, i18n.t("save" if self.editing_name else "edit"), theme.font(13, sc),
               mouse_pos, radius=theme.s(5, sc))
        self._name_rect = field.union(edit_rect)
        self.hits.add(field, self._begin_edit_from_field)
        self.hits.add(edit_rect, self._start_name_edit)
        y = field.bottom + theme.s(14, sc)

        # Yaş
        text(surface, i18n.t("age"), label_f, theme.PANEL_TEXT, (x, y))
        text(surface, i18n.tn("age_value", self.app.settings.age_days()), f, theme.WHITE, (x + label_w, y))
        y += f.get_height() + theme.s(14, sc)

        # İstatistikler
        pet = self.app.world.pet
        bar_w = theme.s(310, sc)
        for key, value, color in (("happiness", pet.happiness, theme.BAR_HAPPINESS),
                                  ("hunger", pet.hunger, theme.BAR_HUNGER),
                                  ("sleep", pet.energy, theme.BAR_ENERGY)):
            text(surface, i18n.t(key), label_f, theme.PANEL_TEXT, (x, y))
            bar_rect = pygame.Rect(x + label_w, y + theme.s(5, sc), bar_w, theme.s(9, sc))
            bar(surface, bar_rect, value, color)
            text(surface, str(int(round(value))), theme.font(13, sc), theme.PANEL_MUTED,
                 (bar_rect.right + theme.s(10, sc), bar_rect.centery), "midleft")
            y += theme.s(26, sc)

        # Renk
        y = max(y, preview.bottom) + theme.s(18, sc)
        self._section_label(surface, i18n.t("color"), (area.left, y))
        self._tint_row(surface, area.left, y + theme.s(26, sc), "pet", "pet_idle")

    def _begin_edit_from_field(self):
        if not self.editing_name:
            self.editing_name = True
            self.name_buffer = self.app.settings["pet_name"]

    def _draw_object_tab(self, surface, area, group, key, info_key):
        sc = self.scale
        preview = pygame.Rect(area.left, area.top, theme.s(130, sc), theme.s(130, sc))
        self._preview(surface, preview, key)
        x = preview.right + theme.s(28, sc)
        self._section_label(surface, i18n.t("color"), (x, area.top))
        bottom = self._tint_row(surface, x, area.top + theme.s(28, sc), group, key)
        f = theme.font(13, sc)
        text(surface, i18n.t(info_key), f, theme.PANEL_MUTED, (x, bottom + theme.s(16, sc)))

    def _draw_house(self, surface, area, mouse_pos):
        self._draw_object_tab(surface, area, "house", "house", "house_info")

    def _draw_ball(self, surface, area, mouse_pos):
        self._draw_object_tab(surface, area, "ball", "ball", "ball_info")

    def _draw_assets(self, surface, area, mouse_pos):
        sc = self.scale
        bar_w = theme.s(10, sc)
        view = pygame.Rect(area.left, area.top, area.width - bar_w - theme.s(10, sc), area.height)
        self._view = view
        tile_w, tile_h = theme.s(104, sc), theme.s(158, sc)
        cols = max(1, (view.width + theme.s(12, sc)) // (tile_w + theme.s(12, sc)))
        gap_x = (view.width - cols * tile_w) // max(1, cols - 1) if cols > 1 else 0
        gap_y = theme.s(12, sc)
        rows = math.ceil(len(SPECS) / cols)
        self._content_h = rows * tile_h + (rows - 1) * gap_y
        self._scroll_by(0)

        label_f = theme.font(12, sc)
        btn_f = theme.font(12, sc)
        btn_h = theme.s(24, sc)
        assets = self.app.assets
        surface.set_clip(view)
        for i, spec in enumerate(SPECS):
            col, row = i % cols, i // cols
            tile = pygame.Rect(view.left + col * (tile_w + gap_x),
                               view.top + row * (tile_h + gap_y) - int(self.scroll), tile_w, tile_h)
            if not tile.colliderect(view):
                continue
            pygame.draw.rect(surface, theme.PANEL_FIELD, tile, border_radius=theme.s(8, sc))
            thumb_box = pygame.Rect(tile.left, tile.top + theme.s(6, sc), tile_w, theme.s(70, sc))
            img = assets.thumbnail(spec.key, theme.s(64, sc))
            if img:
                surface.blit(img, img.get_rect(center=thumb_box.center))
            name = fit_text(i18n.t(f"asset_{spec.key}"), label_f, tile_w - theme.s(8, sc))
            label_rect = text(surface, name, label_f, theme.PANEL_TEXT,
                              (tile.centerx, thumb_box.bottom + theme.s(4, sc)), "midtop")
            custom = assets.has_override(spec.key)
            if custom:
                pygame.draw.circle(surface, theme.PANEL_ACCENT,
                                   (tile.right - theme.s(10, sc), tile.top + theme.s(10, sc)), theme.s(4, sc))
            edit = pygame.Rect(tile.left + theme.s(8, sc), label_rect.bottom + theme.s(6, sc),
                               tile_w - theme.s(16, sc), btn_h)
            button(surface, edit, i18n.t("change"), btn_f, mouse_pos, radius=theme.s(4, sc))
            self._add_clipped(edit, view, self.app.choose_asset, spec.key)
            if custom:
                reset = edit.move(0, btn_h + theme.s(4, sc))
                button(surface, reset, i18n.t("reset"), btn_f, mouse_pos, bg=theme.PANEL_BG,
                       fg=theme.PANEL_TEXT, hover=theme.PANEL_TAB_ACTIVE, radius=theme.s(4, sc))
                self._add_clipped(reset, view, self.app.reset_asset, spec.key)
        surface.set_clip(None)

        self._scrollbar = self._handle = None
        if self._content_h > view.height:
            track = pygame.Rect(view.right + theme.s(10, sc), view.top, bar_w, view.height)
            pygame.draw.rect(surface, theme.PANEL_TABS_BG, track, border_radius=bar_w // 2)
            handle_h = max(theme.s(30, sc), round(view.height * view.height / self._content_h))
            max_scroll = self._content_h - view.height
            handle_y = track.top + round((track.height - handle_h) * self.scroll / max_scroll)
            handle = pygame.Rect(track.left, handle_y, bar_w, handle_h)
            pygame.draw.rect(surface, theme.PANEL_MUTED, handle, border_radius=bar_w // 2)
            self._scrollbar, self._handle = track, handle

    def _add_clipped(self, rect, view, action, *args):
        visible = rect.clip(view)
        if visible.width and visible.height:
            self.hits.add(visible, action, *args)

    def _draw_game_settings(self, surface, area, mouse_pos):
        sc = self.scale
        app = self.app
        f = theme.font(14, sc)
        col_w = (area.width - theme.s(24, sc)) // 2
        btn_h = theme.s(36, sc)
        gap = theme.s(10, sc)
        left_x, right_x = area.left, area.left + col_w + theme.s(24, sc)

        # Sol sütun: seçenekler
        y = area.top
        self._section_label(surface, i18n.t("options"), (left_x, y))
        y += theme.s(28, sc)
        r = checkbox_button(surface, (left_x, y, col_w, btn_h), i18n.t("show_names"),
                            app.settings["show_object_names"], f, mouse_pos, sc)
        self.hits.add(r, app.toggle_show_names)
        y += btn_h + theme.s(4, sc)
        hint_f = theme.font(12, sc)
        text(surface, fit_text(i18n.t("show_names_info"), hint_f, col_w), hint_f, theme.PANEL_MUTED, (left_x, y))
        y += hint_f.get_height() + gap
        r = checkbox_button(surface, (left_x, y, col_w, btn_h), i18n.t("start_with_windows"),
                            app.settings["start_with_windows"], f, mouse_pos, sc)
        self.hits.add(r, app.toggle_startup)
        y += btn_h + gap * 2

        self._section_label(surface, i18n.t("language_options"), (left_x, y))
        y += theme.s(28, sc)
        lang_w = (col_w - gap) // 2
        for i, (code, key) in enumerate((("tr", "turkish"), ("en", "english"))):
            r = pygame.Rect(left_x + i * (lang_w + gap), y, lang_w, btn_h)
            active = i18n.get_language() == code
            button(surface, r, i18n.t(key), f, mouse_pos, bg=theme.PANEL_ACCENT if active else theme.BUTTON_BG,
                   fg=theme.WHITE if active else theme.TEXT, radius=theme.s(5, sc))
            self.hits.add(r, app.set_language, code)

        # Sağ sütun: uygulama
        y = area.top
        self._section_label(surface, i18n.t("application"), (right_x, y))
        y += theme.s(28, sc)
        for key, action, danger in (("reset_settings", app.reset_settings, False),
                                    ("restart_app", app.restart, False),
                                    ("hide_app", app.hide, False),
                                    ("quit", app.quit, True)):
            r = pygame.Rect(right_x, y, col_w, btn_h)
            button(surface, r, i18n.t(key), f, mouse_pos, fg=theme.BUTTON_DANGER if danger else theme.TEXT,
                   radius=theme.s(5, sc))
            self.hits.add(r, action)
            y += btn_h + gap

        small = theme.font(12, sc)
        text(surface, i18n.t("tray_hint"), small, theme.PANEL_MUTED, (right_x, y + theme.s(2, sc)))
        text(surface, i18n.t("version", version=__version__), small, theme.PANEL_MUTED,
             (area.left, area.bottom), "bottomleft")
