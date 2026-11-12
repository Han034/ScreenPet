"""Hayvanın istatistikleri ve davranış durum makinesi."""

import math
import random
from collections import deque

import pygame

from .assets import PET_SIZE, WALK_KEYS

# --- Durumlar ---------------------------------------------------------------
IDLE = "idle"
WALKING = "walking"              # rastgele dolaşma
GOING_HOME = "going_home"
CHASING = "chasing"              # topun peşinde
TRIGGERED_LEFT = "triggered_left"
TRIGGERED_RIGHT = "triggered_right"
SIT_LEFT = "sit_left"
SIT_RIGHT = "sit_right"
BACK = "back"
SMILE = "smile"
KIPS = "kips"
SMILE2 = "smile2"
HAPPY = "happy"
SAD = "sad"
ANGRY = "angry"
SLEEPING = "sleeping"

SHORT_ACTIONS = (SMILE, KIPS, SMILE2)
POSES = (SIT_LEFT, SIT_RIGHT, BACK) + SHORT_ACTIONS
MOVING_STATES = (WALKING, GOING_HOME, CHASING)
BALL_INTEREST_STATES = (IDLE, WALKING) + POSES

# --- Süreler (ms) -------------------------------------------------------------
IDLE_ACTION_INTERVAL = 5000
SHORT_ACTION_DURATION = 1500
POSE_DURATION = 2500
SLEEP_IN_HOUSE_DELAY = 15000
TRIGGER_DURATION = 400
HAPPY_DURATION = 1000
ANGRY_DURATION = 3000
# Yürüme karesi zamana göre değil, alınan yola göre ilerler: hız değişse de
# (yürüme / kovalama / DPI ölçeği) ayaklar yerde kaymaz. Bir döngü (tüm kareler)
# yaklaşık bir gövde boyu yol demektir.
WALK_STRIDE = 0.75                     # bir döngüde alınan yol / hayvan boyu
MULTI_CLICK_INTERVAL = 600
MULTI_CLICK_COUNT = 3

# --- Hızlar (%100 ölçekte piksel/sn) ------------------------------------------
WALK_SPEED = 180.0
CHASE_SPEED = 145.0

# --- İstatistikler (puan/sn) --------------------------------------------------
# Eski sürümde açlık 17, mutluluk 33 dakikada bitiyordu. Şimdi saatler sürüyor.
HUNGER_DECAY = 100 / (6 * 3600)        # tok -> aç: ~6 saat
HAPPINESS_DECAY = 100 / (4 * 3600)     # mutlu -> mutsuz: ~4 saat
ENERGY_DECAY = 100 / (5 * 3600)        # dinç -> yorgun: ~5 saat
SLEEP_REGEN = 100 / (10 * 60)          # uykuda ~10 dakikada dolar
SLEEP_HUNGER_FACTOR = 0.5              # uyurken daha yavaş acıkır

FEED_HAPPINESS = 10
PET_HAPPINESS = 15                     # hızlı tıklama (sevme)
BALL_HAPPINESS = 12                    # top yakalama
BALL_ENERGY_COST = 3

HUNGRY_ANGRY = 20                      # açlık bunun altındaysa sinirli
UNHAPPY_ANGRY = 5
UNHAPPY_SAD = 10
TIRED = 15                             # enerji bunun altındaysa eve gidip uyur
SLEEPY = 80                            # evde beklerken bu enerjinin altındaysa uyur
TOO_TIRED_TO_PLAY = 20

# Uygulama kapalıyken geçen süre
OFFLINE_FACTOR = 0.25                  # kapalıyken istatistikler 4 kat yavaş düşer
OFFLINE_FLOOR = 25                     # kapalıyken bunun altına inmez


def apply_offline_time(stats, seconds):
    """Uygulama kapalıyken geçen süreyi istatistiklere yansıtır."""
    if seconds <= 0:
        return dict(stats)
    out = dict(stats)
    for name, rate in (("hunger", HUNGER_DECAY), ("happiness", HAPPINESS_DECAY)):
        value = out[name]
        if value > OFFLINE_FLOOR:
            out[name] = max(OFFLINE_FLOOR, value - rate * OFFLINE_FACTOR * seconds)
    out["energy"] = min(100.0, out["energy"] + SLEEP_REGEN * seconds)  # kapalıyken dinlendi
    return out


class Pet:
    def __init__(self, stats, center):
        self.happiness = float(stats.get("happiness", 100))
        self.hunger = float(stats.get("hunger", 100))
        self.energy = float(stats.get("energy", 100))
        self.x, self.y = float(center[0]), float(center[1])
        self.scale = 1.0
        self.state = IDLE
        self.direction = "right"
        self.timer = 0.0           # mevcut durumun kalan süresi (ms)
        self.idle_timer = 0.0
        self.house_timer = 0.0
        self.anim_timer = 0.0      # son kare değişiminden beri alınan yol (px)
        self.anim_index = 0
        self.last_step = 0.0
        self.target = None
        self.wants_sleep = False
        self.dragging = False
        self._clicks = deque(maxlen=MULTI_CLICK_COUNT + 1)

    # --- Geometri -------------------------------------------------------------

    @property
    def size(self):
        return max(4, round(PET_SIZE * self.scale))

    @property
    def center(self):
        return int(self.x), int(self.y)

    @property
    def rect(self):
        r = pygame.Rect(0, 0, self.size, self.size)
        r.center = self.center
        return r

    def move_to(self, center):
        self.x, self.y = float(center[0]), float(center[1])

    def shift(self, dx, dy):
        self.x += dx
        self.y += dy
        if self.target:
            self.target = (self.target[0] + dx, self.target[1] + dy)

    # --- İstatistikler --------------------------------------------------------

    def stats(self):
        return {"happiness": round(self.happiness, 2),
                "hunger": round(self.hunger, 2),
                "energy": round(self.energy, 2)}

    def _clamp_stats(self):
        self.happiness = max(0.0, min(100.0, self.happiness))
        self.hunger = max(0.0, min(100.0, self.hunger))
        self.energy = max(0.0, min(100.0, self.energy))

    def _decay(self, dt):
        if self.state == SLEEPING:
            self.energy += SLEEP_REGEN * dt
            self.hunger -= HUNGER_DECAY * SLEEP_HUNGER_FACTOR * dt
        elif not self.dragging:
            self.energy -= ENERGY_DECAY * dt
            self.hunger -= HUNGER_DECAY * dt
            self.happiness -= HAPPINESS_DECAY * dt
        self._clamp_stats()

    def mood(self):
        if self.hunger < HUNGRY_ANGRY or self.happiness < UNHAPPY_ANGRY:
            return ANGRY
        if self.happiness < UNHAPPY_SAD:
            return SAD
        return None

    # --- Dış etkileşimler -----------------------------------------------------

    def _set(self, state, duration=0.0):
        self.state = state
        self.timer = duration
        if state in MOVING_STATES:
            self.anim_index = 0
            self.anim_timer = 0.0
        if state not in MOVING_STATES:
            self.target = None
        if state != GOING_HOME:
            self.wants_sleep = False

    def feed(self):
        self.hunger = 100.0
        self.happiness = min(100.0, self.happiness + FEED_HAPPINESS)
        self._set(HAPPY, HAPPY_DURATION)

    def click(self, now_ms):
        """Sol tık. Hızlı art arda tıklama sevme sayılır, True döner."""
        self._clicks.append(now_ms)
        recent = [t for t in self._clicks if now_ms - t < MULTI_CLICK_INTERVAL]
        if len(recent) >= MULTI_CLICK_COUNT:
            self._clicks.clear()
            self.happiness = min(100.0, self.happiness + PET_HAPPINESS)
            self._set(HAPPY, HAPPY_DURATION)
            return True
        return False

    def start_drag(self):
        self.dragging = True
        if self.state != HAPPY:
            self._set(IDLE)

    def stop_drag(self):
        self.dragging = False
        if self.state != HAPPY:
            self._set(IDLE)

    def caught_ball(self):
        self.happiness = min(100.0, self.happiness + BALL_HAPPINESS)
        self.energy = max(0.0, self.energy - BALL_ENERGY_COST)
        self._set(HAPPY, HAPPY_DURATION)

    def go_home(self, house_center, sleep):
        self._set(GOING_HOME)
        self.target = house_center
        self.wants_sleep = sleep

    # --- Güncelleme -----------------------------------------------------------

    def update(self, dt, world):
        """dt saniye. `world`: display, house_rect, house_dragging, ball, on_ball_caught."""
        ms = dt * 1000.0
        self.scale = world.display.scale_at(self.center)
        self._decay(dt)
        if self.dragging:
            return

        house = world.house_rect
        moving = False

        if self.state == SLEEPING:
            if world.house_dragging:
                self._set(ANGRY, ANGRY_DURATION)
            elif self.energy >= 100:
                self._set(IDLE)
            return

        mood = self.mood()
        if self.energy < TIRED and self.state != GOING_HOME:
            self.go_home(house.center, sleep=True)
        elif mood and self.state not in (HAPPY, GOING_HOME):
            if self.state != mood:
                self._set(mood)
            return
        elif self.state in (ANGRY, SAD):
            self.timer -= ms
            if self.timer <= 0:
                self._set(IDLE)
            return

        if self._wants_ball(world.ball):
            self._spot_ball(world.ball)

        state = self.state
        if state in (WALKING, GOING_HOME):
            if state == GOING_HOME:
                self.target = house.center
            moving, arrived = self._step_towards(self.target, WALK_SPEED, dt)
            if arrived:
                if state == GOING_HOME and self.wants_sleep and house.collidepoint(self.center):
                    self._set(SLEEPING)
                else:
                    self._set(IDLE)
        elif state in (TRIGGERED_LEFT, TRIGGERED_RIGHT):
            self.timer -= ms
            if self.timer <= 0:
                self._set(CHASING)
        elif state == CHASING:
            ball = world.ball
            if not ball.active:
                self._set(IDLE)
            else:
                self.target = ball.center
                reach = self.size / 2 + ball.radius + 5 * self.scale
                dist = math.hypot(ball.x - self.x, ball.y - self.y)
                if dist > reach + 0.5:
                    moving, _ = self._step_towards(self.target, CHASE_SPEED, dt, stop_at=reach)
                elif not ball.dragging:
                    world.on_ball_caught()
                else:
                    self._face(ball.x)
        elif state == HAPPY:
            self.timer -= ms
            if self.timer <= 0:
                self._set(IDLE)
        elif state in POSES:
            self.timer -= ms
            if self.timer <= 0:
                self._set(IDLE)
        elif state == IDLE:
            self._idle(ms, world)

        if moving and WALK_KEYS:
            self.anim_timer += self.last_step
            per_frame = WALK_STRIDE * self.size / len(WALK_KEYS)
            while self.anim_timer >= per_frame:
                self.anim_timer -= per_frame
                self.anim_index = (self.anim_index + 1) % len(WALK_KEYS)

    def _wants_ball(self, ball):
        return (ball.active and self.state in BALL_INTEREST_STATES
                and self.energy >= TOO_TIRED_TO_PLAY)

    def _spot_ball(self, ball):
        self._face(ball.x)
        self._set(TRIGGERED_RIGHT if self.direction == "right" else TRIGGERED_LEFT, TRIGGER_DURATION)
        self.target = ball.center

    def _face(self, target_x):
        if target_x > self.x + 1:
            self.direction = "right"
        elif target_x < self.x - 1:
            self.direction = "left"

    def _step_towards(self, target, speed, dt, stop_at=0.0):
        """Hedefe doğru bir adım. (hareket etti mi, vardı mı) döner."""
        if not target:
            return False, True
        dx, dy = target[0] - self.x, target[1] - self.y
        dist = math.hypot(dx, dy)
        step = speed * self.scale * dt
        if dist - stop_at <= step or dist == 0:
            if dist > stop_at:
                # Durma noktasına tam yerleş (hedefe stop_at uzaklıkta)
                ratio = (dist - stop_at) / dist
                self.x += dx * ratio
                self.y += dy * ratio
                self._face(target[0])
            return False, True
        self.x += dx / dist * step
        self.y += dy / dist * step
        self.last_step = step
        self._face(target[0])
        return True, False

    def _idle(self, ms, world):
        house = world.house_rect
        in_house = house.collidepoint(self.center)
        self.idle_timer += ms
        if in_house:
            self.house_timer += ms
            if self.house_timer >= SLEEP_IN_HOUSE_DELAY and self.energy < SLEEPY:
                self.house_timer = 0.0
                self._set(SLEEPING)
                return
        else:
            self.house_timer = 0.0

        if self.idle_timer < IDLE_ACTION_INTERVAL:
            return
        self.idle_timer = 0.0
        if not in_house and random.random() < 0.3:
            self._set(WALKING)
            self.target = self._wander_target(world.display)
        else:
            action = random.choice(POSES + (IDLE,))
            if action != IDLE:
                self._set(action, SHORT_ACTION_DURATION if action in SHORT_ACTIONS else POSE_DURATION)

    def _wander_target(self, display):
        current = display.nearest_monitor(self.center)
        others = [m for m in display.monitors if m is not current]
        monitor = random.choice(others) if others and random.random() < 0.15 else current
        work = monitor.work
        half = round(PET_SIZE * monitor.scale) // 2
        x = random.randint(work.left + half, max(work.left + half, work.right - half))
        y = random.randint(work.centery, max(work.centery, work.bottom - half))
        return x, y

    # --- Çizim için -----------------------------------------------------------

    def sprite(self):
        """(görsel anahtarı, yatay çevir) döner."""
        state = self.state
        if state in MOVING_STATES and WALK_KEYS:
            return WALK_KEYS[self.anim_index % len(WALK_KEYS)], self.direction == "left"
        fixed = {
            SLEEPING: "pet_sleep", SIT_LEFT: "pet_sit_left", SIT_RIGHT: "pet_sit_right",
            BACK: "pet_back", TRIGGERED_LEFT: "pet_trigger_left", TRIGGERED_RIGHT: "pet_trigger_right",
        }
        if state in fixed:
            return fixed[state], False
        flippable = {
            ANGRY: "pet_angry", SAD: "pet_sad", HAPPY: "pet_happy",
            SMILE: "pet_smile", KIPS: "pet_kips", SMILE2: "pet_smile2",
        }
        return flippable.get(state, "pet_idle"), self.direction == "left"
