import streamlit as st

from src.ui import synthetic_data_banner, under_construction

synthetic_data_banner()
st.title("Retorno e aprendizado")
under_construction(
    "Fase 4",
    "Doze meses depois: previsto vs realizado, atualização da taxa de sucesso das "
    "intervenções e calibração das previsões de cada gestor.",
)
