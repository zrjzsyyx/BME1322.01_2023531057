"""Command-line Gomoku: human vs human, human vs AI, or AI vs AI.

Examples:
    python main.py --mode human-human --board 9 --win 4
    python main.py --mode human-ai --human-color white
    python main.py --mode ai-ai --black-ai gomoku_ai.py --white-ai random_ai.py
"""

import argparse
import importlib.util
import itertools
import sys
import threading
import time
from pathlib import Path

from gomoku_game import GomokuGame, format_board


DEFAULT_AI = Path(__file__).with_name("gomoku_ai.py")
_module_ids = itertools.count()


def load_ai(path, player_id, board_size, win_length):
    """Load any file implementing Gomoku AI Protocol v1."""
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"AI file not found: {path}")
    spec = importlib.util.spec_from_file_location(
        f"_player_ai_{next(_module_ids)}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load AI file: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    ai = module.GomokuAI(player_id, board_size, win_length)
    return ai, str(getattr(module, "NAME", path.stem))


def timed_ai_move(ai, board, last_opponent_move, time_limit):
    """Give an AI a board copy and enforce its per-move wall-clock limit."""
    result = {}

    def run():
        try:
            result["move"] = ai.get_move([row[:] for row in board],
                                         last_opponent_move, time_limit)
        except BaseException as exc:
            result["error"] = exc

    thread = threading.Thread(target=run, daemon=True)
    start = time.perf_counter()
    thread.start()
    thread.join(time_limit)
    elapsed = time.perf_counter() - start
    if thread.is_alive():
        raise TimeoutError(f"AI exceeded {time_limit:g} seconds")
    if "error" in result:
        raise RuntimeError(f"AI raised {result['error']!r}") from result["error"]
    move = result.get("move")
    if (not isinstance(move, tuple) or len(move) != 2
            or any(isinstance(x, bool) or not isinstance(x, int) for x in move)):
        raise ValueError("AI must return an (int, int) tuple")
    return move, elapsed


def human_move(board_size):
    """Read a zero-based row and column; return None if the user quits."""
    while True:
        try:
            answer = input("落子（行 列，输入 q 退出）：").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return None
        if answer.lower() in ("q", "quit", "exit"):
            return None
        parts = answer.replace(",", " ").split()
        if len(parts) != 2:
            print("请输入两个坐标，例如：7 7")
            continue
        try:
            row, col = map(int, parts)
        except ValueError:
            print("坐标必须是整数。")
            continue
        if 0 <= row < board_size and 0 <= col < board_size:
            return row, col
        print(f"坐标范围是 0 到 {board_size - 1}。")


def play_game(args):
    game = GomokuGame(args.board, args.win)
    if args.mode == "human-human":
        human_players = {1, 2}
    elif args.mode == "human-ai":
        human_players = {1 if args.human_color == "black" else 2}
    else:
        human_players = set()

    ai_players = {}
    if 1 not in human_players:
        ai_players[1] = load_ai(args.black_ai, 1, args.board, args.win)
    if 2 not in human_players:
        ai_players[2] = load_ai(args.white_ai, 2, args.board, args.win)

    names = {1: "黑棋 X", 2: "白棋 O"}
    last_move = {1: None, 2: None}
    print(f"{args.board}×{args.board} 棋盘，{args.win} 连获胜。输入行、列坐标，从 0 开始。")
    print(format_board(game.board))

    while not game.finished:
        player = game.next_player
        print(f"\n轮到{names[player]}。")
        if player in human_players:
            move = human_move(args.board)
            if move is None:
                print("对局已退出。")
                return
        else:
            ai, ai_name = ai_players[player]
            try:
                move, elapsed = timed_ai_move(ai, game.board,
                                              last_move[3 - player], args.time)
            except (TimeoutError, RuntimeError, ValueError) as exc:
                print(f"{ai_name} 判负：{exc}")
                print(f"{names[3 - player]}获胜。")
                return
            print(f"{ai_name} 落子：{move[0]} {move[1]}（{elapsed:.3f} 秒）")
        try:
            game.play(*move)
        except ValueError as exc:
            if player in human_players:
                print(f"无效落子：{exc}")
                continue
            print(f"{ai_players[player][1]} 判负：{exc}")
            print(f"{names[3 - player]}获胜。")
            return
        last_move[player] = move
        print(format_board(game.board))

    if game.winner:
        print(f"\n{names[game.winner]}获胜！")
    else:
        print("\n和棋：棋盘已下满。")


def main():
    parser = argparse.ArgumentParser(description="可配置的广义五子棋游戏")
    parser.add_argument("--mode", choices=("human-human", "human-ai", "ai-ai"),
                        default="human-ai", help="对战模式（默认 human-ai）")
    parser.add_argument("--board", type=int, default=15, help="棋盘边长 N（默认 15）")
    parser.add_argument("--win", type=int, default=5, help="连珠数 K（默认 5）")
    parser.add_argument("--human-color", choices=("black", "white"),
                        default="black", help="人机模式中的玩家棋色")
    parser.add_argument("--black-ai", type=Path, default=DEFAULT_AI,
                        help="黑棋 AI 的 Python 文件路径")
    parser.add_argument("--white-ai", type=Path, default=DEFAULT_AI,
                        help="白棋 AI 的 Python 文件路径")
    parser.add_argument("--time", type=float, default=5.0,
                        help="AI 每步时限，单位秒（默认 5）")
    args = parser.parse_args()
    if args.board < 3 or not 3 <= args.win <= args.board:
        parser.error("必须满足 3 <= K <= N，且 N >= 3")
    if args.time <= 0:
        parser.error("--time 必须大于 0")
    try:
        play_game(args)
    except (OSError, ImportError, AttributeError, TypeError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
