from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src.case_text import quadrant

ROOT = Path(__file__).resolve().parents[1]
DECISIONS = {
    "P1": dict(intervention="Ajuste salarial", cause="remuneração", prediction=0.8, justification=""),
    "P2": dict(intervention="Carreira e projeto", cause="crescimento", prediction=0.85, justification=""),
    "P3": dict(intervention="Ajuste salarial", cause="remuneração", prediction=0.75, justification="Abaixo do mercado"),
}


def run(page, advanced):
    at = AppTest.from_file(str(ROOT / "app_pages" / page), default_timeout=120)
    at.session_state["persona_decisions"] = dict(DECISIONS)
    at.session_state["advanced"] = advanced
    return at.run()


@pytest.mark.parametrize("page", ["learning.py", "leadership.py"])
def test_pages_before_and_after_window(page):
    for advanced in (False, True):
        at = run(page, advanced)
        assert not at.exception, (page, advanced)


def test_learning_places_each_persona_in_its_quadrant():
    at = run("learning.py", True)
    html = " ".join(m.value for m in at.markdown)
    assert "Retorno para quem decidiu" in " ".join(h.value for h in at.subheader)
    # Mariana followed and stayed; Diego followed and left; Lucía diverged and left.
    assert "Mariana Costa" in html and "Diego Ramírez" in html and "Lucía Fernández" in html
    assert "um resultado ruim não torna a decisão ruim" in html
    assert "em vez da sugestão" in html


def test_quadrant_labels_do_not_blame():
    for followed in (True, False):
        for stayed in (True, False):
            text = quadrant(followed, stayed).lower()
            assert "erro" not in text and "culpa" not in text


def test_leadership_shows_no_individual_names():
    at = run("leadership.py", True)
    text = " ".join(m.value for m in at.markdown) + " ".join(str(df.value) for df in at.dataframe)
    for name in ("Mariana Costa", "Diego Ramírez", "Lucía Fernández"):
        assert name not in text
