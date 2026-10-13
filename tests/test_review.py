"""Regression tests for the code review of the final phase (each test names the problem it guards against)."""

from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from src import simulation
from src.assumptions import Assumptions
from src.case_text import build_case_message, outcome_message
from src.engine import PEOPLE_TEAM, check_personas_are_cases, run_engine, signal_evidence
from src.generator import generate_world
from src.interventions import annual_cost
from src.leadership import after_window, at_t0

ROOT = Path(__file__).resolve().parents[1]


def _edited(**changes) -> Assumptions:
    base = Assumptions.load()
    table = base.table.copy()
    for key, value in changes.items():
        assert (table["key"] == key).any(), key
        table.loc[table["key"] == key, "value"] = str(value)
    return Assumptions(table, base.signals, base.interventions)


@pytest.fixture(scope="module")
def base():
    a = Assumptions.load()
    w = generate_world(a)
    eng = run_engine(w.public, a)
    ctx = simulation.make_context(w, a)
    return a, w, eng, ctx, simulation.simulated_decisions(ctx, eng, a)


def _message(a, w, eng, emp):
    case = eng.cases.set_index("employee_id").loc[emp].copy()
    case["name"] = w.public["hris"].set_index("employee_id").loc[emp, "name"]
    active = [s for s in eng.signals.columns if eng.signals.loc[emp, s]]
    opts = eng.options[eng.options["employee_id"] == emp]
    return case, build_case_message(case, opts, signal_evidence(w.public, a, emp, active), eng.network_stats, a)


def test_undecided_personas_are_neither_followed_nor_diverged(base):
    a, w, eng, ctx, sim = base
    dec = pd.concat([sim, simulation.persona_decision_rows(ctx, eng, {})], ignore_index=True)
    out = simulation.advance_window(ctx, dec, a)
    learn = simulation.learning(eng, dec, out)
    world = dict(engine=eng, public=w.public)
    after = after_window(world, a, at_t0(world, a, dec), dict(learning=learn, outcomes=out))
    assert after["n_followed"] + after["n_diverged"] == int(dec["decided"].sum()) == len(dec) - 3
    at = AppTest.from_file(str(ROOT / "app_pages" / "learning.py"), default_timeout=120)
    at.session_state["persona_decisions"] = {}
    at.session_state["advanced"] = True
    at.run()
    assert any("Sem decisão registrada" in c.value for c in at.caption)
    quadrants = " ".join(m.value for m in at.markdown if 'class="quad"' in m.value)
    for name in ("Mariana Costa", "Diego Ramírez", "Lucía Fernández"):
        assert name not in quadrants


def test_salary_adjustment_cost_follows_the_distance_to_market(base):
    a, w, eng, *_ = base
    target, minimum = a.num("cost.raise_target_compa"), a.num("cost.raise_min_share")
    assert annual_cost(a, "Ajuste salarial", 70_000, 100_000) == pytest.approx(target * 100_000 - 70_000)
    assert annual_cost(a, "Ajuste salarial", 99_000, 100_000) == pytest.approx(minimum * 99_000)
    # The economic logic now changes some suggestions: far-from-market raises do not always pay.
    rem = eng.cases[eng.cases["cause"] == "remuneração"]
    assert (rem["recommended"] != "Ajuste salarial").any()


def test_monitor_and_cross_suggestions_explain_the_raise(base):
    a, w, eng, *_ = base
    rem = eng.cases[(eng.cases["cause"] == "remuneração") & (eng.cases["recommended"] != "Ajuste salarial")]
    assert len(rem)
    for emp in rem["employee_id"]:
        _, msg = _message(a, w, eng, emp)
        assert "custaria cerca de" in msg["suggestion"] and "equidade salarial" in msg["suggestion"]
        assert "a decisão é sua" in msg["suggestion"].lower()


def test_people_team_is_greeted_as_a_team(base):
    a, w, eng, *_ = base
    rh = eng.cases[eng.cases["decision_maker_id"] == PEOPLE_TEAM[0]]
    assert len(rh)
    _, msg = _message(a, w, eng, rh["employee_id"].iloc[0])
    assert msg["intro"].startswith("Oi, time de People.")


def test_follow_up_compares_forecasts_on_the_same_cases(base):
    a, w, eng, ctx, sim = base
    dec = pd.concat([sim, simulation.persona_decision_rows(ctx, eng, {})], ignore_index=True)
    out = simulation.advance_window(ctx, dec, a)
    learn = simulation.learning(eng, dec, out)
    calib = learn["calibration"].set_index("decision_maker_id")
    emp = ctx.personas.set_index("persona_id").loc["P1", "employee_id"]
    case = eng.cases.set_index("employee_id").loc[emp].copy()
    case["name"] = "Mariana Costa"
    row = calib.loc[case["decision_maker_id"]]
    assert row["n_forecast"] == row["n"] - 1
    text = outcome_message(learn["closed"].set_index("employee_id").loc[emp], case,
                           eng.options[eng.options["employee_id"] == emp], row, a)
    assert f"Nos {int(row['n_forecast'])} casos deste ciclo em que você registrou previsão" in text


def test_options_never_recommended_show_no_follow_rate(base):
    a, w, eng, ctx, sim = base
    dec = pd.concat([sim, simulation.persona_decision_rows(ctx, eng, {})], ignore_index=True)
    view = at_t0(dict(engine=eng, public=w.public), a, dec)
    bi = view["by_intervention"].set_index("intervention")
    for name, row in bi.iterrows():
        if not (dec["recommended"] == name).any():
            assert pd.isna(row["followed"])


@pytest.mark.parametrize("changes,message", [
    ({"network.months": 12}, "precisa ser maior que a janela fixa"),
    ({"behavior.follow_recommendation": 1.0}, "grupo de controle"),
])
def test_impossible_premises_fail_with_a_clear_message(changes, message):
    a = _edited(**changes)
    with pytest.raises(ValueError, match=message):
        run_engine(generate_world(a).public, a)


def test_personas_that_stop_being_cases_fail_with_a_clear_message():
    a = _edited(**{"case.min_signals_same_cause": 3})
    w = generate_world(a)
    with pytest.raises(ValueError, match="não abre"):
        check_personas_are_cases(run_engine(w.public, a), w.public["personas"], a)
