"""Smoke test: every page renders without exceptions; the product screens carry no explanatory banner."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
PAGES = ["home.py", "manager_case.py", "learning.py", "leadership.py", "data.py", "engine_debug.py"]


@pytest.mark.parametrize("page", PAGES)
def test_page_renders(page, monkeypatch):
    monkeypatch.chdir(ROOT)
    at = AppTest.from_file(str(ROOT / "app_pages" / page), default_timeout=60).run()
    assert not at.exception
    assert not any("Dados sintéticos e ilustrativos" in info.value for info in at.info)


def test_entry_point_runs(monkeypatch):
    monkeypatch.chdir(ROOT)
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    assert not at.exception
    labels = [b.label for b in at.sidebar.button]
    assert any("Caso da Mariana" in lbl for lbl in labels) and any("Avançar 12 meses" in lbl for lbl in labels)
    assert any("dados fictícios" in c.value for c in at.sidebar.caption)
