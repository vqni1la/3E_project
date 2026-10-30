"""Environment adapter that uses saved_courses/active_course.json when present.

If no custom course is selected, the project's existing Environment is used.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pygame
from simulation.environment import Environment as ExistingEnvironment

ROOT = Path(__file__).resolve().parent.parent
ACTIVE_COURSE = ROOT / "saved_courses" / "active_course.json"


class Environment(ExistingEnvironment):
    BACKGROUND = (45, 105, 58)
    BORDER_COLOR = (215, 215, 205)
    ROAD_COLOR = (75, 78, 82)
    CENTER_LINE_COLOR = (225, 205, 110)
    START_LINE_COLOR = (245, 245, 245)

    def __init__(self, course_path: str | Path | None = None):
        path = Path(course_path) if course_path else ACTIVE_COURSE
        if not path.is_file():
            super().__init__()
            self.course_name = "既定コース"
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            points = data["points"]
            if not isinstance(points, list) or len(points) < 3:
                raise ValueError("コースには3点以上必要です。")
            canvas_w = float(data.get("canvas_width", 800))
            canvas_h = float(data.get("canvas_height", 600))
            road_width = float(data.get("road_width", 90))
            if canvas_w <= 0 or canvas_h <= 0 or road_width < 20 or road_width > 250:
                raise ValueError("キャンバス寸法または道路幅が範囲外です。")
            # Use the actual Pygame window size. This keeps the editor map and
            # simulation viewport aligned when car_simulator.py is enlarged.
            surface = pygame.display.get_surface()
            if surface is None:
                raise RuntimeError("Pygame display must be initialized before Environment()")
            screen_width, screen_height = surface.get_size()
            sx = screen_width / canvas_w
            sy = screen_height / canvas_h
            # Preserve the 16:9 map proportions. If the monitor uses a
            # different aspect ratio, center the map and leave side bars.
            self.scale = min(sx, sy)
            offset_x = (screen_width - canvas_w * self.scale) / 2.0
            offset_y = (screen_height - canvas_h * self.scale) / 2.0
            self.track_points = []
            for point in points:
                if not isinstance(point, (list, tuple)) or len(point) != 2:
                    raise ValueError("座標データの形式が正しくありません。")
                x, y = float(point[0]), float(point[1])
                if not math.isfinite(x) or not math.isfinite(y):
                    raise ValueError("座標に数値以外が含まれています。")
                self.track_points.append((x * self.scale + offset_x, y * self.scale + offset_y))
            self.road_width = road_width * self.scale
            self.half_width = self.road_width / 2.0
            self.border_width = max(5.0, 8.0 * self.scale)
            self._build_segments()
            self.start_x, self.start_y = self.track_points[0]
            dx = self.track_points[1][0] - self.track_points[0][0]
            dy = self.track_points[1][1] - self.track_points[0][1]
            self.start_angle = math.degrees(math.atan2(dy, dx))
            self.course_name = str(data.get("name", path.stem))
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"カスタムコースを読み込めません: {path}\n{exc}") from exc

    def _build_segments(self) -> None:
        self._segments = []
        cumulative = 0.0
        for i, start in enumerate(self.track_points):
            end = self.track_points[(i + 1) % len(self.track_points)]
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            length = math.hypot(dx, dy)
            if length < 1e-6:
                raise ValueError("コース内に同じ位置の連続した点があります。")
            self._segments.append({
                "start": start,
                "end": end,
                "dx": dx,
                "dy": dy,
                "length": length,
                "cumulative": cumulative,
            })
            cumulative += length
        if cumulative <= 1:
            raise ValueError("コースの長さが不足しています。")
        self.track_length = cumulative

    @staticmethod
    def _distance_to_segment(px, py, segment):
        sx, sy = segment["start"]
        dx, dy = segment["dx"], segment["dy"]
        length_sq = dx * dx + dy * dy
        if length_sq <= 1e-12:
            return math.hypot(px - sx, py - sy), 0.0
        t = ((px - sx) * dx + (py - sy) * dy) / length_sq
        t = max(0.0, min(1.0, t))
        closest_x = sx + t * dx
        closest_y = sy + t * dy
        return math.hypot(px - closest_x, py - closest_y), t

    def is_on_track(self, x, y):
        nearest = min(self._distance_to_segment(x, y, seg)[0] for seg in self._segments)
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
            start_d = segment["cumulative"]
            end_d = start_d + segment["length"]
            if distance_along <= end_d:
                t = (distance_along - start_d) / segment["length"]
                sx, sy = segment["start"]
                return (sx + segment["dx"] * t, sy + segment["dy"] * t)
        return self.track_points[0]

    def _draw_center_dashes(self, screen):
        dash = 18 * self.scale
        gap = 25 * self.scale
        distance = 0.0
        while distance < self.track_length:
            end = min(distance + dash, self.track_length)
            p1 = self._point_at_distance(distance)
            p2 = self._point_at_distance(end)
            pygame.draw.line(screen, self.CENTER_LINE_COLOR, (round(p1[0]), round(p1[1])), (round(p2[0]), round(p2[1])), max(1, round(2 * self.scale)))
            distance += dash + gap

    def draw(self, screen):
        screen.fill(self.BACKGROUND)
        points = [(round(x), round(y)) for x, y in self.track_points]
        outer_width = max(1, round(self.road_width + self.border_width * 2))
        road_width = max(1, round(self.road_width))
        pygame.draw.lines(screen, self.BORDER_COLOR, True, points, outer_width)
        pygame.draw.lines(screen, self.ROAD_COLOR, True, points, road_width)
        # Round joins prevent gaps at sharp corners.
        for x, y in points:
            pygame.draw.circle(screen, self.BORDER_COLOR, (x, y), outer_width // 2)
            pygame.draw.circle(screen, self.ROAD_COLOR, (x, y), road_width // 2)
        self._draw_center_dashes(screen)

        # Start line crosses the road perpendicular to the first segment.
        x, y = self.track_points[0]
        dx = self.track_points[1][0] - x
        dy = self.track_points[1][1] - y
        length = math.hypot(dx, dy) or 1.0
        px, py = -dy / length, dx / length
        half = self.half_width * 0.92
        pygame.draw.line(
            screen, self.START_LINE_COLOR,
            (round(x - px * half), round(y - py * half)),
            (round(x + px * half), round(y + py * half)),
            max(2, round(4 * self.scale)),
        )
