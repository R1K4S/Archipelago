import unittest
from unittest.mock import MagicMock, patch

# Mock das classes necessárias do Archipelago
class MockItem:
    def __init__(self, name, player, advancement=False):
        self.name = name
        self.player = player
        self.advancement = advancement
        self.location = None

class MockLocation:
    def __init__(self, name, player, progress_type=0):
        self.name = name
        self.player = player
        self.item = None
        self.locked = False
        self.progress_type = progress_type

    def can_reach(self, state):
        return False # Simula inacessibilidade

class MockMultiWorld:
    def __init__(self):
        self.players = 1
        self.player_ids = {1}
        self.worlds = {1: MagicMock()}
        self.worlds[1].options.accessibility = MagicMock()
        self.worlds[1].options.accessibility.option_minimal = "minimal"

    def get_locations(self):
        return []

class TestFillBugSimplified(unittest.TestCase):
    def setUp(self):
        # Aplica os patches no setUp para cada teste
        self.multiworld_patch = patch("Fill.MultiWorld", new=MockMultiWorld)
        self.location_patch = patch("Fill.Location", new=MockLocation)
        self.item_patch = patch("Fill.Item", new=MockItem)
        self.collection_state_patch = patch("Fill.CollectionState", new=MagicMock)
        self.accessibility_patch = patch("Fill.Accessibility", new=MagicMock())
        self.accessibility_patch.new.option_minimal = "minimal"

        # Mockar os módulos que causam ModuleNotFoundError
        self.pyevermizer_patch = patch("worlds.soe.pyevermizer", new=MagicMock())
        self.zilliandomizer_patch = patch("worlds.zillion.gen_data.zilliandomizer", new=MagicMock())

        self.MockMultiWorld = self.multiworld_patch.start()
        self.MockLocation = self.location_patch.start()
        self.MockItem = self.item_patch.start()
        self.MockCollectionState = self.collection_state_patch.start()
        self.MockAccessibility = self.accessibility_patch.start()
        self.pyevermizer_patch.start()
        self.zilliandomizer_patch.start()

        # Importa as funções após os mocks serem aplicados
        from Fill import accessibility_corrections
        self.accessibility_corrections = accessibility_corrections

        self.multiworld = MockMultiWorld()
        self.multiworld.players = 1
        self.multiworld.player_ids = {1}
        self.multiworld.worlds = {1: MagicMock()}
        self.multiworld.worlds[1].options.accessibility = MagicMock()
        self.multiworld.worlds[1].options.accessibility.option_minimal = "minimal"

    def tearDown(self):
        # Remove os patches após cada teste
        self.multiworld_patch.stop()
        self.location_patch.stop()
        self.item_patch.stop()
        self.collection_state_patch.stop()
        self.accessibility_patch.stop()
        self.pyevermizer_patch.stop()
        self.zilliandomizer_patch.stop()

    def test_accessibility_corrections_minimal_bug(self):
        multiworld = self.multiworld
        state = MagicMock()
        
        prog_item = MockItem("Prog Item", 1, advancement=True)
        location = MockLocation("Inaccessible Loc", 1)
        location.item = prog_item
        prog_item.location = location
        
        multiworld.get_locations = MagicMock(return_value=[location])
        multiworld.get_filled_locations = MagicMock(return_value=[location])
        multiworld.has_beaten_game = MagicMock(return_value=False)

        pool = []
        locations_list = []
        
        self.accessibility_corrections(multiworld, state, locations_list, pool)
        
        self.assertIn(prog_item, pool)
        self.assertIsNone(location.item)
        self.assertIn(location, locations_list)

if __name__ == '__main__':
    unittest.main()


