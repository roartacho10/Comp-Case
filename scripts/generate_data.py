"""Regenerates the synthetic data from the assumptions base and runs the checks.

Usage: python scripts/generate_data.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.checks import run_checks  # noqa: E402
from src.world_store import GENERATED_DIR, build, write_snapshot  # noqa: E402

a, world = build()
write_snapshot(a, world)
checks = run_checks(world, a)
print(f"Dados gerados em {GENERATED_DIR} (impressão digital das premissas: {a.fingerprint()})")
print(checks[["grupo", "checagem", "meta", "obtido", "ok"]].to_string(index=False))
failed = checks[~checks["ok"]]
if len(failed):
    print(f"\n{len(failed)} checagem(ns) falharam.")
    sys.exit(1)
print("\nTodas as checagens passaram.")
