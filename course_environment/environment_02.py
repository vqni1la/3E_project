"""新コース：非対称ループ＋S字シケイン

既存の car_simulator.py が利用している Environment API に合わせた実装。
既存の simulation/environment.py は先にバックアップしてから置き換えてください。
"""

import math
import pygame

from config.settings import SCREEN_WIDTH, SCREEN_HEIGHT


class Environment:
    """AIカー用の新しい閉ループコース。"""

    # 画面サイズ 800x600 を基準にしたコース中心線。
    # 右側にS字の連続コーナーがあり、従来コースとは違う走行を試せる。
    BASE_POINTS = [
        (140, 365),
        (155, 260),
        (205, 180),
        (300, 130),
        (425, 120),
        (535, 150),
        (610, 210),
        (650, 275),
        (615, 330),
        (650, 385),
        (615, 440),
        (555, 475),
        (450, 490),
        (330, 485),
        (220, 465),
        (165, 440),
        (145, 405),
    ]

    ROAD_WIDTH_BASE = 76
    BORDER_WIDTH_BASE = 10

    BACKGROUND = (45, 105, 58)
    BORDER_COLOR = (215, 215, 205)
    ROAD_COLOR = (75, 78, 82)
    CENTER_LINE_COLOR = (225, 205, 110)
    START_LINE_COLOR = (245, 245, 245)

    def __init__(self):
        self.scale_x = SCREEN_WIDTH / 800.0
        self.scale_y = SCREEN_HEIGHT / 600.0
        self.scale = min(self.scale_x, self.scale_y)

        control_points = [
            (x * self.scale_x, y * self.scale_y)
            for x, y in self.BASE_POINTS
        ]
        # 制御点をそのまま直線で結ぶと角張り、点ごとの円描画で
        # コース幅が膨らんで見えるため、閉じたCatmull-Rom曲線に補間する。
        self.track_points = self._smooth_closed_points(control_points, steps=6)
        self.road_width = max(24, int(self.ROAD_WIDTH_BASE * self.scale))
        self.border_width = max(4, int(self.BORDER_WIDTH_BASE * self.scale))
        self.half_width = self.road_width / 2.0

        self._segments = []
        cumulative = 0.0
        count = len(self.track_points)
        for index in range(count):
            start = self.track_points[index]
            end = self.track_points[(index + 1) % count]
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            length = math.hypot(dx, dy)
            if length <= 0:
                continue
            self._segments.append({
                "start": start,
                "end": end,
                "dx": dx,
                "dy": dy,
                "length": length,
                "cumulative": cumulative,
            })
            cumulative += length

        self.track_length = cumulative

        self.start_x, self.start_y = self.track_points[0]
        first_segment = self._segments[0]
        self.start_angle = math.degrees(
            math.atan2(first_segment["dy"], first_segment["dx"])
        )

    @staticmethod
    def _smooth_closed_points(points, steps=6):
        """制御点から滑らかな閉曲線を作る。返す点列も閉ループ用。"""
        count = len(points)
        smoothed = []
        for i in range(count):
            p0 = points[(i - 1) % count]
            p1 = points[i]
            p2 = points[(i + 1) % count]
            p3 = points[(i + 2) % count]

            for step_index in range(steps):
                t = step_index / steps
                t2 = t * t
                t3 = t2 * t
                x = 0.5 * (
                    2 * p1[0]
                    + (-p0[0] + p2[0]) * t
                    + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                    + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3
                )
                y = 0.5 * (
                    2 * p1[1]
                    + (-p0[1] + p2[1]) * t
                    + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                    + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3
                )
                smoothed.append((x, y))
        return smoothed

    @staticmethod
    def _distance_to_segment(px, py, segment):
        """点(px, py)から線分への最短距離と、線分上の比率を返す。"""
        sx, sy = segment["start"]
        dx = segment["dx"]
        dy = segment["dy"]
        length_squared = dx * dx + dy * dy

        t = ((px - sx) * dx + (py - sy) * dy) / length_squared
        t = max(0.0, min(1.0, t))
        closest_x = sx + t * dx
        closest_y = sy + t * dy
        distance = math.hypot(px - closest_x, py - closest_y)
        return distance, t

    def is_on_track(self, x, y):
        """車の中心がコースの走行可能幅内にあるか判定する。"""
        nearest_distance = float("inf")
        for segment in self._segments:
            distance, _ = self._distance_to_segment(x, y, segment)
            if distance < nearest_distance:
                nearest_distance = distance

        # 描画された路面の境界ぎりぎりを少し避ける。
        return nearest_distance <= self.half_width - 3 * self.scale

    def get_track_progress(self, x, y):
        """コース始点から、最も近い中心線上の位置までの距離を返す。"""
        nearest_distance = float("inf")
        best_progress = 0.0

        for segment in self._segments:
            distance, t = self._distance_to_segment(x, y, segment)
            if distance < nearest_distance:
                nearest_distance = distance
                best_progress = (
                    segment["cumulative"] + t * segment["length"]
                )

        # 周回境界付近で track_length ではなく 0 を返す場合もあり、
        # 呼び出し側の差分処理と組み合わせて周回を数える。
        return best_progress

    def _draw_center_dashes(self, screen):
        """中心線に短い破線を描く。"""
        dash_length = 18 * self.scale
        gap_length = 25 * self.scale
        step = dash_length + gap_length

        distance_along = 0.0
        while distance_along < self.track_length:
            dash_end = min(distance_along + dash_length, self.track_length)
            start_point = self._point_at_distance(distance_along)
            end_point = self._point_at_distance(dash_end)
            pygame.draw.line(
                screen,
                self.CENTER_LINE_COLOR,
                (round(start_point[0]), round(start_point[1])),
                (round(end_point[0]), round(end_point[1])),
                max(1, round(2 * self.scale)),
            )
            distance_along += step

    def _point_at_distance(self, distance_along):
        distance_along %= self.track_length
        for segment in self._segments:
            start_distance = segment["cumulative"]
            end_distance = start_distance + segment["length"]
            if distance_along <= end_distance:
                t = (distance_along - start_distance) / segment["length"]
                sx, sy = segment["start"]
                return (
                    sx + segment["dx"] * t,
                    sy + segment["dy"] * t,
                )
        return self.track_points[0]

    def draw(self, screen):
        """背景、路面、路肩、中心破線、スタートラインを描画する。"""
        screen.fill(self.BACKGROUND)
        points = [(round(x), round(y)) for x, y in self.track_points]

        border_width = self.road_width + self.border_width
        pygame.draw.lines(
            screen, self.BORDER_COLOR, True, points, max(1, border_width)
        )
        pygame.draw.lines(
            screen, self.ROAD_COLOR, True, points, max(1, self.road_width)
        )

        # 補間した点列に沿って円形の継ぎ目を重ね、路面幅を一定に保つ。
        # 点間隔が短いため、元の制御点に円を置く場合のような膨らみが出にくい。
        border_radius = max(1, border_width // 2)
        road_radius = max(1, self.road_width // 2)
        for point in points:
            pygame.draw.circle(screen, self.BORDER_COLOR, point, border_radius)
            pygame.draw.circle(screen, self.ROAD_COLOR, point, road_radius)

        self._draw_center_dashes(screen)

        # スタートラインは始点で中心線に直交させる。
        first = self._segments[0]
        length = first["length"]
        nx = -first["dy"] / length
        ny = first["dx"] / length
        half = self.half_width * 0.92
        start = self.track_points[0]
        p1 = (round(start[0] - nx * half), round(start[1] - ny * half))
        p2 = (round(start[0] + nx * half), round(start[1] + ny * half))
        pygame.draw.line(
            screen,
            self.START_LINE_COLOR,
            p1,
            p2,
            max(2, round(4 * self.scale)),
        )
