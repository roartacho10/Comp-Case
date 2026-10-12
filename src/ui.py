"""Shared UI elements and the light visual alignment with Comp (light surfaces, white rounded cards,
coral accent, pill buttons). Colors and font live in .streamlit/config.toml."""

import html

import streamlit as st

ACCENT = "#EF3F50"

SYNTHETIC_DATA_NOTICE = (
    "**Dados sintéticos e ilustrativos.** Gerados por regras explícitas de causa e efeito; "
    "não representam pessoas, empresas ou resultados reais."
)

CSS = f"""
<style>
h1, h2, h3 {{ letter-spacing: -0.02em; }}
h1 {{ font-weight: 400 !important; }}
.accent {{ color: {ACCENT}; }}
[data-testid="stVerticalBlockBorderWrapper"] > div:has(> [data-testid="stVerticalBlock"]) {{ background: #FFFFFF; }}
div[data-testid="stVerticalBlockBorderWrapper"] {{ box-shadow: 0 2px 14px rgba(20,20,20,0.05); }}
div[data-testid="stAlert"] {{ border-radius: 0.9rem; }}
div[data-testid="stMetric"] {{ background:#FFFFFF; border:1px solid #E5E5E5; border-radius:0.9rem; padding:12px 16px; }}
.stButton > button[kind="primary"] {{ box-shadow: 0 6px 18px rgba(239,63,80,0.28); }}
.fake-sidebar {{background:#141414; color:#D6D6D6; border-radius:14px; padding:14px 12px; font-size:0.86rem; min-height:520px;}}
.fake-sidebar .ws {{font-weight:600; color:#fff; margin-bottom:12px;}}
.fake-sidebar .sec {{color:#9AA0A6; margin:12px 0 4px; font-size:0.74rem; text-transform:uppercase; letter-spacing:.05em;}}
.fake-sidebar .item {{padding:3px 6px; border-radius:6px;}}
.fake-sidebar .active {{background:#2A2A2A; color:#fff; font-weight:600;}}
.msg-head {{display:flex; align-items:center; gap:10px; margin-bottom:4px;}}
.msg-avatar {{width:34px; height:34px; border-radius:10px; background:{ACCENT}; color:#fff; display:flex;
             align-items:center; justify-content:center; font-weight:600;}}
.msg-avatar.person {{background:#141414;}}
.msg-name {{font-weight:600;}}
.msg-badge {{font-size:0.68rem; background:#F1F1F1; color:#555; border-radius:4px; padding:1px 5px;}}
.msg-time {{color:#8A8A8A; font-size:0.8rem;}}
.quad {{border-radius:12px; padding:10px 12px; min-height:110px; border:1px solid #E5E5E5; background:#FFFFFF;}}
.quad .title {{font-size:0.8rem; color:#6B6B6B; margin-bottom:6px;}}
.quad .who {{font-weight:600;}}
.time-chip {{display:inline-block; background:#FDEBED; color:{ACCENT}; border-radius:999px; padding:2px 10px; font-weight:500;}}
</style>
"""


def apply_style() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def synthetic_data_banner() -> None:
    """Render the notice that must appear at the top of every page."""
    st.info(SYNTHETIC_DATA_NOTICE, icon="ℹ️")


def under_construction(phase: str, description: str) -> None:
    """Placeholder for flows that will be built in later phases."""
    st.caption(f"Em construção — {phase}")
    st.write(description)


def md(text: str) -> None:
    """Markdown with dollar signs escaped (otherwise 'R$ ... R$' renders as math)."""
    st.markdown(text.replace("$", "\\$"))


def message_header(name: str, time: str, app: bool = True) -> None:
    initials = "C" if app else "".join(w[0] for w in name.split()[:2])
    badge = '<span class="msg-badge">APP</span>' if app else ""
    cls = "msg-avatar" if app else "msg-avatar person"
    st.markdown(
        f'<div class="msg-head"><div class="{cls}">{initials}</div>'
        f'<span class="msg-name">{html.escape(name)}</span>{badge}<span class="msg-time">{time}</span></div>',
        unsafe_allow_html=True,
    )
