import sys
import json
import time
import random
import Tkinter as tk
import tkMessageBox # Necesario para el GAME OVER
# Quitamos os y msvcrt ya que la GUI maneja el dibujo y el input
 

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
        self.color_pieza_actual = None
        
        if self.tipo_juego == 'TETRIS':
            self.pieza_actual = None
            self.color_pieza_actual = None
            self.pieza_x, self.pieza_y, self.pieza_rotacion = 0, 0, 0
            self.velocidad_gravedad = 0.4
            self.powerups_activos = []  # Lista para almacenar powerups en el tablero
            self.rotaciones_l_piece = 0  # Contador para el logro de powerup
            self.lineas_limpias_simultaneas = 0  # Contador para powerups
        
        if self.tipo_juego == 'SNAKE':
            self.serpiente_cuerpo = []
            self.serpiente_direccion = (1, 0)
            # New structures for evolved snake
            self.food_items = []  # list of {'pos':(x,y), 'type':'FOOD'|'POISON'|'POWERUP_INVULN'}
            self.clouds = []      # list of (x,y)
            self.posicion_comida = None
            self.invulnerable = False
            self.invuln_end_time = 0
            self.tail_colors = []
            # Determine level settings (retrocompat: default BABY)
            levels = self.datos_juego.get('levels', {})
            self.level = 'BABY'
            if levels:
                # pick BABY by default; if JSON contains a key 'DEFAULT' use it
                if 'DEFAULT' in levels:
                    self.level = levels['DEFAULT']
                else:
                    # prefer 'BABY' if present
                    if 'BABY' in levels:
                        self.level = 'BABY'
                    else:
                        # take first available
                        self.level = list(levels.keys())[0]
            # set tick speed from level if provided
            lvlcfg = self.datos_juego.get('levels', {}).get(self.level, {})
            self.velocidad_gravedad = float(lvlcfg.get('TICK_SPEED', 0.15))
            # tail colors for Nyan
            self.tail_colors = lvlcfg.get('TAIL_COLORS', ["#FF0000", "#FF7F00", "#FFFF00", "#00FF00", "#0000FF", "#4B0082", "#9400D3"])
            # snake segment shape: take first shape defined or default RECT
            shapes = self.datos_juego.get('shapes', {})
            if shapes:
                first = list(shapes.keys())[0]
                self.snake_shape_type = shapes[first].get('type', 'RECT')
            else:
                self.snake_shape_type = 'RECT'
        
        self.timer_gravedad = 0
        self.ejecutar_evento('ON_START')
        self.timer_id = None # Para controlar el loop de Tkinter

    def run(self):
        # Inicia el ciclo principal de juego de Tkinter
        self.root.after(50, self.game_loop) 
        self.root.mainloop() 

    def game_loop(self):
        if self.juego_terminado:
            self.mostrar_game_over()
            return

        # Logica de TICK/Gravedad
        self.timer_gravedad += 0.05 
        if self.timer_gravedad >= self.velocidad_gravedad:
            self.timer_gravedad = 0
            self.ejecutar_evento('ON_TICK')

        # Power-up timer check
        if self.tipo_juego == 'SNAKE' and self.invulnerable and time.time() >= self.invuln_end_time:
            self.invulnerable = False

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
            # draw food items
            for item in self.food_items:
                x, y = item['pos']
                if item['type'] == 'FOOD':
                    self.dibujar_celda(x, y, COLOR_FOOD)
                elif item['type'] == 'POISON':
                    self.dibujar_celda(x, y, '#800080')
                elif item['type'] == 'POWERUP_INVULN':
                    self.dibujar_celda(x, y, '#FFFF00')
            # draw clouds
            for cx, cy in self.clouds:
                self.dibujar_celda(cx, cy, '#AAAAAA')

            for i, segmento in enumerate(self.serpiente_cuerpo):
                x, y = segmento
                is_head = (i == 0)
                # choose color per level (Nyan tail colors)
                if self.level == 'NYAN_CAT' and not is_head:
                    color = self.tail_colors[i % len(self.tail_colors)]
                else:
                    color = COLOR_SNAKE_CABEZA if is_head else COLOR_SNAKE_CUERPO
                self.dibujar_segmento(x, y, i, is_head, color)

            # show invulnerability status
            if self.invulnerable:
                self.label_controles.config(text="CONTROLES\nInvulnerable")
            else:
                self.label_controles.config(text="CONTROLES\nFlechas: Mover/Rotar")

    def dibujar_celda(self, x, y, color):
        ts = self.taman_celda 
        x1, y1 = x * ts, y * ts
        x2, y2 = x1 + ts, y1 + ts
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline='#000000')

    def dibujar_segmento(self, x, y, index, is_head, color):
        ts = self.taman_celda
        x1, y1 = x * ts, y * ts
        x2, y2 = x1 + ts, y1 + ts
        shape = self.snake_shape_type
        if self.level == 'NYAN_CAT' and is_head:
            # draw circular head with simple cat eyes
            self.canvas.create_oval(x1, y1, x2, y2, fill=color, outline='#000000')
            # eyes
            ex1 = x1 + ts*0.25; ey = y1 + ts*0.35
            ex2 = x1 + ts*0.75
            self.canvas.create_oval(ex1-2, ey-2, ex1+2, ey+2, fill='black')
            self.canvas.create_oval(ex2-2, ey-2, ex2+2, ey+2, fill='black')
        else:
            if shape == 'CIRCULAR':
                self.canvas.create_oval(x1, y1, x2, y2, fill=color, outline='#000000')
            elif shape == 'TRIANGULAR':
                self.canvas.create_polygon((x1 + ts/2, y1, x2, y2, x1, y2), fill=color, outline='#000000')
            else:
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline='#000000')


    def ejecutar_evento(self, nombre_evento):
        if nombre_evento in self.datos_juego['events']:
            for accion in self.datos_juego['events'][nombre_evento]:
                verbo, objeto = accion.get('accion'), accion.get('objeto')
                
                if verbo == 'INCREASE_SCORE': self.puntuacion += int(objeto)
                if verbo == 'GAME_OVER': self.juego_terminado = True

                if self.tipo_juego == 'TETRIS':
                    if verbo == 'SPAWN': self.tetris_spawn_pieza()
                    if verbo == 'MOVE': self.tetris_mover_pieza(accion['params'][0])
                    if verbo == 'ROTATE': self.tetris_rotar_pieza()

                
                if self.tipo_juego == 'SNAKE':
                    if verbo == 'SPAWN' and objeto == 'PLAYER': self.snake_spawn_jugador(accion)
                    if verbo == 'SPAWN' and objeto in ['FOOD', 'POISON_FRUIT', 'POWERUP_INVULN', 'POISON']:
                        # map object names
                        tipo = 'FOOD'
                        if objeto == 'POISON_FRUIT' or objeto == 'POISON': tipo = 'POISON'
                        if objeto == 'POWERUP_INVULN': tipo = 'POWERUP_INVULN'
                        self.snake_spawn_comida(tipo)
                    if verbo == 'MOVE' and objeto == 'PLAYER': self.snake_mover_jugador()
                    if verbo == 'GROW':
                        # GROW may contain count in params
                        self.snake_crecer(int(accion.get('params')[0]) if accion.get('params') else 1)

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
        x, y = int(coords[0]), int(coords[1])
        self.serpiente_cuerpo = [(x, y)]
        self.serpiente_direccion = (1, 0)
        
    def snake_spawn_comida(self, tipo='FOOD'):
        # spawn a food item of given type at random free position
        while True:
            x, y = random.randint(0, self.ancho - 1), random.randint(0, self.alto - 1)
            if (x, y) not in self.serpiente_cuerpo and (x, y) not in [f['pos'] for f in self.food_items] and (x, y) not in self.clouds:
                self.food_items.append({'pos': (x, y), 'type': tipo})
                break
                
    def snake_mover_jugador(self):
        if not self.serpiente_cuerpo: return
        cabeza_x, cabeza_y = self.serpiente_cuerpo[0]
        dir_x, dir_y = self.serpiente_direccion
        nueva_cabeza = (cabeza_x + dir_x, cabeza_y + dir_y)

        # wall collision
        if not (0 <= nueva_cabeza[0] < self.ancho and 0 <= nueva_cabeza[1] < self.alto):
            self.ejecutar_evento('ON_COLLISION_WALL')
            return

        # self collision
        if nueva_cabeza in self.serpiente_cuerpo[:-1]:
            self.ejecutar_evento('ON_COLLISION_SELF')
            return

        # insert head
        self.serpiente_cuerpo.insert(0, nueva_cabeza)

        # check clouds (obstacle)
        if nueva_cabeza in self.clouds:
            # cloud collision: lose all points; if already 0 -> game over
            if self.puntuacion <= 0 and not self.invulnerable:
                self.ejecutar_evento('ON_COLLISION_WALL')
                return
            else:
                self.puntuacion = 0
                # do not remove head (still alive)
                return

        # check food items
        ate_item = None
        for item in list(self.food_items):
            if item['pos'] == nueva_cabeza:
                ate_item = item
                self.food_items.remove(item)
                break

        if ate_item:
            if ate_item['type'] == 'FOOD':
                # normal food: increase score and grow
                self.puntuacion += 10
                self.snake_crecer(1)
                # spawn another normal food if ON_EAT_FOOD event exists
                if 'ON_EAT_FOOD' in self.datos_juego.get('events', {}):
                    self.ejecutar_evento('ON_EAT_FOOD')
            elif ate_item['type'] == 'POISON':
                # poison behavior depends on level
                if self.level == 'ENTHUSIAST':
                    self.puntuacion = max(0, self.puntuacion - 10)
                elif self.level == 'NYAN_CAT':
                    if self.puntuacion <= 0 and not self.invulnerable:
                        self.juego_terminado = True
                    else:
                        self.puntuacion = 0
                else:
                    # default: penalize 10 points
                    self.puntuacion = max(0, self.puntuacion - 10)
            elif ate_item['type'] == 'POWERUP_INVULN':
                # set invulnerability based on powerup definition
                pu_cfg = self.datos_juego.get('powerups', {}).get('INVULN', {})
                duration = pu_cfg.get('duration', 5)
                self.invulnerable = True
                self.invuln_end_time = time.time() + duration
        else:
            # no food eaten, move tail
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

    def snake_crecer(self):
        # default grow by 1
        self.snake_crecer(1)

    def snake_crecer(self, n=1):
        # add n segments by duplicating last segment
        for _ in range(n):
            if self.serpiente_cuerpo:
                tail = self.serpiente_cuerpo[-1]
                self.serpiente_cuerpo.append((tail[0], tail[1]))
            else:
                # if empty, spawn in center
                self.serpiente_cuerpo.append((self.ancho/2, self.alto/2))


    # METODOS DE SALIDA (ADAPTADOS A GUI)

    def mostrar_game_over(self):
        tkMessageBox.showinfo("Juego Terminado", "Puntuacion Final: " + str(self.puntuacion))
        self.root.destroy()
        sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "Uso: python runtime.py <archivo_juego.json>"
        sys.exit(1)
    archivo_juego = sys.argv[1]
    try:
        with open(archivo_juego, 'r') as f:
            datos_juego = json.load(f)
    except IOError:
        print "Error: No se pudo encontrar el archivo " + archivo_juego
        sys.exit(1)
    juego = Juego(datos_juego)
    juego.run()