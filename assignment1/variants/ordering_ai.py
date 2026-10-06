"""Variant 2: tactical move ordering only, with fixed-depth alpha-beta."""

import importlib.util
import sys
from pathlib import Path


_spec = importlib.util.spec_from_file_location(
    "_gomoku_ordering_core", Path(__file__).with_name("_core.py"))
_core = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _core
_spec.loader.exec_module(_core)

NAME = "MoveOrdering"
DIRECTIONS = _core.DIRECTIONS


class GomokuAI(_core.SearchAI):
    def _local_score(self, board, row, col, player):
        """Rank wins, long runs and open ends without changing evaluation."""
        n, k = self.board_size, self.win_length
        total = 0
        for dr, dc in DIRECTIONS:
            length = 1
            open_ends = 0
            for sign in (-1, 1):
                r, c = row + sign * dr, col + sign * dc
                while 0 <= r < n and 0 <= c < n and board[r][c] == player:
                    length += 1
                    r += sign * dr
                    c += sign * dc
                if 0 <= r < n and 0 <= c < n and board[r][c] == 0:
                    open_ends += 1
            if length >= k:
                return self.win_score
            total += (6 ** length) * (1 + open_ends)
        return total

    def _rank_candidates(self, board, player, limit):
        center = (self.board_size - 1) / 2
        other = 3 - player
        moves = self._candidates(board)
        moves.sort(key=lambda move: (
            -(10 * self._local_score(board, *move, player)
              + 12 * self._local_score(board, *move, other)),
            abs(move[0] - center) + abs(move[1] - center),
            move[0], move[1],
        ))
        return moves[:limit]
