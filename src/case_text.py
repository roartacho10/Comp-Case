"""Message templates for the manager case (Flow 1).

Deterministic text built only from the engine's numbers. Tone: guide, never command. The data
explain what they suggest and what the network learned; the decision stays with the manager.
In Phase 5 these templates become the fallback of the AI layer.
"""

from __future__ import annotations

import pandas as pd

from src.assumptions import Assumptions
from src.engine import MONITOR, PEOPLE_TEAM
from src.format import brl, num, pct
from src.prediction import label as prediction_label
from src.prediction import sentence
from src.periods import OUTCOME_WINDOW_MONTHS

CAUSE_PHRASE = {
    "remuneração": "remuneração",
    "crescimento": "crescimento na carreira",
}


def _first(name: str | None) -> str:
    return name.split()[0] if name else ""


def _greeting(case: pd.Series) -> str:
    """First name of the decision maker; the People team is greeted as a team."""
    if case.get("decision_maker_id") == PEOPLE_TEAM[0]:
        return "time de People"
    return _first(case["decision_maker_name"])


def _times(ratio: float) -> str:
    if ratio < 0.9:
        return "abaixo da média da sua empresa"
    if ratio < 1.1:
        return "perto da média da sua empresa"
    if ratio < 1.5:
        return "um pouco acima da média da sua empresa"
    return f"cerca de {int(ratio + 0.5)} vezes a média da sua empresa"


def _in_ten(p: float) -> str:
    return f"{max(1, int(round(p * 10)))} em cada 10 pessoas"


def hours_of(value: float, case: pd.Series, a: Assumptions) -> int | None:
    """A value in hours of the decision maker's time (their annual cost / working hours per year)."""
    hourly = case.get("decision_maker_hourly_cost")
    if hourly is None or pd.isna(hourly) or hourly <= 0 or value <= 0:
        return None
    h = value / hourly
    return int(round(h / 5) * 5) if h >= 20 else max(1, int(round(h)))


def build_case_message(
    case: pd.Series,
    options: pd.DataFrame,
    evidence: list[dict],
    network_stats: pd.DataFrame,
    a: Assumptions,
) -> dict:
    """Plain-language case message. Only numbers that change the decision; the detail stays on the engine page."""
    window = OUTCOME_WINDOW_MONTHS
    person, decider = _first(case["name"]), _greeting(case)
    opts = options.set_index("intervention")
    rec = case["recommended"]
    raise_name = next((i for i in opts.index if i != MONITOR and opts.loc[i, "recurring"]), None)
    equity = ("Essa conta olha só o custo de perder a pessoa: equidade salarial e a política da empresa podem justificar "
              "o ajuste mesmo assim. ")

    intro = (
        f"Oi, {decider}. Os dados desta semana trouxeram um ponto de atenção sobre **{case['name']}** "
        f"({case['level']}, {case['area']}) que pode valer uma conversa nas próximas semanas."
    )

    signals = [f"**{e['label']}:** {e['plain']}" for e in evidence]

    risk = (
        f"Em casos parecidos na base da Comp, **{_in_ten(case['exit_window_no_action'])} saíram em {window} meses** "
        f"quando nada foi feito, {_times(case['risk_multiple'])}. Não é uma previsão sobre {person}; é o que aconteceu "
        "com pessoas em situação parecida."
    )

    if case["tie"]:
        causes = case["tied_causes"].split(", ")
        cause_text = (
            f"Os sinais se dividem igualmente entre {CAUSE_PHRASE[causes[0]]} e {CAUSE_PHRASE[causes[1]]}, e os dados não "
            f"permitem dizer qual pesa mais. A conversa com {person} é o melhor caminho para definir; a sugestão abaixo "
            f"parte de {CAUSE_PHRASE[case['cause']]}."
        )
    else:
        cause_text = (f"{CAUSE_PHRASE[case['cause']].capitalize()}. Vale confirmar com {person} antes de agir; "
                      "as perguntas abaixo podem ajudar.")

    exit_now = case["exit_window_no_action"]
    replacement = a.num("cost.replacement_share") * case["salary"]
    gap = max(0.0, a.num("cost.replacement_hire_compa") * case["market_median"] - case["salary"])
    years = case["horizon_years"]
    years_txt = "cerca de 1 ano" if years < 1.5 else f"cerca de {int(years + 0.5)} anos"
    loss_txt = f"Se {person} sair, repor custaria cerca de {brl(replacement)} (recrutamento, vaga aberta e tempo até a nova pessoa render)"
    loss_txt += (f", e o substituto seria contratado pelo valor de mercado, {brl(gap)} por ano acima do salário atual."
                 if gap >= 0.05 * case["salary"] else ".")

    if rec == MONITOR:
        why = ""
        if case["cause"] == "remuneração" and raise_name:
            why = (f"Levar {person} para perto do mercado custaria cerca de {brl(opts.loc[raise_name, 'cost_annual'])} por "
                   f"ano, mais do que a perda que o ajuste evita no tempo em que {person} ainda deve ficar ({years_txt}). "
                   f"{loss_txt} {equity}")
        suggestion = (
            f"Pelas contas do sistema, nenhuma das ações tende a compensar o custo neste caso. {why}A sugestão é acompanhar "
            f"de perto e, se {person} for peça-chave, reduzir a dependência (distribuir conhecimento, preparar alguém para a "
            "função). **A decisão é sua: você conhece o contexto que os dados não mostram.**"
        )
    else:
        o = opts.loc[rec]
        exit_with = 1 - o["stay_rate"]
        effect = f"de {pct(exit_now, 0)} para {pct(exit_with, 0)}"
        if o["recurring"]:
            yearly = o["cost_annual"]
            suggestion = (
                f"Considerar um ajuste salarial. Ele custa cerca de {brl(yearly)} por ano. {loss_txt} "
                f"Em casos parecidos, o ajuste reduziu as saídas {effect} em {window} meses. Somando custos e ganhos no "
                f"tempo em que {person} ainda deve ficar ({years_txt}), o ajuste se paga e sobram cerca de {brl(o['ev'])}. "
                "**A decisão é sua: você conhece o contexto que os dados não mostram.**"
            )
        else:
            break_even = o["benefit"]
            h = hours_of(break_even, case, a)
            hours_txt = f", o equivalente a cerca de {h} horas do seu tempo" if h else ""
            action = {
                "Carreira e projeto": ("Conversar sobre um próximo passo de carreira e um novo projeto. Isso tem custo "
                                       f"(o seu tempo e o de outras pessoas para desenhar e acompanhar o escopo, e tirar "
                                       f"{person} do que faz hoje), e você o estima melhor do que nós."),
            }.get(rec, f"{rec}. Isso tem custo, e você o estima melhor do que nós.")
            cross = ""
            if case["cause"] == "remuneração" and raise_name:
                cross = (f"O ajuste salarial custaria cerca de {brl(opts.loc[raise_name, 'cost_annual'])} por ano para levar "
                         f"{person} para perto do mercado, mais do que a perda que ele evita; por isso a sugestão é um "
                         f"caminho de custo menor, ainda que de efeito menor. {equity}")
            suggestion = (
                f"{cross}{action} Em casos parecidos, esse caminho reduziu as saídas {effect} em {window} meses. "
                f"{loss_txt} Por isso, **a iniciativa compensa enquanto o custo total ficar abaixo de cerca de "
                f"{brl(break_even)}**{hours_txt}. A decisão é sua: você conhece o contexto que os dados não mostram."
            )

    questions = a.questions[a.questions["cause"] == case["cause"]].sort_values("order")["question"].tolist()
    closing = (
        f"Quando decidir, registre abaixo o que vai fazer e a sua previsão. Em {window} meses voltamos com o resultado "
        "e com a comparação entre a sua previsão e o que aconteceu."
    )
    return dict(intro=intro, signals=signals, risk=risk, cause=cause_text,
                suggestion=suggestion, questions=questions, closing=closing)


def confirmation_message(decision: dict, case: pd.Series, a: Assumptions) -> str:
    window = OUTCOME_WINDOW_MONTHS
    text = (
        f"Registrado: **{decision['intervention'].lower()}**. Sua previsão para os próximos {window} meses: "
        f"{prediction_label(decision['prediction'], a).lower()}."
    )
    if decision["intervention"] != case["recommended"]:
        text += (" Você seguiu um caminho diferente da sugestão; sua justificativa fica registrada e entra no aprendizado "
                 "junto com o resultado.")
    return text + f" Em {window} meses mostramos o que aconteceu."


QUADRANTS = {
    (True, True): "Seguiu a sugestão e a pessoa ficou: decisão consistente, resultado esperado",
    (True, False): "Seguiu a sugestão e a pessoa saiu: decisão consistente com a evidência, resultado adverso; o risco existia",
    (False, True): "Divergiu e a pessoa ficou: o contexto de quem decidiu pode ter acrescentado algo que os dados não viam",
    (False, False): "Divergiu e a pessoa saiu: a sugestão tinha mais chance; o caso entra no aprendizado",
}


def quadrant(followed: bool, stayed: bool) -> str:
    return QUADRANTS[(bool(followed), bool(stayed))]


def outcome_message(closed: pd.Series, case: pd.Series, options: pd.DataFrame, decider_calib: pd.Series | None,
                    a: Assumptions) -> str:
    """Follow-up sent to the decision maker after the window. Same guiding tone, no blame."""
    window = OUTCOME_WINDOW_MONTHS
    person, decider = _first(case["name"]), _greeting(case)
    opts = options.set_index("intervention")
    chosen, rec = closed["intervention"], case["recommended"]
    stayed = bool(closed["stayed"])

    if stayed:
        result = f"{person} continua no time" + (" e segue performando." if closed["performing"] else ".")
        if closed["note"]:
            result += f" {closed['note']}"
    else:
        result = f"{person} saiu no mês {int(closed['exit_month'])}. {closed['note']}"
    text = f"Oi, {decider}. {window} meses depois: {result} "

    if str(closed.get("origin", "")).endswith("(sem decisão)"):
        text += (f"Não houve decisão registrada; o caso ficou só em acompanhamento. Para casos parecidos, a chance "
                 f"estimada de ficar era de {pct(opts.loc[MONITOR, 'stay_rate'], 0)} sem ação e "
                 f"{pct(opts.loc[rec, 'stay_rate'], 0)} com {rec.lower()}. ")
    elif chosen == rec:
        text += (f"Você seguiu a sugestão ({chosen.lower()}) e considerava {sentence(closed['manager_prediction'], person, a)}; "
                 f"para casos parecidos, o sistema estimava {pct(opts.loc[chosen, 'stay_rate'], 0)} de chance de ficar. ")
        text += ("O resultado confirma o que a base da Comp indicava. " if stayed else
                 f"A decisão foi consistente com a evidência: mesmo assim, cerca de "
                 f"{pct(1 - opts.loc[chosen, 'stay_rate'], 0)} das pessoas em casos parecidos saem. O risco existia, "
                 "e um resultado ruim não torna a decisão ruim. ")
    else:
        why = f" (justificativa: \u201c{closed['justification']}\u201d)" if closed["justification"] else ""
        text += (f"Você escolheu {chosen.lower()} em vez da sugestão, {rec.lower()}{why}, e considerava "
                 f"{sentence(closed['manager_prediction'], person, a)}. Para casos parecidos, a chance de ficar "
                 f"estimada era de {pct(opts.loc[chosen, 'stay_rate'], 0)} com {chosen.lower()} e "
                 f"{pct(opts.loc[rec, 'stay_rate'], 0)} com {rec.lower()}. ")
        text += ("Deu certo: o seu contexto pode ter acrescentado algo que os dados não viam. " if stayed else
                 "A sugestão tinha mais chance, mas nenhuma opção garantia o resultado. ")
    text += "O caso entra no aprendizado da base da Comp."
    if decider_calib is not None and decider_calib["n_forecast"] > 1:
        # Same basis on both sides: only the cases in which this decision maker registered a forecast.
        k = int(decider_calib["n_forecast"])
        expected = decider_calib["exits_expected_manager"]
        realized = int(decider_calib["exits_realized_forecast"])
        basis = (f"Somando os seus {k} casos deste ciclo" if k == int(decider_calib["n"])
                 else f"Nos {k} casos deste ciclo em que você registrou previsão")
        text += (f" {basis}, as suas previsões indicavam {num(expected)} {'saída' if expected < 2 else 'saídas'}; "
                 f"ocorreram {realized}.")
    return text
