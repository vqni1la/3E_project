"""複数コース対応 Environment for 3E Car Simulator.

既存 car_simulator.py が利用する Environment API:
    start_x, start_y, start_angle, track_length
    is_on_track(x, y)
    get_track_progress(x, y)
    draw(screen)

コース切り替え:
    environment.set_course(index)  # index: 0..5
"""

import math
import pygame
from config.settings import SCREEN_WIDTH, SCREEN_HEIGHT


class Environment:
    BACKGROUND = (45, 105, 58)
    BORDER_COLOR = (215, 215, 205)
    ROAD_COLOR = (75, 78, 82)
    CENTER_LINE_COLOR = (225, 205, 110)
    START_LINE_COLOR = (245, 245, 245)

    # 座標は800x600基準。各コースは中心線の折れ線で定義する。
    # road_widthは中心線から左右に広がる道路全体の幅。
    TRACKS = [
        {
            "name": "Rectangle",
            "description": "直角コーナーの基本コース",
            "points": [(145, 125), (655, 125), (655, 475), (145, 475)],
            "road_width": 86,
        },
        {
            "name": "Oval",
            "description": "カーブ主体の高速コース",
            "points": [
                (
                    400 + 270 * math.cos(math.radians(-90 + i * 360 / 48)),
                    300 + 185 * math.sin(math.radians(-90 + i * 360 / 48)),
                )
                for i in range(48)
            ],
            "road_width": 82,
        },
        {
            "name": "Diamond",
            "description": "斜めの直線と鋭いコーナー",
            "points": [(400, 100), (680, 300), (400, 500), (120, 300)],
            "road_width": 80,
        },
        {
            "name": "Switchback",
            "description": "折り返しが連続するジグザグコース",
            "points": [
                (120, 120), (680, 120), (680, 240), (250, 240),
                (250, 360), (680, 360), (680, 480), (120, 480),
            ],
            "road_width": 74,
        },
        {
            "name": "Chicane",
            "description": "左右の切り返しが多いテクニカルコース",
            "points": [
                (120, 140), (680, 140), (680, 230), (500, 230),
                (500, 370), (680, 370), (680, 460), (120, 460),
                (120, 370), (300, 370), (300, 230), (120, 230),
            ],
            "road_width": 70,
        },
        {
            "name": "Angled Loop",
            "description": "斜めの区間を組み合わせた変形コース",
            "points": [
                (160, 110), (620, 110), (700, 260),
                (580, 470), (270, 500), (100, 330),
            ],
            "road_width": 78,
        },
    ]

    def __init__(self, course_index=0):
        self.scale_x = SCREEN_WIDTH / 800.0
        self.scale_y = SCREEN_HEIGHT / 600.0
        self.scale = min(self.scale_x, self.scale_y)
        self.border_width = max(2, round(10 * self.scale))
        self.course_index = 0
        self.set_course(course_index)

    @classmethod
    def course_count(cls):
        return len(cls.TRACKS)

    def set_course(self, course_index):
        """コースを切り替えて、中心線・周長・スタート位置を再計算する。"""
        if not isinstance(course_index, int):
            raise TypeError("course_index must be an integer")
        if not 0 <= course_index < len(self.TRACKS):
            raise ValueError(
                f"course_index must be between 0 and {len(self.TRACKS) - 1}"
            )

        self.course_index = course_index
        definition = self.TRACKS[course_index]
        self.course_name = definition["name"]
        self.course_description = definition["description"]
        self.road_width = definition["road_width"] * self.scale
        self.half_width = self.road_width / 2.0
        self.track_points = [
            (x * self.scale_x, y * self.scale_y)
            for x, y in definition["points"]
        ]

        self._segments = []
        cumulative = 0.0
        for index, start in enumerate(self.track_points):
            end = self.track_points[(index + 1) % len(self.track_points)]
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            length = math.hypot(dx, dy)
            if length <= 1e-9:
                raise ValueError("Track contains two consecutive identical points")
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
        ) % 360

    @staticmethod
    def _distance_to_segment(px, py, segment):
        sx, sy = segment["start"]
        dx, dy = segment["dx"], segment["dy"]
        length_sq = dx * dx + dy * dy
        t = ((px - sx) * dx + (py - sy) * dy) / length_sq
        t = max(0.0, min(1.0, t))
        closest_x = sx + t * dx
        closest_y = sy + t * dy
        return math.hypot(px - closest_x, py - closest_y), t

    def is_on_track(self, x, y):
        nearest = min(
            self._distance_to_segment(x, y, segment)[0]
            for segment in self._segments
        )
        # 境界ぎりぎりを走らないよう、少し余裕を持たせる。
        return nearest <= self.half_width - 4 * self.scale

    def get_track_progress(self, x, y):
        nearest = float("inf")
        best_progress = 0.0
        for segment in self._segments:
            distance, t = self._distance_to_segment(x, y, segment)
            if distance < nearest:
                nearest = distance
                best_progress = segment["cumulative"] + t * segment["length"]
        return best_progress

    def _point_at_distance(self, distance_along):
        distance_along %= self.track_length
        for segment in self._segments:
            start_distance = segment["cumulative"]
            end_distance = start_distance + segment["length"]
            if distance_along <= end_distance:
                t = (distance_along - start_distance) / segment["length"]
                sx, sy = segment["start"]
                return (sx + segment["dx"] * t, sy + segment["dy"] * t)
        return self.track_points[0]

    def _draw_center_dashes(self, screen):
        dash = 18 * self.scale
        gap = 25 * self.scale
        distance_along = 0.0
        line_width = max(1, round(2 * self.scale))
        while distance_along < self.track_length:
            end_distance = min(distance_along + dash, self.track_length)
            p1 = self._point_at_distance(distance_along)
            p2 = self._point_at_distance(end_distance)
            pygame.draw.line(
                screen,
                self.CENTER_LINE_COLOR,
                (round(p1[0]), round(p1[1])),
                (round(p2[0]), round(p2[1])),
                line_width,
            )
            distance_along += dash + gap

    @staticmethod
    def _draw_rounded_polyline(screen, color, points, width):
        width = max(1, int(width))
        if len(points) >= 2:
            pygame.draw.lines(screen, color, True, points, width)
        radius = max(1, width // 2)
        for point in points:
            pygame.draw.circle(screen, color, point, radius)

    def draw(self, screen):
        screen.fill(self.BACKGROUND)
        points = [(round(x), round(y)) for x, y in self.track_points]

        # 外側の壁、道路の順に描く。円形の継ぎ足しで角の隙間を防ぐ。
        outer_width = round(self.road_width + 2 * self.border_width)
        self._draw_rounded_polyline(
            screen, self.BORDER_COLOR, points, outer_width
        )
        self._draw_rounded_polyline(
            screen, self.ROAD_COLOR, points, round(self.road_width)
        )

        self._draw_center_dashes(screen)

        # スタートラインは、最初の進行方向に対して垂直に引く。
        first = self._segments[0]
        length = first["length"]
        normal_x = -first["dy"] / length
        normal_y = first["dx"] / length
        half = self.half_width * 0.92
        x, y = self.start_x, self.start_y
        p1 = (round(x - normal_x * half), round(y - normal_y * half))
        p2 = (round(x + normal_x * half), round(y + normal_y * half))
        pygame.draw.line(
            screen,
            self.START_LINE_COLOR,
            p1,
            p2,
            max(2, round(4 * self.scale)),
        )
