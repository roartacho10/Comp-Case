from pathlib import Path

import pytest

from src.assumptions import Assumptions
from src.checks import run_checks
from src.generator import generate_world
from src.signals import compute_signals
from src.world_store import FINGERPRINT_FILE, GENERATED_DIR, HIDDEN_DIR, snapshot_files

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def world():
    a = Assumptions.load()
    return a, generate_world(a)


def test_all_checks_pass(world):
    a, w = world
    checks = run_checks(w, a)
    failed = checks[~checks["ok"]]
    assert failed.empty, failed[["checagem", "meta", "obtido"]].to_string()


def test_raw_data_reproduces_drawn_signals(world):
    a, w = world
    observed = compute_signals(w.public, a)
    drawn = w.hidden["truth"].set_index("employee_id").loc[observed.index, observed.columns]
    assert (observed == drawn).all().all()


def test_generation_is_deterministic(world):
    a, w = world
    again = generate_world(Assumptions.load())
    for name, df in w.public.items():
        assert df.equals(again.public[name]), name


def test_committed_snapshot_matches_assumptions(world, tmp_path, monkeypatch):
    """The CSVs in the repository are exactly what the current assumptions generate."""
    a, w = world
    import src.world_store as store

    monkeypatch.setattr(store, "GENERATED_DIR", tmp_path / "generated")
    monkeypatch.setattr(store, "HIDDEN_DIR", tmp_path / "hidden")
    monkeypatch.setattr(store, "FINGERPRINT_FILE", tmp_path / "generated" / "_assumptions_fingerprint.txt")
    store.write_snapshot(a, w)
    assert snapshot_files(tmp_path / "generated") == snapshot_files(GENERATED_DIR)
    assert snapshot_files(tmp_path / "hidden") == snapshot_files(HIDDEN_DIR)
    assert FINGERPRINT_FILE.read_text().strip() == a.fingerprint()


def test_system_modules_never_read_hidden_truth():
    """Only the generator, the checks and the tests may touch the hidden truth."""
    allowed = {"generator.py", "checks.py", "world_store.py", "simulation.py", "personas.py"}
    for path in list((ROOT / "src").glob("*.py")) + list((ROOT / "app_pages").glob("*.py")) + [ROOT / "app.py"]:
        if path.name in allowed:
            continue
        text = path.read_text()
        for pattern in (".hidden", "HIDDEN_DIR", '"truth"', "'truth'", "data/hidden"):
            assert pattern not in text, f"{path.name} references {pattern}"
