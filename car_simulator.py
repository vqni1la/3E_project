#全体の起動、各モジュールの連携
import pygame

pygame.init()

screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("3E Car Simulator")

running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill((30, 30, 30))
    pygame.display.flip()

pygame.quit()