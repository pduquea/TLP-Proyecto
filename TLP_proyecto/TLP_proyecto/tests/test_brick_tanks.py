import io
import os
import unittest

import compiler
import runtime


class BrickTanksCompilerTest(unittest.TestCase):
    def test_parser_reads_tank_properties(self):
        base_dir = os.path.dirname(os.path.dirname(__file__))
        brick_path = os.path.join(base_dir, 'games', 'brick_tanks.brick')

        with io.open(brick_path, 'r', encoding='utf-8') as handle:
            codigo = handle.read()

        tokens = compiler.lexer(codigo)
        parser = compiler.Parser(tokens)
        ast = parser.parse()

        self.assertEqual(ast['tipo_juego'], 'BRICK_TANKS')
        self.assertIn('PLAYER_TANK', ast['shapes'])
        self.assertEqual(ast['shapes']['PLAYER_TANK']['resistance'], 3)
        self.assertEqual(ast['shapes']['ENEMY_TANK']['damage'], 1)
        self.assertIn('BOSS_TANK', ast.get('boss', {}))
        self.assertEqual(ast['boss']['hp'], 6)
        self.assertEqual(ast['boss']['damage'], 1)
        self.assertIn('ON_TARGET_SCORE', ast['events'])

    def test_player_spawn_registers_player_and_allows_shooting(self):
        game = type('GameStub', (), {})()
        game.ancho = 12
        game.alto = 18
        game.tank_bullets = []
        game.tank_entities = []
        game.tank_player = None
        game.datos_juego = {
            'shapes': {
                'PLAYER_TANK': {'type': 'PLAYER', 'color': '#1E90FF', 'resistance': 3},
            },
            'powerups': {},
        }
        game.tank_resolver_posicion = lambda *args, **kwargs: (5, 15)

        runtime.Juego.tank_spawn_entity(game, 'PLAYER_TANK')

        self.assertIsNotNone(game.tank_player)
        self.assertEqual(game.tank_player['kind'], 'player')

        runtime.Juego.tank_player_shoot(game)
        self.assertEqual(len(game.tank_bullets), 1)
        self.assertEqual(game.tank_bullets[0]['owner'], 'player')

    def test_enemy_and_boss_spawn_with_friendly_health(self):
        game = type('GameStub', (), {})()
        game.ancho = 12
        game.alto = 18
        game.tank_bullets = []
        game.tank_entities = []
        game.tank_player = None
        game.datos_juego = {
            'shapes': {
                'ENEMY_TANK': {'type': 'ENEMY', 'color': '#FF4D4D', 'resistance': 2},
            },
            'boss': {'BOSS': {'hp': 8, 'damage': 2, 'color': '#800080'}},
            'powerups': {},
        }
        game.tank_resolver_posicion = lambda *args, **kwargs: (5, 1)
        game.tank_get_boss_data = lambda: {'hp': 6, 'damage': 1, 'color': '#800080'}

        runtime.Juego.tank_spawn_entity(game, 'ENEMY_TANK')
        runtime.Juego.tank_spawn_entity(game, 'BOSS')

        enemy = next(entity for entity in game.tank_entities if entity['kind'] == 'enemy')
        boss = next(entity for entity in game.tank_entities if entity['kind'] == 'boss')

        self.assertEqual(enemy['health'], 2)
        self.assertEqual(boss['health'], 6)

    def test_enemy_shoot_respects_cooldown(self):
        game = type('GameStub', (), {})()
        game.tank_bullets = []
        game.tank_entities = []
        game.tank_player = {'kind': 'player', 'x': 5, 'y': 10}
        game.tank_get_entities = lambda nombre_entidad: [entity for entity in game.tank_entities if entity.get('name') == nombre_entidad]
        game.tank_delta_por_direccion = lambda direction, entity: (0, 1)

        game.tank_entities.append({'name': 'ENEMY_TANK', 'kind': 'enemy', 'x': 5, 'y': 1, 'health': 2, 'color': '#FF4D4D', 'shape': 'RECT', 'direction': (0, 1)})

        runtime.Juego.tank_shoot(game, 'ENEMY_TANK', ['DOWN'])
        self.assertEqual(len(game.tank_bullets), 1)

        runtime.Juego.tank_shoot(game, 'ENEMY_TANK', ['DOWN'])
        self.assertEqual(len(game.tank_bullets), 1)

    def test_boss_spawns_after_three_enemy_kills(self):
        game = type('GameStub', (), {})()
        game.ancho = 12
        game.alto = 18
        game.tank_bullets = []
        game.tank_entities = []
        game.tank_player = {'kind': 'player', 'x': 5, 'y': 10}
        game.tank_boss_spawned = False
        game.tank_enemies_defeated = 0
        game.tank_kills_to_boss = 3
        game.puntuacion = 0
        game.tank_get_boss_data = lambda: {'hp': 6, 'damage': 1, 'color': '#800080'}
        game.ejecutar_evento = lambda *args, **kwargs: None

        enemy = {'name': 'ENEMY_TANK', 'kind': 'enemy', 'x': 5, 'y': 1, 'health': 1, 'color': '#FF4D4D', 'shape': 'RECT', 'direction': (0, 1)}
        game.tank_entities.append(enemy)

        runtime.Juego.tank_handle_enemy_defeat(game, enemy)
        runtime.Juego.tank_handle_enemy_defeat(game, enemy)
        runtime.Juego.tank_handle_enemy_defeat(game, enemy)

        self.assertEqual(game.tank_enemies_defeated, 3)
        self.assertTrue(game.tank_boss_spawned)


if __name__ == '__main__':
    unittest.main()
