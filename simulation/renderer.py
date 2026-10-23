#車体、コース、センサーなどの描画
import pygame
from config.settings import POPULATION_SIZE

def draw_simulation(
    screen,
    font,
    environment,
    individuals,
    generation,
    show_sensors,
    simulation_speed,
):
    environment.draw(screen)

    for index, individual in enumerate(individuals):
        car = individual["car"]

        if show_sensors and not individual["finished"]:
            individual["sensor"].draw(screen, car)

        car.draw(screen)

        label = font.render(
            str(index + 1), True, (255, 255, 255)
        )
        screen.blit(
            label,
            (int(car.x) - 5, int(car.y) - 30),
        )

    active_count = sum(
        not individual["finished"] for individual in individuals
    )
    finished_count = POPULATION_SIZE - active_count

    best_lap = min(
        (
            lap_time
            for individual in individuals
            for lap_time in individual["lap_times"]
        ),
        default=None,
    )

    screen.blit(
        font.render(f"Generation: {generation}", True, (255, 255, 255)),
        (20, 15),
    )
    screen.blit(
        font.render(
            f"Running: {active_count}/{POPULATION_SIZE}",
            True, (255, 255, 255),
        ),
        (20, 45),
    )
    screen.blit(
        font.render(
            f"Finished: {finished_count}/{POPULATION_SIZE}",
            True, (255, 255, 255),
        ),
        (20, 75),
    )
    screen.blit(
        font.render(
            f"Sensors: {'ON' if show_sensors else 'OFF'} [S]",
            True, (255, 255, 255),
        ),
        (20, 105),
    )

    if best_lap is not None:
        screen.blit(
            font.render(
                f"Best lap: {best_lap:.2f}s",
                True, (255, 255, 255),
            ),
            (20, 135),
        )
        
        # 速度変更ボタン
    pygame.draw.rect(screen, (70, 70, 70), (20, 155, 40, 40))
    pygame.draw.rect(screen, (70, 70, 70), (120, 155, 40, 40))

    pygame.draw.rect(screen, (230, 230, 230), (20, 155, 40, 40), 2)
    pygame.draw.rect(screen, (230, 230, 230), (120, 155, 40, 40), 2)

    screen.blit(
        font.render("-", True, (255, 255, 255)),
        (35, 163),
    )
    screen.blit(
        font.render("+", True, (255, 255, 255)),
        (132, 163),
    )
    screen.blit(
        font.render(
            f"Speed: {simulation_speed}x",
            True,
            (255, 255, 255),
        ),
        (175, 163),
    )

    pygame.display.flip()