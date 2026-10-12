import html

import pandas as pd
import streamlit as st

from src.app_data import assumptions, load_world
from src.case_text import build_case_message, confirmation_message
from src.engine import MONITOR, comparable_cases, signal_evidence
from src.format import brl, pct
from src.ui import md, message_header, synthetic_data_banner

synthetic_data_banner()
st.title("1. Caso do gestor")
st.caption(
    "O gestor recebe o caso numa conversa de Slack (simulado; sem integração real), com o contexto do que os dados "
    "indicam e do que a rede aprendeu. A decisão é dele, e a previsão registrada agora é comparada com o resultado depois."
)

world = load_world()
a = assumptions()
engine = world["engine"]
tables = world["public"]
W = a.int("outcome.window_months")
cases = engine.cases.set_index("employee_id")
personas = tables["personas"].set_index("persona_id")
hris = tables["hris"].set_index("employee_id")
managers = tables["managers"].set_index("manager_id")
companies = tables["network_companies"].set_index("company_id")

st.session_state.setdefault("persona_decisions", {})
st.session_state.setdefault("advanced", False)



# Whose case -------------------------------------------------------------------
options_map = {}
for pid, p in personas.iterrows():
    c = cases.loc[p["employee_id"]]
    role = "liderança acima do time" if c["escalated"] else "gestão do time"
    options_map[f"{p['name']} · mensagem para {c['decision_maker_name']} ({role})"] = pid
label = st.selectbox("Ver o caso de", list(options_map))
pid = options_map[label]
emp = personas.loc[pid, "employee_id"]
case = cases.loc[emp].copy()
case["name"] = hris.loc[emp, "name"]
opts = engine.options[engine.options["employee_id"] == emp]
active = [s for s in engine.signals.columns if engine.signals.loc[emp, s]]
evidence = signal_evidence(tables, a, emp, active)
team_manager = managers.loc[hris.loc[emp, "manager_id"], "name"] if hris.loc[emp, "manager_id"] in managers.index else None
msg = build_case_message(case, opts, evidence, engine.network_stats, a, team_manager)
decider = case["decision_maker_name"]

left, right = st.columns([1, 4], gap="medium")
with left:
    dms = "".join(
        f'<div class="item{" active" if n == "Comp · Retenção" else ""}">● {html.escape(n)}</div>'
        for n in ["Comp · Retenção", "RH · People", f"Liderança · {case['area']}"]
    )
    st.markdown(
        f'<div class="fake-sidebar"><div class="ws">Empresa (fictícia)</div>'
        f'<div class="sec">Canais</div><div class="item"># geral</div><div class="item"># {html.escape(case["area"].lower())}</div>'
        f'<div class="item"># anúncios</div><div class="sec">Mensagens diretas</div>{dms}'
        f'<div class="sec">Você</div><div class="item">{html.escape(decider)}</div></div>',
        unsafe_allow_html=True,
    )

with right, st.container(border=True):
    message_header("Comp · Retenção", "hoje, 09:12")
    md(msg["intro"])

    st.markdown("**Por que agora**")
    md("\n".join(f"- {s}" for s in msg["signals"]))
    md(msg["risk"])

    st.markdown("**Causa provável**")
    md(msg["cause"])

    st.markdown("**O que a rede aprendeu**")
    md(msg["learned"])

    st.markdown("**Sugestão**")
    md(msg["suggestion"])

    st.markdown("**Perguntas que podem ajudar na conversa**")
    st.markdown("\n".join(f"{i}. {q}" for i, q in enumerate(msg["questions"], 1)))

    st.markdown("**Opções e o que os dados dizem sobre cada uma**")
    table = pd.DataFrame({
        "": opts["intervention"].eq(case["recommended"]).map({True: "★", False: ""}).values,
        "Opção": opts["intervention"].values,
        f"Chance de ficar em {W} meses": [f"{pct(r, 0)} ({pct(lo, 0)} a {pct(hi, 0)})"
                                          for r, lo, hi in zip(opts["stay_rate"], opts["stay_lo"], opts["stay_hi"])],
        "Custo": [("—" if i == MONITOR else f"{brl(c)} em {W} meses" if rec else brl(c))
                  for i, c, rec in zip(opts["intervention"], opts["cost_window"], opts["recurring"])],
        "Retorno esperado": [("referência" if i == MONITOR else f"{brl(e)} ({brl(lo)} a {brl(hi)})")
                             for i, e, lo, hi in zip(opts["intervention"], opts["ev"], opts["ev_lo"], opts["ev_hi"])],
    })
    st.dataframe(table, hide_index=True, width="stretch")
    st.caption(
        "Retorno esperado: quanto a empresa tende a economizar com a opção, descontado o custo, no tempo em que a pessoa "
        f"ainda ficaria (reposição de quem sai e diferença de mercado do substituto). O resultado é verificado em {W} meses; "
        "o restante é estimativa."
    )

    comps = comparable_cases(tables["network_cases"], a, case["cause"], case["level"], case["recommended"])
    with st.expander(f"Casos parecidos na rede ({case['recommended'].lower()}, mesmo nível)"):
        st.dataframe(pd.DataFrame({
            "Empresa": [f"SaaS B2B, {companies.loc[c, 'employees']} pessoas" for c in comps["company_id"]],
            "País": comps["country"].values,
            "Opção": comps["intervention"].values,
            f"Ficou em {W} meses": comps["stayed"].map({True: "sim", False: "não"}).values,
            "Segue performando": comps["performing"].map({True: "sim", False: "não"}).values,
        }), hide_index=True, width="stretch")

    md(msg["closing"])
    st.caption(f"{case['name'].split()[0]} não vê esta mensagem nem nenhum número.")

    # Decision ------------------------------------------------------------------
    registered = st.session_state["persona_decisions"].get(pid)
    if registered:
        st.divider()
        message_header(decider, "hoje, 16:40", app=False)
        reply = f"Vou seguir com **{registered['intervention'].lower()}**. Minha previsão: {pct(registered['prediction'], 0)}."
        if registered["justification"]:
            reply += f" {registered['justification']}"
        md(reply)
        message_header("Comp · Retenção", "hoje, 16:40")
        md(confirmation_message(registered, case, a))
    elif st.session_state["advanced"]:
        st.info(f"Os {W} meses já avançaram sem uma decisão registrada aqui. Reinicie para decidir.")
    else:
        with st.form(f"decision_{pid}"):
            st.markdown("**Sua decisão**")
            names = opts["intervention"].tolist()
            chosen = st.radio("O que você vai fazer", names, index=names.index(case["recommended"]))
            tied = case["tied_causes"].split(", ")
            belief = st.selectbox("Causa em que você acredita, depois da conversa",
                                  tied + [c for c in ("remuneração", "crescimento", "gestor") if c not in tied])
            prediction = st.slider(f"Sua previsão: chance de {case['name'].split()[0]} continuar em {W} meses (%)",
                                   0, 100, 80, 5)
            justification = st.text_area("Por que este caminho? (obrigatório se for diferente da sugestão)")
            if st.form_submit_button("Registrar decisão", type="primary"):
                if chosen != case["recommended"] and not justification.strip():
                    st.error("Você escolheu um caminho diferente da sugestão: conte em uma frase o porquê. "
                             "Isso entra no aprendizado junto com o resultado.")
                else:
                    st.session_state["persona_decisions"][pid] = dict(
                        intervention=chosen, cause=belief, prediction=prediction / 100,
                        justification=justification.strip(),
                    )
                    st.rerun()
