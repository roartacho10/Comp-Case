"""Brazilian number formatting for the interface."""

import math


def pct(x, digits=1) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    return f"{x * 100:.{digits}f}%".replace(".", ",")


def pp(x, digits=1) -> str:
    return f"{x:+.{digits}f} p.p.".replace(".", ",")


def brl(x) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    sign = "−" if x < 0 else ""
    x = abs(x)
    if round(x, -3) >= 1e6:  # 999.600 rounds to "R$ 1,0 mi", not "R$ 1000 mil"
        return f"{sign}R$ {x / 1e6:.1f} mi".replace(".", ",")
    if round(x) >= 1e3:
        return f"{sign}R$ {x / 1e3:.0f} mil"
    return f"{sign}R$ {x:.0f}"


def share_words(x: float) -> str:
    """'metade' for one half, otherwise the percentage ('30%')."""
    return "metade" if abs(x - 0.5) < 1e-9 else pct(x, 0)


def num(x, digits=1) -> str:
    return f"{x:.{digits}f}".replace(".", ",")


def cost_note(a) -> str:
    """How intervention costs are counted: fixed-cost actions use the reference premise."""
    inter = a.interventions
    fixed = inter[(inter["cost_rule"] == "fixed") & (inter["cost_key"] != "")]
    parts = [f"{r['intervention'].lower()} é estimado em {brl(a.num(r['cost_key']))} por caso (tempo de gestor e mentoria)"
             for _, r in fixed.iterrows() if a.num(r["cost_key"]) > 0]
    return ("O custo do ajuste salarial é o valor pago no período; o de " + "; o de ".join(parts) +
            ", porque o custo real depende de cada gestor.") if parts else ""
