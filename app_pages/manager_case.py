import html

import streamlit as st

from src.app_data import assumptions, load_world
from src.case_text import build_case_message, confirmation_message, hours_of
from src.engine import MONITOR, signal_evidence
from src.format import brl, pct
from src.prediction import label as prediction_label
from src.prediction import scale as prediction_scale
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
    first = case["name"].split()[0]
    years = case["horizon_years"]
    years_txt = "cerca de 1 ano" if years < 1.5 else f"cerca de {int(years + 0.5)} anos"
    exit_now = case["exit_window_no_action"]
    rows = [f"| | Opção | Fica em {W} meses | Custo | Perda que evita | Saldo |", "|:-:|---|---|---|---|---|"]
    notes = []
    for _, o in opts.iterrows():
        name, rec = o["intervention"], o["recurring"]
        star = "★" if name == case["recommended"] else ""
        if name == MONITOR:
            cost_txt, avoided, balance = "—", "—", "referência"
        elif rec:
            # Rounded so that the row adds up as shown: perda que evita − custo = saldo.
            cost_r, ev_r = round(o["expected_cost"], -3), round(o["ev"], -3)
            cost_txt = f"{brl(cost_r)} ({brl(o['cost_annual'])}/ano)"
            avoided, balance = brl(cost_r + ev_r), brl(ev_r)
        else:
            cost_txt = "você estima"
            avoided = brl(o["benefit"]) if o["benefit"] > 0 else "—"
            balance = f"positivo se custar menos de {brl(o['benefit'])}" if o["benefit"] > 0 else "não compensa"
            if o["benefit"] > 0:
                h = hours_of(o["benefit"], case, a)
                notes.append(
                    f"**{name}:** reduz a chance de saída de {pct(exit_now, 0)} para {pct(1 - o['stay_rate'], 0)} e evita cerca "
                    f"de {brl(o['benefit'])} em perda esperada. Esse é o máximo que vale investir: se o seu tempo, a mentoria e "
                    f"tirar {first} do que faz hoje custarem menos que isso, compensa."
                    + (f" {brl(o['benefit'])} equivalem a cerca de {h} horas do seu tempo." if h else "")
                )
        rows.append(f"| {star} | {name} | {pct(o['stay_rate'], 0)} | {cost_txt} | {avoided} | {balance} |")
    md("\n".join(rows))
    md(
        f"**Como ler:** saldo = perda que evita − custo, no tempo em que {first} ainda deve ficar ({years_txt}). A perda que "
        f"evita vem da redução na chance de saída, aplicada ao custo de perder {first}: reposição e substituto contratado "
        "a valor de mercado."
    )
    for note in notes:
        md(note)
    st.caption(f"★ opção sugerida. O resultado é medido em {W} meses.")

    md(msg["closing"])
    ai_badge(written)
    st.caption(f"{case['name'].split()[0]} não vê esta mensagem nem nenhum número.")

    # Decision ------------------------------------------------------------------
    registered = st.session_state["persona_decisions"].get(pid)
    if registered:
        st.divider()
        message_header(decider, "hoje, 16:40", app=False)
        reply = (f"Vou seguir com **{registered['intervention'].lower()}**. Minha previsão: "
                 f"{prediction_label(registered['prediction'], a).lower()}.")
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
            levels = dict(prediction_scale(a))
            prediction = st.radio(f"Sua previsão: {case['name'].split()[0]} continua no time daqui a {W} meses?",
                                  list(levels), index=None)
            justification = st.text_area("Por que este caminho? (obrigatório se for diferente da sugestão)")
            if st.form_submit_button("Registrar decisão", type="primary"):
                if prediction is None:
                    st.error("Registre a sua previsão. Ela é comparada com o resultado depois, e é assim que o "
                             "sistema aprende a calibrar as previsões de cada gestor.")
                elif chosen != case["recommended"] and not justification.strip():
                    st.error("Você escolheu um caminho diferente da sugestão: conte em uma frase o porquê. "
                             "Isso entra no aprendizado junto com o resultado.")
                else:
                    st.session_state["persona_decisions"][pid] = dict(
                        intervention=chosen, cause=belief, prediction=levels[prediction],
                        justification=justification.strip(),
                    )
                    st.rerun()
