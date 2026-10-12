"""Injects the three scripted personas into the generated world.

Each persona replaces one generated employee in a team of its area, chosen by an explicit
criterion (the team whose manager has the most open cases, so the persona sits in a realistic
queue), and gets exactly the signals listed for it. Everything comes from data/personas.csv and
data/persona_outcomes.csv.
"""

from __future__ import annotations

import pandas as pd

from src.assumptions import Assumptions
from src.signals import CAUSES, DAYS_PER_MONTH, DAYS_PER_YEAR


def _date_ago(t0: pd.Timestamp, days: float) -> pd.Timestamp:
    return (t0 - pd.Timedelta(days=int(round(days)))).normalize()


def persona_signals(p: pd.Series) -> list[str]:
    return sorted(s for s in str(p["signals"]).split(";") if s)


def _open_cases_by_team(truth: pd.DataFrame, hris: pd.DataFrame, a: Assumptions) -> pd.DataFrame:
    comp = dict(zip(a.signals["signal"], a.signals["component"]))
    counts = pd.DataFrame(
        {c: truth[[s for s in comp if comp[s] == c]].sum(axis=1) for c in CAUSES}
    )
    is_case = counts.max(axis=1) >= a.int("case.min_signals_same_cause")
    out = truth[["employee_id"]].assign(is_case=is_case.values)
    return out.merge(hris[["employee_id", "team_id", "role", "country", "level"]], on="employee_id")


def apply_personas(world, a: Assumptions) -> pd.DataFrame:
    """Mutates world tables in place and returns the persona map (persona -> employee, decision maker)."""
    t0 = a.date("general.reference_date")
    pub, hid = world.public, world.hidden
    hris, events, context, managers = (pub[k] for k in ("hris", "events", "context", "managers"))
    truth = hid["truth"]
    medians, factors = a.group("market.median"), a.group("market.country_factor")
    catalog = set(a.signals["signal"])

    team_mgrs = managers[managers["role"] == "Gestor de time"].set_index("team_id")
    used_people: set[str] = set()
    rows = []

    for _, p in a.personas.iterrows():
        wanted = persona_signals(p)
        unknown = set(wanted) - catalog
        if unknown:
            raise ValueError(f"Sinais desconhecidos para {p['name']}: {sorted(unknown)}")
        cases = _open_cases_by_team(truth, hris[hris["status"] == "ativo"], a)
        candidates = []
        for tid, mgr in team_mgrs.iterrows():
            if mgr["area"] != p["area"]:
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

        events.drop(events.index[events["employee_id"] == target], inplace=True)
        new_events = [dict(employee_id=target, date=hire.date(), event="admissão", detail="")]
        if promo > hire + pd.Timedelta(days=30):
            new_events.append(dict(employee_id=target, date=promo.date(), event="promoção", detail=f"para {p['level']}"))
        if pay_change > promo + pd.Timedelta(days=1):
            new_events.append(dict(employee_id=target, date=pay_change.date(), event="reajuste", detail=""))

        context.drop(context.index[context["employee_id"] == target], inplace=True)
        ctx_row = dict(context_id=f"KP{p['persona_id'][1:]}", employee_id=target, date=_date_ago(t0, 30).date(),
                       source=p["context_source"], text=p["context_text"], extracted_event=p["context_event"],
                       component=p["cause"])

        pub["events"] = events = pd.concat([events, pd.DataFrame(new_events)], ignore_index=True)
        pub["context"] = context = pd.concat([context, pd.DataFrame([ctx_row])], ignore_index=True)

        t_idx = truth.index[truth["employee_id"] == target][0]
        truth.loc[t_idx, "cause"] = p["cause"]
        for s in catalog:
            truth.loc[t_idx, s] = s in wanted
        rows.append(dict(persona_id=p["persona_id"], employee_id=target, name=p["name"], team_id=team_id,
                         decision_maker_id=team_mgrs.loc[team_id, "manager_id"], story=p["story"],
                         other_cases_in_team=int(candidates[0][0])))

    pub["events"] = events.sort_values(["date", "employee_id"]).reset_index(drop=True)
    pub["context"] = context.sort_values("context_id").reset_index(drop=True)
    personas = pd.DataFrame(rows)
    pub["personas"] = personas
    return personas
