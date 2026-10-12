"""Short deterministic summaries for the leadership and results pages (fallback of the AI layer)."""

from __future__ import annotations

from src.format import brl, num, pct, share_words


def leadership_summary(view: dict, window: int) -> tuple[str, dict]:
    ac = view["area_cause"].sort_values("cases", ascending=False).iloc[0]
    facts = {
        "casos_abertos": view["cases"],
        "saidas_esperadas_sem_acao": num(view["exits_no_action"], 0),
        "perda_esperada_sem_acao": brl(view["loss"]),
        "perda_em_saidas_arrependidas": brl(view["regretted_loss"]),
        "saidas_esperadas_com_decisoes": num(view["exits_with_decisions"], 0),
        "custo_das_intervencoes": brl(view["intervention_cost"]),
        "maior_concentracao": f"{ac['area']}, motivo {ac['cause']} ({int(ac['cases'])} casos)",
        "parcela_arrependida": share_words(view["regretted_share"]),
        "janela_meses": window,
    }
    text = (
        f"Hoje há {view['cases']} casos abertos. Sem ação, eles devem gerar cerca de {facts['saidas_esperadas_sem_acao']} "
        f"saídas em {window} meses e {facts['perda_esperada_sem_acao']} em reposição, {facts['parcela_arrependida']} disso "
        "em saídas arrependidas. "
        f"A maior concentração está em {facts['maior_concentracao']}"
        + f". Com as decisões tomadas, a estimativa cai para {facts['saidas_esperadas_com_decisoes']} saídas, "
        f"com {facts['custo_das_intervencoes']} em intervenções."
    )
    return text, facts


def results_summary(view: dict, after: dict, window: int) -> tuple[str, dict]:
    facts = {
        "saidas_esperadas_sem_acao": num(view["exits_no_action"], 0),
        "saidas_ocorridas": after["exits_realized"],
        "saidas_evitadas": num(after["avoided"], 0),
        "valor_preservado": brl(after["value"]),
        "reposicao_evitada": brl(after["saved"]),
        "custo_pago_nas_intervencoes": brl(after["cost_paid"]),
        "permanencia_seguindo_sugestao": pct(after["stay_followed"], 0),
        "permanencia_divergindo": pct(after["stay_diverged"], 0),
        "turnover_antes": pct(after["turnover_before"]),
        "turnover_depois": pct(after["turnover_after"]),
        "janela_meses": window,
        "observacao": "saídas evitadas e valor preservado são estimativas contra o que a base indica sem ação",
    }
    text = (
        f"Em {window} meses, os casos abertos tiveram {after['exits_realized']} saídas, contra cerca de "
        f"{facts['saidas_esperadas_sem_acao']} esperadas sem ação: cerca de {facts['saidas_evitadas']} saídas evitadas, "
        f"o que preserva {facts['valor_preservado']} já descontadas as intervenções (estimativa). Quando a sugestão foi "
        f"seguida, {facts['permanencia_seguindo_sugestao']} ficaram, contra {facts['permanencia_divergindo']} quando a "
        f"decisão divergiu. O turnover voluntário da empresa foi de {facts['turnover_antes']} para {facts['turnover_depois']}."
    )
    return text, facts
