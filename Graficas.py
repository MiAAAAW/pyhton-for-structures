import sys
import pygame
from pygame.locals import *

BLANCO = 255, 255, 255
VERDE = 0, 255, 0
NEGRO = 0, 0, 0
AZUL = 81, 209, 246
ROJO = 255, 0, 0
PURPURA = 128, 0, 128
NARANJA = 255, 165, 0


class Construccion(object):
    def __init__(self, nombre: str, ancho, alto):
        self.tamaño = self.ancho, self.alto = ancho, alto
        self.pantalla = pygame.display.set_mode(self.tamaño)
        self.reloj = pygame.time.Clock()
        pygame.display.set_caption(nombre)
        pygame.init()

    def dibujar_viga(self, nombre: str, pos1, pos2, carga, tamaño=2):
        pygame.draw.line(self.pantalla, BLANCO, pos1, pos2, tamaño)
        self.agregar_texto((pos1+pos2) / (2, 2) + (-15, 15), nombre, clr=AZUL)
        self.agregar_texto((pos1 + pos2) / (2, 2) + (15, -15), "{0:.1f} N".format(round(carga, 3)), clr=AZUL)

    def dibujar_nodo(self, nombre: str, pos, tamaño=10):
        pygame.draw.circle(self.pantalla, BLANCO, (int(pos[0]), int(pos[1])), tamaño, 0)  # relleno
        self.agregar_texto(pos + (-35, 10), nombre, clr=ROJO)

    def dibujar_fuerza(self, nombre: str, pos, fuerza, tamaño=10):
        pos2 = pos+((0.1, -0.1)*fuerza)
        pygame.draw.line(self.pantalla, ROJO, (int(pos[0]), int(pos[1])), (int(pos2[0]), int(pos2[1])), tamaño)
        self.agregar_texto((pos+pos2) / 2 - (25, -25), nombre + "=" + str(fuerza), clr=NARANJA)

    def dibujar_restriccion_x(self, nombre: str, pos, tamaño=7):
        pos2 = pos-((0.2, 0) * pos)
        pygame.draw.line(self.pantalla, VERDE, pos, pos2, tamaño)
        self.agregar_texto(pos2-(0, 25), nombre, clr=VERDE)

    def dibujar_restriccion_y(self, nombre: str, pos, tamaño=7):
        pos2 = pos - ((0, 0.1) * pos)
        pygame.draw.line(self.pantalla, VERDE, pos, pos2, tamaño)
        self.agregar_texto(pos2-(0, 25), nombre, clr=VERDE)

    def dibujar_editable(self, pos, tamaño=7):
        pygame.draw.circle(self.pantalla, PURPURA, (int(pos[0]), int(pos[1])), tamaño, 0)  # relleno

    def agregar_texto(self, pos, texto: str, clr=VERDE, tamaño=24):
        fuente = pygame.font.Font(None, tamaño)
        imagen_texto = fuente.render(texto, 1, clr)
        self.pantalla.blit(imagen_texto, (int(pos[0]), int(pos[1])))

    def mantener(self):
        for evento in pygame.event.get():
            if evento.type == QUIT:
                pygame.display.quit()
                sys.exit(0)
            if evento.type == KEYDOWN and evento.key == K_ESCAPE:
                pygame.display.quit()
                sys.exit(0)
        self.reloj.tick(100)

    def mostrar(self):
        for evento in pygame.event.get():
            if evento.type == QUIT:
                pygame.display.quit()
                sys.exit(0)
            if evento.type == KEYDOWN and evento.key == K_ESCAPE:
                pygame.display.quit()
                sys.exit(0)
        pygame.display.update()
        self.pantalla.fill(NEGRO)


if __name__ == "__main__":
    G = Construccion("Prueba", 720, 480)
    G.mostrar()