import streamlit as st

from src.ui import synthetic_data_banner

synthetic_data_banner()
st.title("Retenção com aprendizado")
st.write(
    "Protótipo de um sistema que identifica onde a empresa corre maior risco de perder "
    "valor por turnover voluntário evitável, sugere a intervenção com maior retorno "
    "esperado e aprende com o resultado das decisões."
)
st.subheader("Ciclo demonstrado")
st.write("Sinal → caso → intervenção → resultado → aprendizado")
st.subheader("Status da construção")
st.markdown(
    """
| Fase | Conteúdo | Status |
|---|---|---|
| 0 | Fundação: repositório, estrutura e publicação | Em validação |
| 1 | Mundo e dados sintéticos | A fazer |
| 2 | Personagens e motor de regras | A fazer |
| 3 | Fluxo 1: caso do gestor | A fazer |
| 4 | Fluxos 2 e 3: aprendizado e liderança | A fazer |
| 5 | Camada de AI | A fazer |
| 6 | Testes, README e publicação final | A fazer |
"""
)
