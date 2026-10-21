#全体の起動、各モジュールの連携

import pygame

from simulation.car import Car
from simulation.environment import Environment
from simulation.sensor import Sensor
from ai.neural_network import NeuralNetwork

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60


def create_car(environment):
    car = Car(
        environment.start_x,
        environment.start_y
    )
    car.angle = environment.start_angle
    return car


def main():
    pygame.init()

    screen = pygame.display.set_mode(
        (SCREEN_WIDTH, SCREEN_HEIGHT)
    )
    pygame.display.set_caption("3E Car Simulator - AI")

    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 28)

    environment = Environment()
    car = create_car(environment)
    sensor = Sensor(max_distance=150)
    brain = NeuralNetwork()

    crashed = False
    running = True
    survival_time = 0.0

    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    car = create_car(environment)
                    crashed = False
                    survival_time = 0.0

        if not crashed:
            # 1. センサーで周囲の距離を測定
            sensor.update(car, environment)

            # 2. センサー値からAIが操作量を計算
            output = brain.predict(sensor.distances)

            steering = float(output[0])
            throttle = float(output[1])

            # 3. AIの出力で車を操作
            car.update_ai(
                dt,
                steering,
                throttle,
                SCREEN_WIDTH,
                SCREEN_HEIGHT
            )

            survival_time += dt

            # 4. コース外に出たか確認
            if not environment.is_on_track(
                car.x, car.y
            ):
                crashed = True

        # 停止中もセンサーを描画できるよう更新
        sensor.update(car, environment)

        # 描画
        environment.draw(screen)
        sensor.draw(screen, car)
        car.draw(screen)

        if crashed:
            status = "CRASHED! Press R to restart"
            color = (255, 70, 70)
        else:
            status = "AI DRIVING"
            color = (255, 255, 255)

        screen.blit(
            font.render(status, True, color),
            (20, 15)
        )

        screen.blit(
            font.render(
                f"Time: {survival_time:.1f}s",
                True,
                (255, 255, 255)
            ),
            (20, 45)
        )

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
