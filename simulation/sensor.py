#赤外線・超音波センサーのシミュレーション

import math
import pygame


class Sensor:
    def __init__(self, max_distance=150):
        # 車の正面を基準にしたセンサーの角度
        self.angles = [-60, -30, 0, 30, 60]

        self.max_distance = max_distance
        self.step = 3

        self.distances = [max_distance] * len(self.angles)
        self.endpoints = []

    def update(self, car, environment):
        self.distances = []
        self.endpoints = []

        for relative_angle in self.angles:
            # 車の向き + センサーの相対角度
            angle = math.radians(
                car.angle + relative_angle
            )

            dx = math.cos(angle)
            dy = math.sin(angle)

            distance = 0

            # 壁やコース外に達するまで光線を伸ばす
            while distance < self.max_distance:
                test_x = car.x + dx * distance
                test_y = car.y + dy * distance

                if not environment.is_on_track(
                    test_x, test_y
                ):
                    break

                distance += self.step

            distance = min(distance, self.max_distance)

            end_x = car.x + dx * distance
            end_y = car.y + dy * distance

            self.distances.append(distance)
            self.endpoints.append((end_x, end_y))

    def draw(self, screen, car):
        for distance, endpoint in zip(
            self.distances, self.endpoints
        ):
            # 壁までの距離に応じて色を変える
            if distance < 45:
                color = (255, 60, 60)
            elif distance < 90:
                color = (255, 220, 50)
            else:
                color = (50, 220, 100)

            pygame.draw.line(
                screen,
                color,
                (round(car.x), round(car.y)),
                (round(endpoint[0]), round(endpoint[1])),
                2
            )

            pygame.draw.circle(
                screen,
                color,
                (round(endpoint[0]), round(endpoint[1])),
                4
            )
