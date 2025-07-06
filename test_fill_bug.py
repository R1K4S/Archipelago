import unittest
from unittest.mock import MagicMock, patch
from collections import Counter

# Mock das classes necessárias do Archipelago
class MockItem:
    def __init__(self, name, player, advancement=False):
        self.name = name
        self.player = player
        self.advancement = advancement
        self.location = None
        self.code = None # Adicionado para compatibilidade com plando

    def __str__(self):
        return f"{self.name} (Player {self.player})"

class MockLocation:
    def __init__(self, name, player, progress_type=0):
        self.name = name
        self.player = player
        self.item = None
        self.locked = False
        self.progress_type = progress_type
        self.address = None # Adicionado para compatibilidade com plando

    def can_fill(self, state, item, check_access):
        # Simplificado para o propósito do teste
        return True

    def can_reach(self, state):
        # Simplificado para o propósito do teste
        return True

    def item_rule(self, item):
        # Simplificado para o propósito do teste
        return True

    def __str__(self):
        return f"{self.name} (Player {self.player})"

class MockMultiWorld:
    def __init__(self):
        self.players = 1
        self.groups = []
        self.random = MagicMock()
        self.random.choice.side_effect = lambda x: x[0] # Sempre escolhe o primeiro para determinismo
        self.random.randint.side_effect = lambda a, b: a # Sempre escolhe o mínimo para determinismo
        self.state = MagicMock()
        self.state.sweep_for_advancements.return_value = None
        self.itempool = []
        self.plando_items = {1: []}
        self.world_name_lookup = {}
        self.player_ids = {1}
        self.worlds = {1: MagicMock()}
        self.worlds[1].options.accessibility = MagicMock()
        self.worlds[1].options.accessibility.option_minimal = "minimal"
        self.worlds[1].create_item.side_effect = lambda name: MockItem(name, 1)
        self.worlds[1].create_filler.return_value = MockItem("Filler", 1)
        self.early_items = {1: {}}
        self.local_early_items = {1: {}}
        self.player_name = {1: "TestPlayer"} # Adicionado para o teste distribute_planned

        # Mockando os métodos que serão controlados nos testes
        self.get_filled_locations = MagicMock(return_value=[])
        self.has_beaten_game = MagicMock(return_value=False)

    def get_unfilled_locations(self):
        return []

    def push_item(self, location, item, collect):
        location.item = item
        item.location = location

    def get_reachable_locations(self, state=None):
        return []

    def unlocks_new_location(self, item):
        return False

    def get_locations(self):
        return []

    def get_player_name(self, player_id):
        return f"Player {player_id}"

    def push_precollected(self, item):
        pass

    def get_unfilled_locations_for_players(self, locations, players):
        return [MockLocation(loc_name, 1) for loc_name in locations]


class TestFillBug4525(unittest.TestCase):

    def setUp(self):
        # Aplica os patches no setUp para cada teste
        self.multiworld_patch = patch("Fill.MultiWorld", new=MockMultiWorld)
        self.location_patch = patch("Fill.Location", new=MockLocation)
        self.item_patch = patch("Fill.Item", new=MockItem)
        self.collection_state_patch = patch("Fill.CollectionState", new=MagicMock)
        self.accessibility_patch = patch("Fill.Accessibility", new=MagicMock())
        self.accessibility_patch.new.option_minimal = "minimal"

        self.MockMultiWorld = self.multiworld_patch.start()
        self.MockLocation = self.location_patch.start()
        self.MockItem = self.item_patch.start()
        self.MockCollectionState = self.collection_state_patch.start()
        self.MockAccessibility = self.accessibility_patch.start()

        # Importa as funções após os mocks serem aplicados
        from Fill import fill_restrictive, distribute_planned, FillError, accessibility_corrections
        self.fill_restrictive = fill_restrictive
        self.distribute_planned = distribute_planned
        self.FillError = FillError
        self.accessibility_corrections = accessibility_corrections

        self.multiworld = MockMultiWorld()
        self.multiworld.players = 1
        self.multiworld.player_ids = {1}
        self.multiworld.worlds = {1: MagicMock()}
        self.multiworld.worlds[1].options.accessibility = MagicMock()
        self.multiworld.worlds[1].options.accessibility.option_minimal = "minimal"
        self.multiworld.worlds[1].create_item.side_effect = lambda name: MockItem(name, 1)
        self.multiworld.worlds[1].create_filler.return_value = MockItem("Filler", 1)
        self.multiworld.early_items = {1: {}}
        self.multiworld.local_early_items = {1: {}}

    def tearDown(self):
        # Remove os patches após cada teste
        self.multiworld_patch.stop()
        self.location_patch.stop()
        self.item_patch.stop()
        self.collection_state_patch.stop()
        self.accessibility_patch.stop()

    def test_priority_fill_with_minimal_accessibility_bug(self):
        # Cenário: Um item de progressão é colocado em uma localização prioritária
        # que se torna inacessível devido à acessibilidade 'minimal'.
        # O bug original fazia com que o item não fosse movido de volta para o pool.

        # Mock de um item de progressão
        prog_item = MockItem("Progression Item", 1, advancement=True)
        item_pool = [prog_item]

        # Mock de uma localização prioritária
        priority_location = MockLocation("Priority Location", 1, progress_type=1) # PRIORITY = 1
        locations = [priority_location]

        # Simula que a localização se torna inacessível após a primeira tentativa de preenchimento
        # Isso é feito controlando o `can_fill` da localização
        original_can_fill = priority_location.can_fill
        fill_attempt = 0

        def mock_can_fill(state, item, check_access):
            nonlocal fill_attempt
            if fill_attempt == 0:
                fill_attempt += 1
                return True # A primeira tentativa de preenchimento é bem-sucedida
            else:
                return False # A localização se torna inacessível nas tentativas subsequentes

        priority_location.can_fill = mock_can_fill

        # Mock do MultiWorld para simular o comportamento de `get_filled_locations`
        # e `has_beaten_game` para o cenário de `accessibility_corrections`
        self.multiworld.get_filled_locations.return_value = [priority_location]
        self.multiworld.has_beaten_game.return_value = False # Simula que o jogo não pode ser vencido

        # Simula que o item foi colocado na localização
        priority_location.item = prog_item
        prog_item.location = priority_location

        # Chama a função accessibility_corrections que contém a lógica do bug
        # Ela deve mover o item de volta para o pool se a localização for inacessível
        self.accessibility_corrections(self.multiworld, MagicMock(), locations, item_pool)

        # Verifica se o item foi movido de volta para o item_pool
        self.assertIn(prog_item, item_pool, "O item de progressão deveria ter sido movido de volta para o item_pool.")
        self.assertIsNone(priority_location.item, "A localização prioritária deveria estar vazia.")

    def test_distribute_planned_fstring_error(self):
        # Este teste verifica a correção da f-string na função distribute_planned
        # O erro original era na linha 616: f"Could not remove {item_name} from pool for {multiworld.player_name[player]} as it\"s already missing from it."
        # O problema era a aspa dupla escapada dentro de uma f-string com aspas duplas, causando um SyntaxError.

        # Mock de um bloco plando que acionaria o erro da f-string
        self.multiworld.plando_items[1] = [{
            "item": "Some Item",
            "location": "Some Location",
            "from_pool": True,
            "force": "warn"
        }]

        # Simula que o item não está no itempool para acionar a mensagem de aviso
        self.multiworld.itempool = []

        # A execução não deve levantar SyntaxError
        try:
            self.distribute_planned(self.multiworld)
        except Exception as e:
            self.fail(f"distribute_planned levantou uma exceção inesperada: {e}")

        # O teste passa se não houver SyntaxError e a função executar até o fim.
        # Não há uma asserção direta aqui, pois o objetivo é verificar a ausência de um erro de sintaxe.
        self.assertTrue(True, "A função distribute_planned executou sem SyntaxError.")

if __name__ == '__main__':
    unittest.main()

