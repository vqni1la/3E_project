#コース、壁、ゴールなどの管理

import pygame


class Environment:
    def __init__(self):
        # 画面サイズ
        self.width = 800
        self.height = 600

        # コースの外側と内側の境界
        self.outer_rect = pygame.Rect(50, 50, 700, 500)
        self.inner_rect = pygame.Rect(200, 150, 400, 300)

        # 色
        self.background_color = (40, 130, 40)
        self.road_color = (70, 70, 70)
        self.line_color = (240, 240, 240)

        # スタート地点
        self.start_x = 400
        self.start_y = 100
        self.start_angle = 0

    def is_on_track(self, x, y):
        # 外側の境界内、かつ内側の領域外ならコース上
        return (
            self.outer_rect.collidepoint(x, y)
            and not self.inner_rect.collidepoint(x, y)
        )

    def draw(self, screen):
        # 背景
        screen.fill(self.background_color)

        # 外側のコース領域
        pygame.draw.rect(
            screen,
            self.road_color,
            self.outer_rect
        )

        # 内側の芝生
        pygame.draw.rect(
            screen,
            self.background_color,
            self.inner_rect
        )

        # コースの境界線
        pygame.draw.rect(
            screen,
            self.line_color,
            self.outer_rect,
            3
        )

        pygame.draw.rect(
            screen,
            self.line_color,
            self.inner_rect,
            3
        )

        # スタートライン
        pygame.draw.line(
            screen,
            (255, 50, 50),
            (350, 80),
            (350, 120),
            4
        )
