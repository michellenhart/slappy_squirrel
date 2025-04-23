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
pygame.mixer.music.set_volume(0.05)
pygame.mixer.music.play(-1)  # -1 = toca em loop

# Efeitos sonoros
som_pulo = pygame.mixer.Sound("sons/pulo.mp3")
som_pulo.set_volume(0.2)
som_colisao = pygame.mixer.Sound("sons/colisao.mp3")
som_colisao.set_volume(0.2)

# Variáveis do jogo
gravidade = -9.8
velocidade = 0.0
altura = 0.0
velocidade_obstaculos = 0.01
angulo_personagem = 0.0
FORCA_PULO = 2

# Variáveis de animação de morte
animando_morte = False
altura_morte = 0.0
velocidade_morte = -0.5
angulo_morte = 0.0
velocidade_rotacao_morte = 360.0
morte_finalizada = False

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
vidas = 1

vidas_extras = []
tempo_para_proxima_vida = 5.0  # segundos entre possíveis aparições
tempo_decorrido_vida = 0.0


# Inicializa uma janela usando GLFW
def init_window(width, height, title):
    if not glfw.init():
        raise Exception("GLFW não pôde ser iniciado!")

    # Cria uma janela com as dimensões especificadas
    window = glfw.create_window(width, height, title, None, None)
    if not window:
        glfw.terminate()
        raise Exception("Falha ao criar a janela!")

    # Torna o contexto OpenGL atual associado a essa janela
    glfw.make_context_current(window)

    # Ativa o V-Sync (sincroniza com o refresh do monitor)
    glfw.swap_interval(1)

    return window


# Carrega uma textura de imagem e retorna o ID da textura e sua altura
def load_texture(path):
    image = Image.open(path).convert("RGBA")  # Converte para 4 canais (RGBA)

    # Rotaciona a imagem 90 graus no sentido horário
    image = image.transpose(Image.Transpose.ROTATE_270)

    # Inverte a imagem verticalmente (necessário para o OpenGL)
    image = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

    img_data = np.array(image, dtype=np.uint8)  # Converte imagem para array de bytes

    tex_id = glGenTextures(1)  # Gera um ID de textura
    glBindTexture(GL_TEXTURE_2D, tex_id)  # Seleciona essa textura como ativa

    # Define os parâmetros de minificação e magnificação (qualidade da textura)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    # Envia a imagem para a GPU
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, image.width, image.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)

    return tex_id, image.height


# Carrega uma textura de fundo (não rotaciona, só inverte verticalmente)
def load_background_texture(filename):
    img = Image.open(filename).convert("RGBA")
    img_data = np.array(img)[::-1]  # Inverte a imagem verticalmente
    tex_id = glGenTextures(1)

    glBindTexture(GL_TEXTURE_2D, tex_id)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, img.width, img.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)

    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    return tex_id


# Função de callback para tratar entradas do teclado
def key_callback(window, key, scancode, action, mods):
    global velocidade, altura, iniciar_jogo, reiniciar_jogo, game_over, \
        animando_morte, altura_morte, angulo_morte, angulo_personagem

    # Pressionou espaço
    if action == glfw.PRESS and key == glfw.KEY_SPACE:
        if not iniciar_jogo and not reiniciar_jogo and not game_over:
            iniciar_jogo = True
        elif iniciar_jogo:
            pygame.mixer.Sound.play(som_pulo)
            velocidade = FORCA_PULO

    # Pressionou ESC para pausar/despausar
    if action == glfw.PRESS and key == glfw.KEY_ESCAPE:
        iniciar_jogo = not iniciar_jogo

    # Pressionou ENTER para reiniciar após game over
    if action == glfw.PRESS and key == glfw.KEY_ENTER:
        if game_over:
            som_colisao.stop()
            pygame.mixer.music.play(-1)
            restart_game(full_reset=True)
            animando_morte = False
            altura = 0.0
            altura_morte = 0.0
            angulo_morte = 0.0
            angulo_personagem = 0.0


# Atualiza a posição e rotação do personagem com base no tempo e gravidade
def update_character(delta_time):
    global velocidade, altura, angulo_personagem

    altura += velocidade * delta_time  # Atualiza altura com base na velocidade
    velocidade += gravidade * delta_time  # Aplica gravidade

    # Define o ângulo de rotação com base na direção do movimento
    if velocidade > 0:
        angulo_alvo = 20.0  # Subindo
    elif velocidade < -2.0:
        angulo_alvo = -30.0  # Caindo rápido
    else:
        angulo_alvo = 0.0  # Estável

    # Suaviza a rotação do personagem
    taxa_rotacao = 80.0 * delta_time
    if angulo_personagem < angulo_alvo:
        angulo_personagem = min(angulo_personagem + taxa_rotacao, angulo_alvo)
    elif angulo_personagem > angulo_alvo:
        angulo_personagem = max(angulo_personagem - taxa_rotacao, angulo_alvo)

    # Limita rotação entre -15° e +15°
    angulo_personagem = max(-15.0, min(15.0, angulo_personagem))


# Desenha o personagem na tela com a textura correta e rotação/posição
def draw_character(tex_parado, tex_pulo, velocidade_vertical):
    global altura, angulo_personagem, animando_morte, altura_morte, angulo_morte

    # Define a posição e rotação com base na animação de morte ou não
    if animando_morte:
        y_pos = altura_morte
        rot = angulo_morte
    else:
        y_pos = altura
        rot = angulo_personagem

    # Escolhe a textura com base na animação
    textura = tex_parado if animando_morte or velocidade_vertical <= 0 else tex_pulo
    glBindTexture(GL_TEXTURE_2D, textura)
    glEnable(GL_TEXTURE_2D)

    # Tamanho do personagem
    largura_personagem = 0.18
    altura_personagem = 0.12

    glPushMatrix()  # Salva a matriz de transformação atual

    # Translação e rotação aplicadas ao personagem
    glTranslatef(0.0, y_pos, 0.0)
    glRotatef(rot, 0.0, 0.0, 1.0)
    glTranslatef(0.0, -y_pos, 0.0)

    # Desenha um quadrado com a textura aplicada
    glBegin(GL_QUADS)
    glTexCoord2f(0, 1)
    glVertex2f(-largura_personagem / 2, -altura_personagem / 2 + y_pos)
    glTexCoord2f(0, 0)
    glVertex2f(largura_personagem / 2, -altura_personagem / 2 + y_pos)
    glTexCoord2f(1, 0)
    glVertex2f(largura_personagem / 2, altura_personagem / 2 + y_pos)
    glTexCoord2f(1, 1)
    glVertex2f(-largura_personagem / 2, altura_personagem / 2 + y_pos)
    glEnd()

    glPopMatrix()  # Restaura a matriz original
    glDisable(GL_TEXTURE_2D)  # Desativa o uso de texturas

# Função para desenhar o fundo com textura
def draw_background(tex_id, zoom=1.2, offset_y=-0.2, scroll_offset=0.0):
    glBindTexture(GL_TEXTURE_2D, tex_id)   # Usa a textura
    glEnable(GL_TEXTURE_2D)                # Ativa texturas

    width = 1.0 * zoom                     # Ajusta largura com zoom
    height = 1.0 * zoom                    # Ajusta altura com zoom

    glBegin(GL_QUADS)                      # Começa a desenhar um quadrado (4 vértices)
    glTexCoord2f(0.0 + scroll_offset, 0)
    glVertex2f(-width, -height + offset_y)

    glTexCoord2f(1.0 + scroll_offset, 0)
    glVertex2f(width, -height + offset_y)

    glTexCoord2f(1.0 + scroll_offset, 1)
    glVertex2f(width, height + offset_y)

    glTexCoord2f(0.0 + scroll_offset, 1)
    glVertex2f(-width, height + offset_y)
    glEnd()

    glDisable(GL_TEXTURE_2D)               # Desativa textura

# Cria obstáculo com gap (espaço) em posição aleatória
def create_obstacle():
    gap_position = random.uniform(-OBSTACLE_MAX_MIN_HEIGHT, OBSTACLE_MAX_MIN_HEIGHT)
    obstacle = {
        'x': 1.2,               # Começa fora da tela
        'gap_position': gap_position,
        'passed': False,
        'counted': False
    }
    obstacles.append(obstacle)

# Desenha os obstáculos (troncos em cima e embaixo)
def draw_obstacles(obstacle_tex, height=None):
    for obstacle in obstacles:
        x = obstacle['x']
        gap = obstacle_gap
        center = obstacle['gap_position']

        bottom_top = center - gap / 2
        top_bottom = center + gap / 2

        draw_obstacle_with_texture(obstacle_tex, x, -1.0, bottom_top, flip_vertical=True)
        draw_obstacle_with_texture(obstacle_tex, x, top_bottom, 1.0)

# Atualiza posição dos obstáculos e gera novos se necessário
def update_obstacles(delta_time):
    global obstacles, velocidade_obstaculos
    for obstacle in obstacles:
        obstacle['x'] -= velocidade_obstaculos * delta_time

        if obstacle['x'] < -1.0 - obstacle_width:
            obstacles.remove(obstacle)

    if len(obstacles) == 0 or obstacles[-1]['x'] < 0.1:
        create_obstacle()

# Verifica colisões com obstáculos ou chão e gerencia vidas/pontos
def check_collision():
    global altura, contador_pontos, velocidade_obstaculos
    global vidas, reiniciar_jogo, game_over, vidas_extras

    if altura < -1.1:
        vidas -= 1
        if vidas <= 0:
            game_over = True
            pygame.mixer.music.stop()
            som_colisao.play()
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
                    pygame.mixer.music.stop()
                    som_colisao.play()
                    global animando_morte, altura_morte, angulo_morte
                    animando_morte = True
                    altura_morte = altura
                    angulo_morte = 0.0
                else:
                    reiniciar_jogo = True

                if reiniciar_jogo:
                    vidas_extras = []

                return True
            else:
                if not obstacle['counted']:
                    obstacle['counted'] = True
                    contador_pontos += 1

    for vida in vidas_extras:
        if not vida['coletada'] and abs(vida['x']) < 0.1 and abs(vida['y'] - altura) < 0.1:
            vida['coletada'] = True
            vidas += 1

    return False

# Anima o personagem após a morte (queda + rotação)
def animar_morte(delta_time):
    global altura_morte, angulo_morte

    altura_morte += velocidade_morte * delta_time
    angulo_morte += velocidade_rotacao_morte * delta_time

# Gera vidas extras em posições seguras e as move na tela
def update_vidas_extras(delta_time):
    global vidas_extras, tempo_decorrido_vida, tempo_para_proxima_vida

    tempo_decorrido_vida += delta_time

    if tempo_decorrido_vida > tempo_para_proxima_vida:
        tempo_decorrido_vida = 0
        if random.random() < 0.5:
            x_spawn = 1.0
            altura_vida = 0.1
            margem_segura = 0.05

            obstaculo_proximo = None
            for obs in obstacles:
                if abs(obs['x'] - x_spawn) < 0.15:
                    obstaculo_proximo = obs
                    break

            if obstaculo_proximo:
                centro_gap = obstaculo_proximo['gap_position']
                limite_inferior = centro_gap - obstacle_gap / 2 + altura_vida / 2 + margem_segura
                limite_superior = centro_gap + obstacle_gap / 2 - altura_vida / 2 - margem_segura

                if limite_superior > limite_inferior:
                    y = random.uniform(limite_inferior, limite_superior)
                    vidas_extras.append({'x': x_spawn, 'y': y, 'coletada': False})
            else:
                y = random.uniform(-0.9, 0.9)
                vidas_extras.append({'x': x_spawn, 'y': y, 'coletada': False})

    for vida in vidas_extras:
        vida['x'] -= velocidade_obstaculos * delta_time

    vidas_extras = [vida for vida in vidas_extras if vida['x'] > -1.2]


def draw_vidas_extras(tex_id):

    # Desenha as vidas extras na tela usando uma textura específica.
    # Cada vida não coletada é representada por um pequeno quad.

    glBindTexture(GL_TEXTURE_2D, tex_id)
    glEnable(GL_TEXTURE_2D)

    for vida in vidas_extras:
        if not vida['coletada']:
            x = vida['x']
            y = vida['y']
            largura = 0.08
            altura_vida = 0.1

            # Desenha um quadrado com a textura da vida
            glBegin(GL_QUADS)
            glTexCoord2f(0, 1)
            glVertex2f(x - largura / 2, y - altura_vida / 2)
            glTexCoord2f(0, 0)
            glVertex2f(x + largura / 2, y - altura_vida / 2)
            glTexCoord2f(1, 0)
            glVertex2f(x + largura / 2, y + altura_vida / 2)
            glTexCoord2f(1, 1)
            glVertex2f(x - largura / 2, y + altura_vida / 2)
            glEnd()

    glDisable(GL_TEXTURE_2D)


font = ImageFont.truetype("verdana.ttf", 32)


def create_text_texture(text):

    # Cria uma textura a partir de um texto usando PIL e converte para OpenGL.

    img = Image.new("RGBA", (512, 128), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), text, font=font, fill=(255, 255, 255, 255))
    img_data = np.array(img)[::-1]  # Inverte verticalmente para OpenGL

    texture_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, img.width, img.height,
                 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
    return texture_id, img.width, img.height


def draw_obstacle_with_texture(tex_id, x, bottom, top, largura=0.1, flip_vertical=False):

    # Desenha um obstáculo com textura.
    # Se flip_vertical=True, inverte verticalmente (para obstáculos inferiores).

    glBindTexture(GL_TEXTURE_2D, tex_id)
    glEnable(GL_TEXTURE_2D)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)

    glBegin(GL_QUADS)
    if flip_vertical:
        glTexCoord2f(0, 1)
        glVertex2f(x - largura, bottom)
        glTexCoord2f(1, 1)
        glVertex2f(x + largura, bottom)
        glTexCoord2f(1, 0)
        glVertex2f(x + largura, top)
        glTexCoord2f(0, 0)
        glVertex2f(x - largura, top)
    else:
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
    # Desenha um quad (retângulo) com uma textura (geralmente usada para textos).

    glBindTexture(GL_TEXTURE_2D, tex_id)
    glEnable(GL_TEXTURE_2D)

    aspect_ratio = width / height
    quad_width = 0.5
    quad_height = quad_width / aspect_ratio
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

    # Aumenta a dificuldade conforme o jogador ganha pontos.
    # A velocidade dos obstáculos aumenta e o espaço entre eles diminui.

    global velocidade_obstaculos, obstacle_gap, contador_pontos
    velocidade_obstaculos = min((((contador_pontos / 50) + 1) * 0.5), 1.8)


def restart_game(full_reset=False, vidas_iniciais=vidas):

    # Reinicia o jogo.
    # Se full_reset=True, também zera os pontos e vidas.

    global obstacles, altura, reiniciar_jogo, contador_pontos, velocidade, vidas, iniciar_jogo, \
        game_over, vidas_extras, angulo_personagem, animando_morte, altura_morte, angulo_morte, morte_finalizada

    obstacles = []
    altura = 0
    velocidade = 0
    iniciar_jogo = False
    reiniciar_jogo = False
    vidas_extras = []
    angulo_personagem = 0.0
    animando_morte = False
    altura_morte = 0.0
    angulo_morte = 0.0
    morte_finalizada = False

    if full_reset:
        vidas = vidas_iniciais
        contador_pontos = 0
        game_over = False


def draw_game_over():
    # Exibe a mensagem "Game Over" como uma textura renderizada na tela.
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



# Inicializa e roda o loop principal do jogo
def main():
    global contador_pontos, iniciar_jogo, reiniciar_jogo

    # Inicializa janela GLFW
    window = init_window(width, height, "Slappy Squirrel")

    # Carrega texturas
    background_tex = load_background_texture("imgs/background.png")
    obstacle_tex = load_texture("imgs/obstacle-2.png")
    personagem_parado_tex = load_texture("imgs/sqrl_closed.png")[0]
    personagem_pulo_tex = load_texture("imgs/sqrl_open.png")[0]
    vida_tex = load_texture("imgs/life.png")[0]

    background_offset = 0.0

    # Define uma projeção ortográfica para visualização 2D
    glOrtho(-1.0, 1.0, -1.0, 1.0, -1.0, 1.0)

    # Ativa o blending para suportar transparência
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    # Define a cor de fundo da tela
    glClearColor(0.95, 0.5, 0.25, 1.0)

    # Define o callback de teclado
    glfw.set_key_callback(window, key_callback)

    tempo_anterior = time.time()

    # Loop principal do jogo
    while not glfw.window_should_close(window):

        # Limpa o buffer de cor
        glClear(GL_COLOR_BUFFER_BIT)

        # Calcula o tempo decorrido desde o último frame
        tempo_atual = time.time()
        delta_time = tempo_atual - tempo_anterior
        tempo_anterior = tempo_atual
        delta_time = min(delta_time, 0.05)  # Limita delta para evitar saltos grandes

        # Atualiza o offset de scroll do fundo
        if background_offset > 1.0:
            background_offset -= 1.0

        # Atualizações de lógica do jogo
        if iniciar_jogo and not game_over:
            update_character(delta_time)  # Atualiza física do personagem
            update_obstacles(delta_time)  # Move e gera obstáculos
            update_vidas_extras(delta_time)  # Move vidas extras
            update_difficulty()  # Ajusta dificuldade com base na pontuação
            background_offset += (velocidade_obstaculos * delta_time) / 15  # Scroll do fundo

        # Renderiza fundo
        draw_background(background_tex, zoom=1.2, offset_y=-0.3, scroll_offset=background_offset)

        # Renderiza obstáculos, personagem e vidas extras
        draw_obstacles(obstacle_tex[0], obstacle_tex[1])
        draw_character(personagem_parado_tex, personagem_pulo_tex, velocidade)
        draw_vidas_extras(vida_tex)

        # Renderiza texto HUD (pontuação e vidas)
        text = f"Pontuação: {contador_pontos} | Vidas: {vidas}"
        tex_id, w, h = create_text_texture(text)
        draw_textured_quad(tex_id, w, h)
        glDeleteTextures(1, [tex_id])  # Libera textura do texto

        # Se perdeu todas as vidas, mostra tela de Game Over
        if game_over:
            draw_game_over()

        # Verifica colisão
        if not game_over and check_collision():
            iniciar_jogo = False

        # Reinicia o jogo se necessário
        if reiniciar_jogo:
            restart_game()

        # Anima a morte do personagem, se aplicável
        if animando_morte:
            animar_morte(delta_time)

        # Troca buffers e processa eventos
        glfw.swap_buffers(window)
        glfw.poll_events()

    # Finaliza GLFW e fecha janela
    glfw.terminate()


if __name__ == "__main__":
    main()
