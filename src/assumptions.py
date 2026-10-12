"""Single access point to the world rules ("premissas determinísticas").

Every rule of the synthetic world lives in data/assumptions.csv and every module
reads it through this class. No rule value is written in code. The class records
which keys were read, so a test can flag assumptions that nothing uses.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
ASSUMPTIONS_PATH = DATA_DIR / "assumptions.csv"
SIGNALS_PATH = DATA_DIR / "signals.csv"
INTERVENTIONS_PATH = DATA_DIR / "interventions.csv"
PERSONAS_PATH = DATA_DIR / "personas.csv"
PERSONA_OUTCOMES_PATH = DATA_DIR / "persona_outcomes.csv"


class Assumptions:
    def __init__(
        self,
        table: pd.DataFrame,
        signals: pd.DataFrame,
        interventions: pd.DataFrame,
        personas: pd.DataFrame | None = None,
        persona_outcomes: pd.DataFrame | None = None,
    ):
        if not table["key"].is_unique:
            dupes = table.loc[table["key"].duplicated(), "key"].tolist()
            raise ValueError(f"Premissas duplicadas: {dupes}")
        self.table = table.copy()
        self.signals = signals.copy()
        self.interventions = interventions.fillna("").copy()
        self.personas = personas.copy() if personas is not None else pd.read_csv(PERSONAS_PATH)
        self.persona_outcomes = (
            persona_outcomes.copy() if persona_outcomes is not None else pd.read_csv(PERSONA_OUTCOMES_PATH)
        )
        self._values = dict(zip(table["key"], table["value"]))
        self.used: set[str] = set()

    @classmethod
    def load(
        cls,
        path: Path = ASSUMPTIONS_PATH,
        signals_path: Path = SIGNALS_PATH,
        interventions_path: Path = INTERVENTIONS_PATH,
    ) -> "Assumptions":
        return cls(
            pd.read_csv(path, dtype={"value": str}),
            pd.read_csv(signals_path),
            pd.read_csv(interventions_path),
        )

    def fingerprint(self) -> str:
        """Hash of the rules, used to cache generated data and detect stale snapshots."""
        tables = (self.table, self.signals, self.interventions, self.personas, self.persona_outcomes)
        payload = "".join(t.to_csv(index=False) for t in tables)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def _raw(self, key: str) -> str:
        if key not in self._values:
            raise KeyError(f"Premissa ausente na base: {key}")
        self.used.add(key)
        return self._values[key]

    def num(self, key: str) -> float:
        return float(self._raw(key))

    def int(self, key: str) -> int:
        return int(round(float(self._raw(key))))

    def text(self, key: str) -> str:
        return str(self._raw(key))

    def date(self, key: str) -> pd.Timestamp:
        return pd.Timestamp(self._raw(key))

    def group(self, prefix: str) -> dict[str, float]:
        """All numeric values under a prefix, e.g. group('population.country') -> {'Brasil': 0.7, ...}."""
        prefix = prefix.rstrip(".") + "."
        out = {k[len(prefix):]: float(self._raw(k)) for k in self._values if k.startswith(prefix)}
        if not out:
            raise KeyError(f"Nenhuma premissa com o prefixo: {prefix}")
        return out

    def distribution(self, prefix: str) -> dict[str, float]:
        """A group whose values must sum to 1 (a categorical distribution)."""
        dist = self.group(prefix)
        total = sum(dist.values())
        if abs(total - 1) > 1e-6:
            raise ValueError(f"A distribuição {prefix} soma {total:.4f}, e não 1")
        return dist

    def unused(self) -> list[str]:
        return sorted(set(self._values) - self.used)
