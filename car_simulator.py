#全体の起動、各モジュールの連携

import pygame
from simulation.car import Car
from simulation.environment import Environment

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60


def main():
    pygame.init()

    screen = pygame.display.set_mode(
        (SCREEN_WIDTH, SCREEN_HEIGHT)
    )
    pygame.display.set_caption("3E Car Simulator")

    clock = pygame.time.Clock()

    # コースと車を作成
    environment = Environment()
    car = Car(
        environment.start_x,
        environment.start_y
    )
    car.angle = environment.start_angle

    running = True
    crashed = False

    font = pygame.font.Font(None, 30)

    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Rキーでリスタート
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    car = Car(
                        environment.start_x,
                        environment.start_y
                    )
                    car.angle = environment.start_angle
                    crashed = False

        keys = pygame.key.get_pressed()

        # コース外に出ていない場合だけ移動
        if not crashed:
            car.update(
                dt,
                keys,
                SCREEN_WIDTH,
                SCREEN_HEIGHT
            )

            if not environment.is_on_track(car.x, car.y):
                crashed = True

        # 描画
        environment.draw(screen)
        car.draw(screen)

        if crashed:
            message = "OUT OF TRACK! Press R to restart"
            color = (255, 70, 70)
        else:
            message = "WASD: Drive | R: Restart"
            color = (255, 255, 255)

        text = font.render(message, True, color)
        screen.blit(text, (20, 15))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
