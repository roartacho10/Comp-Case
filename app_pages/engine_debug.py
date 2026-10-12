import pandas as pd
import streamlit as st

from src import simulation
from src.app_data import assumptions, load_world
from src.engine import MONITOR, comparable_cases, signal_evidence
from src.format import brl, num, pct, pp
from src.ui import synthetic_data_banner

synthetic_data_banner()
st.title("Bastidores do motor")
st.caption(
    "Página provisória: mostra o motor de regras funcionando, sem interface final e sem AI, "
    "para validar a lógica antes de construir os fluxos."
)

world = load_world()
a = assumptions()
engine = world["engine"]
ctx = world["sim_context"]
cases = engine.cases.set_index("employee_id")
options = engine.options
personas = ctx.personas.set_index("persona_id")
tables = world["public"]
W = a.int("outcome.window_months")

st.session_state.setdefault("persona_decisions", {})
st.session_state.setdefault("advanced", False)

# Overview --------------------------------------------------------------------
st.subheader("Visão geral em T0")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Casos abertos", len(cases))
c2.metric("Escalados (causa gestor)", int(cases["escalated"].sum()))
c3.metric("Empates de causa", int(cases["tie"].sum()))
c4.metric(f"Saída voluntária média em {W} meses", pct(engine.company_exit_window))
by = cases.groupby(["cause", "recommended"]).size().unstack(fill_value=0)
by.index.name, by.columns.name = "Causa provável", None
st.caption("Casos por causa provável (linhas) e intervenção recomendada (colunas)")
st.dataframe(by, width="stretch")

# Case ------------------------------------------------------------------------
st.subheader("Caso")
labels = {f"{pid} · {p['name']} ({p['story']})": p["employee_id"] for pid, p in personas.iterrows()}
others = {f"{e} · {r['name']} ({r['cause']})": e for e, r in cases.iterrows() if e not in set(personas["employee_id"])}
choice = st.selectbox("Escolha um personagem ou outro caso", list(labels) + list(others))
emp = {**labels, **others}[choice]
case = cases.loc[emp]
persona_id = next((pid for pid, p in personas.iterrows() if p["employee_id"] == emp), None)

decider = case["decision_maker_name"] or "—"
if case["escalated"]:
    st.warning(
        f"Causa provável ligada à gestão: o caso vai para **{decider}**, liderança acima do gestor do time. "
        "O sistema não recomenda gasto antes de verificar a causa."
    )
else:
    st.info(f"Quem decide: **{decider}** (gestor do time).")

st.markdown(f"**{case['name']}** · {case['level']} · {case['area']} · {case['country']} · time {case['team_id']}")

st.markdown("**Sinais**")
active = [s for s in engine.signals.columns if engine.signals.loc[emp, s]]
ev = pd.DataFrame(signal_evidence(tables, a, emp, active))
st.dataframe(
    ev.rename(columns=dict(description="Sinal", cause="Causa", source="Fonte", evidence="Evidência"))[
        ["Sinal", "Causa", "Fonte", "Evidência"]
    ],
    hide_index=True,
    width="stretch",
)

if case["tie"]:
    st.warning(
        f"**Empate entre causas: {case['tied_causes']}.** As duas têm o mesmo número de sinais. "
        f"Os números abaixo usam {case['cause']} (primeira na ordem fixa: remuneração, crescimento, gestor). "
        "A definição da causa fica com quem decide, depois das perguntas ao colaborador."
    )
st.markdown(
    f"**Causa provável:** {case['cause']} ({case['n_signals']} de 3 sinais).  \n"
    f"**Risco se nada for feito:** {pct(case['exit_window_no_action'])} de chance de sair em {W} meses "
    f"(intervalo de 80%: {pct(case['exit_window_lo'])} a {pct(case['exit_window_hi'])}; {case['exit_window_n']} casos semelhantes na rede), "
    f"{num(case['risk_multiple'])}x a média da empresa.  \n"
    f"**Horizonte do valor esperado:** {num(case['horizon_years'])} anos, o tempo que a pessoa ainda ficaria sem ação."
)

opts = options[options["employee_id"] == emp].copy()
opts["Recomendada"] = opts["intervention"].eq(case["recommended"]).map({True: "★", False: ""})
view = pd.DataFrame({
    "": opts["Recomendada"],
    "Intervenção": opts["intervention"],
    f"Chance de ficar em {W} meses": [f"{pct(r)} ({pct(lo, 0)}–{pct(hi, 0)})" for r, lo, hi in
                                   zip(opts["stay_rate"], opts["stay_lo"], opts["stay_hi"])],
    "Evidência na rede": [f"{pct(r)} ficaram (n={format(int(n), ',').replace(',', '.')})"
                          for r, n in zip(opts["network_stay_rate"], opts["n"])],
    "Redução do risco": [pct(x, 0) for x in opts["reduction"]],
    f"Custo em {W} meses": [brl(x) for x in opts["cost_window"]],
    "Custo no horizonte": [brl(x) for x in opts["cost_horizon"]],
    "Valor esperado no horizonte": [f"{brl(e)} ({brl(lo)} a {brl(hi)})" if i != MONITOR else "referência"
                                    for e, lo, hi, i in zip(opts["ev"], opts["ev_lo"], opts["ev_hi"], opts["intervention"])],
})
st.dataframe(view, hide_index=True, width="stretch")
st.caption(
    "Valor esperado = custo esperado de não agir − custo esperado com a intervenção, mês a mês no horizonte: "
    "custo da intervenção, reposição de quem sai (75% do custo anual) e diferença de mercado paga ao substituto. "
    "A chance de ficar combina o risco deste caso (mesma causa e número de sinais) com o efeito de cada intervenção "
    f"na rede (mesma causa). O resultado é verificado em {W} meses; o restante do horizonte é extrapolação."
)

comps = comparable_cases(tables["network_cases"], a, case["cause"], case["level"], case["recommended"])
if len(comps):
    st.markdown(f"**Casos comparáveis na rede** ({case['recommended']}, {case['cause']}, nível {case['level']})")
    st.dataframe(
        pd.DataFrame({
            "Empresa": comps["company_id"],
            "País": comps["country"],
            "Decisão em": comps["decision_date"],
            f"Ficou em {W} meses": comps["stayed"].map({True: "sim", False: "não"}),
            "Segue performando": comps["performing"].map({True: "sim", False: "não"}),
        }),
        hide_index=True,
        width="stretch",
    )

# Decision (personas only) ----------------------------------------------------------
if persona_id:
    st.markdown("**Decisão**")
    registered = st.session_state["persona_decisions"].get(persona_id)
    if registered:
        st.success(
            f"Registrado: {registered['intervention']} · previsão de ficar em {W} meses: {pct(registered['prediction'], 0)}"
            + (f" · justificativa: {registered['justification']}" if registered["justification"] else "")
        )
    elif st.session_state["advanced"]:
        st.info(f"Os {W} meses já avançaram. Reinicie para decidir de novo.")
    else:
        with st.form(f"decision_{persona_id}"):
            interventions = opts["intervention"].tolist()
            chosen = st.radio("Intervenção", interventions, index=interventions.index(case["recommended"]))
            belief = st.selectbox("Causa em que você acredita", case["tied_causes"].split(", ") +
                                  [c for c in ("remuneração", "crescimento", "gestor") if c not in case["tied_causes"]])
            prediction = st.slider(f"Chance de a pessoa ficar em {W} meses (%)", 0, 100, 80, 5)
            justification = st.text_area("Justificativa (obrigatória se a escolha diverge da recomendação)")
            if st.form_submit_button("Registrar decisão"):
                if chosen != case["recommended"] and not justification.strip():
                    st.error("A escolha diverge da recomendação: registre a justificativa.")
                else:
                    st.session_state["persona_decisions"][persona_id] = dict(
                        intervention=chosen, cause=belief, prediction=prediction / 100, justification=justification.strip()
                    )
                    st.rerun()

# Six months later --------------------------------------------------------------
st.divider()
st.subheader(f"{W} meses depois")
left, right = st.columns(2)
pending = [pid for pid in personas.index if pid not in st.session_state["persona_decisions"]]
if left.button(f"Avançar {W} meses", type="primary", disabled=st.session_state["advanced"]):
    st.session_state["advanced"] = True
    st.rerun()
if right.button("Reiniciar"):
    st.session_state["persona_decisions"] = {}
    st.session_state["advanced"] = False
    st.rerun()
if pending and not st.session_state["advanced"]:
    st.caption(f"Personagens sem decisão ({', '.join(pending)}) serão registrados como 'monitorar' ao avançar.")

if st.session_state["advanced"]:
    decisions = pd.concat(
        [world["simulated_decisions"], simulation.persona_decision_rows(ctx, engine, st.session_state["persona_decisions"])],
        ignore_index=True,
    )
    outcomes = simulation.advance_window(ctx, decisions, a)
    learn = simulation.learning(engine, decisions, outcomes, a.num("ev.interval_level"))
    s = learn["summary"].iloc[0]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Casos fechados", int(s["cases"]))
    m2.metric("Seguiram a recomendação", pct(s["followed"], 0))
    m3.metric(f"Ficaram em {W} meses", pct(s["stayed"], 0))
    m4.metric(f"Custo das intervenções ({W} meses)", brl(s["cost_window"]))
    lo_m, hi_m = s["exits_range_manager"]
    lo_s, hi_s = s["exits_range_system"]
    st.markdown(
        f"**Saídas nos casos abertos: os gestores esperavam {s['exits_expected_manager']:.0f} "
        f"(faixa provável: {lo_m} a {hi_m}), o sistema esperava {s['exits_expected_system']:.0f} "
        f"(faixa provável: {lo_s} a {hi_s}) e ocorreram {int(s['exits_realized'])}.**"
    )
    st.caption(
        f"Faixa provável: onde o número de saídas cai em {pct(a.num('ev.interval_level'), 0)} das vezes se as "
        "probabilidades previstas estiverem certas. Uma rodada isolada oscila em torno do esperado."
    )
    st.caption(
        f"Em chance de ficar: gestores {pct(s['manager_predicted'], 0)}, sistema {pct(s['system_predicted'], 0)}, "
        f"realizado {pct(s['stayed'], 0)}. Como a maioria fica, a diferença aparece melhor no número de saídas. "
        f"Saídas voluntárias na empresa inteira em {W} meses: {int(s['company_exits'])}."
    )

    st.markdown("**Personagens: previsto contra realizado**")
    closed = learn["closed"].set_index("employee_id")
    rows = []
    for pid, p in personas.iterrows():
        r = closed.loc[p["employee_id"]]
        rows.append({
            "Personagem": f"{pid} · {p['name']}",
            "Decisão": r["intervention"] + (" (seguiu)" if r["followed"] else " (divergiu)"),
            "Previsão do gestor": pct(r["manager_prediction"], 0),
            "Previsão do sistema": pct(r["system_prediction"], 0),
            "Resultado": "ficou" if r["stayed"] else f"saiu no mês {int(r['exit_month'])}",
            "O que aconteceu": r["note"],
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

    st.markdown(f"**Aprendizado: taxa de permanência em {W} meses por causa e intervenção**")
    rates = learn["rates"]
    st.dataframe(pd.DataFrame({
        "Causa": rates["cause"],
        "Intervenção": rates["intervention"],
        "Rede antes": [f"{pct(x)} (n={format(int(n), ',').replace(',', '.')})" for x, n in zip(rates["network_before"], rates["n"])],
        "Casos do cliente": [f"{pct(x)} (n={int(n)})" if n else "—" for x, n in zip(rates["client_rate"], rates["n_client"])],
        "Rede depois": [f"{pct(x)} (n={format(int(n), ',').replace(',', '.')})" for x, n in zip(rates["network_after"], rates["n_after"])],
    }), hide_index=True, width="stretch")
    st.caption("Com dezenas de milhares de casos, um cliente quase não move a taxa da rede: o ativo é a rede; "
               "o que se move é o aprendizado do cliente e de cada gestor.")

    st.markdown("**Calibração das previsões por gestor**")
    calib = learn["calibration"]
    deciders = set(personas["decision_maker_id"])
    calib = calib.assign(order=~calib["decision_maker_id"].isin(deciders)).sort_values(["order", "n"], ascending=[True, False])
    st.dataframe(pd.DataFrame({
        "Gestor": calib["decision_maker_name"] + calib["decision_maker_id"].isin(deciders).map({True: " ★", False: ""}),
        "Casos": calib["n"],
        "Previsão do gestor": [pct(x, 0) for x in calib["predicted"]],
        "Previsão do sistema": [pct(x, 0) for x in calib["system"]],
        "Realizado": [pct(x, 0) for x in calib["realized"]],
        "Saídas esperadas pelo gestor": [num(x) for x in calib["exits_expected_manager"]],
        "Saídas esperadas pelo sistema": [num(x) for x in calib["exits_expected_system"]],
        "Saídas que ocorreram": [f"{x:.0f}" for x in calib["exits_realized"]],
        "Viés do gestor": [pp(x) for x in calib["bias_pp"]],
    }), hide_index=True, width="stretch", height=380)
    st.caption("★ decisores dos personagens. Com poucos casos por gestor, a calibração individual ainda é ruidosa.")
