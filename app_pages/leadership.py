import streamlit as st

from src.ui import synthetic_data_banner, under_construction

synthetic_data_banner()
st.title("Visão da liderança")
under_construction(
    "Fase 4",
    "Risco de saída por área, time e causa, valor esperado da perda, intervenções em "
    "andamento e seus resultados.",
)
