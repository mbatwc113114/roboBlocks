import pygame
from server import ThreadedSocketServer

# setup
width = 500
height = 500


pygame.init()

screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("RoboBlocks")

dt =0 
clock = pygame.time.Clock()
running = True

#server
server = ThreadedSocketServer()



# render function
# button properties
# UI layout
button_rect = pygame.Rect(20, 20, 160, 50)

client_box_rect = pygame.Rect(260, 20, 220, 460)

font = pygame.font.SysFont(None, 28)
small_font = pygame.font.SysFont(None, 22)


def update(screen, server):
    screen.fill((30, 30, 30))

    mouse_pos = pygame.mouse.get_pos()
    mouse_click = pygame.mouse.get_pressed()

    # ---------- SERVER BUTTON ----------
    server_on = server.server_status()

    if server_on:
        button_color = (0, 180, 0)
        text = "SERVER ON"
    else:
        button_color = (180, 0, 0)
        text = "SERVER OFF"

    if button_rect.collidepoint(mouse_pos):
        button_color = tuple(min(c + 40, 255) for c in button_color)

        if mouse_click[0]:
            if server_on:
                server.stop_server()
            else:
                server.start_server()
            pygame.time.delay(200)

    pygame.draw.rect(screen, button_color, button_rect, border_radius=8)

    label = font.render(text, True, (255, 255, 255))
    screen.blit(label, label.get_rect(center=button_rect.center))

    # ---------- CLIENT LIST BOX ----------
    pygame.draw.rect(screen, (50, 50, 50), client_box_rect, border_radius=8)
    pygame.draw.rect(screen, (120, 120, 120), client_box_rect, 2, border_radius=8)

    title = font.render("Connected Clients", True, (255, 255, 255))
    screen.blit(title, (client_box_rect.x + 10, client_box_rect.y + 10))

    # list clients
    y_offset = client_box_rect.y + 45

    with server.clients_lock:
        if not server.clients:
            empty = small_font.render("No clients connected", True, (180, 180, 180))
            screen.blit(empty, (client_box_rect.x + 10, y_offset))
        else:
            for i, (_, addr) in enumerate(server.clients):
                client_text = f"{i+1}. {addr[0]}:{addr[1]}"
                label = small_font.render(client_text, True, (200, 200, 200))
                screen.blit(label, (client_box_rect.x + 10, y_offset))
                y_offset += 22

    pygame.display.flip()



# main loop 
while running:
    dt = clock.tick(60)/1000
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    
    
    update(screen,server)





pygame.quit()
