"""Run a four-AI, six-games-per-pair Gomoku round robin.

Each game creates fresh protocol instances. Results are saved after every game
so an interrupted league can continue with --resume.
"""

import argparse
import itertools
import json
import os
import time
from pathlib import Path

from gomoku_game import GomokuGame
from main import load_ai, timed_ai_move


HERE = Path(__file__).resolve().parent
PLAYERS = {
    "Baseline": HERE / "variants" / "baseline_ai.py",
    "Iterative": HERE / "variants" / "iterative_ai.py",
    "Ordering": HERE / "variants" / "ordering_ai.py",
    "MCTS": HERE / "variants" / "mcts_ai.py",
}

# With an even number of games per pair, both sides take black equally often.
# This mapping only fixes the color of game 1 in each pair.
FIRST_BLACK = {
    ("Baseline", "Iterative"): "Baseline",
    ("Baseline", "Ordering"): "Baseline",
    ("Baseline", "MCTS"): "MCTS",
    ("Iterative", "Ordering"): "Iterative",
    ("Iterative", "MCTS"): "Iterative",
    ("Ordering", "MCTS"): "Ordering",
}


def schedule(games_per_pair):
    games = []
    for first, second in itertools.combinations(PLAYERS, 2):
        preferred = FIRST_BLACK[(first, second)]
        other = second if preferred == first else first
        for index in range(games_per_pair):
            black, white = ((preferred, other) if index % 2 == 0
                            else (other, preferred))
            games.append({
                "id": f"{first}-{second}-{index + 1}",
                "pair": [first, second],
                "black": black,
                "white": white,
            })
    return games


def play_one(plan, board_size, win_length, time_limit):
    game = GomokuGame(board_size, win_length)
    names = {1: plan["black"], 2: plan["white"]}
    instances = {
        color: load_ai(PLAYERS[name], color, board_size, win_length)[0]
        for color, name in names.items()
    }
    last_move = {1: None, 2: None}
    timing = {name: {"turns": 0, "seconds": 0.0, "max_seconds": 0.0}
              for name in names.values()}
    started = time.perf_counter()
    reason = ""
    winner = None

    while not game.finished:
        color = game.next_player
        name = names[color]
        try:
            move, elapsed = timed_ai_move(instances[color], game.board,
                                          last_move[3 - color], time_limit)
            timing[name]["turns"] += 1
            timing[name]["seconds"] += elapsed
            timing[name]["max_seconds"] = max(
                timing[name]["max_seconds"], elapsed)
            game.play(*move)
            last_move[color] = move
        except (TimeoutError, RuntimeError, ValueError) as exc:
            winner = names[3 - color]
            reason = f"{name} forfeited: {exc}"
            break

    if not reason:
        winner = names[game.winner] if game.winner else None
        reason = f"{win_length}-in-a-row" if winner else "draw: board full"
    return {
        **plan,
        "winner": winner,
        "reason": reason,
        "moves": game.move_count,
        "wall_seconds": round(time.perf_counter() - started, 4),
        "timing": timing,
    }


def standings(matches):
    rows = {
        name: {"name": name, "played": 0, "wins": 0, "draws": 0,
               "losses": 0, "points": 0, "black": 0, "white": 0,
               "thinking_turns": 0, "thinking_seconds": 0.0,
               "max_move_seconds": 0.0, "total_game_moves": 0}
        for name in PLAYERS
    }
    for match in matches:
        for color in ("black", "white"):
            name = match[color]
            row = rows[name]
            row["played"] += 1
            row[color] += 1
            row["total_game_moves"] += match["moves"]
            timing = match["timing"][name]
            row["thinking_turns"] += timing["turns"]
            row["thinking_seconds"] += timing["seconds"]
            row["max_move_seconds"] = max(row["max_move_seconds"],
                                           timing["max_seconds"])
            if match["winner"] is None:
                row["draws"] += 1
                row["points"] += 1
            elif match["winner"] == name:
                row["wins"] += 1
                row["points"] += 3
            else:
                row["losses"] += 1
    ranked = sorted(rows.values(), key=lambda row: (-row["points"], row["name"]))
    for index, row in enumerate(ranked):
        row["rank"] = (index + 1 if index == 0 or
                       row["points"] != ranked[index - 1]["points"]
                       else ranked[index - 1]["rank"])
        row["average_move_seconds"] = (
            row["thinking_seconds"] / row["thinking_turns"]
            if row["thinking_turns"] else 0.0)
        row["average_game_moves"] = (
            row["total_game_moves"] / row["played"] if row["played"] else 0.0)
    return ranked


def save_results(path, config, matches):
    payload = {"config": config, "completed_games": len(matches),
               "matches": matches, "standings": standings(matches)}
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    os.replace(temporary, path)


def main():
    parser = argparse.ArgumentParser(description="Four-AI Gomoku round robin")
    parser.add_argument("--board", type=int, default=15)
    parser.add_argument("--win", type=int, default=5)
    parser.add_argument("--time", type=float, default=5.0,
                        help="wall-clock seconds per move")
    parser.add_argument("--games-per-pair", type=int, default=6)
    parser.add_argument("--output", type=Path,
                        default=HERE / "league_results.json")
    parser.add_argument("--resume", action="store_true",
                        help="continue matching results from --output")
    args = parser.parse_args()
    if args.board < 3 or not 3 <= args.win <= args.board:
        parser.error("expected 3 <= K <= N")
    if args.time <= 0 or args.games_per_pair < 1:
        parser.error("--time and --games-per-pair must be positive")

    config = {"board": args.board, "win": args.win,
              "time_limit": args.time, "games_per_pair": args.games_per_pair,
              "scoring": {"win": 3, "draw": 1, "loss": 0},
              "players": list(PLAYERS)}
    planned = schedule(args.games_per_pair)
    output = args.output.resolve()
    if args.resume:
        if not output.is_file():
            parser.error(f"resume file does not exist: {output}")
        prior = json.loads(output.read_text(encoding="utf-8"))
        if prior.get("config") != config:
            parser.error("resume file has different league settings")
        matches = prior["matches"]
        if len(matches) > len(planned) or any(
                {key: played[key] for key in ("id", "black", "white")}
                != {key: expected[key] for key in ("id", "black", "white")}
                for played, expected in zip(matches, planned)):
            parser.error("resume file does not match the planned schedule")
    else:
        if output.exists():
            parser.error(f"output already exists: {output}; use --resume")
        matches = []

    print(f"League: {args.board}x{args.board}, K={args.win}, "
          f"{args.time:g}s/move, {len(planned)} games; "
          f"resuming after {len(matches)}", flush=True)
    for plan in planned[len(matches):]:
        match = play_one(plan, args.board, args.win, args.time)
        matches.append(match)
        save_results(output, config, matches)
        result = match["winner"] or "Draw"
        print(f"[{len(matches):02d}/{len(planned)}] "
              f"{match['black']} (X) vs {match['white']} (O): {result}; "
              f"{match['moves']} moves; {match['reason']}; "
              f"{match['wall_seconds']:.2f}s", flush=True)

    print("\nRank  AI          Pts   W  D  L  Black White Avg move", flush=True)
    for row in standings(matches):
        print(f"{row['rank']:>4}  {row['name']:<10} {row['points']:>3}  "
              f"{row['wins']:>2} {row['draws']:>2} {row['losses']:>2} "
              f"{row['black']:>5} {row['white']:>5} "
              f"{row['average_move_seconds']:>7.3f}s", flush=True)
    print(f"Raw results: {output}", flush=True)


if __name__ == "__main__":
    main()
