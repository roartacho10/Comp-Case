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
    """How intervention costs are counted (raise paid while the person stays; career action in manager hours)."""
    from src.interventions import hours

    parts = [f"o de {name.lower()} é o tempo de quem decide, cerca de {num(h, 0)} horas por caso, pelo custo-hora de cada um"
             for name in a.interventions["intervention"] if (h := hours(a, name))]
    return "O custo do ajuste salarial é o valor pago enquanto a pessoa ficou" + ("; " + "; ".join(parts) if parts else "") + "."


def replacement_rule(a) -> str:
    """The replacement-cost rule in words, derived from the premises."""
    base, step, cap = (a.num("cost.replacement_base"), a.num("cost.replacement_per_tenure_year"),
                       a.num("cost.replacement_max"))
    years = (cap - base) / step if step > 0 else 0
    y = f"{years:.1f}".replace(".", ",").removesuffix(",0")
    return (f"{pct(base, 0)} do custo anual para quem acabou de entrar, mais {pct(step, 0).replace('%', '')} pontos por ano "
            f"de casa, até {pct(cap, 0)} a partir de {y} anos")
