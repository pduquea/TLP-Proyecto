import sys
import re
import json

def lexer(codigo_fuente):
    # Elimina solo los comentarios completos de linea, sin borrar los valores de color como #FF5733
    codigo_fuente = re.sub(r'(?m)^\s*#.*$', '', codigo_fuente)
    token_regex = r'\b[A-Z_]+\b|\d+|#(?:[0-9A-Fa-f]{6})|[\[\](),:]'
    tokens = re.findall(token_regex, codigo_fuente)
    return tokens

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.posicion = 0
        self.ast = {"tipo_juego": None, "config": {}, "shapes": {}, "events": {}, "powerups": {}, "levels": {}}

    def parse(self):
        while self.posicion < len(self.tokens):
            token_actual = self.tokens[self.posicion]
            if token_actual == 'GAME_TYPE':
                self.parsear_tipo_juego()
            elif token_actual == 'GAME_GRID':
                self.parsear_grid()
            elif token_actual == 'DEFINE':
                self.consumir('DEFINE')
                tipo_elemento = self.consumir()
                if tipo_elemento == 'SHAPE':
                    self.parsear_shape()
                elif tipo_elemento == 'POWERUP':
                    self.parsear_powerup()
                elif tipo_elemento == 'LEVELS':
                    # backward compatibility: allow DEFINE LEVELS ... END (rare)
                    self.parsear_levels()
            elif token_actual == 'ON':
                self.parsear_evento()
            elif token_actual == 'LEVELS':
                self.parsear_levels()
            else:
                self.posicion += 1
        return self.ast

    def consumir(self, token_esperado=None):
        if self.posicion < len(self.tokens):
            token = self.tokens[self.posicion]
            if token_esperado and token != token_esperado:
                raise Exception("Error de sintaxis: Se esperaba '" + token_esperado + "' pero se encontro '" + token + "'")
            self.posicion += 1
            return token
        if token_esperado:
            raise Exception("Error de sintaxis: Se esperaba '" + token_esperado + "' pero se llego al final del archivo.")
        return None

    def parsear_tipo_juego(self):
        self.consumir('GAME_TYPE')
        self.ast['tipo_juego'] = self.consumir()

    def parsear_grid(self):
        self.consumir('GAME_GRID')
        self.consumir('(')
        ancho = int(self.consumir())
        self.consumir(',')
        alto = int(self.consumir())
        self.consumir(')')
        self.ast['config']['grid_size'] = [ancho, alto]

    def parsear_shape(self):
        nombre_shape = self.consumir()
        self.consumir(':')
        estados = []
        while self.posicion < len(self.tokens) and self.tokens[self.posicion] == 'STATE':
            self.consumir('STATE')
            self.consumir()
            self.consumir(':')
            matriz = []
            while self.posicion < len(self.tokens) and self.tokens[self.posicion] == '[':
                fila = []
                self.consumir('[')
                while self.tokens[self.posicion] != ']':
                    fila.append(int(self.consumir()))
                    if self.posicion < len(self.tokens) and self.tokens[self.posicion] == ',': 
                        self.consumir(',')
                self.consumir(']')
                matriz.append(fila)
            estados.append(matriz)

        # propiedades adicionales: COLOR, CHANCE, TYPE
        color = None
        chance = 1
        shape_type = 'RECT'
        while self.posicion < len(self.tokens) and self.tokens[self.posicion] in ['COLOR', 'CHANCE', 'TYPE']:
            propiedad = self.consumir()
            self.consumir(':')
            if propiedad == 'COLOR':
                color = self.consumir()
            elif propiedad == 'CHANCE':
                chance = int(self.consumir())
            elif propiedad == 'TYPE':
                shape_type = self.consumir()

        self.consumir('END')
        self.ast['shapes'][nombre_shape] = {'estados': estados, 'color': color, 'chance': chance, 'type': shape_type}

    def parsear_powerup(self):
        nombre_powerup = self.consumir()
        self.consumir(':')
        estados = []
        while self.posicion < len(self.tokens) and self.tokens[self.posicion] == 'STATE':
            self.consumir('STATE')
            self.consumir()
            self.consumir(':')
            matriz = []
            while self.posicion < len(self.tokens) and self.tokens[self.posicion] == '[':
                fila = []
                self.consumir('[')
                while self.tokens[self.posicion] != ']':
                    fila.append(int(self.consumir()))
                    if self.posicion < len(self.tokens) and self.tokens[self.posicion] == ',': 
                        self.consumir(',')
                self.consumir(']')
                matriz.append(fila)
            estados.append(matriz)

        color = None
        chance = 1
        duration = None
        while self.posicion < len(self.tokens) and self.tokens[self.posicion] in ['COLOR', 'CHANCE', 'DURATION']:
            propiedad = self.consumir()
            self.consumir(':')
            if propiedad == 'COLOR':
                color = self.consumir()
            elif propiedad == 'CHANCE':
                chance = int(self.consumir())
            elif propiedad == 'DURATION':
                duration = int(self.consumir())

        self.consumir('END')
        if 'powerups' not in self.ast:
            self.ast['powerups'] = {}
        self.ast['powerups'][nombre_powerup] = {'estados': estados, 'color': color, 'chance': chance, 'duration': duration}

    def parsear_levels(self):
        # Parse LEVELS block: LEVEL <NAME> : <props> END ... END
        self.consumir('LEVELS')
        while self.posicion < len(self.tokens) and self.tokens[self.posicion] != 'END':
            if self.tokens[self.posicion] == 'LEVEL':
                self.consumir('LEVEL')
                nombre = self.consumir()
                self.consumir(':')
                props = {}
                while self.posicion < len(self.tokens) and self.tokens[self.posicion] not in ['END', 'LEVEL']:
                    key = self.consumir()
                    # Accept values or ON/OFF
                    if self.tokens[self.posicion] == ':':
                        self.consumir(':')
                    val = self.consumir()
                    # allow lists of colors separated by commas
                    if val and ',' in val:
                        props[key] = [v.strip() for v in val.split(',')]
                    else:
                        # try to numeric
                        try:
                            props[key] = int(val)
                        except:
                            props[key] = val
                # consume optional END after level
                if self.posicion < len(self.tokens) and self.tokens[self.posicion] == 'END':
                    self.consumir('END')
                self.ast['levels'][nombre] = props
            else:
                self.posicion += 1
        # final END
        if self.posicion < len(self.tokens) and self.tokens[self.posicion] == 'END':
            self.consumir('END')

    def parsear_evento(self):
        self.consumir('ON')
        nombre_evento = 'ON_' + self.consumir()
        self.consumir(':')
        acciones = []
        while self.posicion < len(self.tokens) and self.tokens[self.posicion] != 'END':
            verbo = self.consumir()
           
            if verbo == 'GAME_OVER':
                acciones.append({'accion': verbo, 'objeto': None, 'params': []})
                continue
            
            objeto = self.consumir()
            params = []
            if self.posicion < len(self.tokens) and self.tokens[self.posicion] == 'AT':
                self.consumir('AT')
                if self.tokens[self.posicion] == 'RANDOM':
                    params.append(self.consumir())
                else:
                    self.consumir('(')
                    x = int(self.consumir())
                    self.consumir(',')
                    y = int(self.consumir())
                    self.consumir(')')
                    params.append([x, y])
            elif self.posicion < len(self.tokens) and self.tokens[self.posicion] not in ['END', 'ON', 'DEFINE', 'SPAWN', 'MOVE', 'ROTATE', 'INCREASE_SCORE', 'SET_DIRECTION', 'GROW', 'GAME_OVER']:
                params.append(self.consumir())
            acciones.append({'accion': verbo, 'objeto': objeto, 'params': params})
        self.consumir('END')
        self.ast['events'][nombre_evento] = acciones

def generar_codigo(ast, archivo_salida):
    with open(archivo_salida, 'w') as f:
        json.dump(ast, f, indent=2)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "Uso: python compiler.py <archivo_entrada.brick>"
        sys.exit(1)
    archivo_entrada = sys.argv[1]
    archivo_salida = archivo_entrada.replace('.brick', '.json')
    print "Compilando " + archivo_entrada + "..."
    try:
        with open(archivo_entrada, 'r') as f:
            codigo = f.read()
        tokens = lexer(codigo)
        parser = Parser(tokens)
        ast = parser.parse()
        generar_codigo(ast, archivo_salida)
        print "Compilacion exitosa! Archivo de juego creado en " + archivo_salida
    except Exception as e:
        print "\n!!! ERROR DE COMPILACION !!!"
        print str(e)
        sys.exit(1)