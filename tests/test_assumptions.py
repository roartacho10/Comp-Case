import pandas as pd
import pytest

from src.assumptions import Assumptions
from src.checks import run_checks
from src.generator import generate_world


def test_keys_are_unique_and_distributions_sum_to_one():
    a = Assumptions.load()
    assert a.table["key"].is_unique
    for prefix in ("population.country", "population.area", "population.level"):
        assert abs(sum(a.distribution(prefix).values()) - 1) < 1e-9


def test_missing_assumption_raises():
    with pytest.raises(KeyError):
        Assumptions.load().num("does.not.exist")


class _FakeAnthropic:
    """Stands in for anthropic.Anthropic: records the call and returns an empty JSON object."""
    last = {}

    def __init__(self, **kwargs):
        _FakeAnthropic.last["client"] = kwargs
        self.messages = self

    def create(self, **kwargs):
        _FakeAnthropic.last["create"] = kwargs
        block = type("Block", (), {"type": "text", "text": "{}"})()
        return type("Response", (), {"content": [block]})()


def test_every_assumption_is_used(monkeypatch):
    """No orphan rule: every row of the base is read by the generator or the checks."""
    from src import simulation
    from src.engine import comparable_cases, run_engine

    a = Assumptions.load()
    world = generate_world(a)
    run_checks(world, a)
    engine = run_engine(world.public, a)
    ctx = simulation.make_context(world, a)
    decisions = simulation.simulated_decisions(ctx, engine, a)
    simulation.advance_window(ctx, decisions, a)
    from src.leadership import at_t0

    at_t0(dict(engine=engine, public=world.public), a, decisions)
    first = engine.cases.iloc[0]
    comparable_cases(world.public["network_cases"], a, first["cause"], first["level"], first["recommended"])
    import anthropic

    from src import ai

    monkeypatch.setattr(ai, "available", lambda: True)
    monkeypatch.setattr(ai, "_api_key", lambda: "test-key")
    monkeypatch.setattr(anthropic, "Anthropic", _FakeAnthropic)  # exercises the real call path, offline
    ai._store().clear()
    ai.write_summary("texto", {}, a)
    sent = _FakeAnthropic.last["create"]
    assert sent["model"] == a.text("ai.model")
    assert sent["output_config"]["effort"] == a.text("ai.effort")
    assert sent["output_config"]["format"]["type"] == "json_schema"
    assert a.unused() == []


def test_changing_an_assumption_keeps_checks_valid():
    """Targets come from the assumptions, so editing a rule changes the data and the targets together."""
    a = Assumptions.load()
    table = a.table.copy()
    table.loc[table["key"] == "signals.prob_with_cause", "value"] = "0.45"
    edited = Assumptions(table, a.signals, a.interventions)
    checks = run_checks(generate_world(edited), edited)
    failed = checks[~checks["ok"]]
    assert failed.empty, failed[["checagem", "meta", "obtido"]].to_string()
    original_cases = generate_world(a).public["hris"]
    assert not original_cases.equals(generate_world(edited).public["hris"])
