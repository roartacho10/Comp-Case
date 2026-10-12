import html

import pandas as pd
import streamlit as st

from src.app_data import assumptions, load_world
from src.case_text import build_case_message, confirmation_message
from src.engine import MONITOR, signal_evidence
from src.format import brl, pct
from src.signals import CAUSES
from src import ai
from src.state import ai_badge, ai_on
from src.ui import md, message_header, synthetic_data_banner

synthetic_data_banner()
st.title("1. Caso do gestor")
st.caption(
    "O gestor recebe o caso numa conversa de Slack (simulado; sem integração real), com o contexto do que os dados "
    "indicam. A decisão é dele, e a previsão registrada agora é comparada com o resultado depois."
)

world = load_world()
a = assumptions()
engine = world["engine"]
tables = world["public"]
W = a.int("outcome.window_months")
cases = engine.cases.set_index("employee_id")
personas = tables["personas"].set_index("persona_id")
hris = tables["hris"].set_index("employee_id")

st.session_state.setdefault("persona_decisions", {})
st.session_state.setdefault("advanced", False)



# Whose case -------------------------------------------------------------------
options_map = {}
for pid, p in personas.iterrows():
    c = cases.loc[p["employee_id"]]
    options_map[f"{p['name']} · mensagem para {c['decision_maker_name']}, gestor(a) do time"] = pid
label = st.selectbox("Ver o caso de", list(options_map))
pid = options_map[label]
emp = personas.loc[pid, "employee_id"]
case = cases.loc[emp].copy()
case["name"] = hris.loc[emp, "name"]
opts = engine.options[engine.options["employee_id"] == emp]
active = [s for s in engine.signals.columns if engine.signals.loc[emp, s]]
evidence = signal_evidence(tables, a, emp, active)
template = build_case_message(case, opts, evidence, engine.network_stats, a)
notes = tables["context"][tables["context"]["employee_id"] == emp]
facts = dict(
    pessoa=case["name"], primeiro_nome=case["name"].split()[0], quem_decide=case["decision_maker_name"],
    cargo=f"{case['level']}, {case['area']}", anotacoes=notes["text"].tolist(), perguntas_base=template["questions"],
)
with st.spinner("Escrevendo a mensagem…"):
    written = ai.write_case(template, facts, a, enabled=ai_on())
msg = written.value

# The AI also reads the career-conversation note and says which signal it indicates.
expected = ("external_offer" if "external_offer" in active else "growth_request" if "growth_request" in active
            else "none")
note_reading = ai.read_note(notes["text"].iloc[0], expected, a, enabled=ai_on()) if len(notes) else None
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

    st.markdown("**O que chamou atenção**")
    md("\n".join(f"- {s}" for s in msg["signals"]))
    if note_reading is not None and note_reading.source == "ai" and note_reading.value.get("quote"):
        st.caption(f"✦ A anotação da conversa de carreira foi lida por AI, que destacou: "
                   f"\u201c{note_reading.value['quote']}\u201d")
    md(msg["risk"])

    md(f"**O motivo mais provável:** {msg['cause']}")

    st.markdown("**O que os dados sugerem**")
    md(msg["suggestion"])

    st.markdown("**Perguntas que podem ajudar na conversa**")
    st.markdown("\n".join(f"{i}. {q}" for i, q in enumerate(msg["questions"], 1)))

    st.markdown("**As opções lado a lado**")
    table = pd.DataFrame({
        "": opts["intervention"].eq(case["recommended"]).map({True: "★", False: ""}).values,
        "Opção": opts["intervention"].values,
        f"Fica em {W} meses": [pct(r, 0) for r in opts["stay_rate"]],
        "Custo": [("—" if i == MONITOR else f"{brl(c)} por ano" if rec else "você avalia")
                  for i, c, rec in zip(opts["intervention"], opts["cost_window"], opts["recurring"])],
        "Saldo estimado": [("referência" if i == MONITOR else brl(e) if rec
                            else (f"compensa se custar até {brl(e + c)}" if e + c > 0 else "não compensa"))
                           for i, e, c, rec in zip(opts["intervention"], opts["ev"], opts["cost_window"], opts["recurring"])],
    })
    st.dataframe(table, hide_index=True, width="stretch", column_config={
        "": st.column_config.TextColumn(width=30),
        "Opção": st.column_config.TextColumn(width=175),
        f"Fica em {W} meses": st.column_config.TextColumn(width=120),
        "Custo": st.column_config.TextColumn(width=140),
        "Saldo estimado": st.column_config.TextColumn(width=240),
    })
    st.caption(
        "★ opção sugerida. Saldo estimado: o que a empresa tende a economizar evitando a saída (reposição e substituto a valor de mercado), "
        "menos o custo da opção, no tempo em que a pessoa ainda deve ficar. Para ações cujo custo você conhece melhor, "
        f"o sistema mostra até quanto vale gastar. O resultado é medido em {W} meses."
    )

    md(msg["closing"])
    ai_badge(written)
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
            belief = st.selectbox("O motivo em que você acredita, depois da conversa",
                                  tied + [c for c in CAUSES if c not in tied])
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
