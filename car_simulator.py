#全体の起動、各モジュールの連携
import pygame
from simulation.car import Car

# 画面設定
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

    # 車を画面中央に配置
    car = Car(
        SCREEN_WIDTH / 2,
        SCREEN_HEIGHT / 2
    )

    running = True

    while running:
        # 1フレームにかかった時間（秒）
        dt = clock.tick(FPS) / 1000.0

        # イベント処理
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # キー入力を取得
        keys = pygame.key.get_pressed()

        # 車を更新
        car.update(
            dt,
            keys,
            SCREEN_WIDTH,
            SCREEN_HEIGHT
        )

        # 画面描画
        screen.fill((240, 240, 240))
        car.draw(screen)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
