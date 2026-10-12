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
    if x >= 1e6:
        return f"{sign}R$ {x / 1e6:.1f} mi".replace(".", ",")
    if x >= 1e3:
        return f"{sign}R$ {x / 1e3:.0f} mil"
    return f"{sign}R$ {x:.0f}"


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
