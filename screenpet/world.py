"""Oyun dünyası: hayvan, ev, top, efektler ve aralarındaki etkileşimler."""

import pygame

from . import i18n, theme
from .assets import HOUSE_SIZE, PET_SIZE
from .ball import Ball
from .particles import ParticleSystem
from .pet import Pet

DOUBLE_CLICK_MS = 500


class House:
    def __init__(self, center):
        self.x, self.y = float(center[0]), float(center[1])
        self.scale = 1.0
        self.dragging = False

    @property
    def center(self):
        return int(self.x), int(self.y)

    @property
    def rect(self):
        size = round(HOUSE_SIZE * self.scale)
        r = pygame.Rect(0, 0, size, size)
        r.center = self.center
        return r

    def move_to(self, center):
        self.x, self.y = float(center[0]), float(center[1])

    def shift(self, dx, dy):
        self.x += dx
        self.y += dy


class World:
    def __init__(self, display, stats, pet_pos=None, house_pos=None):
        self.display = display
        primary = display.primary
        s = primary.scale
        default_pet = (primary.work.left + round(130 * s), primary.work.bottom - round(PET_SIZE * s / 2) - round(40 * s))
        default_house = (primary.work.right - round(130 * s), primary.work.bottom - round(HOUSE_SIZE * s / 2) - round(50 * s))
        self.pet = Pet(stats, self._restore(pet_pos, default_pet))
        self.house = House(self._restore(house_pos, default_house))
        self.ball = Ball()
        self.particles = ParticleSystem()
        self._last_house_click = -10_000
        self.clamp_all()

    def _restore(self, desktop_pos, fallback):
        if not desktop_pos:
            return fallback
        try:
            pos = self.display.from_desktop((int(desktop_pos[0]), int(desktop_pos[1])))
        except (TypeError, ValueError, IndexError):
            return fallback
        return pos if self.display.is_visible_point(pos) else fallback

    # --- Etkileşim arabirimi (Pet.update bunları kullanır) ----------------

    @property
    def house_rect(self):
        return self.house.rect

    @property
    def house_dragging(self):
        return self.house.dragging

    def on_ball_caught(self):
        self.particles.burst(self.pet.center, 18, self.pet.scale)
        self.ball.remove()
        self.pet.caught_ball()

    # --- Kullanıcı eylemleri ------------------------------------------------

    def feed(self):
        self.pet.feed()
        self.particles.burst(self.pet.center, 10, self.pet.scale)

    def spawn_ball(self, pos):
        self.ball.spawn(pos, self.display)

    def pet_clicked(self, now_ms):
        if self.pet.click(now_ms):
            self.particles.burst(self.pet.center, 15, self.pet.scale, theme.PARTICLE_BLUE)

    def house_clicked(self, now_ms):
        """Eve tıklama. Çift tıklamada hayvan eve gider ve yorgunsa uyur."""
        if now_ms - self._last_house_click < DOUBLE_CLICK_MS:
            self._last_house_click = -10_000
            self.pet.go_home(self.house.center, sleep=self.pet.energy < 95)
            return True
        self._last_house_click = now_ms
        return False

    # --- Güncelleme ---------------------------------------------------------

    def update(self, dt):
        self.house.scale = self.display.scale_at(self.house.center)
        self.pet.update(dt, self)
        self.ball.update(dt, self.display)
        self.particles.update(dt)

    def update_effects(self, dt):
        """Oyun duraklatılmışken sadece efektler."""
        self.particles.update(dt)

    def shift(self, dx, dy):
        """Pencere başlangıcı kaydığında nesnelerin masaüstündeki yeri korunur."""
        for obj in (self.pet, self.house, self.ball, self.particles):
            obj.shift(dx, dy)

    def clamp_all(self):
        """Görünür bir monitörün dışında kalan nesneleri en yakın monitöre taşır."""
        self.house.scale = self.display.scale_at(self.house.center)
        self.house.move_to(self.display.clamp_rect(self.house.rect).center)
        self.pet.scale = self.display.scale_at(self.pet.center)
        self.pet.move_to(self.display.clamp_rect(self.pet.rect).center)
        if self.ball.active and not self.display.is_visible_point(self.ball.center):
            self.ball.x, self.ball.y = self.display.clamp_rect(self.ball.rect).center

    def desktop_positions(self):
        return (list(self.display.to_desktop(self.pet.center)),
                list(self.display.to_desktop(self.house.center)))

    # --- Çizim ----------------------------------------------------------------

    def draw(self, surface, assets, pet_name, show_names):
        house = self.house
        house_img = assets.surface("house", house.scale)
        if house_img:
            surface.blit(house_img, house_img.get_rect(center=house.center))
        else:
            pygame.draw.rect(surface, (120, 180, 120), house.rect, border_radius=8)

        pet = self.pet
        key, flip = pet.sprite()
        img = assets.surface(key, pet.scale) or assets.surface("pet_idle", pet.scale)
        if img:
            if flip:
                img = pygame.transform.flip(img, True, False)
            surface.blit(img, img.get_rect(center=pet.center))
        else:
            pygame.draw.rect(surface, (230, 150, 60), pet.rect, border_radius=6)

        ball = self.ball
        if ball.active:
            ball_img = assets.surface("ball", ball.scale)
            if ball_img:
                rotated = pygame.transform.rotate(ball_img, -ball.angle)
                surface.blit(rotated, rotated.get_rect(center=ball.center))
            else:
                pygame.draw.circle(surface, (220, 90, 40), ball.center, int(ball.radius))

        self.particles.draw(surface)

        if show_names:
            self._label(surface, i18n.t("house"), house.rect, house.scale)
            self._label(surface, pet_name or i18n.t("pet"), pet.rect, pet.scale)
            if ball.active and not ball.dragging:
                self._label(surface, i18n.t("ball"), ball.rect, ball.scale)

    @staticmethod
    def _label(surface, text, rect, scale):
        label = theme.outlined_label(text, 13, scale)
        surface.blit(label, label.get_rect(midbottom=(rect.centerx, rect.top - round(2 * scale))))
