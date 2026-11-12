"""Kalp/parıltı efektleri."""

import math
import random

import pygame

from . import theme


class Particle:
    def __init__(self, x, y, scale, color=None):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(60, 240) * scale
        self.x, self.y = x, y
        self.vx, self.vy = math.cos(angle) * speed, math.sin(angle) * speed
        self.size = random.uniform(4, 8) * scale
        self.shrink = 6 * scale
        self.color = color or random.choice(theme.PARTICLE_HEARTS)
        self.life = random.uniform(0.5, 0.85)

    @property
    def alive(self):
        return self.life > 0 and self.size >= 1

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        self.size -= self.shrink * dt

    def draw(self, surface):
        if self.alive:
            pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), int(self.size))


class ParticleSystem:
    def __init__(self):
        self.items = []

    def burst(self, pos, count, scale=1.0, color=None):
        self.items.extend(Particle(pos[0], pos[1], scale, color) for _ in range(count))

    def update(self, dt):
        for p in self.items:
            p.update(dt)
        self.items = [p for p in self.items if p.alive]

    def draw(self, surface):
        for p in self.items:
            p.draw(surface)

    def shift(self, dx, dy):
        for p in self.items:
            p.x += dx
            p.y += dy
