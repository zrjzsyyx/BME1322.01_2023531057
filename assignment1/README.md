# Assignment 1: Gomoku

Requires Python 3.9 or newer. No third-party packages are needed.

Run these commands from the repository root. Coordinates are zero-based `row col`;
`q` exits a human game.

```bash
# Human vs human
python assignment1/main.py --mode human-human --board 9 --win 4

# Human (white) vs the included AI (black)
python assignment1/main.py --mode human-ai --human-color white

# Included AI vs the random baseline
python assignment1/main.py --mode ai-ai --black-ai assignment1/gomoku_ai.py --white-ai assignment1/random_ai.py --board 9 --win 4 --time 5
```

The default configuration is a 15×15 board with five in a row. `--board N`
and `--win K` work for any `N >= 3` and `3 <= K <= N`. In AI vs AI mode,
each side can load any Python file implementing `GomokuAI(player_id,
board_size, win_length)` and `get_move(board, last_opponent_move, time_limit)`.
The game's AI call is timed; an exception, illegal move, or timeout forfeits.

The file loaded by the course arena is `assignment1/gomoku_ai.py`. For example,
with the provided arena files next to this repository:

```bash
python ../assignment-1-code/arena.py assignment1/gomoku_ai.py ../assignment-1-code/random_ai.py --board 15 --win 5 --quiet
```

## Independent advanced-search variants

Each file below is an arena-compatible `GomokuAI` entry point. They share the
same fixed-depth minimax/alpha-beta rules and evaluation in `variants/_core.py`,
so each variant changes just one advanced search feature:

| File | Search change |
| --- | --- |
| `variants/baseline_ai.py` | Fixed two-ply search for comparison |
| `variants/iterative_ai.py` | Iterative deepening through depths 1–4; only completed depths replace the move |
| `variants/ordering_ai.py` | Tactical move ordering with fixed two-ply search |
| `variants/mcts_ai.py` | MCTS with UCT; fixed two-ply alpha-beta provides a legal fallback |

For example, run each against the supplied random AI by replacing `FILE`:

```bash
python ../assignment-1-code/arena.py assignment1/variants/FILE ../assignment-1-code/random_ai.py --board 9 --win 4 --time 1 --games 2 --quiet
```

`FILE` can be `iterative_ai.py`, `ordering_ai.py`, or `mcts_ai.py`. To play
two variants against each other in the CLI:

```bash
python assignment1/main.py --mode ai-ai --black-ai assignment1/variants/iterative_ai.py --white-ai assignment1/variants/mcts_ai.py --board 9 --win 4
```

The course submission entry point `assignment1/gomoku_ai.py` is the
self-contained fixed-depth baseline. The experimental variants use
`variants/_core.py` from the same repository.

## Four-AI league

`league.py` runs the fixed-depth baseline and the three isolated variants.
Every pair plays six games, alternating colors (three games with black each).
A win earns 3 points, a draw gives each side 1 point, and a loss earns 0.
The league saves each game and updated standings to JSON after every game.

```bash
python assignment1/league.py --board 15 --win 5 --time 5 --games-per-pair 6 --output assignment1/league_replay.json
```

The completed league's raw results are in `assignment1/league_results.json`.
Use `--resume` with a matching output file to continue an interrupted run.

The assignment report is [`report.md`](report.md). Its baseline experiments
were run on the official `assignment1/gomoku_ai.py` submission file: 20 games
against the random AI in each of two board configurations, plus 10 self-play
games. Raw records are in `assignment1/baseline_experiments.json`.
