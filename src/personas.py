"""Injects the three scripted personas into the generated world.

Each persona replaces one generated employee in a team chosen by explicit criteria, and gets
exactly the three signals of its cause. For the manager-cause persona, the team itself is set to
have a recent manager change and recent exits; teammates inherit those team-level signals, as in
any team. Everything comes from data/personas.csv and data/persona_outcomes.csv.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.assumptions import Assumptions
from src.signals import DAYS_PER_MONTH, DAYS_PER_YEAR

CAUSES = ["remuneração", "crescimento", "gestor"]


def _date_ago(t0: pd.Timestamp, days: float) -> pd.Timestamp:
    return (t0 - pd.Timedelta(days=int(round(days)))).normalize()


def _open_cases_by_team(truth: pd.DataFrame, hris: pd.DataFrame, a: Assumptions) -> pd.DataFrame:
    comp = dict(zip(a.signals["signal"], a.signals["component"]))
    counts = pd.DataFrame(
        {c: truth[[s for s in comp if comp[s] == c]].sum(axis=1) for c in CAUSES}
    )
    is_case = counts.max(axis=1) >= a.int("case.min_signals_same_cause")
    out = truth[["employee_id"]].assign(is_case=is_case.values, cause_of_case=counts.idxmax(axis=1).values)
    return out.merge(hris[["employee_id", "team_id", "role", "country", "level"]], on="employee_id")


def apply_personas(world, a: Assumptions) -> pd.DataFrame:
    """Mutates world tables in place and returns the persona map (persona -> employee, decision maker)."""
    t0 = a.date("general.reference_date")
    pub, hid = world.public, world.hidden
    hris, events, pulse, context, managers = (pub[k] for k in ("hris", "events", "pulse", "context", "managers"))
    truth = hid["truth"]
    problem_teams = set(hid["problem_teams"]["team_id"])
    medians, factors = a.group("market.median"), a.group("market.country_factor")
    comp = dict(zip(a.signals["signal"], a.signals["component"]))
    exits_window = a.num("signals.team_exits_window_months") * DAYS_PER_MONTH

    team_mgrs = managers[managers["role"] == "Gestor de time"].set_index("team_id")
    active_ic = hris[(hris["status"] == "ativo") & (hris["role"] == "Individual")]
    team_signal = truth.set_index("employee_id")[["manager_change", "team_exits"]]
    used_people: set[str] = set()
    rows = []

    for _, p in a.personas.iterrows():
        cases = _open_cases_by_team(truth, hris[hris["status"] == "ativo"], a)
        candidates = []
        for tid, mgr in team_mgrs.iterrows():
            if mgr["area"] != p["area"]:
                continue
            members = active_ic[active_ic["team_id"] == tid]
            if members.empty:
                continue
            team_has_signals = team_signal.loc[members["employee_id"]].any().any()
            if p["cause"] == "gestor":
                if tid not in problem_teams:
                    continue
            elif tid in problem_teams or team_has_signals:
                continue
            same = cases[(cases["team_id"] == tid) & cases["is_case"]]
            candidates.append((len(same), tid))
        if not candidates:
            raise ValueError(f"Nenhum time elegível para {p['name']}")
        candidates.sort(key=lambda x: (-x[0], x[1]))
        team_id = candidates[0][1]

        # Replace the member most similar to the persona and without a case of their own.
        members = cases[(cases["team_id"] == team_id) & (cases["role"] == "Individual")
                        & ~cases["employee_id"].isin(used_people)].copy()
        members["score"] = (
            (members["country"] == p["country"]).astype(int) * 2
            + (members["level"] == p["level"]).astype(int)
            - members["is_case"].astype(int) * 4
        )
        target = members.sort_values(["score", "employee_id"], ascending=[False, True]).iloc[0]["employee_id"]
        used_people.add(target)

        # Raw data of the persona.
        hire = _date_ago(t0, p["tenure_years"] * DAYS_PER_YEAR)
        promo = max(_date_ago(t0, p["years_in_level"] * DAYS_PER_YEAR), hire)
        pay_change = max(_date_ago(t0, p["months_since_pay_change"] * DAYS_PER_MONTH), promo)
        cost = round(p["compa"] * medians[p["level"]] * factors[p["country"]], -2)
        idx = hris.index[hris["employee_id"] == target][0]
        hris.loc[idx, ["name", "country", "level", "hire_date", "last_promotion_date", "last_pay_change_date",
                       "annual_cost_brl"]] = [p["name"], p["country"], p["level"], hire.date(), promo.date(),
                                              pay_change.date(), cost]

        events.drop(events.index[(events["employee_id"] == target) & (events["event"] != "troca de gestor")],
                    inplace=True)
        new_events = [dict(employee_id=target, date=hire.date(), event="admissão", detail="")]
        if promo > hire + pd.Timedelta(days=30):
            new_events.append(dict(employee_id=target, date=promo.date(), event="promoção", detail=f"para {p['level']}"))
        if pay_change > promo + pd.Timedelta(days=1):
            new_events.append(dict(employee_id=target, date=pay_change.date(), event="reajuste", detail=""))
        events_add = pd.DataFrame(new_events)

        pulse.loc[pulse["employee_id"] == target, ["score", "date"]] = [int(p["pulse_score"]), _date_ago(t0, 10).date()]
        context.drop(context.index[context["employee_id"] == target], inplace=True)
        ctx_row = dict(context_id=f"KP{p['persona_id'][1:]}", employee_id=target, date=_date_ago(t0, 30).date(),
                       source=p["context_source"], text=p["context_text"], extracted_event=p["context_event"],
                       component=p["cause"])

        # Team-level facts for the manager-cause persona.
        if p["cause"] == "gestor":
            start = _date_ago(t0, float(p["team_manager_change_months"]) * DAYS_PER_MONTH)
            managers.loc[managers["team_id"] == team_id, "team_start_date"] = start.date()
            team_members = hris[(hris["team_id"] == team_id) & (hris["role"] == "Individual") & (hris["status"] == "ativo")]
            events.drop(events.index[events["employee_id"].isin(team_members["employee_id"])
                                     & (events["event"] == "troca de gestor")], inplace=True)
            mgr_id = team_mgrs.loc[team_id, "manager_id"]
            change_events = [dict(employee_id=e, date=start.date(), event="troca de gestor", detail=f"novo gestor: {mgr_id}")
                             for e, h in zip(team_members["employee_id"], pd.to_datetime(team_members["hire_date"])) if h < start]
            events_add = pd.concat([events_add, pd.DataFrame(change_events)], ignore_index=True)

            exits = hris[(hris["status"] == "desligado") & (hris["exit_type"] == "voluntário")]
            age = (t0 - pd.to_datetime(exits["exit_date"])).dt.days
            recent_here = exits[(exits["team_id"] == team_id) & (age <= exits_window)]
            missing = int(p["team_recent_exits"]) - len(recent_here)
            donors = exits[(age > exits_window) & (exits["team_id"] != team_id)].sort_values("employee_id").head(max(missing, 0))
            area = team_mgrs.loc[team_id, "area"]
            for k, (j, d) in enumerate(donors.iterrows()):
                exit_date = _date_ago(t0, 20 + k * 45)
                hire_d = (exit_date - pd.Timedelta(days=int(18 * DAYS_PER_MONTH))).date()
                hris.loc[j, ["team_id", "area", "manager_id", "exit_date", "hire_date", "last_promotion_date",
                             "last_pay_change_date"]] = [team_id, area, mgr_id, exit_date.date(), hire_d, hire_d, hire_d]
                events.loc[(events["employee_id"] == d["employee_id"]) & (events["event"] == "desligamento voluntário"),
                           "date"] = exit_date.date()
                events.loc[(events["employee_id"] == d["employee_id"]) & (events["event"] == "admissão"), "date"] = hire_d
            mask = truth["employee_id"].isin(team_members["employee_id"])
            truth.loc[mask, ["manager_change", "team_exits"]] = True
            decision_maker = team_mgrs.loc[team_id, "superior_id"]
        else:
            decision_maker = team_mgrs.loc[team_id, "manager_id"]

        pub["events"] = events = pd.concat([events, events_add], ignore_index=True)
        pub["context"] = context = pd.concat([context, pd.DataFrame([ctx_row])], ignore_index=True)

        t_idx = truth.index[truth["employee_id"] == target][0]
        truth.loc[t_idx, "cause"] = p["cause"]
        truth.loc[t_idx, "in_problem_team"] = p["cause"] == "gestor"
        for s, c in comp.items():
            truth.loc[t_idx, s] = c == p["cause"]
        rows.append(dict(persona_id=p["persona_id"], employee_id=target, name=p["name"], team_id=team_id,
                         decision_maker_id=decision_maker, story=p["story"],
                         other_cases_in_team=int(candidates[0][0])))

    pub["events"] = events.sort_values(["date", "employee_id"]).reset_index(drop=True)
    pub["context"] = context.sort_values("context_id").reset_index(drop=True)
    personas = pd.DataFrame(rows)
    pub["personas"] = personas
    return personas
