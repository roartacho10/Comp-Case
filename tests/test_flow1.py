from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src.assumptions import Assumptions
from src.case_text import build_case_message
from src.engine import run_engine, signal_evidence
from src.generator import generate_world

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = ["flight risk", "vai sair", "desengajad", "alto potencial", "baixo desempenho", "gestor ruim",
             "problemático", "você deve", "é obrigatório", "faça "]


@pytest.fixture(scope="module")
def messages():
    a = Assumptions.load()
    w = generate_world(a)
    eng = run_engine(w.public, a)
    cases = eng.cases.set_index("employee_id")
    out = {}
    for _, p in w.public["personas"].iterrows():
        emp = p["employee_id"]
        case = cases.loc[emp].copy()
        active = [s for s in eng.signals.columns if eng.signals.loc[emp, s]]
        out[p["persona_id"]] = (case, build_case_message(
            case, eng.options[eng.options["employee_id"] == emp], signal_evidence(w.public, a, emp, active),
            eng.network_stats, a))
    return out


def test_messages_guide_and_never_label(messages):
    for pid, (case, msg) in messages.items():
        text = " ".join(v if isinstance(v, str) else " ".join(v) for v in msg.values()).lower()
        for word in FORBIDDEN:
            assert word not in text, (pid, word)
        assert "a decisão é sua" in text
        assert "não é uma previsão sobre" in text
        assert len(msg["questions"]) == 3


def test_personas_suggestions_follow_their_cause(messages):
    expected = {"P1": "Ajuste salarial", "P2": "Carreira e projeto", "P3": "Carreira e projeto"}
    for pid, (case, msg) in messages.items():
        assert case["recommended"] == expected[pid], pid


def test_rejection_requires_justification():
    at = AppTest.from_file(str(ROOT / "app_pages" / "manager_case.py"), default_timeout=120)
    at.session_state["persona"] = "P3"  # chosen by the demo script in the sidebar
    at.run()
    at.radio[0].set_value("Ajuste salarial").run()
    next(b for b in at.button if b.label == "Registrar decisão").click().run()
    assert any("Registre a sua previsão" in e.value for e in at.error)
    at.radio[1].set_value("Provavelmente fica").run()
    next(b for b in at.button if b.label == "Registrar decisão").click().run()
    assert any("caminho diferente da sugestão" in e.value for e in at.error)
    assert "P3" not in at.session_state["persona_decisions"]
    at.text_area[0].input("Acho que um aumento resolve.").run()
    next(b for b in at.button if b.label == "Registrar decisão").click().run()
    assert at.session_state["persona_decisions"]["P3"]["intervention"] == "Ajuste salarial"
    assert at.session_state["persona_decisions"]["P3"]["prediction"] == 0.7
