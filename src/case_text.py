"""Message templates for the manager case (Flow 1).

Deterministic text built only from the engine's numbers. Tone: guide, never command. The data
explain what they suggest and what the network learned; the decision stays with the manager.
In Phase 5 these templates become the fallback of the AI layer.
"""

from __future__ import annotations

import pandas as pd

from src.assumptions import Assumptions
from src.engine import MONITOR
from src.format import brl, num, pct

CAUSE_PHRASE = {
    "remuneração": "remuneração",
    "crescimento": "crescimento na carreira",
    "gestor": "dinâmica de gestão do time",
}


def _first(name: str | None) -> str:
    return name.split()[0] if name else ""


def _thousands(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _times(ratio: float) -> str:
    if ratio < 1.3:
        return "um pouco acima da média da sua empresa"
    return f"cerca de {int(ratio + 0.5)} vezes a média da sua empresa"


def _in_ten(p: float) -> str:
    return f"{max(1, int(round(p * 10)))} em cada 10 pessoas"


def build_case_message(
    case: pd.Series,
    options: pd.DataFrame,
    evidence: list[dict],
    network_stats: pd.DataFrame,
    a: Assumptions,
    team_manager_name: str | None,
) -> dict:
    """Plain-language case message. Only numbers that change the decision; the detail stays on the engine page."""
    window = a.int("outcome.window_months")
    person, decider = _first(case["name"]), _first(case["decision_maker_name"])
    opts = options.set_index("intervention")
    rec = case["recommended"]

    if case["escalated"]:
        intro = (
            f"Oi, {decider}. Trazemos para você um caso do time {case['team_id']}"
            + (f", liderado por {team_manager_name}" if team_manager_name else "")
            + f". Os sinais sobre {case['name']} ({case['level']}, {case['area']}) apontam para a dinâmica de gestão do time, "
            "e não para uma questão individual. Por isso o caso veio para a liderança acima, e não para o gestor direto."
        )
    else:
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
        suggestion = (
            "Pelas contas do sistema, nenhuma das ações tende a compensar o custo neste caso. A sugestão é acompanhar de "
            f"perto e, se {person} for peça-chave, reduzir a dependência (distribuir conhecimento, preparar alguém para a "
            "função). **A decisão é sua: você conhece o contexto que os dados não mostram.**"
        )
    else:
        o = opts.loc[rec]
        exit_with = 1 - o["stay_rate"]
        effect = f"de {pct(exit_now, 0)} para {pct(exit_with, 0)}"
        if o["recurring"]:
            yearly = a.num(a.interventions.set_index("intervention").loc[rec, "cost_key"]) * case["salary"]
            suggestion = (
                f"Considerar um ajuste salarial. Ele custa cerca de {brl(yearly)} por ano. {loss_txt} "
                f"Em casos parecidos, o ajuste reduziu as saídas {effect} em {window} meses. Somando custos e ganhos no "
                f"tempo em que {person} ainda deve ficar ({years_txt}), o ajuste se paga e sobram cerca de {brl(o['ev'])}. "
                "**A decisão é sua: você conhece o contexto que os dados não mostram.**"
            )
        else:
            break_even = o["ev"] + o["cost_window"]
            action = {
                "Carreira e projeto": ("Conversar sobre um próximo passo de carreira e um novo projeto. Isso tem custo "
                                       f"(o seu tempo e o de outras pessoas para desenhar e acompanhar o escopo, e tirar "
                                       f"{person} do que faz hoje), e você o estima melhor do que nós."),
                "Escalar para a liderança": ("Olhar de perto para o time: uma conversa direta com a equipe e com o "
                                             "gestor sobre prioridades e apoio. Isso tem custo (sobretudo o seu tempo e o "
                                             "do RH), e você o estima melhor do que nós."),
            }.get(rec, f"{rec}. Isso tem custo, e você o estima melhor do que nós.")
            extra = (" Nesses casos, gastar com salário ou com projeto quase não mudou o resultado."
                     if case["escalated"] else "")
            suggestion = (
                f"{action} Em casos parecidos, esse caminho reduziu as saídas {effect} em {window} meses.{extra} "
                f"{loss_txt} Por isso, **a iniciativa compensa enquanto o custo total ficar abaixo de cerca de "
                f"{brl(break_even)}.** A decisão é sua: você conhece o contexto que os dados não mostram."
            )

    questions = a.questions[a.questions["cause"] == case["cause"]].sort_values("order")["question"].tolist()
    closing = (
        f"Quando decidir, registre abaixo o que vai fazer e a sua previsão. Em {window} meses voltamos com o resultado "
        "e com a comparação entre a sua previsão e o que aconteceu."
    )
    return dict(intro=intro, signals=signals, risk=risk, cause=cause_text,
                suggestion=suggestion, questions=questions, closing=closing)


def confirmation_message(decision: dict, case: pd.Series, a: Assumptions) -> str:
    window = a.int("outcome.window_months")
    person = _first(case["name"])
    text = (
        f"Registrado: **{decision['intervention'].lower()}**. Sua previsão: {pct(decision['prediction'], 0)} de chance de "
        f"{person} continuar em {window} meses."
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
    window = a.int("outcome.window_months")
    person, decider = _first(case["name"]), _first(case["decision_maker_name"])
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
        text += (f"Você seguiu a sugestão ({chosen.lower()}) e previu {pct(closed['manager_prediction'], 0)} de chance de "
                 f"{person} ficar; para casos parecidos, o sistema estimava {pct(opts.loc[chosen, 'stay_rate'], 0)}. ")
        text += ("O resultado confirma o que a rede indicava. " if stayed else
                 f"A decisão foi consistente com a evidência: mesmo assim, cerca de "
                 f"{pct(1 - opts.loc[chosen, 'stay_rate'], 0)} das pessoas em casos parecidos saem. O risco existia, "
                 "e um resultado ruim não torna a decisão ruim. ")
    else:
        why = f" (justificativa: \u201c{closed['justification']}\u201d)" if closed["justification"] else ""
        text += (f"Você escolheu {chosen.lower()} em vez da sugestão ({rec.lower()}){why} e previu "
                 f"{pct(closed['manager_prediction'], 0)} de chance de {person} ficar. Para casos parecidos, a chance "
                 f"estimada era de {pct(opts.loc[chosen, 'stay_rate'], 0)} com {chosen.lower()} e "
                 f"{pct(opts.loc[rec, 'stay_rate'], 0)} com {rec.lower()}. ")
        text += ("Deu certo: o seu contexto pode ter acrescentado algo que os dados não viam. " if stayed else
                 "A sugestão tinha mais chance, mas nenhuma opção garantia o resultado. ")
    text += "O caso entra no aprendizado da rede."
    if decider_calib is not None and decider_calib["n"] > 1:
        expected = decider_calib["exits_expected_manager"]
        realized = int(round(decider_calib["exits_realized"]))
        text += (f" Somando os seus {int(decider_calib['n'])} casos deste ciclo, as suas previsões indicavam "
                 f"{num(expected)} {'saída' if expected < 2 else 'saídas'}; ocorreram {realized}.")
    return text
