"""Follow-up to each decision maker, 12 months after the decision: the Slack message they receive."""

import streamlit as st

from src.app_data import assumptions, load_world
from src.case_text import outcome_message
from src import ai
from src.state import ai_on, dates, mark_visited, month_label, results
from src.ui import md, message_header
from src.periods import OUTCOME_WINDOW_MONTHS

world = load_world()
a = assumptions()
engine = world["engine"]
W = OUTCOME_WINDOW_MONTHS
t0, t1 = dates(a)
st.title("Retorno aos gestores")

res = results(world, a)
if res is None:
    st.info(f"Os retornos chegam {W} meses depois das decisões. Use **Avançar {W} meses** na barra lateral.")
    st.stop()
mark_visited("followup")

learn = res["learning"]
closed = learn["closed"].set_index("employee_id")
cases = engine.cases.set_index("employee_id")
personas = world["public"]["personas"].set_index("persona_id")
hris = world["public"]["hris"].set_index("employee_id")
calib = learn["calibration"].set_index("decision_maker_id")

for pid, p in personas.iterrows():
    emp = p["employee_id"]
    case = cases.loc[emp].copy()
    case["name"] = hris.loc[emp, "name"]
    opts = engine.options[engine.options["employee_id"] == emp]
    with st.container(border=True):
        st.markdown(f"**Para {case['decision_maker_name']}** · caso {'da' if case['name'].split()[0][-1] == 'a' else 'do'} "
                    f"{case['name']}")
        message_header("Comp · Retenção", month_label(t1))
        template = outcome_message(closed.loc[emp], case, opts,
                                   calib.loc[case["decision_maker_id"]] if case["decision_maker_id"] in calib.index else None,
                                   a)
        with st.spinner("Escrevendo o retorno…"):
            written = ai.write_followup(template, dict(pessoa=case["name"], quem_decide=case["decision_maker_name"]),
                                        a, enabled=ai_on())
        md(written.value["text"])
