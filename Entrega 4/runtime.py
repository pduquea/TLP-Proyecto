#!/usr/bin/env python
# -*- coding: utf-8 -*-  # comentario: encoding añadido para soportar caracteres no-ASCII
from __future__ import print_function  # comentario: compatibilidad print Py2/Py3
import sys
import json
import time
import random
import Tkinter as tk
import tkMessageBox # Necesario para el GAME OVER
# Quitamos os y msvcrt ya que la GUI maneja el dibujo y el input
# Compatibilidad entre Python2/3 para comprobacion de strings
try:
    BSTRING = basestring
except NameError:
    BSTRING = str
 

class Juego:
    def __init__(self, datos_juego):
        self.datos_juego = datos_juego
        self.tipo_juego = self.datos_juego.get('tipo_juego', 'TETRIS')
        config = self.datos_juego.get('config', {})
        self.ancho = config.get('grid_size', [10, 20])[0]
        self.alto = config.get('grid_size', [10, 20])[1]
        self.grid = [[0 for _ in range(self.ancho)] for _ in range(self.alto)]
        self.puntuacion = 0
        self.juego_terminado = False
        # comentario: inicializar atributos usados por dibujar() para compatibilidad
        self.pieza_actual = None  # usada por TETRIS
        self.color_pieza_actual = None  # usada por dibujar incluso si no es TETRIS
        self.pieza_x = 0
        self.pieza_y = 0
        self.pieza_rotacion = 0
        
        # Configuracion de la GUI
        self.root = tk.Tk()
        self.root.title("BrickScript - " + self.tipo_juego)
        self.root.protocol("WM_DELETE_WINDOW", self.cerrar_ventana)
        
        self.taman_celda = 25 
        self.ancho_canvas = self.ancho * self.taman_celda
        self.alto_canvas = self.alto * self.taman_celda
        
        # Canvas para dibujar el juego
        self.canvas = tk.Canvas(self.root, width=self.ancho_canvas, height=self.alto_canvas, bg='#111111')
        self.canvas.pack(side=tk.LEFT, padx=10, pady=10)

        # Marco lateral para la puntuacion y controles
        self.marco_score = tk.Frame(self.root, width=150, height=self.alto_canvas, bg='#222222')
        self.marco_score.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)
        
        self.label_score = tk.Label(self.marco_score, text="PUNTUACION\n0", bg='#222222', fg='white', font=('Consolas', 16, 'bold'))
        self.label_score.pack(pady=40, padx=10)
        
        self.label_controles = tk.Label(self.marco_score, text="CONTROLES\nFlechas: Mover/Rotar", bg='#222222', fg='gray', font=('Consolas', 10))
        self.label_controles.pack(pady=20, padx=10)

        self.root.bind('<Key>', self.manejar_input_gui)
        
        if self.tipo_juego == 'TETRIS':
            self.pieza_actual = None
            self.color_pieza_actual = None
            self.pieza_x, self.pieza_y, self.pieza_rotacion = 0, 0, 0
            self.velocidad_gravedad = 0.4
            self.powerups_activos = []  # Lista para almacenar powerups en el tablero
            self.rotaciones_l_piece = 0  # Contador para el logro de powerup
            self.lineas_limpias_simultaneas = 0  # Contador para powerups
        
        if self.tipo_juego == 'SNAKE':
            # Estado de la serpiente y elementos del juego
            self.serpiente_cuerpo = []
            self.serpiente_direccion = (1, 0)
            self.posicion_comida = None
            self.posicion_poison = None
            self.posicion_powerup = None
            self.obstacle_positions = []
            self.grow_pending = 0
            self.velocidad_gravedad = 0.15
            self.invulnerable = False
            self.invulnerable_tiempo = 0
            self.nivel_seleccionado = False

            # Detectar forma de segmento desde DEFINE SHAPE / shapes en el archivo de juego
            self.snake_shape = None
            shapes_def = self.datos_juego.get('shapes', {})
            # Prefer explicit 'type' declared in shapes definitions
            for s in shapes_def.values():
                if isinstance(s, dict) and s.get('type'):
                    self.snake_shape = s.get('type')
                    break
            # Backwards-compatible heuristics if no explicit TYPE provided
            if not self.snake_shape:
                for name in ('BALL', 'PIXEL', 'TRI'):
                    if name in shapes_def:
                        entry = shapes_def[name]
                        if isinstance(entry, dict) and entry.get('type'):
                            self.snake_shape = entry.get('type')
                            break
                        else:
                            self.snake_shape = name
                            break
            # Normalizar a nombres simples y mapear sinónimos
            if isinstance(self.snake_shape, BSTRING):
                try:
                    s = self.snake_shape.upper()
                except Exception:
                    s = None
                if s in ('BALL', 'CIRCLE'):
                    self.snake_shape = 'CIRCLE'
                elif s in ('TRI', 'TRIANGLE'):
                    self.snake_shape = 'TRI'
                else:
                    if s in ('RECT', 'RECTANGLE', 'PIXEL', 'SQUARE'):
                        self.snake_shape = None
                    else:
                        self.snake_shape = None
            else:
                self.snake_shape = None

            # Cargar niveles desde el JSON generado por el compilador
            self.levels = self.datos_juego.get('levels', {})
            self.current_level = None
            self.level_config = {}
            self.tail_colors = []
            self.is_nyan_mode = False

            # Mostrar menú de selección de nivel (si hay niveles o usar defaults)
            self.mostrar_menu_nivel()
        
        self.timer_gravedad = 0
        # Sólo ejecutar ON_START automáticamente para juegos que no sean SNAKE
        if self.tipo_juego != 'SNAKE':
            self.ejecutar_evento('ON_START')
        self.timer_id = None # Para controlar el loop de Tkinter

    def run(self):
        # Inicia el ciclo principal de juego de Tkinter
        # Si es Snake y no se ha seleccionado nivel, mostrar el menú y esperar
        if self.tipo_juego == 'SNAKE' and not getattr(self, 'nivel_seleccionado', False):
            self.root.mainloop()
            return
        self.root.after(50, self.game_loop)
        self.root.mainloop()

    def game_loop(self):
        if self.juego_terminado:
            self.mostrar_game_over()
            return
        # Manejo de invulnerabilidad para Snake
        if self.tipo_juego == 'SNAKE' and getattr(self, 'invulnerable', False):
            try:
                self.invulnerable_tiempo -= 0.05
            except Exception:
                self.invulnerable_tiempo = 0
            if self.invulnerable_tiempo <= 0:
                self.invulnerable = False
                self.invulnerable_tiempo = 0

        # Logica de TICK/Gravedad
        self.timer_gravedad += 0.05
        if self.timer_gravedad >= getattr(self, 'velocidad_gravedad', 0.15):
            self.timer_gravedad = 0
            self.ejecutar_evento('ON_TICK')

        self.dibujar()

        # Programa el siguiente ciclo de juego
        self.timer_id = self.root.after(50, self.game_loop)
        
    def cerrar_ventana(self):
        # Detiene el loop de juego de forma segura
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
        self.root.destroy()
        sys.exit(0)


    def manejar_input_gui(self, event):
        key = event.keysym.upper()

        if self.tipo_juego == 'TETRIS':
            if key == 'UP': self.ejecutar_evento('ON_KEY_UP')
            elif key == 'DOWN': self.ejecutar_evento('ON_KEY_DOWN')
            elif key == 'LEFT': self.ejecutar_evento('ON_KEY_LEFT')
            elif key == 'RIGHT': self.ejecutar_evento('ON_KEY_RIGHT')
        elif self.tipo_juego == 'SNAKE':
            if key == 'UP': self.snake_cambiar_direccion('UP')
            elif key == 'DOWN': self.snake_cambiar_direccion('DOWN')
            elif key == 'LEFT': self.snake_cambiar_direccion('LEFT')
            elif key == 'RIGHT': self.snake_cambiar_direccion('RIGHT')


    def dibujar(self):
        self.canvas.delete("all") 
        self.label_score.config(text="PUNTUACION\n" + str(self.puntuacion))
 
        COLOR_GRID_FIJA = '#343434' 
        COLOR_PIEZA = self.color_pieza_actual if self.color_pieza_actual else '#00FFFF' # Color de la pieza desde el .brick
        COLOR_SNAKE_CABEZA = '#00FF00' 
        COLOR_SNAKE_CUERPO = '#33CC33' 
        COLOR_FOOD = '#FF0000'      
        
        # Dibuja la cuadricula estatica (grid base)
        for y in range(self.alto):
            for x in range(self.ancho):
                if self.grid[y][x] == 1:
                     self.dibujar_celda(x, y, COLOR_GRID_FIJA)

        # Dibuja powerups activos
        if self.tipo_juego == 'TETRIS':
            for powerup in self.powerups_activos:
                self.dibujar_celda(powerup['x'], powerup['y'], powerup['color'])

        # Dibujar la pieza actual de Tetris
        if self.tipo_juego == 'TETRIS' and self.pieza_actual:
            matriz_pieza = self.pieza_actual[self.pieza_rotacion]
            for y_offset, fila in enumerate(matriz_pieza):
                for x_offset, celda in enumerate(fila):
                    if celda == 1:
                        self.dibujar_celda(self.pieza_x + x_offset, self.pieza_y + y_offset, COLOR_PIEZA)
        
        if self.tipo_juego == 'SNAKE':
            if self.posicion_comida:
                x, y = self.posicion_comida
                self.dibujar_celda(x, y, COLOR_FOOD)
            if getattr(self, 'posicion_poison', None):
                x, y = self.posicion_poison
                self.dibujar_celda(x, y, '#9933FF', shape='CIRCLE')
            if getattr(self, 'posicion_powerup', None):
                x, y = self.posicion_powerup
                self.dibujar_celda(x, y, '#FFFF00', shape='CIRCLE')
            for (x, y) in self.obstacle_positions:
                self.dibujar_celda(x, y, '#555555')
            for i, segmento in enumerate(self.serpiente_cuerpo):
                x, y = segmento
                # Nyan mode: head circle with cat ears, tail rainbow
                if self.is_nyan_mode:
                    if i == 0:
                        # cabeza como circulo (color verde cabeza)
                        self.dibujar_celda(x, y, COLOR_SNAKE_CABEZA, shape='CIRCLE')
                        # dibujar orejas simples (triangulos)
                        ts = self.taman_celda
                        x1, y1 = x * ts, y * ts
                        x2, y2 = x1 + ts, y1 + ts
                        # oreja izquierda
                        lx1 = x1 + ts * 0.2
                        lx2 = x1 + ts * 0.4
                        points_l = [lx1, y1 + ts*0.25, lx2, y1, lx1 + ts*0.05, y1 + ts*0.05]
                        # oreja derecha
                        rx1 = x2 - ts * 0.2
                        rx2 = x2 - ts * 0.4
                        points_r = [rx1, y1 + ts*0.25, rx2, y1, rx1 - ts*0.05, y1 + ts*0.05]
                        try:
                            self.canvas.create_polygon(points_l, fill='#333333', outline='')
                            self.canvas.create_polygon(points_r, fill='#333333', outline='')
                        except Exception:
                            pass
                    else:
                        if self.tail_colors:
                            color = self.tail_colors[i % len(self.tail_colors)]
                        else:
                            color = COLOR_SNAKE_CUERPO
                        # forma opcional desde DEFINE SHAPE
                        # forma opcional desde DEFINE SHAPE (ya normalizada)
                        shape = self.snake_shape
                        if shape == 'CIRCLE':
                            self.dibujar_celda(x, y, color, shape='CIRCLE')
                        elif shape == 'TRI':
                            self.dibujar_celda(x, y, color, shape='TRI')
                        else:
                            self.dibujar_celda(x, y, color)
                else:
                    color = COLOR_SNAKE_CABEZA if i == 0 else COLOR_SNAKE_CUERPO
                    shape = self.snake_shape  # already 'CIRCLE', 'TRI' or None
                    self.dibujar_celda(x, y, color, shape=shape)

    def dibujar_celda(self, x, y, color, shape=None):
        ts = self.taman_celda 
        x1, y1 = x * ts, y * ts
        x2, y2 = x1 + ts, y1 + ts
        shape_type = None
        if isinstance(shape, BSTRING):
            shape_type = shape.upper()
        if shape_type == 'CIRCLE' or shape_type == 'BALL':
            self.canvas.create_oval(x1, y1, x2, y2, fill=color, outline='#000000')
        elif shape_type == 'TRI' or shape_type == 'TRIANGLE':
            cx = (x1 + x2) / 2
            points = [cx, y1, x2, y2, x1, y2]
            self.canvas.create_polygon(points, fill=color, outline='#000000')
        else:
            self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline='#000000')


    def ejecutar_evento(self, nombre_evento):
        evento_definido = nombre_evento in self.datos_juego['events']
        if evento_definido:
            for accion in self.datos_juego['events'][nombre_evento]:
                verbo, objeto = accion.get('accion'), accion.get('objeto')
                
                if verbo == 'INCREASE_SCORE': self.puntuacion += int(objeto)
                if verbo == 'DECREASE_SCORE': self.puntuacion -= int(objeto)
                if verbo == 'GAME_OVER': self.juego_terminado = True
                if verbo == 'SET_INVULNERABLE':
                    self.invulnerable = True
                    try:
                        self.invulnerable_tiempo = float(self.invulnerability_duration or 0)
                    except Exception:
                        self.invulnerable_tiempo = 0

                if self.tipo_juego == 'TETRIS':
                    if verbo == 'SPAWN': self.tetris_spawn_pieza()
                    if verbo == 'MOVE': self.tetris_mover_pieza(accion['params'][0])
                    if verbo == 'ROTATE': self.tetris_rotar_pieza()

                if self.tipo_juego == 'SNAKE':
                    if verbo == 'SPAWN' and objeto == 'PLAYER': self.snake_spawn_jugador(accion)
                    if verbo == 'SPAWN' and objeto == 'FOOD': self.snake_spawn_comida()
                    if verbo == 'SPAWN' and objeto == 'POISON': self.snake_spawn_poison()
                    if verbo == 'SPAWN' and objeto == 'POWERUP': self.snake_spawn_powerup()
                    if verbo == 'MOVE' and objeto == 'PLAYER': self.snake_mover_jugador()
                    if verbo == 'GROW':
                        try:
                            amt = int(accion.get('params', [1])[0])
                        except Exception:
                            amt = 1
                        self.snake_crecer(amt)

        if self.tipo_juego == 'SNAKE' and not evento_definido:
            if nombre_evento == 'ON_EAT_POISON':
                # Guardar puntuacion antes para detectar si baja A cero
                puntuacion_antes = self.puntuacion
                self.puntuacion -= 10
                if self.puntuacion < 0:
                    self.puntuacion = 0
                # Game over solo si la puntuacion BAJA A cero (no si ya estaba en 0)
                if puntuacion_antes > 0 and self.puntuacion == 0:
                    self.juego_terminado = True
                if getattr(self, 'poison_enabled', False):
                    self.snake_spawn_poison()
            elif nombre_evento == 'ON_EAT_POWERUP':
                # Activar invulnerabilidad por la duracion del nivel
                self.invulnerable = True
                try:
                    self.invulnerable_tiempo = float(self.invulnerability_duration or 0)
                except Exception:
                    self.invulnerable_tiempo = 0
                # Siempre spawnearse otro powerup
                self.snake_spawn_powerup()
            elif nombre_evento == 'ON_COLLISION_OBSTACLE':
                if self.puntuacion <= 0:
                    self.juego_terminado = True
                else:
                    self.puntuacion = 0

    def tetris_spawn_pieza(self):
        # Seleccion ponderada basada en CHANCE sin usar numpy
        nombres_piezas = self.datos_juego['shapes'].keys()
        pesos = []
        for nombre in nombres_piezas:
            chance = self.datos_juego['shapes'][nombre].get('chance', 1)
            pesos.append(chance)
        
        # Crea lista expandida segun pesos 
        lista_ponderada = []
        for i, nombre in enumerate(nombres_piezas):
            lista_ponderada.extend([nombre] * pesos[i])
        
        # Elige aleatoriamente de la lista ponderada
        nombre_pieza = random.choice(lista_ponderada)
        
        datos_pieza = self.datos_juego['shapes'][nombre_pieza]
        self.pieza_actual = datos_pieza['estados']
        color_hex = datos_pieza.get('color', '00FFFF')
        if color_hex and not color_hex.startswith('#'):
            color_hex = '#' + color_hex
        self.color_pieza_actual = color_hex if color_hex else '#00FFFF'
        self.pieza_x, self.pieza_y, self.pieza_rotacion = self.ancho / 2 - 2, 0, 0
        if self.tetris_verificar_colision(self.pieza_x, self.pieza_y, self.pieza_rotacion):
            self.juego_terminado = True

    def tetris_mover_pieza(self, direccion):
        if not self.pieza_actual: return
        dx, dy = 0, 0
        if direccion == 'LEFT': dx = -1
        elif direccion == 'RIGHT': dx = 1
        elif direccion == 'DOWN': dy = 1
        if not self.tetris_verificar_colision(self.pieza_x + dx, self.pieza_y + dy, self.pieza_rotacion):
            self.pieza_x += dx
            self.pieza_y += dy
        elif dy > 0:
            self.tetris_fijar_pieza()

    def tetris_rotar_pieza(self):
        if not self.pieza_actual: return
        nueva_rotacion = (self.pieza_rotacion + 1) % len(self.pieza_actual)
        if not self.tetris_verificar_colision(self.pieza_x, self.pieza_y, nueva_rotacion):
            self.pieza_rotacion = nueva_rotacion
            # Contar rotaciones de L_PIECE (si es que existe) para logro de powerup
            self.rotaciones_l_piece += 1

    def tetris_fijar_pieza(self):
        matriz_pieza = self.pieza_actual[self.pieza_rotacion]
        for y_offset, fila in enumerate(matriz_pieza):
            for x_offset, celda in enumerate(fila):
                if celda == 1:
                    px = self.pieza_x + x_offset
                    py = self.pieza_y + y_offset
                    if 0 <= py < self.alto and 0 <= px < self.ancho:
                        self.grid[py][px] = 1
                        # Verificar si la pieza toca un powerup
                        for powerup in self.powerups_activos:
                            if powerup['x'] == px and powerup['y'] == py:
                                self.puntuacion += 50  # Bonus por recoger powerup
                                self.powerups_activos.remove(powerup)
        
        self.pieza_actual = None
        self.color_pieza_actual = None
        self.tetris_limpiar_lineas()
        self.ejecutar_evento('ON_START')

    def tetris_verificar_colision(self, x, y, rotacion):
        if not self.pieza_actual: return False
        matriz_pieza = self.pieza_actual[rotacion]
        for y_offset, fila in enumerate(matriz_pieza):
            for x_offset, celda in enumerate(fila):
                if celda == 1:
                    nuevo_x, nuevo_y = x + x_offset, y + y_offset
                    if not (0 <= nuevo_x < self.ancho and 0 <= nuevo_y < self.alto and self.grid[nuevo_y][nuevo_x] == 0):
                        return True
        return False

    def tetris_limpiar_lineas(self):
        nuevo_grid = [fila for fila in self.grid if not all(fila)]
        lineas_limpias = self.alto - len(nuevo_grid)
        if lineas_limpias > 0:
            self.grid = [[0] * self.ancho for _ in range(lineas_limpias)] + nuevo_grid
            for _ in range(lineas_limpias): 
                self.ejecutar_evento('ON_LINE_CLEAR')
            
            #Si se limpian 3+ lineas simultaneas, spawneamos un powerup
            if lineas_limpias >= 3 and self.rotaciones_l_piece >= 10:
                self.tetris_spawn_powerup()
                self.rotaciones_l_piece = 0 
    
    def tetris_spawn_powerup(self):
        # Spawneamos el powerup BONUS_STAR si existe
        if 'powerups' in self.datos_juego and 'BONUS_STAR' in self.datos_juego['powerups']:
            # Encontrar una posicion aleatoria vacia en el grid
            while True:
                x = random.randint(0, self.ancho - 1)
                y = random.randint(0, self.alto - 1)
                if self.grid[y][x] == 0:
                    powerup_data = self.datos_juego['powerups']['BONUS_STAR']
                    color_hex = powerup_data.get('color', 'FFD700')
                    if color_hex and not color_hex.startswith('#'):
                        color_hex = '#' + color_hex
                    self.powerups_activos.append({
                        'x': x,
                        'y': y,
                        'color': color_hex if color_hex else '#FFD700'
                    })
                    break
    
    def snake_spawn_jugador(self, accion):
        coords = accion['params'][0] if accion['params'] else [self.ancho / 2, self.alto / 2]
        self.serpiente_cuerpo = [(coords[0], coords[1])]
        self.serpiente_direccion = (1, 0)
        
    def snake_spawn_comida(self):
        while True:
            x, y = random.randint(0, self.ancho - 1), random.randint(0, self.alto - 1)
            if (x, y) not in self.serpiente_cuerpo and (x, y) not in self.obstacle_positions:
                self.posicion_comida = (x, y)
                break
        # Generar poison si el nivel lo permite
        if getattr(self, 'poison_enabled', False) and not getattr(self, 'posicion_poison', None):
            self.snake_spawn_poison()

    def snake_spawn_poison(self):
        if not getattr(self, 'poison_enabled', False):
            return
        while True:
            x, y = random.randint(0, self.ancho - 1), random.randint(0, self.alto - 1)
            if (x, y) not in self.serpiente_cuerpo and (x, y) != self.posicion_comida and (x, y) not in self.obstacle_positions:
                self.posicion_poison = (x, y)
                break

    def snake_spawn_powerup(self):
        if not getattr(self, 'powerup_enabled', False):
            return
        while True:
            x, y = random.randint(0, self.ancho - 1), random.randint(0, self.alto - 1)
            if (x, y) not in self.serpiente_cuerpo and (x, y) != self.posicion_comida and (x, y) != getattr(self, 'posicion_poison', None) and (x, y) not in self.obstacle_positions:
                self.posicion_powerup = (x, y)
                break
                
    def snake_mover_jugador(self):
        if not self.serpiente_cuerpo: return
        cabeza_x, cabeza_y = self.serpiente_cuerpo[0]
        dir_x, dir_y = self.serpiente_direccion
        nueva_cabeza = (cabeza_x + dir_x, cabeza_y + dir_y)
        # Colisiones con paredes
        if not (0 <= nueva_cabeza[0] < self.ancho and 0 <= nueva_cabeza[1] < self.alto):
            if getattr(self, 'invulnerable', False):
                # Cuando hay invulnerabilidad, la serpiente atraviesa la pared y reaparece
                # en el lado opuesto del panel de juego.
                nueva_cabeza = (nueva_cabeza[0] % self.ancho, nueva_cabeza[1] % self.alto)
            else:
                if self.is_nyan_mode:
                    if self.puntuacion <= 0:
                        self.juego_terminado = True
                    else:
                        self.puntuacion = 0
                    return
                self.ejecutar_evento('ON_COLLISION_WALL')
                return

        # Colision con si mismo
        if nueva_cabeza in self.serpiente_cuerpo[:-1]:
            if getattr(self, 'invulnerable', False):
                if self.puntuacion <= 0:
                    self.juego_terminado = True
                else:
                    self.puntuacion = 0
                return
            if self.is_nyan_mode:
                if self.puntuacion <= 0:
                    self.juego_terminado = True
                else:
                    self.puntuacion = 0
                return
            self.ejecutar_evento('ON_COLLISION_SELF')
            return

        # Colision con obstaculos
        if getattr(self, 'obstacles_enabled', False) and nueva_cabeza in self.obstacle_positions:
            if getattr(self, 'invulnerable', False):
                if self.puntuacion <= 0:
                    self.juego_terminado = True
                else:
                    self.puntuacion = 0
                return
            if self.puntuacion - 50 <= 0:
                self.juego_terminado = True
                return
            self.puntuacion -= 50
            self.ejecutar_evento('ON_COLLISION_OBSTACLE')
            return

        self.serpiente_cuerpo.insert(0, nueva_cabeza)

        # Comer comida / poison / powerup
        if nueva_cabeza == self.posicion_comida:
            self.puntuacion += 10
            self.snake_crecer(1)
            self.posicion_comida = None
            self.snake_spawn_comida()
            self.ejecutar_evento('ON_EAT_FOOD')
        elif getattr(self, 'posicion_poison', None) and nueva_cabeza == self.posicion_poison:
            self.posicion_poison = None
            # Penalizacion por comer fruta venenosa (por defecto)
            try:
                self.puntuacion -= 10
            except Exception:
                self.puntuacion = 0
            self.ejecutar_evento('ON_EAT_POISON')
        elif getattr(self, 'posicion_powerup', None) and nueva_cabeza == self.posicion_powerup:
            self.posicion_powerup = None
            # El evento ON_EAT_POWERUP activará la invulnerabilidad
            self.ejecutar_evento('ON_EAT_POWERUP')

        if self.grow_pending > 0:
            self.grow_pending -= 1
        else:
            self.serpiente_cuerpo.pop()

    def snake_cambiar_direccion(self, direccion):
        if direccion == 'UP' and self.serpiente_direccion[1] != 1:
            self.serpiente_direccion = (0, -1)
        elif direccion == 'DOWN' and self.serpiente_direccion[1] != -1:
            self.serpiente_direccion = (0, 1)
        elif direccion == 'LEFT' and self.serpiente_direccion[0] != 1:
            self.serpiente_direccion = (-1, 0)
        elif direccion == 'RIGHT' and self.serpiente_direccion[0] != -1:
            self.serpiente_direccion = (1, 0)

    def snake_crecer(self, cantidad=1):
        # Incrementa contador de crecimiento; el cuerpo crecerá en los siguientes ticks
        try:
            self.grow_pending += int(cantidad)
        except Exception:
            try:
                self.grow_pending += 1
            except Exception:
                self.grow_pending = 1


    # METODOS DE SALIDA (ADAPTADOS A GUI)

    def mostrar_game_over(self):
        tkMessageBox.showinfo("Juego Terminado", "Puntuacion Final: " + str(self.puntuacion))
        self.root.destroy()
        sys.exit(0)

    def mostrar_menu_nivel(self):
        niveles = list(self.levels.keys())
        # Si no hay niveles, crear valores por defecto para compatibilidad
        if not niveles:
            self.levels = {
                'BABY': {'SPEED': '0.15'},
                'ENTHUSIAST': {'SPEED': '0.10', 'POISON_FOOD': '1', 'INVULNERABILITY_DURATION': '5'},
                'NYAN': {'SPEED': '0.06', 'POISON_FOOD': '1', 'OBSTACLES': '5', 'INVULNERABILITY_DURATION': '5', 'TAIL_COLORS': ['#FF0000','#FF7F00','#FFFF00','#00FF00','#0000FF','#4B0082','#9400D3']}
            }
            niveles = list(self.levels.keys())

        self.menu_frame = tk.Frame(self.root, bg='#111111')
        self.menu_frame.place(x=0, y=0, width=self.ancho_canvas, height=self.alto_canvas)

        label = tk.Label(self.menu_frame, text='Seleccione dificultad de Snake', bg='#111111', fg='white', font=('Consolas', 18, 'bold'))
        label.pack(pady=20)

        self.nivel_seleccion = tk.StringVar()
        self.nivel_seleccion.set(niveles[0])

        for lvl in niveles:
            tk.Radiobutton(self.menu_frame, text=lvl, variable=self.nivel_seleccion, value=lvl, bg='#111111', fg='white', selectcolor='#333333', font=('Consolas', 14)).pack(anchor='w', padx=20)

        boton = tk.Button(self.menu_frame, text='Iniciar Juego', command=self.seleccionar_nivel, bg='#00AA00', fg='white', font=('Consolas', 12, 'bold'))
        boton.pack(pady=30)

    def seleccionar_nivel(self):
        self.current_level = self.nivel_seleccion.get()
        self.level_config = self.levels.get(self.current_level, {})
        self.aplicar_config_nivel()
        self.nivel_seleccionado = True
        if hasattr(self, 'menu_frame'):
            try:
                self.menu_frame.destroy()
            except Exception:
                pass
        # Iniciar el juego ahora que hay un nivel seleccionado
        self.ejecutar_evento('ON_START')
        # Asegurar spawn inicial de elementos tras ON_START
        if self.tipo_juego == 'SNAKE':
            if not getattr(self, 'posicion_comida', None):
                self.snake_spawn_comida()
            if getattr(self, 'powerup_enabled', False) and not getattr(self, 'posicion_powerup', None):
                self.snake_spawn_powerup()
            if getattr(self, 'poison_enabled', False) and not getattr(self, 'posicion_poison', None):
                self.snake_spawn_poison()
        self.root.after(50, self.game_loop)

    def aplicar_config_nivel(self):
        self.tail_colors = self.level_config.get('TAIL_COLORS', []) if isinstance(self.level_config, dict) else []
        self.is_nyan_mode = bool(self.tail_colors)
        self.poison_enabled = bool(int(self.level_config.get('POISON_FOOD', '0') if self.level_config.get('POISON_FOOD') is not None else 0))
        self.obstacles_enabled = bool(int(self.level_config.get('OBSTACLES', '0') if self.level_config.get('OBSTACLES') is not None else 0))
        self.powerup_enabled = bool(int(self.level_config.get('INVULNERABILITY_DURATION', '0') if self.level_config.get('INVULNERABILITY_DURATION') is not None else 0))
        try:
            self.invulnerability_duration = float(self.level_config.get('INVULNERABILITY_DURATION', '0') or 0)
        except Exception:
            self.invulnerability_duration = 0
        try:
            self.velocidad_gravedad = float(self.level_config.get('SPEED', '0.15') or 0.15)
        except Exception:
            self.velocidad_gravedad = 0.15
        if self.obstacles_enabled:
            try:
                self.snake_generar_obstaculos(int(self.level_config.get('OBSTACLES', '3')))
            except Exception:
                self.snake_generar_obstaculos(3)

    def snake_generar_obstaculos(self, cantidad):
        self.obstacle_positions = []
        for _ in range(cantidad):
            attempts = 0
            while attempts < 200:
                x = random.randint(1, self.ancho - 2)
                y = random.randint(1, self.alto - 2)
                if (x, y) not in self.serpiente_cuerpo and (x, y) != self.posicion_comida and (x, y) not in self.obstacle_positions:
                    self.obstacle_positions.append((x, y))
                    break
                attempts += 1

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python runtime.py <archivo_juego.json>")  # comentario: reemplazado por print() para Py3
        sys.exit(1)
    archivo_juego = sys.argv[1]
    try:
        with open(archivo_juego, 'r') as f:
            datos_juego = json.load(f)
    except IOError:
        print("Error: No se pudo encontrar el archivo " + archivo_juego)  # comentario: print() Py3
        sys.exit(1)
    juego = Juego(datos_juego)
    juego.run()
    