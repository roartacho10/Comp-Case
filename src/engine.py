"""Rule engine (no AI). Reads only what the system can observe: raw client data and the Comp network.

Flow per employee: signals -> case (2+ signals of the same cause) -> probable cause (ties shown, human
decides) -> risk if nothing is done (network) -> expected value of each intervention over the horizon
the person would still stay -> recommendation, comparable cases and who decides (the team manager).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.assumptions import Assumptions
from src.format import num
from src.interventions import annual_cost, is_recurring, replacement_share, tenure_years
from src.signals import CAUSES, DAYS_PER_MONTH, compute_signals
from src.periods import HISTORY_MONTHS, OUTCOME_WINDOW_MONTHS

MONITOR = "Monitorar"
PEOPLE_TEAM = ("RH", "Time de People (RH)")  # decides the cases of leaders who have no superior


@dataclass
class EngineResult:
    signals: pd.DataFrame          # employee x signal (bool)
    cases: pd.DataFrame            # one row per open case
    options: pd.DataFrame          # one row per case x intervention
    network_stats: pd.DataFrame    # stay rates by attributed cause x number of signals x intervention
    company_exit_window: float     # observed voluntary exit rate within the outcome window (client history)


def _beta_interval(successes, n, level):
    """Equal-tailed interval of a Beta(1 + s, 1 + n - s) posterior, by sampling (deterministic seed)."""
    rng = np.random.default_rng(0)
    draws = rng.beta(1 + successes, 1 + n - successes, 4000)
    lo, hi = np.quantile(draws, [(1 - level) / 2, 1 - (1 - level) / 2])
    return float(lo), float(hi)


def network_stats(network: pd.DataFrame, a: Assumptions) -> pd.DataFrame:
    comp = dict(zip(a.signals["signal"], a.signals["component"]))
    net = network.copy()
    net["n_signals"] = 0
    for c in CAUSES:
        cols = [f"sig_{s}" for s in comp if comp[s] == c]
        mask = net["attributed_cause"] == c
        net.loc[mask, "n_signals"] = net.loc[mask, cols].sum(axis=1)
    g = net.groupby(["attributed_cause", "n_signals", "intervention"])
    stats = g.agg(n=("stayed", "size"), stayed=("stayed", "sum"), performing=("performing", "sum")).reset_index()
    stats["stay_rate"] = stats["stayed"] / stats["n"]
    stats["success_rate"] = stats["performing"] / stats["n"]
    level = a.num("ev.interval_level")
    bounds = [_beta_interval(s, n, level) for s, n in zip(stats["stayed"], stats["n"])]
    stats["stay_lo"], stats["stay_hi"] = zip(*bounds)
    return stats


def _cost_of_path(h_paths, months, salary, median, replacement, a: Assumptions, recurring, one_off):
    """Expected cost over the horizon for monthly hazard paths (draws x months)."""
    gap = max(0.0, a.num("cost.replacement_hire_compa") * median - salary)  # per year, paid to the substitute
    dt = 1 / 12
    survive = np.ones(h_paths.shape[0])
    stay_years = np.zeros_like(survive)
    exit_prob = np.zeros_like(survive)
    gap_years = np.zeros_like(survive)
    for m in range(months):
        leave = survive * (1 - np.exp(-h_paths[:, m] * dt))
        stay_years += (survive - leave / 2) * dt
        exit_prob += leave
        survive = survive - leave
        gap_years += (1 - survive) * dt
    return one_off + recurring * stay_years + exit_prob * replacement + gap * gap_years


def run_engine(tables: dict[str, pd.DataFrame], a: Assumptions) -> EngineResult:
    t0 = a.date("general.reference_date")
    hris = tables["hris"]
    active = hris[hris["status"] == "ativo"].set_index("employee_id")
    signals = compute_signals(tables, a)
    comp = dict(zip(a.signals["signal"], a.signals["component"]))
    min_signals = a.int("case.min_signals_same_cause")

    counts = pd.DataFrame({c: signals[[s for s in comp if comp[s] == c]].sum(axis=1) for c in CAUSES})
    top = counts.max(axis=1)
    is_case = top >= min_signals

    # Client history: annual voluntary exit rate over the recorded history, converted to the outcome window.
    history = HISTORY_MONTHS
    former = hris[(hris["status"] == "desligado") & (hris["exit_type"] == "voluntário")]
    recent = former[(t0 - pd.to_datetime(former["exit_date"])).dt.days <= history * DAYS_PER_MONTH]
    window = OUTCOME_WINDOW_MONTHS
    annual_rate = min(0.99, len(recent) / len(active) * 12 / history)
    company_exit_window = 1 - (1 - annual_rate) ** (window / 12)

    stats = network_stats(tables["network_cases"], a)
    pooled_stats = stats.groupby(["attributed_cause", "intervention"])[["n", "stayed"]].sum()
    managers = tables["managers"].set_index("manager_id")
    team_manager_of = tables["managers"].dropna(subset=["team_id"]).set_index("team_id")["manager_id"]
    bench = tables["benchmark"].drop_duplicates(["level", "country"]).set_index(["level", "country"])["median_annual_brl"]

    inter = a.interventions.set_index("intervention")
    one_off_months = a.int("intervention.one_off_effect_months")
    cap_years = a.num("ev.horizon_cap_years")
    draws = a.int("ev.uncertainty_draws")
    level = a.num("ev.interval_level")
    rng = np.random.default_rng(a.int("general.seed"))

    case_rows, option_rows = [], []
    for emp in counts.index[is_case]:
        person = active.loc[emp]
        tied = [c for c in CAUSES if counts.loc[emp, c] == top[emp]]
        cause = tied[0]
        k = int(counts.loc[emp, cause])
        # Who decides: the person's manager (the team manager for team members).
        decider = team_manager_of.get(person["team_id"]) if person["role"] == "Individual" else person["manager_id"]
        decider = decider if isinstance(decider, str) else PEOPLE_TEAM[0]

        # Risk if nothing is done: same cause and same number of signals (monitored cases).
        st_k = stats[(stats["attributed_cause"] == cause) & (stats["n_signals"] == k)].set_index("intervention")
        if MONITOR not in st_k.index:
            raise ValueError(
                f"A rede não tem casos de {cause} com {k} sinais em que nada foi feito, então não há como medir o risco "
                "sem ação. Isso acontece quando todos os gestores seguem a sugestão (premissa "
                "behavior.follow_recommendation igual a 1). Numa solução real, um pequeno grupo de controle ou o "
                "histórico de antes do sistema cumpre esse papel.")
        base = st_k.loc[MONITOR]
        exit_w = 1 - base["stay_rate"]
        hazard = -(12 / window) * np.log(1 - exit_w)  # annual
        horizon_years = min(1 / hazard, cap_years)
        months = max(1, int(round(horizon_years * 12)))
        salary = float(person["annual_cost_brl"])
        median = float(bench[(person["level"], person["country"])])
        tenure = tenure_years(person["hire_date"], t0)
        replacement = replacement_share(a, tenure) * salary

        # Effect of each intervention: pooled over the number of signals of the same cause (more cases,
        # less noise). Uncertainty comes from Beta posteriors on the network counts.
        pooled = pooled_stats.loc[cause]

        def sample(stayed, n):
            return rng.beta(1 + stayed, 1 + n - stayed, draws)

        base_draws = np.clip(1 - sample(base["stayed"], base["n"]), 1e-4, 0.9999)
        h0 = -(12 / window) * np.log(1 - base_draws)
        base_cost = _cost_of_path(np.repeat(h0[:, None], months, axis=1), months, salary, median, replacement, a, 0.0, 0.0)
        pool_monitor = np.clip(1 - sample(pooled.loc[MONITOR, "stayed"], pooled.loc[MONITOR, "n"]), 1e-4, 0.9999)

        for name, row in pooled.iterrows():
            pool_exit = np.clip(1 - sample(row["stayed"], row["n"]), 1e-4, 0.9999)
            reduction = 0.0 if name == MONITOR else 1 - pool_exit / pool_monitor
            stay_case = 1 - base_draws * (1 - reduction)
            recurring = name != MONITOR and is_recurring(a, name)
            h1 = h0 * (1 - reduction)
            if name == MONITOR:
                ev = benefit = np.zeros(draws)
                cost_total, cost_window, cost_annual = 0.0, 0.0, 0.0
            else:
                paths = np.repeat(np.broadcast_to(h1, (draws,))[:, None], months, axis=1)
                if not recurring:
                    paths[:, one_off_months:] = h0[:, None]
                cost_per_year_or_case = float(annual_cost(a, name, salary, median))
                rec_cost = cost_per_year_or_case if recurring else 0.0
                one_cost = 0.0 if recurring else cost_per_year_or_case
                ev = base_cost - _cost_of_path(paths, months, salary, median, replacement, a, rec_cost, one_cost)
                benefit = base_cost - _cost_of_path(paths, months, salary, median, replacement, a, 0.0, 0.0)
                cost_total = round(rec_cost * horizon_years, -2) if recurring else one_cost
                cost_window = round(rec_cost * window / 12, -2) if recurring else one_cost
                cost_annual = round(rec_cost, -2) if recurring else one_cost
            option_rows.append(dict(
                employee_id=emp, intervention=name,
                target_cause=inter.loc[name, "target_cause"] if name in inter.index else "",
                stay_rate=float(np.median(stay_case)),
                stay_lo=float(np.quantile(stay_case, (1 - level) / 2)),
                stay_hi=float(np.quantile(stay_case, 1 - (1 - level) / 2)),
                network_stay_rate=float(row["stayed"] / row["n"]), n=int(row["n"]),
                reduction=float(np.median(reduction)) if name != MONITOR else 0.0,
                cost_window=cost_window, cost_annual=cost_annual, cost_horizon=cost_total, recurring=bool(recurring),
                ev=float(np.median(ev)), expected_cost=float(np.median(benefit - ev)),
                benefit=float(np.median(ev) + np.median(benefit - ev)), ev_lo=float(np.quantile(ev, (1 - level) / 2)),
                ev_hi=float(np.quantile(ev, 1 - (1 - level) / 2)),
            ))

        opts = pd.DataFrame([o for o in option_rows if o["employee_id"] == emp]).set_index("intervention")
        active_opts = opts.drop(index=MONITOR)
        best = active_opts["ev"].idxmax()
        recommended = best if active_opts.loc[best, "ev"] > 0 else MONITOR
        case_rows.append(dict(
            employee_id=emp, name=person["name"], area=person["area"], team_id=person["team_id"], level=person["level"],
            country=person["country"], role=person["role"], decision_maker_id=decider,
            decision_maker_name=managers.loc[decider, "name"] if decider in managers.index else PEOPLE_TEAM[1],
            decision_maker_hourly_cost=(float(active.loc[decider, "annual_cost_brl"]) / a.num("general.work_hours_per_year")
                                        if decider in active.index else np.nan),
            cause=cause, tied_causes=", ".join(tied), tie=len(tied) > 1,
            n_signals=k, signals=", ".join(s for s in signals.columns if signals.loc[emp, s]),
            exit_window_no_action=float(exit_w), exit_window_lo=float(1 - base["stay_hi"]), exit_window_hi=float(1 - base["stay_lo"]),
            exit_window_n=int(base["n"]), risk_multiple=float(exit_w / company_exit_window) if company_exit_window else np.nan,
            horizon_years=float(horizon_years), salary=salary, market_median=median,
            tenure_years=float(tenure), replacement_cost=float(replacement),
            recommended=recommended, recommended_ev=float(opts.loc[recommended, "ev"]),
            system_stay=float(opts.loc[recommended, "stay_rate"]),
        ))

    return EngineResult(
        signals=signals, cases=pd.DataFrame(case_rows), options=pd.DataFrame(option_rows),
        network_stats=stats, company_exit_window=company_exit_window,
    )


def check_personas_are_cases(engine: EngineResult, personas: pd.DataFrame, a: Assumptions | None = None) -> None:
    """The scripted personas must open a case; otherwise the demo has nothing to show. Fails with a clear message."""
    missing = personas[~personas["employee_id"].isin(engine.cases["employee_id"])]
    if len(missing):
        names = ", ".join(missing["name"])
        raise ValueError(
            f"Com as premissas atuais, {names} não abre(m) caso: é preciso ter pelo menos "
            f"{a.int('case.min_signals_same_cause') if a else 'o mínimo de'} sinais da mesma causa. Revise "
            "data/personas.csv ou a premissa case.min_signals_same_cause.")


def signal_evidence(tables: dict[str, pd.DataFrame], a: Assumptions, employee_id: str, active_signals: list[str]) -> list[dict]:
    """Evidence for each active signal, built only from raw data: a technical version (for the engine page)
    and a plain-language version (for the manager)."""
    t0 = a.date("general.reference_date")
    hris = tables["hris"].set_index("employee_id")
    p = hris.loc[employee_id]
    catalog = a.signals.set_index("signal")
    bench = tables["benchmark"].drop_duplicates(["level", "country"]).set_index(["level", "country"])["median_annual_brl"]
    from src.signals import CONTEXT_EVENT_TO_SIGNAL

    ctx = tables["context"]
    ctx = ctx[(ctx["employee_id"] == employee_id)
              & ((t0 - pd.to_datetime(ctx["date"])).dt.days <= a.num("signals.context_window_months") * DAYS_PER_MONTH)]
    out = []
    for s in active_signals:
        if s == "compa_below":
            median = bench[(p["level"], p["country"])]
            gap = 1 - p["annual_cost_brl"] / median
            ev = (f"Custo anual de R$ {p['annual_cost_brl']/1000:.0f} mil, contra mediana de mercado de R$ {median/1000:.0f} mil "
                  f"(compa-ratio {num(p['annual_cost_brl']/median, 2)}; limiar {num(a.num('signals.compa_threshold'), 2)})")
            plain = (f"recebe R$ {p['annual_cost_brl']/1000:.0f} mil por ano em salário e encargos; empresas parecidas "
                     f"pagam em média R$ {median/1000:.0f} mil para o mesmo cargo e senioridade ({gap*100:.0f}% abaixo).")
        elif s == "no_raise":
            months = (t0 - pd.Timestamp(p["last_pay_change_date"])).days / DAYS_PER_MONTH
            ev = f"Última mudança salarial há {months:.0f} meses (limiar: {a.int('signals.no_raise_months')})"
            plain = f"o último aumento (promoção ou reajuste) foi há {months:.0f} meses."
        elif s == "time_in_level":
            years = (t0 - pd.Timestamp(p["last_promotion_date"])).days / 365.25
            typical = a.group("signals.time_in_level_ref")[p["level"]]
            ref = typical * a.num("signals.time_in_level_multiple")
            ev = f"{num(years)} anos no nível {p['level']} (limiar: {num(ref, 2)} anos)"
            yrs = f"{years:.0f}" if abs(years - round(years)) < 0.05 else num(years)
            plain = (f"está há {yrs} anos no mesmo cargo e senioridade ({p['level']}); "
                     f"o comum é haver uma promoção em cerca de {num(typical)} anos.")
        elif s == "tenure_milestone":
            years = (t0 - pd.Timestamp(p["hire_date"])).days / 365.25
            ev = f"{num(years)} anos de casa; completa um marco de tempo de casa nos próximos {a.int('signals.milestone_window_months')} meses"
            plain = (f"completa {int(round(years))} anos de empresa nos próximos meses, momento em que muita gente "
                     "reavalia a carreira.")
        elif s in ("external_offer", "growth_request"):
            ev = " / ".join(ctx.loc[ctx["extracted_event"].map(CONTEXT_EVENT_TO_SIGNAL) == s, "text"])
            plain = ev[0].lower() + ev[1:] if ev else ""
        else:
            ev, plain = "", ""
        out.append(dict(signal=s, description=catalog.loc[s, "description"], label=catalog.loc[s, "manager_label"],
                        cause=catalog.loc[s, "component"], source=catalog.loc[s, "source"], evidence=ev, plain=plain))
    return out


def comparable_cases(network: pd.DataFrame, a: Assumptions, cause: str, level: str, intervention: str) -> pd.DataFrame:
    n = a.int("case.comparable_cases")
    sub = network[(network["attributed_cause"] == cause) & (network["level"] == level)
                  & (network["intervention"] == intervention)]
    return sub.sort_values("decision_date", ascending=False).head(n)
