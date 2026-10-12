"""Verbal prediction scale. Managers pick a phrase, not a percentage; each phrase maps to a chance
of staying (premises prediction.scale.*), which is what the calibration uses."""

from __future__ import annotations

from src.assumptions import Assumptions

LEVELS = [
    ("quase_certo_fica", "Quase certo que fica"),
    ("provavelmente_fica", "Provavelmente fica"),
    ("provavelmente_sai", "Provavelmente sai"),
    ("quase_certo_sai", "Quase certo que sai"),
]


def scale(a: Assumptions) -> list[tuple[str, float]]:
    """(label, chance of staying), from the most to the least confident that the person stays."""
    return [(label, a.num(f"prediction.scale.{key}")) for key, label in LEVELS]


def nearest(p: float, a: Assumptions) -> float:
    """Snaps a chance of staying to the closest value of the scale."""
    return min((v for _, v in scale(a)), key=lambda v: (abs(v - p), -v))


def label(p: float, a: Assumptions) -> str:
    return min(scale(a), key=lambda lv: abs(lv[1] - p))[0]


def sentence(p: float, person: str, a: Assumptions) -> str:
    """'quase certo que Mariana ficaria', 'provável que Mariana saísse'..."""
    text = label(p, a)
    return {
        "Quase certo que fica": f"quase certo que {person} ficaria",
        "Provavelmente fica": f"provável que {person} ficasse",
        "Provavelmente sai": f"provável que {person} saísse",
        "Quase certo que sai": f"quase certo que {person} sairia",
    }[text]
