"""Session state shared by every page: persona decisions and the global clock (T0 or T0 + window)."""

from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from src import simulation
from src.assumptions import Assumptions

MONTHS = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def init() -> None:
    st.session_state.setdefault("persona_decisions", {})
    st.session_state.setdefault("advanced", False)


def month_label(date: pd.Timestamp) -> str:
    return f"{MONTHS[date.month - 1]}/{date.year}"


def dates(a: Assumptions) -> tuple[pd.Timestamp, pd.Timestamp]:
    t0 = a.date("general.reference_date")
    return t0, t0 + pd.DateOffset(months=a.int("outcome.window_months"))


def sidebar_controls(a: Assumptions) -> None:
    init()
    w = a.int("outcome.window_months")
    t0, t1 = dates(a)
    now = t1 if st.session_state["advanced"] else t0
    with st.sidebar:
        st.markdown(f'Hoje: <span class="time-chip">{month_label(now)}</span>', unsafe_allow_html=True)
        if st.button(f"Avançar {w} meses", type="primary", disabled=st.session_state["advanced"], width="stretch"):
            st.session_state["advanced"] = True
            st.rerun()
        if st.button("Reiniciar", width="stretch"):
            st.session_state["persona_decisions"] = {}
            st.session_state["advanced"] = False
            st.session_state.pop("results_cache", None)
            st.rerun()
        decided = len(st.session_state["persona_decisions"])
        if not st.session_state["advanced"]:
            st.caption(f"Decisões registradas nos casos dos personagens: {decided} de 3. "
                       "Sem decisão, o caso fica como 'monitorar'.")


def results(world: dict, a: Assumptions) -> dict | None:
    """Decisions, outcomes and learning after the window; None while the clock is at T0."""
    init()
    if not st.session_state["advanced"]:
        return None
    key = json.dumps(st.session_state["persona_decisions"], sort_keys=True)
    cache = st.session_state.get("results_cache")
    if cache and cache["key"] == key:
        return cache["value"]
    engine, ctx = world["engine"], world["sim_context"]
    decisions = pd.concat(
        [world["simulated_decisions"],
         simulation.persona_decision_rows(ctx, engine, st.session_state["persona_decisions"])],
        ignore_index=True,
    )
    outcomes = simulation.advance_window(ctx, decisions, a)
    value = dict(decisions=decisions, outcomes=outcomes,
                 learning=simulation.learning(engine, decisions, outcomes, a.num("ev.interval_level")))
    st.session_state["results_cache"] = dict(key=key, value=value)
    return value


def current_decisions(world: dict) -> pd.DataFrame:
    """Decisions in force at T0 (simulated managers + personas registered so far)."""
    init()
    return pd.concat(
        [world["simulated_decisions"],
         simulation.persona_decision_rows(world["sim_context"], world["engine"], st.session_state["persona_decisions"])],
        ignore_index=True,
    )
