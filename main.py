import glfw
from OpenGL.GL import *
import random
import time
from PIL import Image, ImageFont, ImageDraw
import numpy as np
import pygame

pygame.mixer.init()

# Música de fundo (loop)
pygame.mixer.music.load("sons/flappy_squirrel_madness.mp3")
pygame.mixer.music.play(-1)  # -1 = toca em loop

# Efeitos sonoros
# som_pulo = pygame.mixer.Sound("sons/pulo.wav")
# som_colisao = pygame.mixer.Sound("sons/colisao.wav")

# Variáveis do jogo
gravidade = -9.8
velocidade = 0.0
altura = 0.0
velocidade_obstaculos = 0.01

FORCA_PULO = 2

# Tamanho da tela
width, height = 800, 600

# Obstáculos
obstacles = []
obstacle_width = 0.1

obstacle_gap = 0.6

OBSTACLE_MAX_MIN_HEIGHT = 0.5

# Variavel usada para começar o jogo, monitora quando é o primeiro clique no espaço do usuário
iniciar_jogo = False
reiniciar_jogo = False
game_over = False

contador_pontos = 0
vidas = 5


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

def load_texture(path):
    image = Image.open(path).convert("RGBA")

    # Rotaciona 90 graus no sentido horário
    image = image.transpose(Image.Transpose.ROTATE_270)

    # Inverte a imagem verticalmente (necessário para OpenGL)
    image = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

    img_data = np.array(image, dtype=np.uint8)

    tex_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    glTexImage2D(
        GL_TEXTURE_2D, 0, GL_RGBA,
        image.width, image.height, 0,
        GL_RGBA, GL_UNSIGNED_BYTE, img_data
    )

    return tex_id, image.height


def load_background_texture(filename):
    img = Image.open(filename).convert("RGBA")
    img_data = np.array(img)[::-1]  # Inverte verticalmente
    tex_id = glGenTextures(1)

    glBindTexture(GL_TEXTURE_2D, tex_id)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, img.width, img.height,
                 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    return tex_id

# TODO : adicionar sons de colisão e pulo
def key_callback(window, key, scancode, action, mods):
    global velocidade, altura, iniciar_jogo, reiniciar_jogo, game_over

    if action == glfw.PRESS and key == glfw.KEY_SPACE:
        if not iniciar_jogo and not reiniciar_jogo and not game_over:
            iniciar_jogo = True
        elif iniciar_jogo:
            velocidade = FORCA_PULO

    if  action == glfw.PRESS and  key == glfw.KEY_ESCAPE:
        iniciar_jogo = not iniciar_jogo

    if  action == glfw.PRESS and key == glfw.KEY_ENTER:
        if game_over:
            restart_game(full_reset=True)



def update_character(delta_time):
    global velocidade, altura

    altura += velocidade * delta_time
    velocidade += gravidade * delta_time


def draw_character(tex_parado, tex_pulo, velocidade_vertical):
    glBindTexture(GL_TEXTURE_2D, tex_parado if velocidade_vertical <= 0 else tex_pulo)
    glEnable(GL_TEXTURE_2D)

    largura_personagem = 0.18
    altura_personagem = 0.12

    glBegin(GL_QUADS)
    glVertex2f(-largura_personagem / 2, -altura_personagem / 2 + altura)
    glVertex2f(largura_personagem / 2, -altura_personagem / 2 + altura)
    glVertex2f(largura_personagem / 2, altura_personagem / 2 + altura)
    glVertex2f(-largura_personagem / 2, altura_personagem / 2 + altura)

    # Coordenadas de textura TROCADAS (para teste de rotação)
    glTexCoord2f(0, 1)
    glVertex2f(-largura_personagem / 2, -altura_personagem / 2 + altura)
    glTexCoord2f(0, 0)
    glVertex2f(largura_personagem / 2, -altura_personagem / 2 + altura)
    glTexCoord2f(1, 0)
    glVertex2f(largura_personagem / 2, altura_personagem / 2 + altura)
    glTexCoord2f(1, 1)
    glVertex2f(-largura_personagem / 2, altura_personagem / 2 + altura)
    glEnd()

    glDisable(GL_TEXTURE_2D)

def draw_background(tex_id, zoom=1.2, offset_y=-0.2):
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glEnable(GL_TEXTURE_2D)

    # Tamanho da tela com zoom aplicado
    width = 1.0 * zoom
    height = 1.0 * zoom

    glBegin(GL_QUADS)
    glTexCoord2f(0, 0)
    glVertex2f(-width, -height + offset_y)
    glTexCoord2f(1, 0)
    glVertex2f(width, -height + offset_y)
    glTexCoord2f(1, 1)
    glVertex2f(width, height + offset_y)
    glTexCoord2f(0, 1)
    glVertex2f(-width, height + offset_y)
    glEnd()

    glDisable(GL_TEXTURE_2D)

def create_obstacle():
    gap_position = random.uniform(-OBSTACLE_MAX_MIN_HEIGHT, OBSTACLE_MAX_MIN_HEIGHT)
    obstacle = {
        'x': 1.0,  # Inicia à direita da tela
        'gap_position': gap_position,
        'passed': False,
        'counted': False
    }
    obstacles.append(obstacle)


def draw_obstacles(obstacle_tex, height=None):
    for obstacle in obstacles:
        x = obstacle['x']
        gap = obstacle_gap
        center = obstacle['gap_position']

        bottom_top = center - gap / 2
        top_bottom = center + gap / 2

        # Parte de baixo - INVERTIDA
        draw_obstacle_with_texture(obstacle_tex, x, -1.0, bottom_top, flip_vertical=True)

        # Parte de cima - NORMAL
        draw_obstacle_with_texture(obstacle_tex, x, top_bottom, 1.0)


def update_obstacles(delta_time):
    global obstacles, velocidade_obstaculos
    for obstacle in obstacles:
        obstacle['x'] -= velocidade_obstaculos * delta_time

        if obstacle['x'] < -1.0 - obstacle_width:
            obstacles.remove(obstacle)

    if len(obstacles) == 0 or obstacles[-1]['x'] < 0.1:
        create_obstacle()


def check_collision():
    global altura, contador_pontos, velocidade_obstaculos, vidas, reiniciar_jogo, game_over

    if altura < -1.1:
        vidas -= 1
        if vidas <= 0:
            game_over = True
        else:
            reiniciar_jogo = True
        return True

    for obstacle in obstacles:
        if -0.1 < obstacle['x'] < 0.1:
            if (altura - 0.05 < obstacle['gap_position'] - obstacle_gap / 2 or
                    altura + 0.05 > obstacle['gap_position'] + obstacle_gap / 2):
                vidas -= 1
                if vidas <= 0:
                    game_over = True
                else:
                    reiniciar_jogo = True
                return True
            else:
                if not obstacle['counted']:
                    obstacle['counted'] = True
                    contador_pontos += 1
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

def draw_obstacle_with_texture(tex_id, x, bottom, top, largura=0.1, flip_vertical=False):
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glEnable(GL_TEXTURE_2D)

    glBegin(GL_QUADS)
    if flip_vertical:
        # Coordenadas do vértice e coordenadas da textura (u, v) - invertido verticalmente
        glTexCoord2f(0, 1)
        glVertex2f(x - largura, bottom)

        glTexCoord2f(1, 1)
        glVertex2f(x + largura, bottom)

        glTexCoord2f(1, 0)
        glVertex2f(x + largura, top)

        glTexCoord2f(0, 0)
        glVertex2f(x - largura, top)
    else:
        # Coordenadas do vértice e coordenadas da textura (u, v) - normal
        glTexCoord2f(0, 0)
        glVertex2f(x - largura, bottom)

        glTexCoord2f(1, 0)
        glVertex2f(x + largura, bottom)

        glTexCoord2f(1, 1)
        glVertex2f(x + largura, top)

        glTexCoord2f(0, 1)
        glVertex2f(x - largura, top)
    glEnd()

    glDisable(GL_TEXTURE_2D)


def draw_textured_quad(tex_id, width, height):
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glEnable(GL_TEXTURE_2D)

    aspect_ratio = width / height
    quad_width = 0.5
    quad_height = quad_width / aspect_ratio

    # Posiciona no topo (0.8 no Y)
    center_y = 0.8
    glBegin(GL_QUADS)
    glTexCoord2f(0, 0)
    glVertex2f(-quad_width, center_y - quad_height)
    glTexCoord2f(1, 0)
    glVertex2f(quad_width, center_y - quad_height)
    glTexCoord2f(1, 1)
    glVertex2f(quad_width, center_y + quad_height)
    glTexCoord2f(0, 1)
    glVertex2f(-quad_width, center_y + quad_height)
    glEnd()

    glDisable(GL_TEXTURE_2D)

def update_difficulty():
    global velocidade_obstaculos, obstacle_gap, contador_pontos
    velocidade_obstaculos = (((contador_pontos / 50) + 1) * 0.5)
    print(f"[DEBUG] Velocidade obstáculos: {velocidade_obstaculos:.4f}")


def restart_game(full_reset=False):
    global obstacles, altura, reiniciar_jogo, contador_pontos, velocidade, vidas, iniciar_jogo, game_over

    obstacles = []
    altura = 0
    velocidade = 0
    iniciar_jogo = False
    reiniciar_jogo = False

    if full_reset:
        vidas = 5
        contador_pontos = 0
        game_over = False


def draw_game_over():
    text = "GAME OVER - Pressione ENTER para reiniciar"
    tex_id, w, h = create_text_texture(text)

    glBindTexture(GL_TEXTURE_2D, tex_id)
    glEnable(GL_TEXTURE_2D)

    aspect_ratio = w / h
    quad_width = 0.8
    quad_height = quad_width / aspect_ratio
    center_y = 0.0

    glBegin(GL_QUADS)
    glTexCoord2f(0, 0)
    glVertex2f(-quad_width, center_y - quad_height)
    glTexCoord2f(1, 0)
    glVertex2f(quad_width, center_y - quad_height)
    glTexCoord2f(1, 1)
    glVertex2f(quad_width, center_y + quad_height)
    glTexCoord2f(0, 1)
    glVertex2f(-quad_width, center_y + quad_height)
    glEnd()

    glDisable(GL_TEXTURE_2D)
    glDeleteTextures(1, [tex_id])



def main():
    global contador_pontos, iniciar_jogo, reiniciar_jogo
    window = init_window(width, height, "Flappy Bird")
    background_tex = load_background_texture("imgs/background.png")
    obstacle_tex = load_texture("imgs/obstacle-2.png")
    personagem_parado_tex = load_texture("imgs/sqrl_closed.png")[0]
    personagem_pulo_tex = load_texture("imgs/sqrl_open.png")[0]

    glOrtho(-1.0, 1.0, -1.0, 1.0, -1.0, 1.0)  # Define a projeção ortográfica
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    tempo_anterior = time.time()
    glClearColor(0.95, 0.5, 0.25, 1.0)

    glfw.set_key_callback(window, key_callback)

    while not glfw.window_should_close(window):
        glClear(GL_COLOR_BUFFER_BIT)

        tempo_atual = time.time()
        delta_time = tempo_atual - tempo_anterior
        tempo_anterior = tempo_atual
        delta_time = min(delta_time, 0.05)


        if iniciar_jogo and not game_over:
            update_character(delta_time)
            update_obstacles(delta_time)
            update_difficulty()

        draw_background(background_tex, zoom=1.2, offset_y=-0.3)
        draw_obstacles(obstacle_tex[0], obstacle_tex[1])
        draw_character(personagem_parado_tex, personagem_pulo_tex, velocidade)
        # HUD: pontuação + vidas
        text = f"Pontuação: {contador_pontos} | Vidas: {vidas}"
        tex_id, w, h = create_text_texture(text)
        draw_textured_quad(tex_id, w, h)
        glDeleteTextures(1, [tex_id])

        if game_over:
            draw_game_over()

        if not game_over and check_collision():
            iniciar_jogo = False

        if reiniciar_jogo:
            restart_game()

        glfw.swap_buffers(window)
        glfw.poll_events()

    glfw.terminate()


if __name__ == "__main__":
    main()
