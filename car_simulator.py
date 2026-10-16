#全体の起動、各モジュールの連携
import pygame

pygame.init()

map_width = 1800
map_height = 600

screen = pygame.display.set_mode((map_width, map_height))
pygame.display.set_caption("3E Car Simulator")

car = pygame.Rect(0, 0, 80, 50)
clock = pygame.time.Clock()
speed = 600
angle = 0

running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    dt = clock.tick(60) / 1000
    distance = speed * dt
    
    key = pygame.key.get_pressed()
    if key[pygame.K_d] and car.right + distance <= map_width:
            car.move_ip(distance,0)
            
    if key[pygame.K_a] and car.left - distance >= 0:
        car.move_ip(-distance,0)
        
    if key[pygame.K_w] and car.top - distance >= 0:
            car.move_ip(0,-distance)
            
    if key[pygame.K_s] and car.bottom + distance <= map_height:
            car.move_ip(0,distance)
    
    screen.fill((30, 30, 30))
    pygame.draw.rect(screen, (0, 150, 255), car)
    pygame.display.flip()

pygame.quit()