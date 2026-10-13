"""Session state shared by every page: persona decisions and the global clock (T0 or T0 + window)."""

from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from src import simulation
from src.assumptions import Assumptions
from src.periods import OUTCOME_WINDOW_MONTHS

MONTHS = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def init() -> None:
    st.session_state.setdefault("persona_decisions", {})
    st.session_state.setdefault("advanced", False)
    st.session_state.setdefault("visited", set())
    st.session_state.setdefault("persona", "P1")


def month_label(date: pd.Timestamp) -> str:
    return f"{MONTHS[date.month - 1]}/{date.year}"


def dates(a: Assumptions) -> tuple[pd.Timestamp, pd.Timestamp]:
    t0 = a.date("general.reference_date")
    return t0, t0 + pd.DateOffset(months=OUTCOME_WINDOW_MONTHS)


GUIDE_URL = "https://claude.ai/artifact/8mfpRg2sGhpGHZge4M8tvZ"


def demo_sidebar(a: Assumptions, pages: dict, current) -> None:
    """The demo script in the sidebar: one step per screen, in order, each showing what that user would see."""
    from src.app_data import load_world

    init()
    ss = st.session_state
    personas = load_world()["public"]["personas"]
    w = OUTCOME_WINDOW_MONTHS
    t0, t1 = dates(a)
    advanced = ss["advanced"]
    page = current.url_path
    moment = ss.get("lead_moment", "after" if advanced else "now")

    steps = [dict(key=f"case_{p['persona_id']}", label=f"Caso {'da' if p['name'].split()[0][-1] == 'a' else 'do'} "
                  f"{p['name'].split()[0]}", page="caso", persona=p["persona_id"],
                  done=p["persona_id"] in ss["persona_decisions"],
                  current=page == "caso" and ss.get("persona", "P1") == p["persona_id"])
             for _, p in personas.iterrows()]
    steps += [
        dict(key="lead_now", label="Painel da liderança, hoje", page="lideranca", moment="now",
             done="lead_now" in ss["visited"], current=page == "lideranca" and moment == "now"),
        dict(key="advance", label=f"Avançar {w} meses", done=advanced, current=False, disabled=advanced),
        dict(key="followup", label="Retorno aos gestores", page="retorno", done="followup" in ss["visited"],
             current=page == "retorno", disabled=not advanced),
        dict(key="lead_after", label=f"Painel da liderança, {w} meses depois", page="lideranca", moment="after",
             done="lead_after" in ss["visited"], current=page == "lideranca" and moment == "after",
             disabled=not advanced),
    ]
    with st.sidebar:
        st.markdown(f'Hoje: <span class="time-chip">{month_label(t1 if advanced else t0)}</span>', unsafe_allow_html=True)
        st.page_link(pages["home"], label="Início")
        st.markdown("**Roteiro da demonstração**")
        for step in steps:
            label = f"✓ {step['label']}" if step["done"] else step["label"]
            if st.button(label, key=f"step_{step['key']}", width="stretch", disabled=step.get("disabled", False),
                         type="primary" if step["current"] else "secondary"):
                if step["key"] == "advance":
                    ss["advanced"] = True
                    ss["visited"].add("followup")
                    st.switch_page(pages["retorno"])
                if not step["key"].startswith("case_"):
                    ss["visited"].add(step["key"])
                if "persona" in step:
                    ss["persona"] = step["persona"]
                if "moment" in step:
                    ss["lead_moment"] = step["moment"]
                st.switch_page(pages[step["page"]])
        if st.button("Reiniciar", key="step_reset", width="stretch"):
            for k in ("results_cache", "lead_moment"):
                ss.pop(k, None)
            ss.update(persona_decisions={}, advanced=False, visited=set(), persona="P1")
            st.switch_page(pages["home"])
        st.divider()
        st.caption(f"Demonstração com dados fictícios · [Como funciona]({GUIDE_URL})")


def mark_visited(step: str) -> None:
    init()
    st.session_state["visited"].add(step)


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


def ai_on() -> bool:
    """Live AI texts on (default) or off; the switch lives on the backstage page."""
    return bool(st.session_state.get("ai_enabled", True))
