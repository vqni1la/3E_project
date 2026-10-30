#車体の位置・向き・速度・移動処理

import math
import pygame


class Car:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)

        self.angle = 0.0
        self.speed = 200.0
        self.turn_speed = 180.0

        self.width = 40
        self.height = 24
        self.color = (0, 100, 255)
        
        self.track_width = 24.0

    def update(self, dt, keys, screen_width, screen_height):
        # 手動操作：A/Dで旋回
        steering = 0

        if keys[pygame.K_a]:
            steering -= 1

        if keys[pygame.K_d]:
            steering += 1

        # W/Sで速度指令
        throttle = 0

        if keys[pygame.K_w]:
            throttle += 1

        if keys[pygame.K_s]:
            throttle -= 1

        self.update_ai(
            dt, steering, throttle,
            screen_width, screen_height
        )

    def update_ai(
        self, dt, steering, throttle,
        screen_width, screen_height
    ):
        # 操舵・速度指令を -1～1 に制限
        steering = max(-1.0, min(1.0, float(steering)))
        throttle = max(-1.0, min(1.0, float(throttle)))

        # 操舵量に応じて旋回
        self.angle += steering * self.turn_speed * dt
        self.angle %= 360

        # 進行方向へ移動
        rad = math.radians(self.angle)
        distance = throttle * self.speed * dt

        self.x += math.cos(rad) * distance
        self.y += math.sin(rad) * distance

        # 画面外に出ないように制限
        margin = math.hypot(self.width, self.height) / 2

        self.x = max(
            margin, min(screen_width - margin, self.x)
        )
        self.y = max(
            margin, min(screen_height - margin, self.y)
        )

    def draw(self, screen):
        car_surface = pygame.Surface(
            (self.width, self.height),
            pygame.SRCALPHA
        )

        pygame.draw.rect(
            car_surface,
            self.color,
            (0, 0, self.width, self.height)
        )

        rotated = pygame.transform.rotate(
            car_surface, -self.angle
        )

        rect = rotated.get_rect(
            center=(round(self.x), round(self.y))
        )

        screen.blit(rotated, rect)
