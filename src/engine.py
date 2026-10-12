"""Rule engine (no AI). Reads only what the system can observe: raw client data and the Comp network.

Flow per employee: signals -> case (2+ signals of the same cause) -> probable cause (ties shown, human
decides) -> risk if nothing is done (network) -> expected value of each intervention over the horizon
the person would still stay -> recommendation, comparable cases and who decides.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.assumptions import Assumptions
from src.format import num
from src.signals import DAYS_PER_MONTH, compute_signals

CAUSES = ["remuneração", "crescimento", "gestor"]
MONITOR = "Monitorar"


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


def _cost_of_path(h_paths, months, salary, median, a: Assumptions, recurring, one_off):
    """Expected cost over the horizon for monthly hazard paths (draws x months)."""
    replacement = a.num("cost.replacement_share") * salary
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

    # Client history: voluntary exits in the last 12 months, per 6 months.
    former = hris[(hris["status"] == "desligado") & (hris["exit_type"] == "voluntário")]
    recent = former[(t0 - pd.to_datetime(former["exit_date"])).dt.days <= 12 * DAYS_PER_MONTH]
    window = a.num("outcome.window_months")
    company_exit_window = 1 - (1 - len(recent) / len(active)) ** (window / 12)

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
        # Who decides: manager cause goes one level up.
        if person["role"] == "Individual":
            team_mgr = team_manager_of.get(person["team_id"])
            decider = managers.loc[team_mgr, "superior_id"] if cause == "gestor" else team_mgr
        else:
            decider = person["manager_id"]
        decider = decider if isinstance(decider, str) else None

        # Risk if nothing is done: same cause and same number of signals (monitored cases).
        st_k = stats[(stats["attributed_cause"] == cause) & (stats["n_signals"] == k)].set_index("intervention")
        base = st_k.loc[MONITOR]
        exit_w = 1 - base["stay_rate"]
        hazard = -(12 / window) * np.log(1 - exit_w)  # annual
        horizon_years = min(1 / hazard, cap_years)
        months = max(1, int(round(horizon_years * 12)))
        salary = float(person["annual_cost_brl"])
        median = float(bench[(person["level"], person["country"])])

        # Effect of each intervention: pooled over the number of signals of the same cause (more cases,
        # less noise). Uncertainty comes from Beta posteriors on the network counts.
        pooled = pooled_stats.loc[cause]

        def sample(stayed, n):
            return rng.beta(1 + stayed, 1 + n - stayed, draws)

        base_draws = np.clip(1 - sample(base["stayed"], base["n"]), 1e-4, 0.9999)
        h0 = -(12 / window) * np.log(1 - base_draws)
        base_cost = _cost_of_path(np.repeat(h0[:, None], months, axis=1), months, salary, median, a, 0.0, 0.0)
        pool_monitor = np.clip(1 - sample(pooled.loc[MONITOR, "stayed"], pooled.loc[MONITOR, "n"]), 1e-4, 0.9999)

        for name, row in pooled.iterrows():
            pool_exit = np.clip(1 - sample(row["stayed"], row["n"]), 1e-4, 0.9999)
            reduction = 0.0 if name == MONITOR else 1 - pool_exit / pool_monitor
            stay_case = 1 - base_draws * (1 - reduction)
            recurring = name in inter.index and inter.loc[name, "cost_rule"] == "share_of_annual_cost"
            h1 = h0 * (1 - reduction)
            if name == MONITOR:
                ev = np.zeros(draws)
                cost_total, cost_window = 0.0, 0.0
            else:
                paths = np.repeat(np.broadcast_to(h1, (draws,))[:, None], months, axis=1)
                if not recurring:
                    paths[:, one_off_months:] = h0[:, None]
                rate_cost = a.num(inter.loc[name, "cost_key"])
                rec_cost = rate_cost * salary if recurring else 0.0
                one_cost = 0.0 if recurring else rate_cost
                ev = base_cost - _cost_of_path(paths, months, salary, median, a, rec_cost, one_cost)
                cost_total = round(rec_cost * horizon_years, -2) if recurring else one_cost
                cost_window = round(rec_cost * window / 12, -2) if recurring else one_cost
            option_rows.append(dict(
                employee_id=emp, intervention=name,
                target_cause=inter.loc[name, "target_cause"] if name in inter.index else "",
                stay_rate=float(np.median(stay_case)),
                stay_lo=float(np.quantile(stay_case, (1 - level) / 2)),
                stay_hi=float(np.quantile(stay_case, 1 - (1 - level) / 2)),
                network_stay_rate=float(row["stayed"] / row["n"]), n=int(row["n"]),
                reduction=float(np.median(reduction)) if name != MONITOR else 0.0,
                cost_window=cost_window, cost_horizon=cost_total, recurring=bool(recurring),
                ev=float(np.median(ev)), ev_lo=float(np.quantile(ev, (1 - level) / 2)),
                ev_hi=float(np.quantile(ev, 1 - (1 - level) / 2)),
            ))

        opts = pd.DataFrame([o for o in option_rows if o["employee_id"] == emp]).set_index("intervention")
        active_opts = opts.drop(index=MONITOR)
        best = active_opts["ev"].idxmax()
        recommended = best if active_opts.loc[best, "ev"] > 0 else MONITOR
        case_rows.append(dict(
            employee_id=emp, name=person["name"], area=person["area"], team_id=person["team_id"], level=person["level"],
            country=person["country"], role=person["role"], decision_maker_id=decider,
            decision_maker_name=managers.loc[decider, "name"] if decider in managers.index else None,
            escalated=cause == "gestor", cause=cause, tied_causes=", ".join(tied), tie=len(tied) > 1,
            n_signals=k, signals=", ".join(s for s in signals.columns if signals.loc[emp, s]),
            exit_window_no_action=float(exit_w), exit_window_lo=float(1 - base["stay_hi"]), exit_window_hi=float(1 - base["stay_lo"]),
            exit_window_n=int(base["n"]), risk_multiple=float(exit_w / company_exit_window) if company_exit_window else np.nan,
            horizon_years=float(horizon_years), salary=salary, market_median=median,
            recommended=recommended, recommended_ev=float(opts.loc[recommended, "ev"]),
            system_stay=float(opts.loc[recommended, "stay_rate"]),
        ))

    return EngineResult(
        signals=signals, cases=pd.DataFrame(case_rows), options=pd.DataFrame(option_rows),
        network_stats=stats, company_exit_window=company_exit_window,
    )


def signal_evidence(tables: dict[str, pd.DataFrame], a: Assumptions, employee_id: str, active_signals: list[str]) -> list[dict]:
    """Human-readable evidence for each active signal, built only from raw data."""
    t0 = a.date("general.reference_date")
    hris = tables["hris"].set_index("employee_id")
    p = hris.loc[employee_id]
    catalog = a.signals.set_index("signal")
    bench = tables["benchmark"].drop_duplicates(["level", "country"]).set_index(["level", "country"])["median_annual_brl"]
    out = []
    for s in active_signals:
        if s == "compa_below":
            median = bench[(p["level"], p["country"])]
            ev = (f"Custo anual de R$ {p['annual_cost_brl']/1000:.0f} mil, contra mediana de mercado de R$ {median/1000:.0f} mil "
                  f"(compa-ratio {num(p['annual_cost_brl']/median, 2)}; limiar {num(a.num('signals.compa_threshold'), 2)})")
        elif s == "no_raise":
            months = (t0 - pd.Timestamp(p["last_pay_change_date"])).days / DAYS_PER_MONTH
            ev = f"Última mudança salarial há {months:.0f} meses (limiar: {a.int('signals.no_raise_months')})"
        elif s == "time_in_level":
            years = (t0 - pd.Timestamp(p["last_promotion_date"])).days / 365.25
            ref = a.group("signals.time_in_level_ref")[p["level"]] * a.num("signals.time_in_level_multiple")
            ev = f"{num(years)} anos no nível {p['level']} (limiar: {num(ref, 2)} anos)"
        elif s == "tenure_milestone":
            years = (t0 - pd.Timestamp(p["hire_date"])).days / 365.25
            ev = f"{num(years)} anos de casa; completa um marco de tempo de casa nos próximos {a.int('signals.milestone_window_months')} meses"
        elif s in ("external_offer", "growth_request"):
            ctx = tables["context"]
            rows = ctx[ctx["employee_id"] == employee_id]
            ev = " / ".join(rows["text"]) if len(rows) else ""
        elif s == "manager_change":
            mgr = tables["managers"].set_index("team_id").loc[p["team_id"]]
            months = (t0 - pd.Timestamp(mgr["team_start_date"])).days / DAYS_PER_MONTH
            ev = f"O time {p['team_id']} trocou de gestor há {months:.0f} meses"
        elif s == "team_exits":
            ex = tables["hris"]
            ex = ex[(ex["team_id"] == p["team_id"]) & (ex["status"] == "desligado") & (ex["exit_type"] == "voluntário")]
            ex = ex[(t0 - pd.to_datetime(ex["exit_date"])).dt.days <= a.num("signals.team_exits_window_months") * DAYS_PER_MONTH]
            ev = f"{len(ex)} saídas voluntárias no time nos últimos {a.int('signals.team_exits_window_months')} meses"
        elif s == "pulse_manager":
            pl = tables["pulse"]
            score = pl[pl["employee_id"] == employee_id].sort_values("date")["score"].iloc[-1]
            ev = f"Nota {score} de 5 em 'tenho clareza e apoio do meu gestor'"
        else:
            ev = ""
        out.append(dict(signal=s, description=catalog.loc[s, "description"], cause=catalog.loc[s, "component"],
                        source=catalog.loc[s, "source"], evidence=ev))
    return out


def comparable_cases(network: pd.DataFrame, a: Assumptions, cause: str, level: str, intervention: str) -> pd.DataFrame:
    n = a.int("case.comparable_cases")
    sub = network[(network["attributed_cause"] == cause) & (network["level"] == level)
                  & (network["intervention"] == intervention)]
    return sub.sort_values("decision_date", ascending=False).head(n)
