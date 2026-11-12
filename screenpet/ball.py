"""Top fiziği. Top bulunduğu monitörün zeminine düşer, kenarlardan seker.

Bitişik bir monitöre doğru giderse geçer, boşluğa doğru giderse kenardan seker.
"""

import math
from collections import deque

import pygame

from .assets import BALL_RADIUS

GRAVITY = 1800.0          # piksel/sn², %100 ölçekte
BOUNCE = -0.7             # dikey sekme
WALL_BOUNCE = -0.9        # yatay sekme
REST_SPEED = 90.0         # bu hızın altındaki dikey sekme durdurulur
ROLL_FRICTION = 0.9       # zeminde yuvarlanırken saniyede kaybedilen hız oranı
MAX_THROW = 2600.0


class Ball:
    def __init__(self):
        self.active = False
        self.dragging = False
        self.x = self.y = 0.0
        self.vx = self.vy = 0.0
        self.angle = 0.0
        self.scale = 1.0
        self._trail = deque(maxlen=6)  # fırlatma hızı için son fare konumları

    @property
    def radius(self):
        return BALL_RADIUS * self.scale

    @property
    def center(self):
        return int(self.x), int(self.y)

    @property
    def rect(self):
        r = self.radius
        return pygame.Rect(int(self.x - r), int(self.y - r), int(2 * r), int(2 * r))

    def spawn(self, pos, display):
        self.active = True
        self.x, self.y = pos
        self.vx = self.vy = 0.0
        self.angle = 0.0
        self.scale = display.scale_at(pos)

    def remove(self):
        self.active = False
        self.dragging = False
        self.vx = self.vy = 0.0

    # --- Sürükleme ve fırlatma --------------------------------------------

    def start_drag(self, now_ms):
        self.dragging = True
        self.vx = self.vy = 0.0
        self._trail.clear()
        self._trail.append((now_ms, self.x, self.y))

    def drag_to(self, pos, now_ms):
        self.x, self.y = pos
        self._trail.append((now_ms, self.x, self.y))

    def release(self, now_ms):
        self.dragging = False
        recent = [p for p in self._trail if now_ms - p[0] <= 120]
        if len(recent) >= 2:
            t0, x0, y0 = recent[0]
            t1, x1, y1 = recent[-1]
            elapsed = max(1, t1 - t0) / 1000.0
            vx, vy = (x1 - x0) / elapsed, (y1 - y0) / elapsed
            speed = math.hypot(vx, vy)
            limit = MAX_THROW * self.scale
            if speed > limit:
                vx, vy = vx * limit / speed, vy * limit / speed
            self.vx, self.vy = vx, vy
        self._trail.clear()

    # --- Fizik --------------------------------------------------------------

    def update(self, dt, display):
        if not self.active or self.dragging:
            if self.active:
                self.scale = display.scale_at(self.center)
            return
        monitor = display.nearest_monitor(self.center)
        self.scale = monitor.scale
        r = self.radius
        area = monitor.rect
        floor = monitor.work.bottom

        self.vy += GRAVITY * self.scale * dt
        self.x += self.vx * dt
        self.y += self.vy * dt

        if self.y + r > floor:
            self.y = floor - r
            self.vy = 0.0 if abs(self.vy) < REST_SPEED * self.scale else self.vy * BOUNCE
        elif self.y - r < area.top:
            self.y = area.top + r
            self.vy *= BOUNCE

        if self.x + r > area.right and not display.is_visible_point((self.x + r, self.y)):
            self.x = area.right - r
            self.vx *= WALL_BOUNCE
        elif self.x - r < area.left and not display.is_visible_point((self.x - r, self.y)):
            self.x = area.left + r
            self.vx *= WALL_BOUNCE

        on_floor = self.y + r >= floor - 1 and self.vy == 0.0
        if on_floor:
            self.vx *= max(0.0, 1.0 - ROLL_FRICTION * dt)
            if abs(self.vx) < 5 * self.scale:
                self.vx = 0.0

        # Yuvarlanma: kat edilen yol / yarıçap (radyan)
        self.angle = (self.angle + math.degrees(self.vx * dt / max(1.0, r))) % 360

    def shift(self, dx, dy):
        self.x += dx
        self.y += dy
