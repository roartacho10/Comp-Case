"""World loading for the app: generated from the assumptions base and cached by its fingerprint."""

from __future__ import annotations

import streamlit as st

from src import simulation
from src.assumptions import Assumptions
from src.checks import run_checks
from src.engine import check_personas_are_cases, run_engine
from src.generator import generate_world


@st.cache_data(show_spinner="Gerando os dados a partir das premissas…")
def _load(fingerprint: str):
    a = Assumptions.load()
    world = generate_world(a)
    engine = run_engine(world.public, a)
    check_personas_are_cases(engine, world.public["personas"], a)
    context = simulation.make_context(world, a)
    return dict(
        assumptions=a.table,
        signals=a.signals,
        interventions=a.interventions,
        public=world.public,
        checks=run_checks(world, a),
        engine=engine,
        sim_context=context,
        simulated_decisions=simulation.simulated_decisions(context, engine, a),
    )


def load_world() -> dict:
    return _load(Assumptions.load().fingerprint())


def assumptions() -> Assumptions:
    return Assumptions.load()
