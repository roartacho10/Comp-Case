import altair as alt
import pandas as pd
import streamlit as st

from src.app_data import assumptions, load_world
from src.format import brl, num, pct
from src.leadership import after_window, at_t0
from src.state import current_decisions, dates, month_label, results
from src.ui import ACCENT, md, synthetic_data_banner

synthetic_data_banner()
st.title("3. Visão da liderança")

world = load_world()
a = assumptions()
W = a.int("outcome.window_months")
t0, t1 = dates(a)
st.caption(
    "Onde a empresa corre maior risco de perder valor por saídas evitáveis, o que está sendo feito e com que resultado. "
    f"Só dados agregados: nenhum nome, e grupos com menos de {a.int('privacy.min_group_size')} pessoas não aparecem."
)

res = results(world, a)
view = at_t0(world, a, res["decisions"] if res else current_decisions(world))

# Value at risk -----------------------------------------------------------------------
st.subheader(f"Risco em {month_label(t0)}")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Colaboradores", f"{view['employees']:,}".replace(",", "."))
c2.metric("Casos abertos", view["cases"], help="Pessoas com 2 ou mais sinais da mesma causa")
c3.metric(f"Saídas esperadas nos casos, sem ação ({W} meses)", num(view["exits_no_action"], 0))
c4.metric("Perda esperada, sem ação", brl(view["loss"]), help="Saídas esperadas × custo de reposição (75% do custo anual)")
md(
    f"Se nada for feito, os {view['cases']} casos abertos devem gerar cerca de **{num(view['exits_no_action'], 0)} saídas** "
    f"em {W} meses, com perda esperada de **{brl(view['loss'])}** em reposição; cerca de metade em saídas arrependidas "
    f"({brl(view['regretted_loss'])}). Com as decisões tomadas, o sistema estima {num(view['exits_with_decisions'], 0)} saídas "
    f"e perda de {brl(view['loss_with_decisions'])}, para um custo de intervenções de {brl(view['intervention_cost'])}. "
    f"Turnover voluntário dos últimos 12 meses: {pct(view['turnover_12m'])}."
)

# Where the risk is -------------------------------------------------------------------
st.subheader("Onde está o risco")
left, right = st.columns([3, 2], gap="large")
with left:
    st.markdown("**Casos abertos por área e causa provável**")
    ac = view["area_cause"]
    grid = pd.MultiIndex.from_product([sorted(ac["area"].unique()), ["remuneração", "crescimento", "gestor"]],
                                      names=["area", "cause"])
    ac = ac.set_index(["area", "cause"]).reindex(grid, fill_value=0).reset_index()
    base = alt.Chart(ac).encode(
        x=alt.X("cause:N", title=None, sort=["remuneração", "crescimento", "gestor"], axis=alt.Axis(labelAngle=0, orient="top")),
        y=alt.Y("area:N", title=None),
    )
    heat = base.mark_rect(cornerRadius=6, stroke="#FFFFFF", strokeWidth=2).encode(
        color=alt.Color("cases:Q", scale=alt.Scale(range=["#FDEBED", ACCENT]), legend=None),
        tooltip=[alt.Tooltip("area:N", title="Área"), alt.Tooltip("cause:N", title="Causa"),
                 alt.Tooltip("cases:Q", title="Casos")],
    )
    labels = base.mark_text(fontSize=13).encode(
        text="cases:Q",
        color=alt.condition(alt.datum.cases > ac["cases"].max() * 0.55, alt.value("#FFFFFF"), alt.value("#141414")),
    )
    st.altair_chart((heat + labels).properties(height=260), width="stretch")
with right:
    st.markdown("**Times com maior concentração de casos**")
    teams = view["teams"].head(8)
    st.dataframe(pd.DataFrame({
        "Time": teams["team_id"],
        "Área": teams["area"],
        "Pessoas": teams["people"],
        "Casos": teams["cases"],
        "% do time": [pct(x, 0) for x in teams["share"]],
        "Causa predominante": teams["cause"],
    }), hide_index=True, width="stretch")
    st.caption("Times em que a causa predominante é gestão indicam onde a liderança acima pode olhar primeiro.")

# What is being done ------------------------------------------------------------------
st.subheader("O que está sendo feito")
bi = view["by_intervention"]
st.dataframe(pd.DataFrame({
    "Intervenção": bi["intervention"],
    "Casos": bi["cases"],
    f"Custo em {W} meses": [brl(x) for x in bi["cost"]],
    "Seguiram a sugestão": [pct(x, 0) for x in bi["followed"]],
}), hide_index=True, width="stretch")

# After the window --------------------------------------------------------------------
st.subheader(f"{W} meses depois ({month_label(t1)})")
if res is None:
    st.info(f"Use **Avançar {W} meses** na barra lateral para ver o resultado das decisões.")
    st.stop()
after = after_window(world, a, view, res)
d1, d2, d3, d4 = st.columns(4)
d1.metric("Saídas esperadas sem ação", num(view["exits_no_action"], 0))
d2.metric("Saídas que ocorreram", after["exits_realized"])
d3.metric("Saídas evitadas (estimativa)", num(after["avoided"], 0))
d4.metric("Valor preservado (estimativa)", brl(after["value"]),
          help="Saídas evitadas × custo médio de reposição − custo das intervenções")
md(
    f"Nos casos abertos, o sistema esperava {num(view['exits_no_action'], 0)} saídas se nada fosse feito; ocorreram "
    f"**{after['exits_realized']}**. A diferença, cerca de **{num(after['avoided'], 0)} saídas evitadas**, vale aproximadamente "
    f"**{brl(after['value'])}** já descontado o custo das intervenções ({brl(view['intervention_cost'])})."
)
st.caption(
    "Estimativa: compara o resultado com o que a rede indica para casos parecidos sem ação, não com um grupo de controle. "
    "A prova causal vem da comparação entre áreas que adotaram e que ainda não adotaram o sistema, ao longo do tempo. "
    f"Na empresa inteira, houve {after['company_exits']} saídas voluntárias no período."
)
