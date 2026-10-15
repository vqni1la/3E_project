#全体の起動、各モジュールの連携
import pygame

pygame.init()

screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("3E Car Simulator")

car = pygame.Rect(0, 0, 80, 50)

running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    key = pygame.key.get_pressed()
    if key[pygame.K_d] and car.right <= 800:
            car.move_ip(1,0)
            
    if key[pygame.K_a] and car.left >= 0:
        car.move_ip(-1,0)
        
    if key[pygame.K_w] and car.top >= 0:
            car.move_ip(0,-1)
            
    if key[pygame.K_s] and car.bottom <= 600:
            car.move_ip(0,1)
    
    screen.fill((30, 30, 30))
    pygame.draw.rect(screen, (0, 150, 255), car)
    pygame.display.flip()

pygame.quit()