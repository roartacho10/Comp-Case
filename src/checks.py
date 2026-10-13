"""Validation of the generated world against the assumptions.

Targets are derived from the assumptions, never fixed in code: if an assumption
changes, the target changes with it and the check remains valid. Tolerances for
random quantities are three standard errors (at least 2 p.p.).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.assumptions import Assumptions
from src.generator import World
from src.personas import persona_signals
from src.signals import CAUSES, compute_signals
from src.periods import HISTORY_MONTHS, OUTCOME_WINDOW_MONTHS


def _tol(p: float, n: int) -> float:
    return max(0.02, 3 * np.sqrt(p * (1 - p) / max(n, 1)))


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%".replace(".", ",")


def _brl_m(x: float) -> str:
    return f"R$ {x / 1e6:.1f} mi".replace(".", ",")


def run_checks(world: World, a: Assumptions) -> pd.DataFrame:
    rows = []

    def add(group, check, target, observed, ok, note=""):
        rows.append(dict(grupo=group, checagem=check, meta=target, obtido=observed, ok=bool(ok), nota=note))

    pub, hid = world.public, world.hidden
    hris = pub["hris"]
    active = hris[hris["status"] == "ativo"]
    n = len(active)

    # Population ----------------------------------------------------------------
    for dim, col in (("country", "country"), ("area", "area"), ("level", "level")):
        dist = a.distribution(f"population.{dim}")
        obs = active[col].value_counts(normalize=True)
        gap = max(abs(obs.get(k, 0) - v) for k, v in dist.items())
        label = {"country": "país", "area": "área", "level": "nível"}[dim]
        add("População", f"Distribuição por {label}: maior desvio", "≤ 2,0 p.p.", f"{gap * 100:.1f}".replace(".", ",") + " p.p.", gap <= 0.02)
    add("População", "Colaboradores ativos em T0", str(a.int("general.n_employees")), str(n), n == a.int("general.n_employees"))

    mgrs = pub["managers"]
    team_mgrs = mgrs[mgrs["role"] == "Gestor de time"]
    target_reports = a.num("structure.reports_per_team_manager")
    mean_reports = team_mgrs["n_reports"].mean()
    add("População", "Liderados por gestor de time (média)", f"{target_reports:.0f} ± 1,5",
        f"{mean_reports:.1f}".replace(".", ",") + f" (mín. {team_mgrs['n_reports'].min()}, máx. {team_mgrs['n_reports'].max()})",
        abs(mean_reports - target_reports) <= 1.5)

    medians, factors = a.group("market.median"), a.group("market.country_factor")
    level_d, country_d = a.distribution("population.level"), a.distribution("population.country")
    expected_payroll = n * a.num("pay.compa_mean") * sum(
        lv * medians[l] * cv * factors[c] for l, lv in level_d.items() for c, cv in country_d.items()
    )
    payroll = active["annual_cost_brl"].sum()
    add("População", "Folha anual", f"{_brl_m(expected_payroll)} ± 5%", _brl_m(payroll),
        abs(payroll / expected_payroll - 1) <= 0.05, "Seção 3.3: folha de ~R$ 250 mi")

    # Causes --------------------------------------------------------------------
    truth = hid["truth"]
    expected_causes = {
        "remuneração": a.num("cause.compensation"),
        "crescimento": a.num("cause.growth"),
        "externa": a.num("cause.external"),
    }
    obs_causes = truth["cause"].value_counts(normalize=True)
    for c, p in expected_causes.items():
        o = obs_causes.get(c, 0.0)
        tol = _tol(p, len(truth))
        add("Causas (ocultas)", f"Pessoas com causa '{c}'", f"{_pct(p)} ± {_pct(tol)}", _pct(o), abs(o - p) <= tol)

    # Signals -------------------------------------------------------------------
    observed = compute_signals(pub, a)
    drawn = truth.set_index("employee_id").loc[observed.index, observed.columns]
    match = (observed == drawn).all(axis=1).mean()
    add("Sinais", "Sinais recalculados dos dados brutos = sinais sorteados pelas regras", "100%", _pct(match), match == 1.0,
        "Prova de que os dados brutos exibem exatamente os sinais definidos pela causa")

    p_with, p_without = a.num("signals.prob_with_cause"), a.num("signals.prob_without_cause")
    for _, s in a.signals.iterrows():
        pc = expected_causes[s["component"]]
        expected = pc * p_with + (1 - pc) * p_without
        tol = _tol(expected, n)
        o = observed[s["signal"]].mean()
        add("Sinais", f"Prevalência: {s['description']}", f"{_pct(expected)} ± {_pct(tol)}", _pct(o), abs(o - expected) <= tol)

    comp = dict(zip(a.signals["signal"], a.signals["component"]))
    counts = pd.DataFrame({c: observed[[s for s in observed.columns if comp[s] == c]].sum(axis=1) for c in CAUSES})
    n_cases = int((counts.max(axis=1) >= a.int("case.min_signals_same_cause")).sum())
    add("Sinais", "Casos que seriam abertos em T0 (informativo)", "—", f"{n_cases} (~" + f"{n_cases / len(team_mgrs):.1f}".replace(".", ",") + " por gestor de time)", True)

    # Exits ---------------------------------------------------------------------
    former = hris[(hris["status"] == "desligado") & (hris["exit_type"] == "voluntário")]
    turnover = len(former) / n
    exp_turnover = world.notes["expected_turnover"] * HISTORY_MONTHS / 12
    add("Saídas", "Turnover voluntário nos últimos 12 meses", f"{_pct(exp_turnover)} ± 1,0 p.p.", _pct(turnover),
        abs(turnover - exp_turnover) <= 0.01, "Seção 3.3: ~15% ao ano")
    reg = former["regretted"].astype(bool).mean()
    reg_target = a.num("exit.regretted_share")
    tol = _tol(reg_target, len(former))
    add("Saídas", "Fração de saídas arrependidas", f"{_pct(reg_target)} ± {_pct(tol)}", _pct(reg), abs(reg - reg_target) <= tol,
        "Seção 3.3: metade arrependida")
    loss = (former.loc[former["regretted"].astype(bool), "annual_cost_brl"] * a.num("cost.replacement_share")).sum()
    add("Saídas", "Custo de reposição das saídas arrependidas em 12 meses (informativo)", "Seção 3.3: ~R$ 14 mi",
        _brl_m(loss), True)

    # Network -------------------------------------------------------------------
    net = pub["network_cases"]
    companies = pub["network_companies"]
    employees = int(companies["employees"].sum())
    years = (a.num("network.months") - OUTCOME_WINDOW_MONTHS) / 12
    expected_cases = int(round(employees * world.notes["case_rate"] * years))
    add("Rede", "Colaboradores nos clientes da rede (informativo)", "—", f"{employees:,}".replace(",", "."), True)
    add("Rede", "Casos fechados na rede", f"{expected_cases:,}".replace(",", "."), f"{len(net):,}".replace(",", "."),
        len(net) == expected_cases,
        "Colaboradores da rede × fração com caso aberto no cliente × anos de decisões com resultado")
    add("Rede", "Empresas na rede", str(a.int("network.n_companies")), str(net["company_id"].nunique()),
        net["company_id"].nunique() == a.int("network.n_companies"))
    by_cause = dict(zip(a.interventions["target_cause"], a.interventions["intervention"]))
    for c in CAUSES:
        sub = net[net["attributed_cause"] == c]
        rates = sub.groupby("intervention")["stayed"].agg(["mean", "size"])
        best = rates["mean"].idxmax()
        detail = "; ".join(f"{k}: {_pct(r['mean'])} (n={int(r['size'])})" for k, r in rates.iterrows())
        add("Rede", f"Causa atribuída '{c}': intervenção certa tem a maior permanência na janela de resultado",
            by_cause[c], best, best == by_cause[c], detail)
    cell_min = int(net.groupby(["attributed_cause", "intervention"]).size().min())
    add("Rede", "Menor número de casos por combinação causa × intervenção", "≥ 30", str(cell_min), cell_min >= 30)

    # Personas and engine ------------------------------------------------------------
    from src.engine import run_engine

    engine = run_engine(pub, a)
    cases = engine.cases.set_index("employee_id")
    comp = dict(zip(a.signals["signal"], a.signals["component"]))
    by_cause = dict(zip(a.interventions["target_cause"], a.interventions["intervention"]))
    script = a.personas.set_index("persona_id")
    for _, p in pub["personas"].iterrows():
        emp, label = p["employee_id"], p["name"]
        cause = script.loc[p["persona_id"], "cause"]
        expected = persona_signals(script.loc[p["persona_id"]])
        found = sorted(s for s in engine.signals.columns if engine.signals.loc[emp, s])
        add("Personagens", f"{label}: sinais encontrados pelo motor", ", ".join(expected), ", ".join(found), found == expected)
        ok_case = emp in cases.index
        add("Personagens", f"{label}: causa provável", cause, cases.loc[emp, "cause"] if ok_case else "sem caso",
            ok_case and cases.loc[emp, "cause"] == cause and not cases.loc[emp, "tie"])
        add("Personagens", f"{label}: recomendação", by_cause[cause], cases.loc[emp, "recommended"] if ok_case else "—",
            ok_case and cases.loc[emp, "recommended"] == by_cause[cause])
        others = int((cases["decision_maker_id"] == p["decision_maker_id"]).sum()) - 1
        add("Personagens", f"{label}: outros casos com o mesmo decisor", "≥ 2", str(others), others >= 2,
            "Para o retorno comparar a previsão de quem decide em mais de um caso")
    accuracy = (hid["truth"].set_index("employee_id").loc[cases.index, "cause"] == cases["cause"]).mean()
    add("Motor", "Casos abertos em T0", "—", str(len(cases)), True)
    add("Motor", "Causa provável igual à causa verdadeira (informativo)", "—", _pct(accuracy), True,
        "O motor não vê a causa verdadeira; ela só é usada aqui para medir o acerto")

    return pd.DataFrame(rows)
