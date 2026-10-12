"""Builds the world from the assumptions base and writes/reads the CSV snapshot."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.assumptions import DATA_DIR, Assumptions
from src.generator import World, generate_world

GENERATED_DIR = DATA_DIR / "generated"
HIDDEN_DIR = DATA_DIR / "hidden"
FINGERPRINT_FILE = GENERATED_DIR / "_assumptions_fingerprint.txt"
COMPRESSED = {"network_cases", "network_truth"}  # large tables: gzip, deterministic (mtime=0)


def _write(df: pd.DataFrame, directory: Path, name: str) -> None:
    if name in COMPRESSED:
        df.to_csv(directory / f"{name}.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
    else:
        df.to_csv(directory / f"{name}.csv", index=False)


def build() -> tuple[Assumptions, World]:
    a = Assumptions.load()
    return a, generate_world(a)


def write_snapshot(a: Assumptions, world: World) -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    HIDDEN_DIR.mkdir(parents=True, exist_ok=True)
    for old in list(GENERATED_DIR.glob("*.csv*")) + list(HIDDEN_DIR.glob("*.csv*")):
        old.unlink()
    for name, df in world.public.items():
        _write(df, GENERATED_DIR, name)
    for name, df in world.hidden.items():
        _write(df, HIDDEN_DIR, name)
    FINGERPRINT_FILE.write_text(a.fingerprint() + "\n")


def snapshot_files(directory: Path) -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in sorted(directory.glob("*.csv*"))}
