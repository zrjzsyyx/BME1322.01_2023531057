"""Self-contained Gomoku AI Protocol v1 submission.

Uses fixed-depth minimax, alpha-beta pruning, nearby candidates, a K-aware
evaluation function, and an internal wall-clock deadline.
"""

import time


DIRECTIONS = ((1, 0), (0, 1), (1, 1), (1, -1))
NAME = "FixedDepthBaseline"


class SearchTimeout(Exception):
    pass


class SearchAI:
    def __init__(self, player_id, board_size, win_length):
        if player_id not in (1, 2):
            raise ValueError("player_id must be 1 or 2")
        if board_size < 3 or not 3 <= win_length <= board_size:
            raise ValueError("expected 3 <= K <= N")
        self.player_id = player_id
        self.opponent = 3 - player_id
        self.board_size = board_size
        self.win_length = win_length
        self.windows = self._make_windows()
        self.weights = [0] + [6 ** count for count in range(1, win_length + 1)]
        self.win_score = 1000 * self.weights[win_length] * board_size * board_size
        self.infinity = 2 * self.win_score
        self.deadline = 0.0
        self.best_move = None
        self.last_completed_depth = 0

    def _make_windows(self):
        n, k = self.board_size, self.win_length
        windows = []
        for r in range(n):
            for c in range(n):
                for dr, dc in DIRECTIONS:
                    if 0 <= r + (k - 1) * dr < n and 0 <= c + (k - 1) * dc < n:
                        windows.append(tuple((r + i * dr, c + i * dc)
                                             for i in range(k)))
        return windows

    def _check_time(self):
        if time.perf_counter() >= self.deadline:
            raise SearchTimeout

    def _is_win(self, board, row, col, player):
        n = self.board_size
        for dr, dc in DIRECTIONS:
            count = 1
            for sign in (-1, 1):
                r, c = row + sign * dr, col + sign * dc
                while 0 <= r < n and 0 <= c < n and board[r][c] == player:
                    count += 1
                    r += sign * dr
                    c += sign * dc
            if count >= self.win_length:
                return True
        return False

    def _candidates(self, board, limit=None):
        """Nearby legal moves in a deterministic, geometry-only order."""
        n = self.board_size
        nearby = set()
        has_stone = False
        for r in range(n):
            for c in range(n):
                if board[r][c]:
                    has_stone = True
                    for rr in range(max(0, r - 2), min(n, r + 3)):
                        for cc in range(max(0, c - 2), min(n, c + 3)):
                            if board[rr][cc] == 0:
                                nearby.add((rr, cc))
        if not has_stone:
            return [(n // 2, n // 2)]
        center = (n - 1) / 2
        moves = sorted(nearby, key=lambda move: (
            abs(move[0] - center) + abs(move[1] - center),
            move[0], move[1]))
        return moves if limit is None else moves[:limit]

    def _rank_candidates(self, board, player, limit):
        """Baseline selection: no tactical move ordering inside the search."""
        return self._candidates(board, limit)

    def _evaluate(self, board):
        score = 0
        me, other = self.player_id, self.opponent
        for window in self.windows:
            mine = theirs = 0
            for r, c in window:
                stone = board[r][c]
                if stone == me:
                    mine += 1
                elif stone == other:
                    theirs += 1
                if mine and theirs:
                    break
            else:
                if mine:
                    score += 10 * self.weights[mine]
                elif theirs:
                    score -= 12 * self.weights[theirs]
        return score

    def _minimax(self, board, depth, player, alpha, beta,
                 last_move, empty_count):
        self._check_time()
        if last_move is not None and self._is_win(board, *last_move, 3 - player):
            return (self.win_score + depth if 3 - player == self.player_id
                    else -self.win_score - depth)
        if empty_count == 0:
            return 0
        if depth == 0:
            return self._evaluate(board)

        moves = self._rank_candidates(board, player, 8)
        if not moves:
            return 0
        maximizing = player == self.player_id
        best = -self.infinity if maximizing else self.infinity
        for row, col in moves:
            board[row][col] = player
            try:
                value = self._minimax(board, depth - 1, 3 - player,
                                      alpha, beta, (row, col), empty_count - 1)
            finally:
                board[row][col] = 0
            if maximizing:
                best = max(best, value)
                alpha = max(alpha, best)
            else:
                best = min(best, value)
                beta = min(beta, best)
            if alpha >= beta:
                break
        return best

    def _search_root(self, board, moves, depth, empty_count):
        """Finish a whole minimax depth or raise SearchTimeout."""
        best_move = None
        best_score = -self.infinity
        alpha, beta = -self.infinity, self.infinity
        for row, col in moves:
            self._check_time()
            board[row][col] = self.player_id
            try:
                score = self._minimax(board, depth - 1, self.opponent,
                                      alpha, beta, (row, col), empty_count - 1)
            finally:
                board[row][col] = 0
            if score > best_score:
                best_move, best_score = (row, col), score
            alpha = max(alpha, best_score)
        return best_move, best_score

    def _choose(self, board, moves, empty_count, time_limit):
        """Baseline: one fixed two-ply alpha-beta search."""
        best, _ = self._search_root(board, moves, 2, empty_count)
        if best is not None:
            self.best_move = best
            self.last_completed_depth = 2
        return self.best_move

    def get_move(self, board, last_opponent_move, time_limit):
        n = self.board_size
        if len(board) != n or any(len(row) != n for row in board):
            raise ValueError("board has the wrong size")
        if any(cell not in (0, 1, 2) for row in board for cell in row):
            raise ValueError("board contains an invalid cell")
        board = [row[:] for row in board]
        empty_count = sum(cell == 0 for row in board for cell in row)
        if not empty_count:
            raise ValueError("no legal moves remain")
        self.last_completed_depth = 0
        if empty_count == n * n:
            self.best_move = (n // 2, n // 2)
            return self.best_move

        self.deadline = time.perf_counter() + max(0.0, 0.75 * time_limit)
        candidates = self._candidates(board)
        self.best_move = candidates[0]
        try:
            wins, blocks = [], []
            for row, col in candidates:
                self._check_time()
                board[row][col] = self.player_id
                try:
                    if self._is_win(board, row, col, self.player_id):
                        wins.append((row, col))
                finally:
                    board[row][col] = 0
                board[row][col] = self.opponent
                try:
                    if self._is_win(board, row, col, self.opponent):
                        blocks.append((row, col))
                finally:
                    board[row][col] = 0
            if wins:
                self.best_move = min(wins)
                return self.best_move

            moves = sorted(blocks) if blocks else self._rank_candidates(
                board, self.player_id, 14)
            self.best_move = moves[0]
            if len(moves) == 1:
                return self.best_move
            return self._choose(board, moves, empty_count, time_limit)
        except SearchTimeout:
            return self.best_move


class GomokuAI(SearchAI):
    """Course arena entry point for the fixed-depth baseline."""
