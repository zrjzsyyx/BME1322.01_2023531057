"""Variant 3: MCTS with UCT on the common fixed-depth baseline.

The baseline alpha-beta result is a legal fallback. MCTS explores the same
root candidates independently and selects the most visited move once every
candidate has been sampled. No iterative deepening or alpha-beta move ordering
is enabled in this variant.
"""

import importlib.util
import math
import random
import sys
import time
from pathlib import Path


_spec = importlib.util.spec_from_file_location(
    "_gomoku_mcts_core", Path(__file__).with_name("_core.py"))
_core = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _core
_spec.loader.exec_module(_core)

NAME = "MCTS-UCT"


class _Node:
    __slots__ = ("move", "parent", "player_just_moved", "children",
                 "untried", "visits", "value")

    def __init__(self, move, parent, player_just_moved):
        self.move = move
        self.parent = parent
        self.player_just_moved = player_just_moved
        self.children = []
        self.untried = None
        self.visits = 0
        self.value = 0.0


class GomokuAI(_core.SearchAI):
    def __init__(self, player_id, board_size, win_length):
        super().__init__(player_id, board_size, win_length)
        self.last_simulations = 0
        self.last_mcts_selected = False

    def get_move(self, board, last_opponent_move, time_limit):
        self.last_simulations = 0
        self.last_mcts_selected = False
        return super().get_move(board, last_opponent_move, time_limit)

    def _rollout(self, board, player, last_move, empty_count, rng):
        """Play bounded nearby moves, then estimate a nonterminal position."""
        max_steps = min(empty_count, max(12, 3 * self.win_length + 6))
        for _ in range(max_steps):
            self._check_time()
            if last_move is not None and self._is_win(
                    board, *last_move, 3 - player):
                return 1.0 if 3 - player == self.player_id else 0.0
            if empty_count == 0:
                return 0.5

            choices = self._candidates(board, 12)
            # Terminal tactics make a simulated game more informative than
            # uniformly random moves on a large board.
            move = None
            for candidate in choices:
                r, c = candidate
                board[r][c] = player
                won = self._is_win(board, r, c, player)
                board[r][c] = 0
                if won:
                    move = candidate
                    break
            if move is None:
                opponent = 3 - player
                for candidate in choices:
                    r, c = candidate
                    board[r][c] = opponent
                    won = self._is_win(board, r, c, opponent)
                    board[r][c] = 0
                    if won:
                        move = candidate
                        break
            if move is None:
                move = rng.choice(choices)
            board[move[0]][move[1]] = player
            last_move = move
            player = 3 - player
            empty_count -= 1

        if last_move is not None and self._is_win(board, *last_move, 3 - player):
            return 1.0 if 3 - player == self.player_id else 0.0
        if empty_count == 0:
            return 0.5
        scale = 20 * self.weights[max(1, self.win_length - 2)]
        return 0.5 + 0.5 * math.tanh(self._evaluate(board) / scale)

    @staticmethod
    def _uct_child(node):
        """UCT = mean reward for the mover + sqrt(2 log N / n)."""
        parent_log = math.log(max(1, node.visits))
        return max(node.children, key=lambda child: (
            float("inf") if child.visits == 0 else
            child.value / child.visits
            + math.sqrt(2.0 * parent_log / child.visits)))

    def _simulate(self, root, initial_board, empty_count, rng):
        board = [row[:] for row in initial_board]
        node = root
        player = self.player_id
        last_move = None
        remaining = empty_count

        while True:
            self._check_time()
            if last_move is not None and self._is_win(
                    board, *last_move, 3 - player):
                reward = 1.0 if 3 - player == self.player_id else 0.0
                break
            if remaining == 0:
                reward = 0.5
                break
            if node.untried is None:
                node.untried = self._candidates(board, 8)
                rng.shuffle(node.untried)
            if node.untried:
                move = node.untried.pop()
                child = _Node(move, node, player)
                node.children.append(child)
                board[move[0]][move[1]] = player
                last_move = move
                remaining -= 1
                player = 3 - player
                node = child
                reward = self._rollout(board, player, last_move, remaining, rng)
                break
            if not node.children:
                reward = 0.5
                break

            node = self._uct_child(node)
            move = node.move
            board[move[0]][move[1]] = player
            last_move = move
            remaining -= 1
            player = 3 - player

        while node is not None:
            node.visits += 1
            node.value += (reward if node.player_just_moved == self.player_id
                           else 1.0 - reward)
            node = node.parent

    def _choose(self, board, moves, empty_count, time_limit):
        self.last_simulations = 0
        self.last_mcts_selected = False
        overall_deadline = self.deadline
        self.deadline = min(overall_deadline, time.perf_counter()
                            + max(0.01, min(0.25, 0.20 * time_limit)))
        try:
            best, _ = self._search_root(board, moves, 2, empty_count)
            if best is not None:
                self.best_move = best
                self.last_completed_depth = 2
        except _core.SearchTimeout:
            pass
        finally:
            self.deadline = overall_deadline

        root = _Node(None, None, self.opponent)
        root.untried = list(moves)
        rng = random.Random()
        rng.shuffle(root.untried)
        try:
            while True:
                self._check_time()
                self._simulate(root, board, empty_count, rng)
                self.last_simulations += 1
        except _core.SearchTimeout:
            pass

        # A partial first pass favors whichever moves happened to be sampled.
        # Keep the baseline result until UCT has visited every root candidate.
        if (not root.untried and root.children
                and all(child.visits > 0 for child in root.children)):
            selected = max(root.children, key=lambda child: (
                child.visits, child.value / child.visits,
                -child.move[0], -child.move[1]))
            self.best_move = selected.move
            self.last_mcts_selected = True
        return self.best_move
