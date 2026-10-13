"""Testes de uma auditoria independente do código, incorporados à suíte.

"INVARIANTE": protege o que já estava certo. "ACHADO": reproduzia um problema do relatório de auditoria e
passou a valer depois da correção (teste de regressão). Três testes foram ajustados à correção escolhida:
previsão ausente fica vazia (e não 0,5), o custo anual tem coluna própria (cost_annual) e a regra de grupo
mínimo vale para times (a legenda foi corrigida). Os testes marcados "slow" rodam com: pytest -m slow
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import ai, simulation  # noqa: E402
from src.assumptions import Assumptions  # noqa: E402
from src.case_text import _times, build_case_message, outcome_message  # noqa: E402
from src.engine import MONITOR, run_engine, signal_evidence  # noqa: E402
from src.format import brl  # noqa: E402
from src.generator import generate_world  # noqa: E402
from src.leadership import after_window, at_t0  # noqa: E402
from src.periods import OUTCOME_WINDOW_MONTHS  # noqa: E402
from src.prediction import scale  # noqa: E402
from src.summaries import leadership_summary  # noqa: E402


def _edited(a: Assumptions, **changes) -> Assumptions:
    table = a.table.copy()
    for key, value in changes.items():
        assert (table["key"] == key).any(), key
        table.loc[table["key"] == key, "value"] = str(value)
    return Assumptions(table, a.signals, a.interventions)


@pytest.fixture(scope="module")
def base():
    a = Assumptions.load()
    w = generate_world(a)
    eng = run_engine(w.public, a)
    ctx = simulation.make_context(w, a)
    sim = simulation.simulated_decisions(ctx, eng, a)
    return a, w, eng, ctx, sim


def _close(ctx, eng, sim, a, persona_decisions):
    dec = pd.concat([sim, simulation.persona_decision_rows(ctx, eng, persona_decisions)], ignore_index=True)
    out = simulation.advance_window(ctx, dec, a)
    return dec, out, simulation.learning(eng, dec, out, a.num("ev.interval_level"))


# --- INVARIANTES: dados ------------------------------------------------------------------------

def test_invariante_hris_integridade_e_datas(base):
    a, w, *_ = base
    hris = w.public["hris"].copy()
    ids = set(hris["employee_id"])
    assert hris["employee_id"].is_unique
    assert hris["manager_id"].dropna().isin(ids).all()
    for col in ("hire_date", "last_promotion_date", "last_pay_change_date", "exit_date"):
        hris[col] = pd.to_datetime(hris[col])
    t0 = a.date("general.reference_date")
    assert (hris["hire_date"] <= t0).all()
    assert (hris["last_promotion_date"] >= hris["hire_date"]).all()
    assert (hris["last_pay_change_date"] >= hris["last_promotion_date"]).all()
    gone = hris[hris["status"] == "desligado"]
    assert (gone["exit_date"] > gone["hire_date"]).all()
    assert not hris.loc[hris["status"] == "ativo", "name"].duplicated().any()


def test_invariante_eventos_batem_com_hris(base):
    _, w, *_ = base
    hris = w.public["hris"].set_index("employee_id")
    ev = w.public["events"].assign(date=lambda d: pd.to_datetime(d["date"]))
    adm = ev[ev["event"] == "admissão"].set_index("employee_id")["date"]
    assert (adm == pd.to_datetime(hris.loc[adm.index, "hire_date"])).all()
    promo = ev[ev["event"] == "promoção"].groupby("employee_id")["date"].max()
    assert (promo == pd.to_datetime(hris.loc[promo.index, "last_promotion_date"])).all()


# --- INVARIANTES: motor e simulação ------------------------------------------------------------

def test_invariante_motor_calibrado_contra_a_verdade_oculta(base):
    """O risco sem ação estimado pela rede bate com o que a verdade oculta implica (±5%)."""
    a, w, eng, ctx, sim = base
    cases = eng.cases.set_index("employee_id")
    true_no_action = sum(simulation._p_window(a, ctx.true_cause[e]) for e in cases.index)
    assert abs(cases["exit_window_no_action"].sum() / true_no_action - 1) < 0.05


def test_invariante_tabela_de_opcoes_fecha_a_conta(base):
    """Para o ajuste salarial, perda que evita − custo = saldo, com os números arredondados da tela."""
    a, w, eng, *_ = base
    rec = eng.options[eng.options["recurring"]]
    cost_r, ev_r = rec["expected_cost"].round(-3), rec["ev"].round(-3)
    shown_avoided = (cost_r + ev_r)
    assert np.allclose(shown_avoided - cost_r, ev_r)
    assert np.allclose(rec["benefit"] - rec["expected_cost"], rec["ev"])


@pytest.mark.parametrize("pid,intervention", [(p, i) for p in ("P1", "P2", "P3")
                                              for i in ("Ajuste salarial", "Carreira e projeto", MONITOR)])
def test_invariante_roteiro_de_todas_as_combinacoes(base, pid, intervention):
    """Cobre as 9 combinações personagem × intervenção (a suíte original cobre 6)."""
    a, w, eng, ctx, sim = base
    dec, out, _ = _close(ctx, eng, sim, a, {pid: dict(intervention=intervention, prediction=0.7)})
    script = a.persona_outcomes.set_index(["persona_id", "intervention"]).loc[(pid, intervention)]
    emp = ctx.personas.set_index("persona_id").loc[pid, "employee_id"]
    row = out.set_index("employee_id").loc[emp]
    assert bool(row["stayed"]) == bool(script["stays"])


def test_invariante_textos_padrao_passam_na_propria_checagem_da_ai(base):
    """Os textos padrão dos três casos não usam termos vetados pela camada de AI."""
    a, w, eng, *_ = base
    cases = eng.cases.set_index("employee_id")
    for _, p in w.public["personas"].iterrows():
        emp = p["employee_id"]
        active = [s for s in eng.signals.columns if eng.signals.loc[emp, s]]
        msg = build_case_message(cases.loc[emp], eng.options[eng.options["employee_id"] == emp],
                                 signal_evidence(w.public, a, emp, active), eng.network_stats, a)
        payload = dict(texto_de_referencia=msg)
        assert ai.check(msg, payload, list(msg), "a decisão é sua") == "", p["name"]


@pytest.mark.slow
@pytest.mark.parametrize("seed", range(1, 11))
def test_invariante_checagens_passam_em_outras_sementes(seed):
    from src.checks import run_checks

    a = _edited(Assumptions.load(), **{"general.seed": seed})
    checks = run_checks(generate_world(a), a)
    failed = checks[~checks["ok"]]
    assert failed.empty, failed[["checagem", "meta", "obtido"]].to_string()


# --- ACHADOS: roteamento e calibração ----------------------------------------------------------

def test_achado_todo_caso_tem_quem_decida(base):
    """Líderes de área sem superior abrem caso, mas o caso não vai para ninguém."""
    _, _, eng, *_ = base
    sem_decisor = eng.cases[eng.cases["decision_maker_id"].isna()]
    assert sem_decisor.empty, sem_decisor[["employee_id", "role", "cause"]].to_string()


def test_achado_calibracao_cobre_todos_os_casos(base):
    """groupby descarta decisores nulos: a soma por gestor não fecha com o total."""
    a, w, eng, ctx, sim = base
    _, _, learn = _close(ctx, eng, sim, a, {})
    assert learn["calibration"]["n"].sum() == learn["summary"].iloc[0]["cases"]


def test_achado_personagem_sem_decisao_nao_vira_previsao_de_50(base):
    """Sem decisão, a previsão entra como 0,5, valor que não existe na escala verbal."""
    a, w, eng, ctx, sim = base
    rows = simulation.persona_decision_rows(ctx, eng, {})
    assert rows["manager_prediction"].isna().all()
    decided = simulation.persona_decision_rows(ctx, eng, {"P1": dict(intervention=MONITOR, prediction=0.3)})
    assert set(decided["manager_prediction"].dropna()) <= {v for _, v in scale(a)}


def test_achado_aprendizado_usa_a_mesma_causa_da_rede(base):
    """A rede é agrupada pela causa atribuída pelo motor; o caso do personagem entra pela crença do gestor."""
    a, w, eng, ctx, sim = base
    decisions = {"P3": dict(intervention="Ajuste salarial", cause="remuneração", prediction=0.7,
                            justification="Acho que um aumento resolve")}
    dec, out, learn = _close(ctx, eng, sim, a, decisions)
    engine_cause = eng.cases.set_index("employee_id")["cause"]
    expected = int((engine_cause.loc[dec["employee_id"]] == "remuneração").sum())
    rates = learn["rates"]
    assert int(rates.loc[rates["cause"] == "remuneração", "n_client"].sum()) == expected


# --- ACHADOS: textos que não seguem as premissas -----------------------------------------------

def test_achado_resumo_da_lideranca_segue_a_fracao_arrependida(base):
    a, w, eng, ctx, sim = base
    edited = _edited(a, **{"exit.regretted_share": 0.3})
    view = at_t0(dict(engine=eng, public=w.public), edited, sim)
    text, _ = leadership_summary(view, OUTCOME_WINDOW_MONTHS)
    assert "metade" not in text


def test_achado_custo_rotulado_por_ano_e_anual(base):
    """A tela mostra o custo com o rótulo '/ano': precisa ser o custo anual da regra do ajuste salarial."""
    from src.interventions import annual_cost

    a, w, eng, *_ = base
    rec = eng.options[eng.options["recurring"]]
    cases = eng.cases.set_index("employee_id").loc[rec["employee_id"]]
    annual = np.round(annual_cost(a, "Ajuste salarial", cases["salary"].values, cases["market_median"].values), -2)
    assert np.allclose(rec["cost_annual"].values, annual)


def test_achado_turnover_antes_e_depois_no_mesmo_periodo(base):
    """Turnover antes e depois medido em períodos de mesmo tamanho (a janela fixa)."""
    a, w, eng, ctx, sim = base
    dec, out, learn = _close(ctx, eng, sim, a, {})
    world = dict(engine=eng, public=w.public)
    view = at_t0(world, a, dec)
    after = after_window(world, a, view, dict(learning=learn, outcomes=out))
    hris = w.public["hris"]
    t0 = a.date("general.reference_date")
    exits = pd.to_datetime(hris["exit_date"])
    last_w = ((t0 - exits).dt.days <= OUTCOME_WINDOW_MONTHS * 30.4375).sum()
    assert after["turnover_before"] == pytest.approx(last_w / (hris["status"] == "ativo").sum())


def test_achado_resumo_nao_cita_a_causa_gestao_retirada(base):
    """O resumo ainda fala de 'sinais ligados à gestão' quando um time tem 100% de casos."""
    a, w, eng, ctx, sim = base
    view = at_t0(dict(engine=eng, public=w.public), a, sim)
    view["teams"] = view["teams"].assign(share=1.0)
    text, _ = leadership_summary(view, OUTCOME_WINDOW_MONTHS)
    assert "gestão" not in text


def test_achado_textos_padrao_seguem_a_regra_de_jargao_do_prompt(base):
    """prompts/system.md proíbe 'rede'; o retorno padrão usa 'rede' duas vezes."""
    a, w, eng, ctx, sim = base
    dec, out, learn = _close(ctx, eng, sim, a, {"P1": dict(intervention="Ajuste salarial", prediction=0.9)})
    closed = learn["closed"].set_index("employee_id")
    cases = eng.cases.set_index("employee_id")
    emp = ctx.personas.set_index("persona_id").loc["P1", "employee_id"]
    text = outcome_message(closed.loc[emp], cases.loc[emp], eng.options[eng.options["employee_id"] == emp], None, a)
    assert " rede" not in text.lower()


# --- ACHADOS: camada de AI ---------------------------------------------------------------------

def test_achado_checagem_de_numeros_pega_numero_por_extenso():
    """'Todo número do texto existe nos fatos': números por extenso escapam da checagem."""
    template = {"text": "Em casos parecidos, 4 em cada 10 pessoas saíram em 12 meses. A decisão é sua."}
    payload = dict(texto_de_referencia=template["text"])
    invented = {"text": "Em casos parecidos, sete em cada dez pessoas saíram em doze meses. A decisão é sua."}
    assert ai.check(invented, payload, ["text"], None) != ""


# --- ACHADOS: evidências e formatação ----------------------------------------------------------

def test_achado_evidencia_especifica_por_sinal(base):
    """Quem tem proposta externa e pedido de crescimento recebe as duas anotações nos dois sinais."""
    a, w, eng, *_ = base
    s = eng.signals
    both = sorted(set(s[s["external_offer"] & s["growth_request"]].index) & set(eng.cases["employee_id"]))
    assert both, "sem caso com os dois sinais de contexto nesta semente"
    ev = {e["signal"]: e["plain"] for e in signal_evidence(w.public, a, both[0], ["external_offer", "growth_request"])}
    assert ev["external_offer"] != ev["growth_request"]


def test_achado_times_respeitam_o_grupo_minimo(base):
    """A regra de privacidade vale para times (a legenda diz "times com menos de N pessoas não aparecem")."""
    a, w, eng, ctx, sim = base
    view = at_t0(dict(engine=eng, public=w.public), a, sim)
    assert (view["teams"]["people"] >= a.int("privacy.min_group_size")).all()
    assert "times com menos de" in (ROOT / "app_pages" / "leadership.py").read_text()


def test_achado_brl_na_virada_de_mil_para_milhao():
    assert brl(999_600) == "R$ 1,0 mi"


@pytest.mark.parametrize("ratio", [0.8, 1.4])
def test_achado_multiplo_de_risco_em_texto(ratio):
    """Hoje não ocorre (mínimo 2,4×), mas o texto erra abaixo da média e entre 1,3× e 1,5×."""
    text = _times(ratio)
    assert "1 vezes" not in text
    if ratio < 1:
        assert "acima" not in text


# --- Páginas com todas as decisões dos personagens ---------------------------------------------

COMBOS = [{p: dict(intervention=i, cause="crescimento", prediction=0.3, justification="teste")}
          for p in ("P1", "P2", "P3") for i in ("Ajuste salarial", "Carreira e projeto", MONITOR)]


@pytest.mark.slow
@pytest.mark.parametrize("page", ["learning.py", "results.py", "leadership.py"])
@pytest.mark.parametrize("combo", range(len(COMBOS)))
def test_invariante_paginas_com_cada_decisao(page, combo):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ROOT / "app_pages" / page), default_timeout=180)
    at.session_state["persona_decisions"] = dict(COMBOS[combo])
    at.session_state["advanced"] = True
    at.run()
    assert not at.exception
