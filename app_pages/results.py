import pandas as pd
import streamlit as st

from src.app_data import assumptions, load_world
from src.format import brl, cost_note, num, pct
from src.leadership import after_window, at_t0
from src.state import dates, month_label, results
from src import ai
from src.state import ai_badge, ai_on
from src.summaries import results_summary
from src.ui import md, synthetic_data_banner
from src.periods import OUTCOME_WINDOW_MONTHS

synthetic_data_banner()
world = load_world()
a = assumptions()
W = OUTCOME_WINDOW_MONTHS
t0, t1 = dates(a)
st.title(f"4. Resultado em {W} meses")
st.caption(f"O que as decisões tomadas em {month_label(t0)} produziram até {month_label(t1)}, para a empresa.")

res = results(world, a)
if res is None:
    st.info(f"As decisões ainda estão em andamento ({month_label(t0)}). Use **Avançar {W} meses** na barra lateral.")
    st.stop()

view = at_t0(world, a, res["decisions"])
after = after_window(world, a, view, res)

summary_text, summary_facts = results_summary(view, after, W)
with st.container(border=True):
    st.markdown("**Em resumo**")
    with st.spinner("Escrevendo o resumo…"):
        written = ai.write_summary(summary_text, summary_facts, a, enabled=ai_on())
    md(written.value["text"])
    ai_badge(written)

# Headline ----------------------------------------------------------------------------
st.subheader("Saídas evitadas e valor preservado")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Esperadas sem ação", num(view["exits_no_action"], 0), help="Saídas esperadas nos casos abertos se nada fosse feito, segundo a base da Comp")
c2.metric("Saídas que ocorreram", after["exits_realized"])
c3.metric("Saídas evitadas", num(after["avoided"], 0))
c4.metric("Valor preservado", brl(after["value"]), help="Reposição evitada menos o custo das intervenções")
md(
    f"Nos {view['cases']} casos abertos em {month_label(t0)}, a base da Comp indicava cerca de "
    f"**{num(view['exits_no_action'], 0)} saídas** se nada fosse feito. Ocorreram **{after['exits_realized']}**. "
    f"As cerca de **{num(after['avoided'], 0)} saídas evitadas** representam {brl(after['saved'])} em reposição que não "
    f"precisou acontecer. Descontado o custo pago nas intervenções ({brl(after['cost_paid'])}), sobram "
    f"**{brl(after['value'])}**: cada R$ 1 investido nas intervenções evitou cerca de "
    f"R$ {num(after['return_per_real'])} em reposição."
)
st.caption(cost_note(a))

# Following the suggestion ---------------------------------------------------------------
st.subheader("Seguir a sugestão fez diferença")
f1, f2 = st.columns(2)
f1.metric("Ficaram, quando a sugestão foi seguida", pct(after["stay_followed"], 0), help=f"{after['n_followed']} casos")
f2.metric("Ficaram, quando a decisão divergiu", pct(after["stay_diverged"], 0), help=f"{after['n_diverged']} casos")
st.caption("Comparação descritiva: gestores que seguem e que divergem podem enfrentar casos diferentes; "
           "por isso a decisão continua sendo deles, e cada divergência entra no aprendizado.")

# By cause --------------------------------------------------------------------------------
st.subheader("Por motivo")
bc = after["by_cause"]
st.dataframe(pd.DataFrame({
    "Motivo mais provável": bc["cause"],
    "Casos": bc["cases"].astype(str),
    "Saídas esperadas sem ação": [num(x, 0) for x in bc["expected"]],
    "Saídas que ocorreram": bc["realized"].astype(str),
    "Saídas evitadas": [num(x, 0) for x in bc["avoided"]],
}), hide_index=True, width="stretch")

# Company-wide ---------------------------------------------------------------------------
st.subheader("Na empresa inteira")
e1, e2 = st.columns(2)
e1.metric(f"Turnover voluntário em {W} meses", pct(after["turnover_after"]),
          delta=f"{(after['turnover_after'] - after['turnover_before']) * 100:+.1f}".replace(".", ",") + " p.p.",
          delta_color="inverse", help=f"Nos {W} meses anteriores: {pct(after['turnover_before'])}")
e2.metric("Saídas voluntárias arrependidas", after["company_regretted"],
          delta=after["company_regretted"] - after["regretted_before"], delta_color="inverse",
          help=f"Nos {W} meses anteriores: {after['regretted_before']}")

st.caption(
    "Estimativa: as saídas evitadas comparam o resultado com o que a base da Comp indica para casos parecidos sem ação, "
    "não com um grupo de controle. A prova causal vem da comparação, ao longo do tempo, entre áreas que adotaram e que "
    "ainda não adotaram o sistema."
)
