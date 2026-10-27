#コース、壁、ゴールなどの管理

import pygame


class Environment:
    def __init__(self):
        self.width = 800
        self.height = 600

        self.outer_rect = pygame.Rect(50, 50, 700, 500)
        self.inner_rect = pygame.Rect(200, 150, 400, 300)

        self.background_color = (40, 130, 40)
        self.road_color = (70, 70, 70)
        self.line_color = (240, 240, 240)

        self.start_x = 400
        self.start_y = 100
        self.start_angle = 0

        # コースの中央を通る経路
        self.left = 125
        self.right = 675
        self.top = 100
        self.bottom = 500

        self.top_length = self.right - self.left
        self.side_length = self.bottom - self.top

        self.track_length = (
            2 * self.top_length + 2 * self.side_length
        )

        # スタート地点の経路上の位置
        self.start_progress = self.start_x - self.left

    def is_on_track(self, x, y):
        return (
            self.outer_rect.collidepoint(x, y)
            and not self.inner_rect.collidepoint(x, y)
        )

    def get_track_progress(self, x, y):
        """コース上の位置をスタート地点基準の距離に変換する。"""

        # 各辺への距離を計算し、最も近い辺を選ぶ
        candidates = []

        # 上辺：左から右へ
        px = max(self.left, min(self.right, x))
        candidates.append((
            (x - px) ** 2 + (y - self.top) ** 2,
            px - self.left,
        ))

        # 右辺：上から下へ
        py = max(self.top, min(self.bottom, y))
        candidates.append((
            (x - self.right) ** 2 + (y - py) ** 2,
            self.top_length + py - self.top,
        ))

        # 下辺：右から左へ
        px = max(self.left, min(self.right, x))
        candidates.append((
            (x - px) ** 2 + (y - self.bottom) ** 2,
            self.top_length + self.side_length
            + self.right - px,
        ))

        # 左辺：下から上へ
        py = max(self.top, min(self.bottom, y))
        candidates.append((
            (x - self.left) ** 2 + (y - py) ** 2,
            2 * self.top_length + self.side_length
            + self.bottom - py,
        ))

        _, position = min(candidates, key=lambda item: item[0])

        # スタート地点からの進捗に変換
        return (
            position - self.start_progress
        ) % self.track_length

    def draw(self, screen):
        screen.fill(self.background_color)

        pygame.draw.rect(
            screen, self.road_color, self.outer_rect
        )
        pygame.draw.rect(
            screen, self.background_color, self.inner_rect
        )

        pygame.draw.rect(
            screen, self.line_color, self.outer_rect, 3
        )
        pygame.draw.rect(
            screen, self.line_color, self.inner_rect, 3
        )

        pygame.draw.line(
            screen,
            (255, 50, 50),
            (350, 80),
            (350, 120),
            4,
        )
