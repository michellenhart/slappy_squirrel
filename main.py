import glfw
from OpenGL.GL import *
import random
import time

# Variáveis do jogo
gravidade = -9.8
velocidade = 0.0
altura = 0.0

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
        'passed': False
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
    global obstacles
    for obstacle in obstacles:
        obstacle['x'] -= 0.01

        if obstacle['x'] < -1.0 - obstacle_width:
            obstacles.remove(obstacle)

    if len(obstacles) == 0 or obstacles[-1]['x'] < 0.1:
        create_obstacle()


def check_collision():
    global altura
    if altura < -1.1:
        return True

    for obstacle in obstacles:
        if -0.1 < obstacle['x'] < 0.1:
            if altura - 0.05 < obstacle['gap_position'] - obstacle_gap / 2 or altura + 0.05  > obstacle['gap_position'] + obstacle_gap / 2:
                return True
            else:
                obstacle['passed'] = True
    return False


def count_passed():
    print(sum(1 for o in obstacles if o['passed']))



def main():
    window = init_window(width, height, "Flappy Bird")

    glOrtho(-1.0, 1.0, -1.0, 1.0, -1.0, 1.0)  # Define a projeção ortográfica

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

        draw_obstacles()
        draw_character()

        if check_collision():
            print("Game Over!")
            glfw.set_window_should_close(window, True)

        count_passed()

        glfw.swap_buffers(window)
        glfw.poll_events()

    glfw.terminate()


if __name__ == "__main__":
    main()
