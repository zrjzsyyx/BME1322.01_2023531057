"""Rules for a configurable (N, N, K) Gomoku game."""

DIRECTIONS = ((1, 0), (0, 1), (1, 1), (1, -1))


class GomokuGame:
    def __init__(self, board_size=15, win_length=5):
        if (isinstance(board_size, bool) or not isinstance(board_size, int)
                or board_size < 3):
            raise ValueError("board_size must be an integer >= 3")
        if (isinstance(win_length, bool) or not isinstance(win_length, int)
                or not 3 <= win_length <= board_size):
            raise ValueError("win_length must satisfy 3 <= K <= N")
        self.board_size = board_size
        self.win_length = win_length
        self.board = [[0] * board_size for _ in range(board_size)]
        self.next_player = 1
        self.move_count = 0
        self.winner = 0
        self.finished = False

    def play(self, row, col):
        """Place the next player's stone, or raise ValueError for an illegal move."""
        if self.finished:
            raise ValueError("the game is already over")
        if (isinstance(row, bool) or isinstance(col, bool)
                or not isinstance(row, int) or not isinstance(col, int)
                or not (0 <= row < self.board_size and 0 <= col < self.board_size)):
            raise ValueError("coordinates must be integers inside the board")
        if self.board[row][col] != 0:
            raise ValueError("that cell is occupied")

        player = self.next_player
        self.board[row][col] = player
        self.move_count += 1
        if self._is_win(row, col, player):
            self.winner = player
            self.finished = True
        elif self.move_count == self.board_size * self.board_size:
            self.finished = True
        else:
            self.next_player = 3 - player

    def _is_win(self, row, col, player):
        for dr, dc in DIRECTIONS:
            count = 1
            for sign in (-1, 1):
                r, c = row + sign * dr, col + sign * dc
                while (0 <= r < self.board_size and 0 <= c < self.board_size
                       and self.board[r][c] == player):
                    count += 1
                    r += sign * dr
                    c += sign * dc
            if count >= self.win_length:
                return True
        return False


def format_board(board):
    """Return a board with zero-based row and column labels."""
    width = max(2, len(str(len(board) - 1)))
    lines = [" " * (width + 1) + " ".join(f"{c:>{width}}" for c in range(len(board)))]
    for r, cells in enumerate(board):
        symbols = ("." if cell == 0 else "X" if cell == 1 else "O" for cell in cells)
        lines.append(f"{r:>{width}} " + " ".join(f"{s:>{width}}" for s in symbols))
    return "\n".join(lines)
