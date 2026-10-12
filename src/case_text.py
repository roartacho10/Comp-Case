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
    "gestor": "a dinâmica de gestão do time",
}


def _first(name: str | None) -> str:
    return name.split()[0] if name else ""


def _thousands(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def build_case_message(
    case: pd.Series,
    options: pd.DataFrame,
    evidence: list[dict],
    network_stats: pd.DataFrame,
    a: Assumptions,
    team_manager_name: str | None,
) -> dict:
    window = a.int("outcome.window_months")
    person, decider = _first(case["name"]), _first(case["decision_maker_name"])
    opts = options.set_index("intervention")
    rec = case["recommended"]

    # Greeting and why the message arrives now.
    if case["escalated"]:
        intro = (
            f"Oi, {decider}. Trazemos para você um caso do time {case['team_id']}"
            + (f", liderado por {team_manager_name}" if team_manager_name else "")
            + f". Os sinais sobre {case['name']} ({case['level']}, {case['area']}) apontam para a dinâmica de gestão do time, "
            "e não para uma questão individual. Por isso o caso veio para a liderança acima, e não para o gestor direto."
        )
    else:
        intro = (
            f"Oi, {decider}. Os dados desta semana trouxeram um ponto de atenção sobre {case['name']} "
            f"({case['level']}, {case['area']}) que pode valer uma conversa nas próximas semanas."
        )

    signals = [f"**{e['description']}.** {e['evidence']}" for e in evidence]

    risk = (
        f"Em casos parecidos na rede da Comp (mesma causa e mesmo número de sinais), "
        f"**{pct(case['exit_window_no_action'], 0)} das pessoas saíram em {window} meses quando nada foi feito**, "
        f"cerca de {num(case['risk_multiple'])}x a média da sua empresa. "
        f"Não é uma previsão sobre {person}; é o que aconteceu com pessoas em situação parecida "
        f"(faixa provável de {pct(case['exit_window_lo'], 0)} a {pct(case['exit_window_hi'], 0)}, "
        f"com base em {_thousands(case['exit_window_n'])} casos)."
    )

    if case["tie"]:
        causes = case["tied_causes"].split(", ")
        cause_text = (
            f"Os sinais se dividem igualmente entre {CAUSE_PHRASE[causes[0]]} e {CAUSE_PHRASE[causes[1]]}. "
            f"Os dados não permitem dizer qual pesa mais; a conversa com {person} é o melhor caminho para definir. "
            f"Os números abaixo partem de {CAUSE_PHRASE[case['cause']]}."
        )
    else:
        cause_text = (
            f"A hipótese mais provável é **{CAUSE_PHRASE[case['cause']]}** ({case['n_signals']} de 3 sinais). "
            f"Vale confirmar com {person} antes de agir; as perguntas abaixo podem ajudar."
        )

    # What the network learned for this cause.
    pooled = network_stats[network_stats["attributed_cause"] == case["cause"]].groupby("intervention")[["n", "stayed"]].sum()
    pooled["rate"] = pooled["stayed"] / pooled["n"]
    total = int(network_stats["n"].sum())
    best_net = pooled["rate"].idxmax()
    others = [i for i in pooled.index if i not in (best_net, MONITOR)]
    learned = (
        f"Em {_thousands(total)} casos já acompanhados na rede, quando a causa provável era {CAUSE_PHRASE[case['cause']]}, "
        f"**{best_net.lower()}** foi a intervenção com mais gente ficando: {pct(pooled.loc[best_net, 'rate'], 0)} "
        f"continuaram depois de {window} meses, contra {pct(pooled.loc[MONITOR, 'rate'], 0)} quando o caso só foi acompanhado. "
        + (
            "As demais opções ficaram perto de quem não recebeu nenhuma ação: "
            + " e ".join(f"{o.lower()} ({pct(pooled.loc[o, 'rate'], 0)})" for o in others) + "."
            if others else ""
        )
    )

    # Suggestion, in a guiding tone.
    if rec == MONITOR:
        suggestion = (
            f"Pelas contas do sistema, nenhuma das intervenções tende a compensar o custo neste caso. "
            f"A sugestão é acompanhar de perto e, se {person} for peça-chave, pensar em reduzir a dependência "
            "(distribuir conhecimento, preparar alguém para a função). A decisão é sua."
        )
    else:
        o = opts.loc[rec]
        cost = (f"custo estimado de {brl(o['cost_window'])} em {window} meses" if o["recurring"]
                else f"custo estimado de {brl(o['cost_window'])}")
        lead = ("Por isso, o caminho que os dados sugerem é" if not case["escalated"]
                else "Nesses casos, gastar com salário ou com projeto quase não muda o resultado. O que tende a funcionar é")
        action = {
            "Ajuste salarial": "considerar um ajuste salarial",
            "Carreira e projeto": "conversar sobre um próximo passo de carreira e um novo projeto",
            "Escalar para a liderança": "você olhar de perto para o time, com uma conversa direta com a equipe",
        }.get(rec, rec.lower())
        suggestion = (
            f"{lead} {action} ({cost}). Com essa opção, a chance estimada de {person} ficar em {window} meses vai a "
            f"{pct(o['stay_rate'], 0)} (de {pct(o['stay_lo'], 0)} a {pct(o['stay_hi'], 0)}), e o retorno esperado é de "
            f"{brl(o['ev'])} no tempo em que {person} ainda ficaria (de {brl(o['ev_lo'])} a {brl(o['ev_hi'])}). "
            f"A decisão é sua: você conhece o contexto que os dados não mostram."
        )

    questions = a.questions[a.questions["cause"] == case["cause"]].sort_values("order")["question"].tolist()
    closing = (
        f"Quando decidir, registre abaixo o que vai fazer e a sua previsão. Em {window} meses voltamos com o resultado "
        "e com a comparação entre a sua previsão e o que aconteceu."
    )
    return dict(intro=intro, signals=signals, risk=risk, cause=cause_text, learned=learned,
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
