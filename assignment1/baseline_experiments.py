"""Reproducible baseline-vs-random and baseline self-play experiments."""

import argparse
import json
import os
import random
from pathlib import Path

from gomoku_game import GomokuGame
from main import load_ai, timed_ai_move


HERE = Path(__file__).resolve().parent
BASELINE = HERE / "gomoku_ai.py"
RANDOM_AI = HERE / "random_ai.py"
CONFIGURATIONS = ((15, 5), (9, 4))


def schedule(random_games, self_games):
    plans = []
    for n, k in CONFIGURATIONS:
        for index in range(random_games):
            baseline_black = index % 2 == 0
            plans.append({
                "id": f"random-{n}-{k}-{index + 1}",
                "kind": "random",
                "board": n,
                "win": k,
                "black": "Baseline" if baseline_black else "Random",
                "white": "Random" if baseline_black else "Baseline",
                "seed": 20260929 + 1000 * n + 100 * k + index,
            })
    for index in range(self_games):
        plans.append({
            "id": f"self-{index + 1}",
            "kind": "self",
            "board": 15,
            "win": 5,
            "black": "Baseline-A" if index % 2 == 0 else "Baseline-B",
            "white": "Baseline-B" if index % 2 == 0 else "Baseline-A",
            "seed": None,
        })
    return plans


def play_one(plan, time_limit):
    random.seed(plan["seed"])
    game = GomokuGame(plan["board"], plan["win"])
    names = {1: plan["black"], 2: plan["white"]}
    ai = {
        color: load_ai(RANDOM_AI if name == "Random" else BASELINE,
                       color, plan["board"], plan["win"])[0]
        for color, name in names.items()
    }
    last_move = {1: None, 2: None}
    timing = {name: {"turns": 0, "seconds": 0.0, "max_seconds": 0.0}
              for name in names.values()}
    winner = None
    reason = ""

    while not game.finished:
        color = game.next_player
        name = names[color]
        try:
            move, elapsed = timed_ai_move(ai[color], game.board,
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
        reason = f"{plan['win']}-in-a-row" if winner else "draw: board full"
    return {**plan, "winner": winner, "reason": reason,
            "moves": game.move_count, "timing": timing}


def summarize(matches):
    result = {f"{n}x{n}-K{k}": {} for n, k in CONFIGURATIONS}
    for n, k in CONFIGURATIONS:
        group = [m for m in matches if m["kind"] == "random"
                 and m["board"] == n and m["win"] == k]
        turns = sum(m["timing"]["Baseline"]["turns"] for m in group)
        seconds = sum(m["timing"]["Baseline"]["seconds"] for m in group)
        result[f"{n}x{n}-K{k}"] = {
            "games": len(group),
            "wins": sum(m["winner"] == "Baseline" for m in group),
            "draws": sum(m["winner"] is None for m in group),
            "losses": sum(m["winner"] == "Random" for m in group),
            "baseline_black_games": sum(m["black"] == "Baseline" for m in group),
            "baseline_white_games": sum(m["white"] == "Baseline" for m in group),
            "baseline_black_wins": sum(m["winner"] == "Baseline" and
                                       m["black"] == "Baseline" for m in group),
            "baseline_white_wins": sum(m["winner"] == "Baseline" and
                                       m["white"] == "Baseline" for m in group),
            "baseline_turns": turns,
            "baseline_thinking_seconds": seconds,
            "baseline_average_move_seconds": seconds / turns if turns else 0.0,
            "average_game_moves": (sum(m["moves"] for m in group) / len(group)
                                   if group else 0.0),
        }

    group = [m for m in matches if m["kind"] == "self"]
    turns = sum(sum(stats["turns"] for stats in m["timing"].values())
                for m in group)
    seconds = sum(sum(stats["seconds"] for stats in m["timing"].values())
                  for m in group)
    result["self-play-15x15-K5"] = {
        "games": len(group),
        "black_wins": sum(m["winner"] == m["black"] for m in group),
        "white_wins": sum(m["winner"] == m["white"] for m in group),
        "draws": sum(m["winner"] is None for m in group),
        "baseline_a_black_games": sum(m["black"] == "Baseline-A" for m in group),
        "baseline_a_white_games": sum(m["white"] == "Baseline-A" for m in group),
        "average_game_moves": (sum(m["moves"] for m in group) / len(group)
                               if group else 0.0),
        "average_move_seconds": seconds / turns if turns else 0.0,
        "game_lengths": [m["moves"] for m in group],
    }
    return result


def save(path, config, matches):
    payload = {"config": config, "completed_games": len(matches),
               "matches": matches, "summary": summarize(matches)}
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    os.replace(temporary, path)


def main():
    parser = argparse.ArgumentParser(description="Gomoku baseline experiments")
    parser.add_argument("--time", type=float, default=5.0)
    parser.add_argument("--random-games", type=int, default=20,
                        help="games per configuration, split equally by color")
    parser.add_argument("--self-games", type=int, default=10,
                        help="baseline self-play games, labels swap colors")
    parser.add_argument("--output", type=Path,
                        default=HERE / "baseline_experiments.json")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.time <= 0 or args.random_games < 2 or args.self_games < 2:
        parser.error("positive time and at least two games are required")
    if args.random_games % 2 or args.self_games % 2:
        parser.error("game counts must be even to balance colors")

    plans = schedule(args.random_games, args.self_games)
    config = {"time_limit": args.time,
              "random_games_per_configuration": args.random_games,
              "self_games": args.self_games,
              "configurations": [list(pair) for pair in CONFIGURATIONS],
              "baseline_file": "gomoku_ai.py",
              "random_file": "random_ai.py"}
    output = args.output.resolve()
    if args.resume:
        if not output.is_file():
            parser.error(f"resume file not found: {output}")
        prior = json.loads(output.read_text(encoding="utf-8"))
        if prior.get("config") != config:
            parser.error("resume file settings differ")
        matches = prior["matches"]
        if len(matches) > len(plans) or any(
                played["id"] != expected["id"]
                for played, expected in zip(matches, plans)):
            parser.error("resume file does not match the planned games")
    else:
        if output.exists():
            parser.error(f"output exists: {output}; use --resume")
        matches = []

    print(f"Baseline experiments: {len(plans)} games, "
          f"resuming after {len(matches)}", flush=True)
    for plan in plans[len(matches):]:
        match = play_one(plan, args.time)
        matches.append(match)
        save(output, config, matches)
        print(f"[{len(matches):02d}/{len(plans)}] {plan['id']}: "
              f"{match['winner'] or 'Draw'}, {match['moves']} moves; "
              f"{match['reason']}", flush=True)
    print(json.dumps(summarize(matches), ensure_ascii=False, indent=2), flush=True)
    print(f"Raw results: {output}", flush=True)


if __name__ == "__main__":
    main()
