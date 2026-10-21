#車体の位置・向き・速度・移動処理

import math
import pygame


class Car:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)

        # 車の向き（度）
        self.angle = 0.0

        self.speed = 200.0
        self.turn_speed = 180.0

        self.width = 40
        self.height = 24

        self.color = (0, 100, 255)

    def update(self, dt, keys, screen_width, screen_height):
        # A / D で旋回
        if keys[pygame.K_a]:
            self.angle -= self.turn_speed * dt

        if keys[pygame.K_d]:
            self.angle += self.turn_speed * dt

        # 角度を 0～360 度に収める
        self.angle %= 360

        # 度数法からラジアンに変換
        rad = math.radians(self.angle)

        # W / S で前進・後退
        move = 0

        if keys[pygame.K_w]:
            move += 1

        if keys[pygame.K_s]:
            move -= 1

        self.x += math.cos(rad) * self.speed * move * dt
        self.y += math.sin(rad) * self.speed * move * dt

        # 画面端から出ないようにする
        margin = math.hypot(self.width, self.height) / 2

        self.x = max(
            margin,
            min(screen_width - margin, self.x)
        )

        self.y = max(
            margin,
            min(screen_height - margin, self.y)
        )

    def draw(self, screen):
        # 車の画像に相当する四角形を作る
        car_surface = pygame.Surface(
            (self.width, self.height),
            pygame.SRCALPHA
        )

        pygame.draw.rect(
            car_surface,
            self.color,
            (0, 0, self.width, self.height)
        )

        # 車の向きに合わせて回転
        rotated = pygame.transform.rotate(
            car_surface,
            -self.angle
        )

        # 車の中心を (x, y) に合わせて描画
        rect = rotated.get_rect(
            center=(round(self.x), round(self.y))
        )

        screen.blit(rotated, rect)
