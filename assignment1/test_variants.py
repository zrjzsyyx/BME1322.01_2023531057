"""Checks that each isolated search variant runs through the arena protocol."""

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


VARIANT_DIR = Path(__file__).with_name("variants")
VARIANTS = ("baseline_ai", "iterative_ai", "ordering_ai", "mcts_ai")


class ReadOnlyRow(list):
    def __setitem__(self, key, value):
        raise AssertionError("the input board must not be modified")


def load_variant(name):
    spec = importlib.util.spec_from_file_location(
        f"_test_{name}", VARIANT_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class VariantTests(unittest.TestCase):
    def test_protocol_tactics_and_board_ownership(self):
        board = [[0] * 7 for _ in range(7)]
        for col in (1, 2, 3):
            board[3][col] = 1
        original = [row[:] for row in board]
        for name in VARIANTS:
            module = load_variant(name)
            for player in (1, 2):
                with self.subTest(name=name, player=player):
                    move = module.GomokuAI(player, 7, 4).get_move(
                        board, None, 0.5)
                    self.assertIn(move, ((3, 0), (3, 4)))
                    self.assertEqual(board, original)

    def test_multiple_board_and_win_sizes(self):
        for name in VARIANTS:
            module = load_variant(name)
            for n, k in ((5, 3), (9, 4), (15, 7)):
                with self.subTest(name=name, n=n, k=k):
                    board = [[0] * n for _ in range(n)]
                    board[0][0] = 2
                    move = module.GomokuAI(1, n, k).get_move(
                        board, (0, 0), 0.3)
                    self.assertIsInstance(move, tuple)
                    self.assertEqual(len(move), 2)
                    self.assertEqual(board[move[0]][move[1]], 0)

    def test_variants_do_not_modify_input_board(self):
        board = [ReadOnlyRow([0] * 7) for _ in range(7)]
        board[3] = ReadOnlyRow([0, 1, 1, 1, 0, 0, 0])
        for name in VARIANTS:
            with self.subTest(name=name):
                move = load_variant(name).GomokuAI(1, 7, 4).get_move(
                    board, None, 1.0)
                self.assertIn(move, ((3, 0), (3, 4)))

    def test_iterative_version_finishes_each_depth_before_publishing(self):
        ai = load_variant("iterative_ai").GomokuAI(1, 5, 4)
        seen = []

        def fake_search(board, moves, depth, empty_count):
            seen.append(depth)
            return moves[depth % len(moves)], 0

        with patch.object(ai, "_search_root", side_effect=fake_search):
            move = ai._choose([[0] * 5 for _ in range(5)],
                              [(0, 0), (0, 1)], 25, 1.0)
        self.assertEqual(seen, [1, 2, 3, 4])
        self.assertEqual(ai.last_completed_depth, 4)
        self.assertEqual(move, (0, 0))

    def test_ordering_promotes_a_tactical_move(self):
        board = [[0] * 9 for _ in range(9)]
        for col in (0, 1, 2):
            board[0][col] = 1
        board[4][4] = 2
        baseline = load_variant("baseline_ai").GomokuAI(1, 9, 4)
        ordered = load_variant("ordering_ai").GomokuAI(1, 9, 4)
        self.assertNotEqual(baseline._rank_candidates(board, 1, 1)[0], (0, 3))
        self.assertEqual(ordered._rank_candidates(board, 1, 1)[0], (0, 3))

    def test_mcts_actually_simulates(self):
        module = load_variant("mcts_ai")
        ai = module.GomokuAI(1, 5, 5)
        board = [[0] * 5 for _ in range(5)]
        board[2][2] = 2
        move = ai.get_move(board, (2, 2), 1.0)
        self.assertEqual(board[move[0]][move[1]], 0)
        self.assertGreater(ai.last_simulations, 0)
        self.assertTrue(ai.last_mcts_selected)

        root = module._Node(None, None, 2)
        root.visits = 100
        popular = module._Node((0, 0), root, 1)
        popular.visits, popular.value = 90, 72.0
        exploratory = module._Node((0, 1), root, 1)
        exploratory.visits, exploratory.value = 10, 5.0
        root.children = [popular, exploratory]
        self.assertIs(ai._uct_child(root), exploratory)


if __name__ == "__main__":
    unittest.main()
