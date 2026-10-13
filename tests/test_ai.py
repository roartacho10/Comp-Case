"""AI layer with a simulated model: accepted outputs, every rejection path and the fallback."""

import json

import pytest

from src import ai
from src.assumptions import Assumptions

TEMPLATE = {
    "intro": "Oi, Daniela. Ponto de atenção sobre Mariana Costa.",
    "signals": ["**Salário abaixo do mercado:** ganha R$ 280 mil por ano; o mercado paga R$ 350 mil (20% abaixo)."],
    "risk": "Em casos parecidos, 4 em cada 10 pessoas saíram em 12 meses quando nada foi feito.",
    "cause": "Remuneração. Vale confirmar com Mariana.",
    "suggestion": "Considerar um ajuste salarial de cerca de R$ 28 mil por ano; de 39% para 19%. Sobram R$ 29 mil. "
                  "A decisão é sua: você conhece o contexto que os dados não mostram.",
    "questions": ["Pergunta 1?", "Pergunta 2?", "Pergunta 3?"],
    "closing": "Registre a decisão; em 12 meses voltamos.",
}
FACTS = {"pessoa": "Mariana Costa", "quem_decide": "Daniela Gomes"}


@pytest.fixture
def a():
    return Assumptions.load()


@pytest.fixture
def fake(monkeypatch):
    """Simulated model: returns whatever the test puts in `fake.reply`."""
    class Fake:
        reply = ""
        calls = 0

    f = Fake()
    ai._store().clear()
    monkeypatch.setattr(ai, "available", lambda: True)

    def call(system, user, a, task="summary"):
        f.calls += 1
        if isinstance(f.reply, Exception):
            raise f.reply
        return f.reply

    monkeypatch.setattr(ai, "_call_model", call)
    return f


def written(**changes):
    out = dict(TEMPLATE, **changes)
    return json.dumps(out, ensure_ascii=False)


def test_valid_output_is_used_and_stored(a, fake):
    fake.reply = written(intro="Oi, Daniela. Queria trazer um ponto sobre a Mariana Costa.")
    r = ai.write_case(TEMPLATE, FACTS, a)
    assert r.source == "ai" and r.value["intro"].startswith("Oi, Daniela. Queria")
    ai.write_case(TEMPLATE, FACTS, a)
    assert fake.calls == 1  # second view comes from the server-side store


@pytest.mark.parametrize("change,reason", [
    (dict(risk="Em casos parecidos, 7 em cada 10 pessoas saíram."), "número fora do pacote"),
    (dict(cause="Ela vai sair se nada mudar."), "termo vetado"),
    (dict(suggestion="Você deve dar um ajuste de R$ 28 mil. A decisão é sua."), "termo vetado"),
    (dict(suggestion="Considerar um ajuste salarial de R$ 28 mil por ano."), "faltou a frase"),
    (dict(questions=["Só uma?"]), "formato inválido"),
])
def test_rejected_outputs_fall_back_to_template(a, fake, change, reason):
    fake.reply = written(**change)
    r = ai.write_case(TEMPLATE, FACTS, a)
    assert r.source == "padrão" and r.value == TEMPLATE and reason in r.reason


def test_timeout_and_garbage_fall_back(a, fake):
    fake.reply = TimeoutError("lento")
    assert ai.write_case(TEMPLATE, FACTS, a).reason.startswith("falha na chamada")
    fake.reply = "não é JSON"
    assert ai.write_case(TEMPLATE, FACTS, a).source == "padrão"


def test_no_key_or_disabled_uses_template(a, monkeypatch):
    monkeypatch.setattr(ai, "available", lambda: False)
    assert "sem chave configurada" in ai.write_case(TEMPLATE, FACTS, a).reason
    monkeypatch.setattr(ai, "available", lambda: True)
    assert "desligada" in ai.write_case(TEMPLATE, FACTS, a, enabled=False).reason


def test_session_limit(a, fake, monkeypatch):
    import streamlit as st

    st.session_state["ai_calls"] = a.int("ai.max_calls_per_session")
    fake.reply = written()
    assert ai.write_case(TEMPLATE, FACTS, a).reason == "limite de chamadas da sessão"
    st.session_state["ai_calls"] = 0


def test_note_reading_must_match_and_quote_literally(a, fake):
    note = "Na conversa de carreira, comentou que tem recebido abordagens de recrutadores."
    fake.reply = json.dumps({"signal": "external_offer", "quote": "tem recebido abordagens de recrutadores"})
    assert ai.read_note(note, "external_offer", a).source == "ai"
    ai._store().clear()
    fake.reply = json.dumps({"signal": "growth_request", "quote": "tem recebido abordagens"})
    assert ai.read_note(note, "external_offer", a).source == "padrão"
    ai._store().clear()
    fake.reply = json.dumps({"signal": "external_offer", "quote": "recebeu uma oferta de R$ 400 mil"})
    assert ai.read_note(note, "external_offer", a).source == "padrão"


def test_prompts_carry_the_validated_rules():
    system = (ai.PROMPTS_DIR / "system.md").read_text().lower()
    for rule in ("oriente, não mande", "use apenas os fatos e números do pacote", "nunca rotule",
                 "nunca uma previsão sobre a pessoa", "não sugira nenhuma ação fora das opções"):
        assert rule in system


class EchoAnthropic:
    """Fake SDK client that rewrites nothing: returns the reference text it received, as the model would."""

    def __init__(self, **kwargs):
        self.messages = self

    def create(self, **kwargs):
        payload = json.loads(kwargs["messages"][0]["content"])
        ref = payload.get("texto_de_referencia")
        if isinstance(ref, dict):
            out = ref
        elif ref is not None:
            out = {"text": ref}
        else:
            out = {"signal": "none", "quote": ""}
        block = type("Block", (), {"type": "text", "text": json.dumps(out, ensure_ascii=False)})()
        return type("Response", (), {"content": [block]})()


@pytest.mark.parametrize("page,advanced", [("manager_case.py", False), ("learning.py", True),
                                           ("leadership.py", False), ("leadership.py", True)])
def test_pages_show_ai_text_when_key_is_configured(monkeypatch, page, advanced):
    from pathlib import Path

    import anthropic
    from streamlit.testing.v1 import AppTest

    monkeypatch.setattr(anthropic, "Anthropic", EchoAnthropic)
    ai._store().clear()
    root = Path(__file__).resolve().parents[1]
    at = AppTest.from_file(str(root / "app_pages" / page), default_timeout=120)
    at.secrets["ANTHROPIC_API_KEY"] = "test-key"
    at.session_state["ai_enabled"] = True
    at.session_state["advanced"] = advanced
    at.session_state["persona_decisions"] = {}
    at.run()
    assert not at.exception
    assert len(ai._store()) > 0, page  # an AI text passed the checks and was used (no badge on product screens)
