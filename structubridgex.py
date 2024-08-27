import numpy as np
import math
import Graficas
import pygame
from typing import List
import json
from scipy.optimize import fmin_powell
Vector = List[float]
import time


# Inicializa Pygame
pygame.init()

# Cargar la imagen de fondo
fondo = pygame.image.load('aqua3.png')

# Opcional: Redimensionar la imagen de fondo si no coincide con el tamaño de la ventana
fondo = pygame.transform.scale(fondo, (1280, 720))  # Ajusta las dimensiones según tus necesidades

class Nodo(object):
    """Un objeto que define una posición"""
    def __init__(self, nombre: str, pos, restriccion_x=0, restriccion_y=0):
        """Nodo: tiene un nombre, posición y restricciones. Las cargas se añaden cuando se coloca el peso distribuido en la viga. Un valor opcional es optimizar, para cada dimensión la posición del nodo se puede optimizar para optimizar la construcción."""
        self.nombre: str = nombre
        self.pos = np.array(pos)
        self.carga: Vector = np.array([0, 0])
        self.lista_cargas = np.array([0])
        self.restriccion_x = restriccion_x
        self.restriccion_y = restriccion_y
        self.optimizar: List = np.array([0, 0])

    def __str__(self):
        texto: str = self.nombre
        texto += ": " + str(self.pos)
        return texto


class Viga(object):
    """Una viga o barra que se coloca entre dos nodos. Una viga conoce los dos nodos entre los que se coloca y, por lo tanto, su longitud. Con otros datos como densidad y área de sección transversal, se puede determinar el peso; la carga colocada se divide entre los dos nodos."""
    def __init__(self, nombre: str, nodos, carga_v, a, b):
        self.nombre: str = nombre
        self.longitud: float = self.absoluto(nodos[a].pos - nodos[b].pos)
        self.nodo_a = a
        self.nodo_b = b
        self.pos1: Vector = nodos[a].pos
        self.pos2: Vector = nodos[b].pos
        self.carga: Vector = np.array(carga_v)
        self.carga_nodos: Vector = 0.5 * np.array(carga_v) * self.longitud
        self.delta_0: Vector = nodos[a].pos - nodos[b].pos
        self.delta_1: Vector = nodos[b].pos - nodos[a].pos
        self.angulo_0: float = math.atan2(self.delta_0[1], self.delta_0[0])
        self.angulo_1: float = math.atan2(self.delta_1[1], self.delta_1[0])
        self.area = 0.10
        self.modulo_E = 210 * 1e+9
        self.densidad = 7850
        self.resistencia_fluencia = 250 * 1e+6
        self.fuerza_interna = 0
        self.peso = 0.0
        self.conexiones = np.zeros(len(2 * nodos))
        self.conexiones[2 * a] = math.cos(self.angulo_0)
        self.conexiones[2 * a + 1] = math.sin(self.angulo_0)
        self.conexiones[2 * b] = math.cos(self.angulo_1)
        self.conexiones[2 * b + 1] = math.sin(self.angulo_1)

    @staticmethod
    def absoluto(arr):
        """Devuelve la longitud absoluta de un vector"""
        return np.linalg.norm(arr)

    def calcular_peso_viga(self, nueva_fuerza):
        """
        Calcula el peso de una viga usando la fuerza interna de la viga y la resistencia a la fluencia del material
        :param nueva_fuerza:
        :return: -
        """
        self.fuerza_interna = abs(nueva_fuerza)
        if nueva_fuerza >= 0:
            # La fuerza está estirando la viga
            self.area = self.fuerza_interna / self.resistencia_fluencia
        else:
            # La fuerza está comprimiendo la viga
            self.area = math.pow(((self.fuerza_interna * (0.5 * self.longitud) ** 2 / (
                math.pi ** 2 * self.modulo_E)) / (math.pi / 4)), 1 / 2) * math.pi
        self.peso = self.area * self.longitud * self.densidad

    def __str__(self):
        """
        Sobrescribe el método str, imprime datos importantes de la viga
        :return texto:
        """
        texto: str = "\n"
        texto += "Viga: " + self.nombre + "\n"
        texto += "\tLongitud: {0:.2f} m\n".format(round(self.longitud, 2))
        texto += "\tÁrea: {0:.2f} mm²\n".format(round(self.area * 1e6, 2))
        texto += "\tPeso: {0:.3f} kg\n".format(round(self.peso, 3))
        return texto

    def una_linea(self):
        texto: str = self.nombre
        texto += ": {0:.2f}m".format(round(self.longitud, 2))
        texto += ", {0:.2f}mm²".format(round(self.area * 1e6, 2))
        texto += ", {0:.3f}kg".format(round(self.peso, 3))
        return texto


class Construccion(object):
    def __init__(self, nombre: str, nodos: List, lista_vigas: List, lista_cargas: List):
        """
        Crea una construcción con los nodos, vigas, cargas y restricciones dadas
        :param nombre:
        :param nodos:
        :param lista_vigas:
        """
        self.vigas_temporales = lista_vigas
        self.materiales = {}
        self.material: str = ""
        self.nombre: str = nombre
        self.ventana = Graficas.Construccion("Structubridgex", 1280, 720)
        self.nodos: List = nodos
        self.vigas: List = []
        self.cargas_actuales = 0
        self.lista_cargas = lista_cargas
        self.vigas = []
        self.ultima_iteracion = False
        self.vigas_maximas = []
        self.establecer_vigas()
        self.cargas_opcionales: List = []
        self.iteracion = 0
        

        # Declarar datos que se usarán más tarde
        self.matriz = []
        self.B = []
        self.X = []
        self.peso = np.inf
        self.obtener_materiales()
        self.grafico_interactivo = False
        print("Construcción creada...")

    def establecer_vigas(self):
        """
        Reconstruye todas las vigas entre los nodos con los nuevos valores
        :return:
        """
        self.vigas = []
        for x in range(0, len(self.vigas_temporales)):
            self.vigas.append(Viga(str(self.vigas_temporales[x][0]),
                                   self.nodos,
                                   self.lista_cargas[self.cargas_actuales][x],
                                   self.vigas_temporales[x][1],
                                   self.vigas_temporales[x][2]))

    def optimizar(self, activo=True, grafico_interactivo=True):
        """
        Optimizar generará una construcción con un peso mínimo para la carga dada
        Opcional: activo activará la función de minimización para crear una construcción altamente optimizada
        :param activo:
        :param grafico_interactivo:
        :return:
        """
        self.grafico_interactivo = grafico_interactivo
        suposicion_inicial = []
        for x in range(0, len(self.nodos)):
            if not np.any(self.nodos[x].optimizar):
                continue
            for val in range(0, len(self.nodos[x].optimizar)):
                if self.nodos[x].optimizar[val] != 0:
                    suposicion_inicial.append(self.nodos[x].pos[val])

        suposicion_inicial = np.array(suposicion_inicial)
        print("Suposición Inicial", suposicion_inicial)
        print("Calculando Construcción....")
        pesos_construccion = []
        cargas_nr_max_peso = []
        resultados = []
        self.vigas_maximas = []
        for a in range(0, len(self.lista_cargas)):
            # Iterar a través de todas las cargas
            self.cargas_actuales = a
            print("\n\nCalculando construcción para carga: ", self.cargas_actuales)
            # Crear óptimo para la carga actual
            if activo:
                resultado = fmin_powell(self.establecer_y_calcular, suposicion_inicial, xtol=0.01, ftol=0.005)
            else:
                resultado = self.establecer_y_calcular(suposicion_inicial)
            self.graficar_construccion()
            pesos_construccion.append(self.peso)
            cargas_nr_max_peso.append(a)
            resultados.append(resultado)
            self.vigas_maximas.append(self.vigas)
            for y in range(0, len(self.lista_cargas)):
                # Hacer la construcción fuerte para que el óptimo actual pueda soportar todas las cargas
                if a == y:
                    continue
                self.cargas_actuales = y
                self.establecer_y_calcular(resultado)
                for t in range(0, len(self.vigas)):
                    if self.vigas_maximas[a][t].peso < self.vigas[t].peso:
                        self.vigas_maximas[a][t] = self.vigas[t]
                # Calcular el peso del óptimo actual fuerte
                self.peso = 0
                for t in range(0, len(self.vigas)):
                    self.vigas[t] = self.vigas_maximas[a][t]
                    self.peso += self.vigas[t].peso

                if self.peso > pesos_construccion[a]:
                    pesos_construccion[a] = self.peso
                    cargas_nr_max_peso[a] = y

        minimo = min(pesos_construccion)
        indice_carga = pesos_construccion.index(minimo)
        self.cargas_actuales = cargas_nr_max_peso[indice_carga]
        self.establecer_y_calcular(resultados[indice_carga])
        self.vigas = self.vigas_maximas[indice_carga]
        self.peso = minimo
        print("\n\nEl mejor peso para todas las cargas es:", minimo, "kg")

        print("Este puente está optimizado para la carga nr: ", indice_carga)
        self.graficar_construccion(terminado=True)
        while True:
            self.ventana.mantener()

    def establecer_y_calcular(self, nuevos_valores):
        """
        Establece las posiciones variables, reconstruye todas las vigas y calcula el peso de la construcción
        :return:
        """
        self.iteracion += 1
        t = 0
        for x in range(0, len(self.nodos)):
            if not np.any(self.nodos[x].optimizar):
                continue
            for val in range(0, len(self.nodos[x].optimizar)):
                if self.nodos[x].optimizar[val] != 0:
                    self.nodos[x].pos[val] = nuevos_valores[t]
                    t += 1
        self.establecer_vigas()
        self.obtener_peso()
        if self.grafico_interactivo:
            try:
                self.graficar_construccion()
            except:
                print("\nAdvertencia: la gráfica falló \n")
        return self.peso

    def obtener_peso(self):
        peso_mas_ligero = np.inf
        mejor_material = {}
        for material in self.materiales:
            self.establecer_material(self.materiales[material])
            self.calcular_peso()
            if self.peso < peso_mas_ligero:
                mejor_material = material
                peso_mas_ligero = self.peso

        self.establecer_material(self.materiales[mejor_material])
        self.material = str(mejor_material)
        self.calcular_peso()

    def obtener_vigas_maximas(self):
        pass

    def calcular_peso(self):
        """
        Calcula el peso de cada viga y el peso total de la construcción usando álgebra lineal
        :return:
        """
        self.matriz = []
        for x in range(0, len(self.vigas)):
            self.matriz.append(self.vigas[x].conexiones)

        self.matriz = np.array(self.matriz)
        self.matriz = self.matriz.transpose()

        tamaño = np.shape(self.matriz)
        faltante = tamaño[0] - tamaño[1]
        for x in range(0, faltante):
            ceros = np.array([np.zeros(tamaño[0])])
            self.matriz = np.concatenate((self.matriz, ceros.T), axis=1)

        t = tamaño[1]
        for x in range(0, len(self.nodos)):
            if self.nodos[x].restriccion_x != 0:
                self.matriz[2 * x][t] = self.nodos[x].restriccion_x
                t += 1
            if self.nodos[x].restriccion_y != 0:
                self.matriz[2 * x + 1][t] = self.nodos[x].restriccion_y
                t += 1

        self.B = np.zeros(np.shape(self.matriz)[0])
        for x in range(0, len(self.nodos)):
            self.nodos[x].carga = np.array([0, 0])

        for x in range(0, len(self.vigas)):
            self.nodos[self.vigas[x].nodo_a].carga = \
                self.nodos[self.vigas[x].nodo_a].carga + self.vigas[x].carga_nodos
            self.nodos[self.vigas[x].nodo_b].carga = \
                self.nodos[self.vigas[x].nodo_b].carga + self.vigas[x].carga_nodos

        for x in range(0, len(self.nodos)):
            self.B[2 * x] = self.nodos[x].carga[0]
            self.B[2 * x + 1] = self.nodos[x].carga[1]

        self.peso = 0
        try:
            self.X = np.dot(np.linalg.inv(self.matriz), self.B)
        except np.linalg.LinAlgError:
            print("\nAdvertencia: Error de álgebra lineal\n")
            self.X = np.full(tamaño[0], 1e20)

        for x in range(0, len(self.vigas)):
            self.vigas[x].calcular_peso_viga(self.X[x])
            self.peso += self.vigas[x].peso

        return self.peso

    def establecer_material(self, material_actual: dict):
        """Establece el material seleccionado actualmente"""
        for viga in self.vigas:
            viga.resistencia_fluencia = material_actual["resistencia_fluencia"]
            viga.modulo_E = material_actual["modulo_E"]
            viga.densidad = material_actual["densidad"]

    def obtener_materiales(self):
        """Obtiene todos los materiales disponibles del diccionario materials.json"""
        with open("materials.json", "r") as archivo_lectura:
            self.materiales = json.load(archivo_lectura)
        archivo_lectura.close()
        self.establecer_material(self.materiales[list(self.materiales.keys())[0]])

    def __str__(self):
        """Método sobrescrito para imprimir sus datos en un cierto formato al usar print() o str()"""
        texto: str = "\n  "
        texto += "\nA =\n" + str(self.matriz)
        texto += "\n\nB = \n" + str(self.B)
        texto += "\n\nX = \n" + str(self.X)
        texto += "\n\n\t  "

        for x in range(0, len(self.vigas)):
            texto += str(self.vigas[x])

        texto += "\n\nPeso total del puente: {0:.3f} kg\n".format(round(self.peso, 3))
        return texto
    
   

    

    def graficar_construccion(self, terminado=False):
        desplazamiento: Vector = (500, 300)

        def inv(pos: Vector):
            pos: Vector = pos * np.array([1, -1])  # invierte el eje y para gráficos
            pos: Vector = pos * 170 + desplazamiento
            return pos
        
        # Dibujar el fondo en la ventana
        self.ventana.pantalla.blit(fondo, (0, 0))

       


        # Define los parámetros de la barra lateral y su color
        ANCHO_BARRA_LATERAL = 330
        COLOR_BARRA_LATERAL = (30, 30, 30)  # Un gris oscuro

        # Dibujar la barra lateral
        pygame.draw.rect(self.ventana.pantalla, COLOR_BARRA_LATERAL, (0, 0, ANCHO_BARRA_LATERAL, self.ventana.alto))

        for viga in self.vigas:
            self.ventana.dibujar_viga(viga.nombre,
                                      inv(viga.pos1),
                                      inv(viga.pos2),
                                      viga.fuerza_interna,
                                      tamaño=int((viga.area * 1e6) ** 0.7))

        for nodo in self.nodos:
            self.ventana.dibujar_nodo(nodo.nombre, inv(nodo.pos))
            self.ventana.dibujar_fuerza(nodo.nombre, inv(nodo.pos), nodo.carga)
            if nodo.restriccion_x != 0:
                self.ventana.dibujar_restriccion_x(nodo.nombre + "x", inv(nodo.pos))
            if nodo.restriccion_y != 0:
                self.ventana.dibujar_restriccion_y(nodo.nombre + "y", inv(nodo.pos))
            if np.any(nodo.optimizar):
                self.ventana.dibujar_editable(inv(nodo.pos))


        # Cargar el logo
        logo = pygame.image.load('BSLOGO.png')
        logo = pygame.transform.scale(logo, (150, 150))  # Ajusta el tamaño según tus necesidades

        # Coordenadas para colocar el logo
        x_logo = 80
        y_logo = 50

        # Dibujar el logo
        self.ventana.pantalla.blit(logo, (x_logo, y_logo))

        # Ajustar y_pos para que el texto comience después del logo
        #y_pos = y_logo + logo.get_height() + 100

         # Agregar información a la barra lateral
        fuente = pygame.font.Font(None, 30)
        informacion = [
            "       STRUCTUBRIDGEX",
            "---------------------------------------",
            "Peso: {0:.3f} kg".format(round(self.peso, 3)),
            "Material: ",
             self.material,
            "Iteración: " + str(self.iteracion),
        ]

        y_pos = 220
        for linea in informacion:
            texto = fuente.render(linea, True, (255, 255, 255))  # Texto en color blanco
            self.ventana.pantalla.blit(texto, (20, y_pos))
            y_pos += 40  # Incrementa la posición para la siguiente línea       

        titulo = "Software Simulador de Optimización para PuenteS"
        descripcion = "Simulación y optimización estructural para minimizar el peso soportando diversas cargas."


        self.ventana.agregar_texto((600, 10), titulo, clr=(0, 255, 0), tamaño=30)  # Título
        self.ventana.agregar_texto((350, 30), descripcion, clr=(0, 255, 0), tamaño=30)  # Título
         

        # self.ventana.agregar_texto((50, 70), "Peso: {0:.3f} kg".format(round(self.peso, 3)))
        # self.ventana.agregar_texto((50, 90), "Material: " + self.material)
        # self.ventana.agregar_texto((50, 120), "Iteración: " + str(self.iteracion))
        if terminado:
            self.ventana.agregar_texto((350, 50), "SE ENCONTRÓ LA SOLUCIÓN ÓPTIMA: ")
            self.ventana.agregar_texto((50, 520), "NODOS: ")
            for x in range(0, len(self.nodos)):
                b = 50 + (x // 5) * 150
                h = (x % 5) * 30 + 550
                self.ventana.agregar_texto((b, h), str(self.nodos[x]))
                self.ventana.agregar_texto((400, 520), "VIGAS: ")
            for x in range(0, len(self.vigas)):
                b = 400 + (x // 5) * 300
                h = (x % 5) * 30 + 550
                self.ventana.agregar_texto((b, h), self.vigas[x].una_linea())
        self.ventana.mostrar()


if __name__ == "__main__":
    np.set_printoptions(precision=2)
    escala: float = 1  # metro
    carga: float = 1000  # Newton

    # Una lista de todos los nodos en la construcción
    o_nodos = [
        Nodo("A", (0.00001, 0.00001), restriccion_x=-1, restriccion_y=-1),
        Nodo("B", (1.00001 * escala, 0.00001)),
        Nodo("C", (1.99999 * escala, 0.00001)),
        Nodo("D", (3.00001 * escala, 0.00001)),
        Nodo("E", (4.00001 * escala, 0.00001), restriccion_y=-1),
        Nodo("F", (3.00002 * escala, 1.00002 * escala)),
        Nodo("G", (2.00001 * escala, 1.000001 * escala)),
        Nodo("H", (1.00003 * escala, 1.00003 * escala))
    ]

    # Una lista de todas las vigas o barras que se conectan a ciertos nodos
    o_vigas = [
        ["AB", 0, 1],
        ["AH", 0, 7],
        ["BC", 1, 2],
        ["BH", 1, 7],
        ["BG", 1, 6],
        ["CD", 2, 3],
        ["CG", 2, 6],
        ["DE", 3, 4],
        ["DF", 3, 5],
        ["DG", 3, 6],
        ["EF", 4, 5],
        ["FG", 5, 6],
        ["GH", 6, 7],
    ]

    # Una lista de todas las cargas diferentes colocadas en las vigas
    o_cargas = [
        [
            [0, -1 * carga],
            [0, 0],
            [0, -1 * carga],
            [0, 0],
            [0, 0],
            [0, -1 * carga],
            [0, 0],
            [0, -1 * carga],
            [0, 0],
            [0, 0],
            [0, 0],
            [0, 0],
            [0, 0]
        ],
        [
            [0, -2 * carga],
            [0, 0],
            [0, -1 * carga],
            [0, 0],
            [0, 0],
            [0, -0.5 * carga],
            [0, 0],
            [0, -1 * carga],
            [0, 0],
            [0, 0],
            [0, 0],
            [0, 0],
            [0, 0]
        ],
        [
            [0, -3 * carga],
            [0, 0],
            [0, -1 * carga],
            [0, 0],
            [0, 0],
            [0, -4 * carga],
            [0, 0],
            [0, -1 * carga],
            [0, 0],
            [0, 0],
            [0, 0],
            [0, 0],
            [0, 0]
        ]
    ]

    # Todas

     # Todas las dimensiones de los nodos que se optimizarán se les da un valor de 1
    o_nodos[1].optimizar = np.array([1, 0])
    o_nodos[2].optimizar = np.array([1, 0])
    o_nodos[3].optimizar = np.array([1, 0])
    o_nodos[5].optimizar = np.array([1, 1])
    o_nodos[6].optimizar = np.array([1, 1])
    o_nodos[7].optimizar = np.array([1, 1])

    # Crea una construcción con los nodos y vigas dados
    puente_1 = Construccion("Puente 1", o_nodos, o_vigas, o_cargas)

    # El puente se calcula para obtener la relación peso/carga más óptima
    puente_1.optimizar(activo=True, grafico_interactivo=True)
    print(puente_1)