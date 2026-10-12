import pandas as pd
import streamlit as st

from src.app_data import assumptions, load_world
from src.case_text import outcome_message, quadrant
from src.format import num, pct
from src.state import dates, month_label, results
from src import ai
from src.state import ai_badge, ai_on
from src.ui import md, message_header, synthetic_data_banner

synthetic_data_banner()
st.title("2. Retorno e aprendizado")

world = load_world()
a = assumptions()
engine = world["engine"]
W = a.int("outcome.window_months")
t0, t1 = dates(a)
st.caption(
    f"{W} meses depois das decisões: o que aconteceu, como as previsões se compararam com o resultado e o que o "
    "sistema aprendeu. É a prova de que o sistema melhora com o uso."
)

res = results(world, a)
if res is None:
    st.info(
        f"Os casos ainda estão abertos ({month_label(t0)}). Registre as decisões no Fluxo 1, se quiser, e use "
        f"**Avançar {W} meses** na barra lateral para ver o resultado."
    )
    st.stop()

decisions, outcomes, learn = res["decisions"], res["outcomes"], res["learning"]
closed = learn["closed"].set_index("employee_id")
cases = engine.cases.set_index("employee_id")
personas = world["public"]["personas"].set_index("persona_id")
hris = world["public"]["hris"].set_index("employee_id")
calib = learn["calibration"].set_index("decision_maker_id")
s = learn["summary"].iloc[0]

# 1. Follow-up to each decision maker ---------------------------------------------
st.subheader("Retorno para quem decidiu")
st.caption(f"Mensagens enviadas em {month_label(t1)} no Slack (simulado), no mesmo tom de orientação.")
cols = st.columns(3)
for col, (pid, p) in zip(cols, personas.iterrows()):
    emp = p["employee_id"]
    case = cases.loc[emp].copy()
    case["name"] = hris.loc[emp, "name"]
    c = closed.loc[emp]
    opts = engine.options[engine.options["employee_id"] == emp]
    with col, st.container(border=True):
        st.markdown(f"**{case['name']}**  \nRetorno para {case['decision_maker_name']}")
        message_header("Comp · Retenção", month_label(t1))
        template = outcome_message(c, case, opts, calib.loc[case["decision_maker_id"]] if case["decision_maker_id"] in calib.index else None, a)
        with st.spinner("Escrevendo o retorno…"):
            written = ai.write_followup(template, dict(pessoa=case["name"], quem_decide=case["decision_maker_name"]),
                                        a, enabled=ai_on())
        md(written.value["text"])
        ai_badge(written)

# 2. Decision x outcome ------------------------------------------------------------
st.subheader("Decisão e resultado são coisas diferentes")
st.caption("Decisões são avaliadas pela qualidade da informação e do raciocínio no momento em que foram tomadas, "
           "e não só pelo resultado, que também depende de fatores externos.")
placed = {}
for pid, p in personas.iterrows():
    c = closed.loc[p["employee_id"]]
    placed.setdefault((bool(c["followed"]), bool(c["stayed"])), []).append(hris.loc[p["employee_id"], "name"])
header = st.columns([1, 2, 2])
header[1].markdown("**A pessoa ficou**")
header[2].markdown("**A pessoa saiu**")
for followed, row_label in ((True, "Seguiu a sugestão"), (False, "Divergiu da sugestão")):
    row = st.columns([1, 2, 2])
    row[0].markdown(f"**{row_label}**")
    for k, stayed in enumerate((True, False), start=1):
        who = ", ".join(placed.get((followed, stayed), [])) or "—"
        row[k].markdown(
            f'<div class="quad"><div class="title">{quadrant(followed, stayed)}</div><div class="who">{who}</div></div>',
            unsafe_allow_html=True,
        )

# 3. Calibration -----------------------------------------------------------------
st.subheader("Previsões contra o que aconteceu")
lo_m, hi_m = s["exits_range_manager"]
lo_s, hi_s = s["exits_range_system"]
c1, c2, c3 = st.columns(3)
c1.metric("Previsão dos gestores (saídas)", f"{s['exits_expected_manager']:.0f}", help=f"Faixa provável: {lo_m} a {hi_m}")
c2.metric("Previsão do sistema (saídas)", f"{s['exits_expected_system']:.0f}", help=f"Faixa provável: {lo_s} a {hi_s}")
c3.metric("Saídas que ocorreram", int(s["exits_realized"]))
md(
    f"Nos {int(s['cases'])} casos abertos em {month_label(t0)}, os gestores esperavam {s['exits_expected_manager']:.0f} saídas "
    f"(faixa provável de {lo_m} a {hi_m}), o sistema esperava {s['exits_expected_system']:.0f} ({lo_s} a {hi_s}) e ocorreram "
    f"**{int(s['exits_realized'])}**. Os gestores tendem a subestimar o risco do próprio time; registrar a previsão antes de "
    "agir é o que permite medir isso e, com o tempo, ponderar recomendações pela calibração de quem decide."
)
st.caption("Faixa provável: onde o número de saídas cai em 80% das vezes se as probabilidades previstas estiverem certas.")

deciders = set(personas["decision_maker_id"])
view = learn["calibration"][learn["calibration"]["decision_maker_id"].isin(deciders)]
st.dataframe(pd.DataFrame({
    "Quem decidiu": view["decision_maker_name"],
    "Casos": view["n"],
    "Saídas esperadas (gestor)": [num(x) for x in view["exits_expected_manager"]],
    "Saídas esperadas (sistema)": [num(x) for x in view["exits_expected_system"]],
    "Saídas que ocorreram": [str(int(round(x))) for x in view["exits_realized"]],
}), hide_index=True, width="stretch")
st.caption("Com poucos casos por pessoa, a calibração individual ainda é ruidosa; ela ganha precisão a cada ciclo.")

# 4. What the system learned ---------------------------------------------------------
st.subheader("O que o sistema aprendeu")
rates = learn["rates"]
focus = rates[rates["cause"].isin(cases.loc[personas["employee_id"], "cause"])]
st.dataframe(pd.DataFrame({
    "Causa provável": focus["cause"],
    "Intervenção": focus["intervention"],
    "Rede antes": [f"{pct(x)} (n={format(int(n), ',').replace(',', '.')})" for x, n in zip(focus["network_before"], focus["n"])],
    "Casos deste cliente": [f"{pct(x, 0)} (n={int(n)})" if n else "—" for x, n in zip(focus["client_rate"], focus["n_client"])],
    "Rede depois": [f"{pct(x)} (n={format(int(n), ',').replace(',', '.')})" for x, n in zip(focus["network_after"], focus["n_after"])],
}), hide_index=True, width="stretch")
md(
    f"Taxa de permanência em {W} meses. Com dezenas de milhares de casos, um cliente quase não move a taxa da rede: "
    "**o ativo é a rede**, que nenhum cliente teria sozinho. O que se move rápido é o aprendizado local: as taxas deste "
    "cliente e a calibração de cada gestor."
)
