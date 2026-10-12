"""Builds the world from the assumptions base and writes/reads the CSV snapshot."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.assumptions import DATA_DIR, Assumptions
from src.generator import World, generate_world

GENERATED_DIR = DATA_DIR / "generated"
HIDDEN_DIR = DATA_DIR / "hidden"
FINGERPRINT_FILE = GENERATED_DIR / "_assumptions_fingerprint.txt"


def build() -> tuple[Assumptions, World]:
    a = Assumptions.load()
    return a, generate_world(a)


def write_snapshot(a: Assumptions, world: World) -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    HIDDEN_DIR.mkdir(parents=True, exist_ok=True)
    for name, df in world.public.items():
        df.to_csv(GENERATED_DIR / f"{name}.csv", index=False)
    for name, df in world.hidden.items():
        df.to_csv(HIDDEN_DIR / f"{name}.csv", index=False)
    FINGERPRINT_FILE.write_text(a.fingerprint() + "\n")


def snapshot_files(directory: Path) -> dict[str, str]:
    return {p.name: p.read_text() for p in sorted(directory.glob("*.csv"))}


def read_public_snapshot() -> dict[str, pd.DataFrame]:
    return {p.stem: pd.read_csv(p) for p in sorted(GENERATED_DIR.glob("*.csv"))}
