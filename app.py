"""Entry point: page configuration and navigation."""

import streamlit as st

st.set_page_config(page_title="Comp | Retenção com aprendizado", page_icon="🔁", layout="wide")

pages = [
    st.Page("app_pages/home.py", title="Início", default=True),
    st.Page("app_pages/manager_case.py", title="1. Caso do gestor"),
    st.Page("app_pages/learning.py", title="2. Retorno e aprendizado"),
    st.Page("app_pages/leadership.py", title="3. Visão da liderança"),
]

st.navigation(pages).run()
