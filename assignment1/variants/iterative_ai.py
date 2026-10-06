"""Variant 1: iterative deepening only, on the common alpha-beta baseline."""

import importlib.util
import sys
from pathlib import Path


_spec = importlib.util.spec_from_file_location(
    "_gomoku_iterative_core", Path(__file__).with_name("_core.py"))
_core = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _core
_spec.loader.exec_module(_core)

NAME = "IterativeDeepening"


class GomokuAI(_core.SearchAI):
    def _choose(self, board, moves, empty_count, time_limit):
        # Only completed depths replace the previous legal answer. Candidate
        # order stays identical to the common baseline at every depth.
        for depth in (1, 2, 3, 4):
            best, score = self._search_root(board, moves, depth, empty_count)
            if best is not None:
                self.best_move = best
                self.last_completed_depth = depth
            if score >= self.win_score:
                break
        return self.best_move
