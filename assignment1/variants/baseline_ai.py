"""Fixed-depth minimax/alpha-beta baseline for comparisons."""

import importlib.util
import sys
from pathlib import Path


_spec = importlib.util.spec_from_file_location(
    "_gomoku_baseline_core", Path(__file__).with_name("_core.py"))
_core = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _core
_spec.loader.exec_module(_core)

NAME = "FixedDepthBaseline"
GomokuAI = _core.SearchAI
