"""Leadership panel, in two moments: today (risk and what is being done) and 12 months later (the result)."""

import altair as alt
import pandas as pd
import streamlit as st

from src.app_data import assumptions, load_world
from src.format import brl, num, pct, share_words
from src.leadership import after_window, at_t0
from src.signals import CAUSES
from src.state import ai_on, current_decisions, dates, init, mark_visited, month_label, results
from src import ai
from src.summaries import leadership_summary, results_summary
from src.ui import ACCENT, md, table
from src.periods import OUTCOME_WINDOW_MONTHS

init()
world = load_world()
a = assumptions()
W = OUTCOME_WINDOW_MONTHS
t0, t1 = dates(a)
res = results(world, a)
moment = st.session_state.get("lead_moment", "after" if res is not None else "now")
if res is None:
    moment = "now"
mark_visited(f"lead_{moment}")
view = at_t0(world, a, res["decisions"] if res else current_decisions(world))


def summary_box(text: str, facts: dict) -> None:
    with st.container(border=True):
        st.markdown("**Em resumo**")
        with st.spinner("Escrevendo o resumo…"):
            written = ai.write_summary(text, facts, a, enabled=ai_on())
        md(written.value["text"])


# ===================================================================================== Today
if moment == "now":
    st.title("Painel da liderança")
    st.caption(f"Risco de saídas evitáveis e o que está sendo feito · {month_label(t0)}")
    summary_box(*leadership_summary(view, W))

    st.subheader("Risco hoje")
    c1, c2, c3 = st.columns(3)
    c1.metric("Casos abertos", view["cases"])
    c2.metric(f"Saídas esperadas em {W} meses, sem ação", num(view["exits_no_action"], 0))
    c3.metric("Perda esperada, sem ação", brl(view["loss"]))
    employees = f"{view['employees']:,}".replace(",", ".")
    md(
        f"Na empresa de {employees} pessoas, se nada for feito, os {view['cases']} casos abertos devem gerar cerca de "
        f"**{num(view['exits_no_action'], 0)} saídas** em {W} meses, com perda esperada de **{brl(view['loss'])}** em "
        f"reposição; {share_words(a.num('exit.regretted_share'))} em saídas arrependidas ({brl(view['regretted_loss'])}). "
        f"Com as decisões tomadas, a estimativa cai para {num(view['exits_with_decisions'], 0)} saídas e perda de "
        f"{brl(view['loss_with_decisions'])}, com {brl(view['intervention_cost'])} em intervenções. Turnover voluntário "
        f"dos últimos 12 meses: {pct(view['turnover_12m'])}."
    )

    st.subheader("Onde está o risco")
    st.markdown("**Casos abertos por área e motivo**")
    ac = view["area_cause"]
    grid = pd.MultiIndex.from_product([sorted(ac["area"].unique()), CAUSES], names=["area", "cause"])
    ac = ac.set_index(["area", "cause"]).reindex(grid, fill_value=0).reset_index()
    base = alt.Chart(ac).encode(
        x=alt.X("cause:N", title=None, sort=CAUSES, axis=alt.Axis(labelAngle=0, orient="top")),
        y=alt.Y("area:N", title=None, axis=alt.Axis(labelLimit=200)),
    )
    heat = base.mark_rect(cornerRadius=6, stroke="#FFFFFF", strokeWidth=2).encode(
        color=alt.Color("cases:Q", scale=alt.Scale(range=["#FDEBED", ACCENT]), legend=None),
        tooltip=[alt.Tooltip("area:N", title="Área"), alt.Tooltip("cause:N", title="Motivo"),
                 alt.Tooltip("cases:Q", title="Casos")],
    )
    labels = base.mark_text(fontSize=13).encode(
        text="cases:Q",
        color=alt.condition(alt.datum.cases > ac["cases"].max() * 0.55, alt.value("#FFFFFF"), alt.value("#141414")),
    )
    st.altair_chart((heat + labels).properties(height=260), width="stretch")
    st.markdown("**Times com maior concentração de casos**")
    teams = view["teams"].head(8)
    table({
        "Time": teams["team_id"], "Área": teams["area"], "Pessoas": teams["people"], "Casos": teams["cases"],
        "% do time": [pct(x, 0) for x in teams["share"]], "Motivo predominante": teams["cause"],
    })

    st.subheader("O que está sendo feito")
    bi = view["by_intervention"]
    table({
        "Intervenção": bi["intervention"], "Casos": bi["cases"],
        f"Custo em {W} meses": [brl(x) for x in bi["cost"]],
        "Seguiram a sugestão": [pct(x, 0) if x == x else None for x in bi["followed"]],
    })

# ===================================================================================== 12 months later
else:
    after = after_window(world, a, view, res)
    s = res["learning"]["summary"].iloc[0]
    st.title("Painel da liderança")
    st.caption(f"Resultado das decisões de {month_label(t0)} · {month_label(t1)}")
    summary_box(*results_summary(view, after, W))

    st.subheader("Saídas evitadas e valor preservado")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Esperadas sem ação", num(view["exits_no_action"], 0))
    c2.metric("Saídas que ocorreram", after["exits_realized"])
    c3.metric("Saídas evitadas", num(after["avoided"], 0))
    c4.metric("Valor preservado", brl(after["value"]))
    md(
        f"Nos {view['cases']} casos abertos em {month_label(t0)}, eram esperadas cerca de "
        f"**{num(view['exits_no_action'], 0)} saídas** sem ação. Ocorreram **{after['exits_realized']}**. As cerca de "
        f"**{num(after['avoided'], 0)} saídas evitadas** representam {brl(after['saved'])} em reposição. Descontado o "
        f"custo das intervenções ({brl(after['cost_paid'])}), sobram **{brl(after['value'])}**: cada R$ 1 investido "
        f"evitou cerca de R$ {num(after['return_per_real'])} em reposição."
    )

    st.subheader("Seguir a sugestão fez diferença")
    f1, f2 = st.columns(2)
    f1.metric("Ficaram, quando a sugestão foi seguida", pct(after["stay_followed"], 0))
    f2.metric("Ficaram, quando a decisão divergiu", pct(after["stay_diverged"], 0))
    md(
        f"**Previsões dos gestores × resultado:** somando as previsões registradas nos {int(s['cases'])} casos, os "
        f"gestores esperavam cerca de {num(s['exits_expected_manager'], 0)} saídas; o sistema, "
        f"{num(s['exits_expected_system'], 0)}; ocorreram {int(s['exits_realized'])}."
    )

    st.subheader("Por motivo")
    bc = after["by_cause"]
    table({
        "Motivo mais provável": bc["cause"], "Casos": bc["cases"],
        "Saídas esperadas sem ação": [num(x, 0) for x in bc["expected"]],
        "Saídas que ocorreram": bc["realized"], "Saídas evitadas": [num(x, 0) for x in bc["avoided"]],
    })

    st.subheader("Na empresa inteira")
    e1, e2 = st.columns(2)
    e1.metric(f"Turnover voluntário em {W} meses", pct(after["turnover_after"]),
              delta=f"{(after['turnover_after'] - after['turnover_before']) * 100:+.1f}".replace(".", ",") + " p.p.",
              delta_color="inverse", help=f"Nos {W} meses anteriores: {pct(after['turnover_before'])}")
    e2.metric("Saídas voluntárias arrependidas", after["company_regretted"],
              delta=after["company_regretted"] - after["regretted_before"], delta_color="inverse",
              help=f"Nos {W} meses anteriores: {after['regretted_before']}")
