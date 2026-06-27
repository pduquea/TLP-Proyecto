from __future__ import print_function  # comentario: compatibilidad print Py2/Py3
import sys
import re
import json

def lexer(codigo_fuente):
    # Elimina solo los comentarios completos de linea, sin borrar los valores de color como #FF5733
    codigo_fuente = re.sub(r'(?m)^\s*#.*$', '', codigo_fuente)
    token_regex = r'\b[A-Z_]+\b|\d+\.\d+|\d+|#(?:[0-9A-Fa-f]{6})|[\[\](),:]'
    tokens = re.findall(token_regex, codigo_fuente)
    return tokens

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.posicion = 0
        # Added 'levels' key to AST to support level-specific settings (e.g., TAIL_COLORS)
        self.ast = {"tipo_juego": None, "config": {}, "shapes": {}, "powerups": {}, "events": {}, "levels": {}, "boss": {}}

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
                    self.parsear_levels()
                elif tipo_elemento == 'LEVEL':
                    self.parsear_level()
                elif tipo_elemento == 'BOSS':
                    self.parsear_boss()
            elif token_actual == 'ON':
                self.parsear_evento()
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

    def _parse_matriz(self):
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
        return matriz

    def _parse_valor_literal(self, valor):
        try:
            if '.' in valor:
                return float(valor)
            return int(valor)
        except Exception:
            return valor

    def _parse_propiedades(self):
        propiedades = {}
        while self.posicion < len(self.tokens) and self.tokens[self.posicion] != 'END':
            propiedad = self.consumir()
            if propiedad == 'END':
                break
            self.consumir(':')
            valor = self.consumir()
            propiedades[propiedad.lower()] = self._parse_valor_literal(valor)
        return propiedades

    def parsear_shape(self):
        nombre_shape = self.consumir()
        self.consumir(':')
        estados = []
        while self.posicion < len(self.tokens) and self.tokens[self.posicion] == 'STATE':
            self.consumir('STATE')
            self.consumir()
            self.consumir(':')
            estados.append(self._parse_matriz())

        propiedades = self._parse_propiedades()
        self.consumir('END')
        shape_data = {'estados': estados, 'color': None, 'chance': 1, 'type': None}
        for nombre_propiedad, valor in propiedades.items():
            if nombre_propiedad == 'color':
                shape_data['color'] = valor
            elif nombre_propiedad == 'chance':
                shape_data['chance'] = valor
            elif nombre_propiedad == 'type':
                shape_data['type'] = valor
            else:
                shape_data[nombre_propiedad] = valor
        self.ast['shapes'][nombre_shape] = shape_data

    def parsear_powerup(self):
        nombre_powerup = self.consumir()
        self.consumir(':')
        estados = []
        while self.posicion < len(self.tokens) and self.tokens[self.posicion] == 'STATE':
            self.consumir('STATE')
            self.consumir()
            self.consumir(':')
            estados.append(self._parse_matriz())

        propiedades = self._parse_propiedades()
        self.consumir('END')
        powerup_data = {'estados': estados, 'color': None, 'chance': 1, 'type': None}
        for nombre_propiedad, valor in propiedades.items():
            if nombre_propiedad == 'color':
                powerup_data['color'] = valor
            elif nombre_propiedad == 'chance':
                powerup_data['chance'] = valor
            elif nombre_propiedad == 'type':
                powerup_data['type'] = valor
            else:
                powerup_data[nombre_propiedad] = valor
        if 'powerups' not in self.ast:
            self.ast['powerups'] = {}
        self.ast['powerups'][nombre_powerup] = powerup_data

    def parsear_boss(self):
        nombre_boss = self.consumir()
        self.consumir(':')
        estados = []
        while self.posicion < len(self.tokens) and self.tokens[self.posicion] == 'STATE':
            self.consumir('STATE')
            self.consumir()
            self.consumir(':')
            estados.append(self._parse_matriz())

        propiedades = self._parse_propiedades()
        self.consumir('END')
        boss_data = {'estados': estados, 'color': None, 'hp': 1, 'damage': 1, 'type': 'RECT'}
        for nombre_propiedad, valor in propiedades.items():
            if nombre_propiedad == 'color':
                boss_data['color'] = valor
            elif nombre_propiedad == 'hp':
                boss_data['hp'] = valor
            elif nombre_propiedad == 'damage':
                boss_data['damage'] = valor
            elif nombre_propiedad == 'type':
                boss_data['type'] = valor
            else:
                boss_data[nombre_propiedad] = valor
        self.ast['boss'][nombre_boss] = boss_data
        self.ast['boss']['hp'] = boss_data['hp']
        self.ast['boss']['damage'] = boss_data['damage']
        self.ast['boss']['color'] = boss_data['color']
        self.ast['boss']['estados'] = boss_data['estados']

    def parsear_level(self):
        # Parse a single level block: DEFINE LEVEL <name>: [properties] END
        nombre_nivel = self.consumir()
        self.consumir(':')
        nivel = self.parsear_propiedades_nivel()
        self.consumir('END')
        self.ast['levels'][nombre_nivel] = nivel

    def parsear_levels(self):
        # Parse nested level blocks inside DEFINE LEVELS: ... END
        self.consumir('LEVELS')
        self.consumir(':')
        while self.posicion < len(self.tokens) and self.tokens[self.posicion] != 'END':
            if self.tokens[self.posicion] == 'LEVEL':
                self.consumir('LEVEL')
                nombre_nivel = self.consumir()
                self.consumir(':')
                nivel = self.parsear_propiedades_nivel()
                self.consumir('END')
                self.ast['levels'][nombre_nivel] = nivel
            else:
                self.posicion += 1
        self.consumir('END')

    def parsear_propiedades_nivel(self):
        nivel = {}
        while self.posicion < len(self.tokens) and self.tokens[self.posicion] not in ['END', 'LEVEL']:
            prop = self.consumir()
            self.consumir(':')
            if prop == 'TAIL_COLORS':
                nivel['TAIL_COLORS'] = self.parsear_lista_colores()
            else:
                valor = self.consumir()
                nivel[prop] = self._parse_valor_literal(valor)
        return nivel

    def parsear_lista_colores(self):
        colores = []
        self.consumir('[')
        while self.posicion < len(self.tokens) and self.tokens[self.posicion] != ']':
            colores.append(self.consumir())
            if self.posicion < len(self.tokens) and self.tokens[self.posicion] == ',':
                self.consumir(',')
        self.consumir(']')
        return colores

    def parsear_evento(self):
        self.consumir('ON')
        nombre_evento = 'ON_' + self.consumir()
        self.consumir(':')
        acciones = []
        stop_tokens = ['END', 'ON', 'DEFINE']

        while self.posicion < len(self.tokens) and self.tokens[self.posicion] != 'END':
            verbo = self.consumir()

            if verbo in ['GAME_OVER', 'SET_INVULNERABLE', 'ROTATE']:
                acciones.append({'accion': verbo, 'objeto': None, 'params': []})
                continue

            objeto = None
            params = []

            if self.posicion < len(self.tokens) and self.tokens[self.posicion] not in stop_tokens:
                objeto = self.consumir()

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
            elif self.posicion < len(self.tokens) and self.tokens[self.posicion] not in stop_tokens:
                params.append(self.consumir())

            acciones.append({
                'accion': verbo,
                'objeto': objeto,
                'params': params
            })

        self.consumir('END')
        self.ast['events'][nombre_evento] = acciones
 
def generar_codigo(ast, archivo_salida):
    with open(archivo_salida, 'w') as f:
        json.dump(ast, f, indent=2)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python compiler.py <archivo_entrada.brick>")  # comentario: print() Py3
        sys.exit(1)
    archivo_entrada = sys.argv[1]
    archivo_salida = archivo_entrada.replace('.brick', '.json')
    print("Compilando " + archivo_entrada + "...")  # comentario: print() Py3
    try:
        with open(archivo_entrada, 'r') as f:
            codigo = f.read()
        tokens = lexer(codigo)
        parser = Parser(tokens)
        ast = parser.parse()
        generar_codigo(ast, archivo_salida)
        print("Compilacion exitosa! Archivo de juego creado en " + archivo_salida)  # comentario: print() Py3
    except Exception as e:
        print("\n!!! ERROR DE COMPILACION !!!")
        print(str(e))
        sys.exit(1)