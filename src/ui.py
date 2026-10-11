"""Shared UI elements used by every page."""

import streamlit as st

SYNTHETIC_DATA_NOTICE = (
    "**Dados sintéticos e ilustrativos.** Gerados por regras explícitas de causa e efeito; "
    "não representam pessoas, empresas ou resultados reais."
)


def synthetic_data_banner() -> None:
    """Render the notice that must appear at the top of every page."""
    st.info(SYNTHETIC_DATA_NOTICE, icon="ℹ️")


def under_construction(phase: str, description: str) -> None:
    """Placeholder for flows that will be built in later phases."""
    st.caption(f"Em construção — {phase}")
    st.write(description)
