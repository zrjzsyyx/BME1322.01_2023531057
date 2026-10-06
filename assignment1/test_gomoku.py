"""Focused rule and protocol checks for the configurable game."""

import unittest

from assignment1.gomoku_ai import GomokuAI
from assignment1.gomoku_game import GomokuGame


class ReadOnlyRow(list):
    def __setitem__(self, key, value):
        raise AssertionError("the input board must not be modified")


class GameRulesTests(unittest.TestCase):
    def test_four_win_directions(self):
        lines = (
            [(0, 0), (0, 1), (0, 2), (0, 3)],
            [(0, 0), (1, 0), (2, 0), (3, 0)],
            [(0, 0), (1, 1), (2, 2), (3, 3)],
            [(0, 3), (1, 2), (2, 1), (3, 0)],
        )
        for line in lines:
            with self.subTest(line=line):
                game = GomokuGame(5, 4)
                for index, move in enumerate(line):
                    game.play(*move)
                    if index < 3:
                        game.play(4, index + 1)
                self.assertTrue(game.finished)
                self.assertEqual(game.winner, 1)

    def test_draw_and_illegal_moves(self):
        game = GomokuGame(3, 3)
        moves = ((0, 0), (0, 1), (0, 2), (1, 1), (1, 0),
                 (1, 2), (2, 1), (2, 0), (2, 2))
        with self.assertRaises(ValueError):
            game.play(-1, 0)
        game.play(*moves[0])
        with self.assertRaises(ValueError):
            game.play(*moves[0])
        for move in moves[1:]:
            game.play(*move)
        self.assertTrue(game.finished)
        self.assertEqual(game.winner, 0)
        with self.assertRaises(ValueError):
            game.play(0, 0)


class AiProtocolTests(unittest.TestCase):
    def test_immediate_win_and_block(self):
        board = [[0] * 7 for _ in range(7)]
        for col in (1, 2, 3):
            board[3][col] = 1
        snapshot = [row[:] for row in board]
        for player in (1, 2):
            move = GomokuAI(player, 7, 4).get_move(board, None, 1.0)
            self.assertIn(move, ((3, 0), (3, 4)))
            self.assertEqual(board, snapshot)

    def test_nonstandard_k_and_nearly_full_board(self):
        for n, k in ((5, 3), (9, 4), (15, 7), (15, 15)):
            with self.subTest(n=n, k=k):
                board = [[0] * n for _ in range(n)]
                board[0][0] = 2
                move = GomokuAI(1, n, k).get_move(board, (0, 0), 0.1)
                self.assertEqual(board[move[0]][move[1]], 0)
                self.assertIsInstance(move, tuple)
        board = [[1] * 5 for _ in range(5)]
        board[4][4] = 0
        self.assertEqual(GomokuAI(2, 5, 5).get_move(board, None, 0.1), (4, 4))

    def test_input_board_is_read_only(self):
        board = [ReadOnlyRow([0] * 7) for _ in range(7)]
        board[3] = ReadOnlyRow([0, 1, 1, 1, 0, 0, 0])
        self.assertIn(GomokuAI(1, 7, 4).get_move(board, None, 1.0),
                      ((3, 0), (3, 4)))


if __name__ == "__main__":
    unittest.main()
