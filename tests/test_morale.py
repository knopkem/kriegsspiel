import unittest

from core.units import MoraleState, Side, make_infantry_half_battalion


class MoraleStateTestCase(unittest.TestCase):
    def test_degrade_morale_steps_down_state_machine(self) -> None:
        infantry = make_infantry_half_battalion("i", "3rd Fusiliers", Side.BLUE)

        infantry.degrade_morale()
        self.assertEqual(infantry.morale_state, MoraleState.SHAKEN)

        infantry.degrade_morale(2)
        self.assertEqual(infantry.morale_state, MoraleState.BROKEN)

    def test_improve_morale_steps_up_state_machine(self) -> None:
        infantry = make_infantry_half_battalion("i", "3rd Fusiliers", Side.BLUE)
        infantry.morale_state = MoraleState.ROUTING

        infantry.improve_morale()
        self.assertEqual(infantry.morale_state, MoraleState.SHAKEN)

        infantry.improve_morale()
        self.assertEqual(infantry.morale_state, MoraleState.STEADY)


if __name__ == "__main__":
    unittest.main()
