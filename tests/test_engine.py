import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from src import simulation
from src.assumptions import Assumptions
from src.engine import MONITOR, run_engine
from src.generator import generate_world


@pytest.fixture(scope="module")
def setup():
    a = Assumptions.load()
    world = generate_world(a)
    engine = run_engine(world.public, a)
    ctx = simulation.make_context(world, a)
    return a, world, engine, ctx


def test_manager_cause_is_escalated(setup):
    a, world, engine, ctx = setup
    cases = engine.cases
    managers = world.public["managers"].set_index("manager_id")
    for _, c in cases[cases["cause"] == "gestor"].iterrows():
        team_mgr = world.public["hris"].set_index("employee_id").loc[c["employee_id"], "manager_id"]
        assert c["decision_maker_id"] == managers.loc[team_mgr, "superior_id"]


def test_recommendation_has_highest_positive_expected_value(setup):
    a, world, engine, ctx = setup
    for emp, opts in engine.options.groupby("employee_id"):
        rec = engine.cases.set_index("employee_id").loc[emp, "recommended"]
        active = opts[opts["intervention"] != MONITOR]
        best = active.loc[active["ev"].idxmax()]
        assert rec == (best["intervention"] if best["ev"] > 0 else MONITOR)


def test_simulation_is_deterministic_and_independent_of_persona_choices(setup):
    a, world, engine, ctx = setup
    sim_dec = simulation.simulated_decisions(ctx, engine, a)
    choice_1 = {"P1": dict(intervention="Ajuste salarial", prediction=0.8)}
    choice_2 = {"P1": dict(intervention=MONITOR, prediction=0.3)}
    out_1 = simulation.advance_window(
        ctx, pd.concat([sim_dec, simulation.persona_decision_rows(ctx, engine, choice_1)]), a)
    out_2 = simulation.advance_window(
        ctx, pd.concat([sim_dec, simulation.persona_decision_rows(ctx, engine, choice_2)]), a)
    persona_ids = set(ctx.personas["employee_id"])
    others_1 = out_1[~out_1["employee_id"].isin(persona_ids)].reset_index(drop=True)
    others_2 = out_2[~out_2["employee_id"].isin(persona_ids)].reset_index(drop=True)
    assert others_1.drop(columns=["intervention", "had_case"]).equals(others_2.drop(columns=["intervention", "had_case"]))


@pytest.mark.parametrize("pid,intervention,stays,month", [
    ("P1", "Ajuste salarial", True, None), ("P1", MONITOR, False, 4),
    ("P2", "Carreira e projeto", False, 5),
    ("P3", "Escalar para a liderança", True, None), ("P3", "Ajuste salarial", False, 5),
])
def test_persona_scripts(setup, pid, intervention, stays, month):
    a, world, engine, ctx = setup
    sim_dec = simulation.simulated_decisions(ctx, engine, a)
    rows = simulation.persona_decision_rows(ctx, engine, {pid: dict(intervention=intervention, prediction=0.7)})
    out = simulation.advance_window(ctx, pd.concat([sim_dec, rows]), a).set_index("employee_id")
    emp = ctx.personas.set_index("persona_id").loc[pid, "employee_id"]
    assert bool(out.loc[emp, "stayed"]) is stays
    if month:
        assert out.loc[emp, "exit_month"] == month


def test_engine_page_full_flow():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    at = AppTest.from_file(str(root / "app_pages" / "engine_debug.py"), default_timeout=120).run()
    assert not at.exception
    next(b for b in at.button if b.label.startswith("Avançar")).click().run()  # undecided personas -> monitor
    assert not at.exception
    assert any("Personagens: previsto contra realizado" in m.value for m in at.markdown)
