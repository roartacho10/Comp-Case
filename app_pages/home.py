import streamlit as st

from src.app_data import assumptions, load_world
from src.state import dates, month_label
from src.periods import OUTCOME_WINDOW_MONTHS

world = load_world()
a = assumptions()
t0, _ = dates(a)
W = OUTCOME_WINDOW_MONTHS
hris = world["public"]["hris"]
people = f"{int((hris['status'] == 'ativo').sum()):,}".replace(",", ".")
cases = len(world["engine"].cases)

st.title("Comp · Retenção")
st.caption(f"Empresa B2B SaaS · {people} pessoas · {month_label(t0)}")
st.markdown(
    f"Hoje, **{cases} pessoas** têm sinais de que podem sair por um motivo que a empresa consegue tratar. Cada caso chega "
    "ao gestor no Slack, no momento em que aparece, com o contexto e as opções lado a lado. O gestor decide e registra o "
    f"que espera que aconteça; a liderança acompanha o risco e o que está sendo feito; e, {W} meses depois, todos "
    "recebem o resultado."
)
st.markdown(
    "Esta demonstração segue o roteiro da barra lateral: os casos de três pessoas, do ponto de vista de quem decide, "
    f"o painel da liderança, o salto de {W} meses e o retorno."
)
first = world["public"]["personas"].set_index("persona_id").loc["P1", "name"].split()[0]
if st.button(f"Começar: caso {'da' if first[-1] == 'a' else 'do'} {first}", type="primary"):
    st.session_state["persona"] = "P1"
    st.switch_page("app_pages/manager_case.py")
