import streamlit as st

from src.ui import synthetic_data_banner, under_construction

synthetic_data_banner()
st.title("Caso do gestor")
under_construction(
    "Fase 3",
    "O gestor recebe um caso no Slack com sinais, causa provável, perguntas a verificar, "
    "intervenções com custo e chance de sucesso e casos comparáveis da rede. "
    "Escolhe uma intervenção e registra sua previsão.",
)
