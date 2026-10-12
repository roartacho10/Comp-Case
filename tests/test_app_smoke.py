"""Smoke test: every page renders without exceptions and shows the synthetic-data notice."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
PAGES = ["home.py", "manager_case.py", "learning.py", "leadership.py", "data.py", "engine_debug.py"]


@pytest.mark.parametrize("page", PAGES)
def test_page_renders_with_notice(page, monkeypatch):
    monkeypatch.chdir(ROOT)
    at = AppTest.from_file(str(ROOT / "app_pages" / page), default_timeout=60).run()
    assert not at.exception
    assert any("Dados sintéticos e ilustrativos" in info.value for info in at.info)


def test_entry_point_runs(monkeypatch):
    monkeypatch.chdir(ROOT)
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    assert not at.exception
