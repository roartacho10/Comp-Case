"""AI layer: reads unstructured notes and writes messages from facts computed by the engine.

The AI never calculates and never decides. Every response goes through four checks before it is
shown (format, numbers, forbidden terms, required phrase). If any check fails, if there is no key,
if the call times out or if the session limit is reached, the page shows the reviewed standard text.
Generated texts are stored server-side by input, so later visitors see them instantly.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

import streamlit as st

from src.assumptions import Assumptions

PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"

FORBIDDEN_TERMS = [
    "flight risk", "vai sair", "desengajad", "alto potencial", "baixo desempenho", "gestor ruim", "problemátic",
    "você deve", "é obrigatório", "compa-ratio", "probabilidade posterior",
]
SMALL_NUMBERS_ALLOWED = {"1", "2", "3"}


@dataclass
class AIResult:
    value: dict
    source: str          # "ai" or "padrão"
    reason: str = ""     # why the standard text was used, if it was


def _prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.md").read_text()


def prompts_version() -> str:
    payload = "".join(p.read_text() for p in sorted(PROMPTS_DIR.glob("*.md")))
    return hashlib.sha256(payload.encode()).hexdigest()[:12]


def _api_key() -> str | None:
    try:
        return st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:  # no secrets file at all
        return None


def available() -> bool:
    return bool(_api_key())


@st.cache_resource
def _store() -> dict:
    """Server-wide store of validated AI outputs, keyed by task + input + prompts + model."""
    return {}


def _numbers(text: str) -> set[str]:
    out = set()
    for token in re.findall(r"\d+(?:[.,]\d+)*", text):
        t = token.replace(".", "").replace(",", ".") if re.search(r"\d\.\d{3}", token) else token.replace(",", ".")
        out.add(t.rstrip("0").rstrip(".") if "." in t else t)
    return out


def check(output: dict, payload: dict, required_keys: list[str], required_phrase: str | None) -> str:
    """Returns '' if the output may be shown, or the reason it may not."""
    if not isinstance(output, dict) or any(k not in output for k in required_keys):
        return "formato inválido"
    text = json.dumps(output, ensure_ascii=False)
    lower = text.lower()
    for term in FORBIDDEN_TERMS:
        if term in lower:
            return f"termo vetado: {term}"
    if required_phrase and required_phrase.lower() not in lower:
        return f"faltou a frase: {required_phrase}"
    allowed = _numbers(json.dumps(payload, ensure_ascii=False)) | SMALL_NUMBERS_ALLOWED
    invented = _numbers(text) - allowed
    if invented:
        return f"número fora do pacote: {sorted(invented)[:3]}"
    return ""


def _parse(text: str) -> dict:
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < 0:
        raise ValueError("resposta sem JSON")
    return json.loads(text[start:end + 1])


STRING = {"type": "string"}
SCHEMAS = {
    "case": {
        "type": "object",
        "properties": {
            "intro": STRING, "signals": {"type": "array", "items": STRING}, "risk": STRING, "cause": STRING,
            "suggestion": STRING, "questions": {"type": "array", "items": STRING}, "closing": STRING,
        },
        "required": ["intro", "signals", "risk", "cause", "suggestion", "questions", "closing"],
        "additionalProperties": False,
    },
    "followup": {"type": "object", "properties": {"text": STRING}, "required": ["text"], "additionalProperties": False},
    "summary": {"type": "object", "properties": {"text": STRING}, "required": ["text"], "additionalProperties": False},
    "extract": {
        "type": "object",
        "properties": {
            "signal": {"type": "string", "enum": ["external_offer", "growth_request", "manager_relationship", "none"]},
            "quote": STRING,
        },
        "required": ["signal", "quote"],
        "additionalProperties": False,
    },
}


class EmptyResponse(ValueError):
    pass


def _call_model(system: str, user: str, a: Assumptions, task: str = "summary") -> str:
    """One call with low effort, minimal thinking and the answer constrained to the task's JSON schema."""
    import anthropic

    client = anthropic.Anthropic(api_key=_api_key(), timeout=a.num("ai.timeout_seconds"), max_retries=1)
    response = client.messages.create(
        model=a.text("ai.model"),
        max_tokens=a.int("ai.max_tokens"),
        system=system,
        messages=[{"role": "user", "content": user}],
        thinking={"type": "between_tools"},
        output_config={"effort": a.text("ai.effort"), "format": {"type": "json_schema", "schema": SCHEMAS[task]}},
    )
    text = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
    if not text.strip():
        raise EmptyResponse(f"resposta vazia (stop_reason={getattr(response, 'stop_reason', '?')})")
    return text


def generate(task: str, payload: dict, fallback: dict, required_keys: list[str], a: Assumptions,
             required_phrase: str | None = None, enabled: bool = True) -> AIResult:
    if not available():
        return AIResult(fallback, "padrão", "AI indisponível: sem chave configurada")
    if not enabled:
        return AIResult(fallback, "padrão", "AI desligada na barra lateral")
    key = hashlib.sha256(
        json.dumps([task, payload, prompts_version(), a.text("ai.model")], ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()
    store = _store()
    if key in store:
        return AIResult(store[key], "ai")
    calls = st.session_state.get("ai_calls", 0)
    if calls >= a.int("ai.max_calls_per_session"):
        return AIResult(fallback, "padrão", "limite de chamadas da sessão")
    st.session_state["ai_calls"] = calls + 1
    try:
        system = _prompt("system") + "\n\n" + _prompt(task)
        raw = _call_model(system, json.dumps(payload, ensure_ascii=False, indent=1), a, task)
        output = _parse(raw)
    except Exception as exc:  # timeout, network, API error, empty or invalid answer
        detail = str(exc).replace("\n", " ")[:140]
        return AIResult(fallback, "padrão", f"falha na chamada: {type(exc).__name__}: {detail}")
    reason = check(output, payload, required_keys, required_phrase)
    if reason:
        return AIResult(fallback, "padrão", reason)
    store[key] = output
    return AIResult(output, "ai")


# Tasks ------------------------------------------------------------------------------------

def write_case(template: dict, facts: dict, a: Assumptions, enabled: bool = True) -> AIResult:
    payload = dict(facts, texto_de_referencia={k: v for k, v in template.items()})
    keys = ["intro", "signals", "risk", "cause", "suggestion", "questions", "closing"]
    result = generate("case", payload, template, keys, a, required_phrase="a decisão é sua", enabled=enabled)
    if result.source == "ai" and (len(result.value["questions"]) != 3 or not result.value["signals"]):
        return AIResult(template, "padrão", "formato inválido")
    return result


def write_followup(template_text: str, facts: dict, a: Assumptions, enabled: bool = True) -> AIResult:
    payload = dict(facts, texto_de_referencia=template_text)
    return generate("followup", payload, {"text": template_text}, ["text"], a, enabled=enabled)


def write_summary(template_text: str, facts: dict, a: Assumptions, enabled: bool = True) -> AIResult:
    payload = dict(facts, texto_de_referencia=template_text)
    return generate("summary", payload, {"text": template_text}, ["text"], a, enabled=enabled)


def read_note(note: str, expected_signal: str, a: Assumptions, enabled: bool = True) -> AIResult:
    """Classifies a career-conversation note. Shown only when it matches what the engine expects."""
    fallback = {"signal": expected_signal, "quote": ""}
    result = generate("extract", {"anotacao": note}, fallback, ["signal", "quote"], a, enabled=enabled)
    if result.source == "ai":
        quote = str(result.value.get("quote", ""))
        if result.value.get("signal") != expected_signal or (quote and quote.strip(" .\"“”") not in note):
            return AIResult(fallback, "padrão", "leitura divergente da anotação")
    return result
