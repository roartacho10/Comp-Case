"""The world's clock: what happens in the outcome window (premissa outcome.window_months) after the decisions.

This module plays the role of reality, so it may read the hidden truth (the true cause of each
person). The engine and the interface never do. Outcomes follow the world rules; the three personas
follow their script (data/persona_outcomes.csv). Random streams are fixed by the simulation seed, so
advancing gives the same result every time, and the personas' choices never change anyone else's outcome.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.assumptions import Assumptions
from src.engine import MONITOR, EngineResult
from src.prediction import nearest

NO_CAUSE = "nenhuma"


@dataclass
class SimContext:
    true_cause: pd.Series        # employee_id -> true cause
    personas: pd.DataFrame       # persona_id, employee_id, decision_maker_id, ...
    persona_outcomes: pd.DataFrame
    active_ids: list[str]


def make_context(world, a: Assumptions) -> SimContext:
    truth = world.hidden["truth"].set_index("employee_id")
    hris = world.public["hris"]
    return SimContext(
        true_cause=truth["cause"],
        personas=world.public["personas"],
        persona_outcomes=a.persona_outcomes,
        active_ids=hris.loc[hris["status"] == "ativo", "employee_id"].tolist(),
    )


def _effect(a: Assumptions, intervention: str, cause: str) -> float:
    target = a.interventions.set_index("intervention").loc[intervention, "target_cause"]
    if target == "":
        return 0.0
    return a.num("intervention.effect_right") if target == cause else a.num("intervention.effect_wrong")


def _p_window(a: Assumptions, cause: str) -> float:
    """Exit probability within the outcome window, assuming a constant exit rate over the year."""
    annual = a.num("exit.annual_prob_no_cause") if cause == NO_CAUSE else a.num("exit.annual_prob_with_cause")
    return 1 - (1 - annual) ** (a.num("outcome.window_months") / 12)


def simulated_decisions(ctx: SimContext, engine: EngineResult, a: Assumptions) -> pd.DataFrame:
    """Decisions of the simulated managers for every open case that is not a persona."""
    rng = np.random.default_rng([a.int("general.simulation_seed"), 1])
    inter = a.interventions
    by_cause = dict(zip(inter["target_cause"], inter["intervention"]))
    options = inter["intervention"].tolist()
    follow = a.num("behavior.follow_recommendation")
    sq_right = a.num("behavior.status_quo_prob_right")
    under = a.num("behavior.risk_underestimation")
    noise = a.num("behavior.prediction_noise_pp") / 100
    opts = engine.options.set_index(["employee_id", "intervention"])
    persona_ids = set(ctx.personas["employee_id"])

    rows = []
    for _, case in engine.cases.sort_values("employee_id").iterrows():
        u_follow, u_right, u_pick, u_noise = rng.random(), rng.random(), rng.random(), rng.normal()
        if case["employee_id"] in persona_ids:
            continue
        cause = ctx.true_cause[case["employee_id"]]
        right = by_cause.get(cause)
        if u_follow < follow:
            chosen = case["recommended"]
        elif right is not None and u_right < sq_right:
            chosen = right
        else:
            pool = [o for o in options if o != right]
            chosen = pool[int(u_pick * len(pool))]
        true_exit = _p_window(a, cause) * (1 - _effect(a, chosen, cause))
        prediction = nearest(1 - true_exit * (1 - under) + noise * u_noise, a)  # verbal scale
        rows.append(dict(
            employee_id=case["employee_id"], decision_maker_id=case["decision_maker_id"],
            decision_maker_name=case["decision_maker_name"], cause=case["cause"],
            recommended=case["recommended"], intervention=chosen, followed=chosen == case["recommended"],
            manager_prediction=prediction, system_prediction=float(opts.loc[(case["employee_id"], chosen), "stay_rate"]),
            cost_window=float(opts.loc[(case["employee_id"], chosen), "cost_window"]), justification="", origin="simulado",
        ))
    return pd.DataFrame(rows)


def persona_decision_rows(ctx: SimContext, engine: EngineResult, persona_decisions: dict) -> pd.DataFrame:
    """Persona decisions registered in the interface; undecided personas default to monitoring."""
    cases = engine.cases.set_index("employee_id")
    opts = engine.options.set_index(["employee_id", "intervention"])
    rows = []
    for _, p in ctx.personas.iterrows():
        case = cases.loc[p["employee_id"]]
        d = persona_decisions.get(p["persona_id"], {})
        chosen = d.get("intervention", MONITOR)
        rows.append(dict(
            employee_id=p["employee_id"], decision_maker_id=case["decision_maker_id"],
            decision_maker_name=case["decision_maker_name"], cause=case["cause"], manager_cause=d.get("cause"),
            recommended=case["recommended"], intervention=chosen, followed=chosen == case["recommended"],
            manager_prediction=float(d["prediction"]) if "prediction" in d else np.nan,  # no decision: no forecast
            system_prediction=float(opts.loc[(p["employee_id"], chosen), "stay_rate"]),
            cost_window=float(opts.loc[(p["employee_id"], chosen), "cost_window"]),
            justification=d.get("justification", "" if d else "Sem decisão registrada: monitorar"),
            origin="personagem" if d else "personagem (sem decisão)",
        ))
    return pd.DataFrame(rows)


def advance_window(ctx: SimContext, decisions: pd.DataFrame, a: Assumptions) -> pd.DataFrame:
    """Outcome after the outcome window for every active employee."""
    rng = np.random.default_rng([a.int("general.simulation_seed"), 2])
    window = a.int("outcome.window_months")
    chosen = decisions.set_index("employee_id")["intervention"].to_dict()
    script = ctx.persona_outcomes.set_index(["persona_id", "intervention"])
    persona_of = dict(zip(ctx.personas["employee_id"], ctx.personas["persona_id"]))
    perf_t, perf_u = a.num("outcome.performing_if_treated"), a.num("outcome.performing_if_untreated")
    regretted_share = a.num("exit.regretted_share")
    targets = dict(zip(a.interventions["intervention"], a.interventions["target_cause"]))

    rows = []
    for emp in sorted(ctx.active_ids):
        u_exit, u_month, u_perf, u_reg = rng.random(), rng.integers(1, window + 1), rng.random(), rng.random()
        cause = ctx.true_cause[emp]
        action = chosen.get(emp)
        effect = _effect(a, action, cause) if action else 0.0
        treated = cause == NO_CAUSE or (action is not None and targets.get(action) == cause)
        stayed = u_exit >= _p_window(a, cause) * (1 - effect)
        month = None if stayed else int(u_month)
        performing = bool(stayed and u_perf < (perf_t if treated else perf_u))
        note = ""
        if emp in persona_of:
            s = script.loc[(persona_of[emp], action or MONITOR)]
            stayed = bool(s["stays"])
            month = None if stayed else int(s["exit_month"])
            performing = bool(s["performing"])
            note = s["note"]
        rows.append(dict(employee_id=emp, stayed=stayed, exit_month=month, performing=performing,
                         regretted=bool(not stayed and u_reg < regretted_share), had_case=action is not None,
                         intervention=action, note=note))
    return pd.DataFrame(rows)


def _exit_range(probs: pd.Series, level: float) -> tuple[int, int]:
    """Likely range of the number of exits if the forecast probabilities are right (normal approximation)."""
    from statistics import NormalDist

    z = NormalDist().inv_cdf(1 - (1 - level) / 2)
    mean, sd = probs.sum(), float(np.sqrt((probs * (1 - probs)).sum()))
    return int(np.floor(mean - z * sd)), int(np.ceil(mean + z * sd))


def learning(engine: EngineResult, decisions: pd.DataFrame, outcomes: pd.DataFrame, level: float = 0.8) -> dict[str, pd.DataFrame]:
    closed = decisions.merge(outcomes[["employee_id", "stayed", "performing", "exit_month", "note"]],
                             on="employee_id")

    # Success rates: network before, client cases, network after (network + client).
    net = engine.network_stats.groupby(["attributed_cause", "intervention"])[["n", "stayed"]].sum().reset_index()
    net = net.rename(columns={"attributed_cause": "cause"})
    cli = closed.groupby(["cause", "intervention"]).agg(n_client=("stayed", "size"),
                                                         stayed_client=("stayed", "sum")).reset_index()
    rates = net.merge(cli, on=["cause", "intervention"], how="left").fillna({"n_client": 0, "stayed_client": 0})
    rates["network_before"] = rates["stayed"] / rates["n"]
    rates["client_rate"] = np.where(rates["n_client"] > 0, rates["stayed_client"] / rates["n_client"].clip(lower=1), np.nan)
    rates["network_after"] = (rates["stayed"] + rates["stayed_client"]) / (rates["n"] + rates["n_client"])
    rates["n_after"] = rates["n"] + rates["n_client"]

    # Calibration of each decision maker and of the system, on the same cases.
    # Cases without a registered forecast count in the outcome but not in the manager's expected exits.
    closed = closed.assign(_mgr_exit=1 - closed["manager_prediction"])
    calib = closed.groupby(["decision_maker_id", "decision_maker_name"], dropna=False).agg(
        n=("stayed", "size"), predicted=("manager_prediction", "mean"),
        system=("system_prediction", "mean"), realized=("stayed", "mean"),
        exits_expected_manager=("_mgr_exit", "sum"),
    ).reset_index()
    calib["bias_pp"] = (calib["predicted"] - calib["realized"]) * 100
    calib["exits_expected_system"] = (1 - calib["system"]) * calib["n"]
    calib["exits_realized"] = (1 - calib["realized"]) * calib["n"]
    calib["system_bias_pp"] = (calib["system"] - calib["realized"]) * 100

    summary = pd.DataFrame([dict(
        cases=len(closed), followed=closed["followed"].mean(), stayed=closed["stayed"].mean(),
        performing=closed["performing"].mean(), cost_window=closed["cost_window"].sum(),
        manager_predicted=closed["manager_prediction"].mean(), system_predicted=closed["system_prediction"].mean(),
        exits_expected_manager=(1 - closed["manager_prediction"]).sum(),
        exits_expected_system=(1 - closed["system_prediction"]).sum(),
        exits_range_manager=_exit_range((1 - closed["manager_prediction"]).dropna(), level),
        exits_range_system=_exit_range(1 - closed["system_prediction"], level),
        exits_realized=int((~closed["stayed"]).sum()),
        company_exits=int((~outcomes["stayed"]).sum()), company_regretted=int(outcomes["regretted"].sum()),
    )])
    return dict(closed=closed, rates=rates, calibration=calib, summary=summary)
