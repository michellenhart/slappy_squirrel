import glfw
from OpenGL.GL import *
import random
import time
from PIL import Image, ImageFont, ImageDraw
import numpy as np

# Variáveis do jogo
gravidade = -9.8
velocidade = 0.0
altura = 0.0
velocidade_obstaculos = 0.01

FORCA_PULO = 1.5

# Tamanho da tela
width, height = 800, 600

# Obstáculos
obstacles = []
obstacle_width = 0.1

# TODO - Tentar ir diminuindo o espaço para o esquilo passar conforme o tempo que vai passando
obstacle_gap = 0.6

OBSTACLE_MAX_MIN_HEIGHT = 0.5

# Variavel usada para começar o jogo, monitora quando é o primeiro clique no espaço do usuário
iniciar_jogo = False

contador_pontos = 0

def init_window(width, height, title):
    if not glfw.init():
        raise Exception("GLFW não pôde ser iniciado!")

    window = glfw.create_window(width, height, title, None, None)
    if not window:
        glfw.terminate()
        raise Exception("Falha ao criar a janela!")

    glfw.make_context_current(window)
    glfw.swap_interval(1)  # Ativa o V-Sync
    return window


def process_input(window):
    global velocidade, altura, iniciar_jogo
    if glfw.get_key(window, glfw.KEY_SPACE) == glfw.PRESS:
        if not iniciar_jogo:
            iniciar_jogo = True
        velocidade = FORCA_PULO


def update_character(delta_time):
    global velocidade, altura

    altura += velocidade * delta_time
    velocidade += gravidade * delta_time


def draw_character():
    glBegin(GL_QUADS)
    glVertex2f(-0.05, -0.05 + altura)
    glVertex2f(0.05, -0.05 + altura)
    glVertex2f(0.05, 0.05 + altura)
    glVertex2f(-0.05, 0.05 + altura)
    glEnd()

def create_obstacle():
    gap_position = random.uniform(-OBSTACLE_MAX_MIN_HEIGHT, OBSTACLE_MAX_MIN_HEIGHT)
    obstacle = {
        'x': 1.0,  # Inicia à direita da tela
        'gap_position': gap_position,
        'passed': False,
        'counted': False
    }
    obstacles.append(obstacle)


def draw_obstacles():
    for obstacle in obstacles:
        gap_position = obstacle['gap_position']
        glBegin(GL_QUADS)
        glVertex2f(obstacle['x'] - obstacle_width, gap_position + obstacle_gap / 2)
        glVertex2f(obstacle['x'] + obstacle_width, gap_position + obstacle_gap / 2)
        glVertex2f(obstacle['x'] + obstacle_width, 1.0)
        glVertex2f(obstacle['x'] - obstacle_width, 1.0)
        glEnd()

        glBegin(GL_QUADS)
        glVertex2f(obstacle['x'] - obstacle_width, -1.0)
        glVertex2f(obstacle['x'] + obstacle_width, -1.0)
        glVertex2f(obstacle['x'] + obstacle_width, gap_position - obstacle_gap / 2)
        glVertex2f(obstacle['x'] - obstacle_width, gap_position - obstacle_gap / 2)
        glEnd()


def update_obstacles():
    global obstacles, velocidade_obstaculos
    for obstacle in obstacles:
        obstacle['x'] -= velocidade_obstaculos

        if obstacle['x'] < -1.0 - obstacle_width:
            obstacles.remove(obstacle)

    if len(obstacles) == 0 or obstacles[-1]['x'] < 0.1:
        create_obstacle()


def check_collision():
    global altura,contador_pontos, velocidade_obstaculos
    if altura < -1.1:
        return True

    for obstacle in obstacles:
        if -0.1 < obstacle['x'] < 0.1:
            if altura - 0.05 < obstacle['gap_position'] - obstacle_gap / 2 or altura + 0.05  > obstacle['gap_position'] + obstacle_gap / 2:
                return True
            else:
                obstacle['passed'] = True
                if not obstacle['counted']:
                    obstacle['counted'] = True
                    contador_pontos += 1
                    print(f'{contador_pontos}')
                    print(velocidade_obstaculos)

    return False

font = ImageFont.truetype("verdana.ttf", 32)  # Use uma fonte .ttf disponível no seu sistema

def create_text_texture(text):
    img = Image.new("RGBA", (512, 128), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), text, font=font, fill=(255, 255, 255, 255))
    img_data = np.array(img)[::-1]

    texture_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, img.width, img.height,
                 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
    return texture_id, img.width, img.height

def draw_textured_quad(tex_id, width, height):
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glEnable(GL_TEXTURE_2D)

    aspect_ratio = width / height
    quad_width = 0.5
    quad_height = quad_width / aspect_ratio

    # Posiciona no topo (0.8 no Y)
    center_y = 0.8
    glBegin(GL_QUADS)
    glTexCoord2f(0, 0); glVertex2f(-quad_width, center_y - quad_height)
    glTexCoord2f(1, 0); glVertex2f( quad_width, center_y - quad_height)
    glTexCoord2f(1, 1); glVertex2f( quad_width, center_y + quad_height)
    glTexCoord2f(0, 1); glVertex2f(-quad_width, center_y + quad_height)
    glEnd()

    glDisable(GL_TEXTURE_2D)

def update_difficulty():
    global velocidade_obstaculos, obstacle_gap, contador_pontos
    velocidade_obstaculos =  (((contador_pontos / 20) + 1)  * 0.01)

def main():
    global contador_pontos
    window = init_window(width, height, "Flappy Bird")

    glOrtho(-1.0, 1.0, -1.0, 1.0, -1.0, 1.0)  # Define a projeção ortográfica
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    tempo_anterior = time.time()
    while not glfw.window_should_close(window):
        glClear(GL_COLOR_BUFFER_BIT)

        tempo_atual = time.time()
        delta_time = tempo_atual - tempo_anterior
        tempo_anterior = tempo_atual
        delta_time = min(delta_time, 0.05)

        process_input(window)
        if(iniciar_jogo):
            update_character(delta_time)
            update_obstacles()
            update_difficulty()

        draw_obstacles()
        draw_character()
        text = f"Pontuação: {contador_pontos}"
        tex_id, w, h = create_text_texture(text)

        draw_textured_quad(tex_id, w, h)
        glDeleteTextures(1, [tex_id])

        if check_collision():
            print("Game Over!")
            glfw.set_window_should_close(window, True)

        glfw.swap_buffers(window)
        glfw.poll_events()

    glfw.terminate()


if __name__ == "__main__":
    main()
