"""Entry point: page configuration, code-reload guard and navigation."""

import hashlib
import sys
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Comp | Retenção com aprendizado", page_icon="🔁", layout="wide")

# After a new deploy, the server can keep old versions of some modules in memory and mix them with
# new ones. If any project source or data file changed, drop every project module and the data cache,
# so this run imports everything fresh.
ROOT = Path(__file__).resolve().parent
_files = sorted(list((ROOT / "src").glob("*.py")) + list((ROOT / "data").glob("*.csv")))
_fingerprint = hashlib.sha256(b"".join(p.read_bytes() for p in _files)).hexdigest()


@st.cache_resource
def _loaded_code() -> dict:
    return {"fingerprint": None}


_state = _loaded_code()
if _state["fingerprint"] != _fingerprint:
    for name in [m for m in sys.modules if m == "src" or m.startswith("src.")]:
        del sys.modules[name]
    st.cache_data.clear()
    _state["fingerprint"] = _fingerprint

from src.app_data import assumptions  # noqa: E402  (imported after the reload guard)
from src.state import sidebar_controls  # noqa: E402
from src.ui import apply_style  # noqa: E402

apply_style()
sidebar_controls(assumptions())

pages = [
    st.Page("app_pages/home.py", title="Início", default=True),
    st.Page("app_pages/manager_case.py", title="1. Caso do gestor"),
    st.Page("app_pages/learning.py", title="2. Retorno e aprendizado"),
    st.Page("app_pages/leadership.py", title="3. Visão da liderança"),
    st.Page("app_pages/results.py", title="4. Resultado em 12 meses"),
    st.Page("app_pages/data.py", title="Como os dados foram gerados"),
    st.Page("app_pages/engine_debug.py", title="Bastidores do motor", url_path="bastidores", visibility="hidden"),
]

st.navigation(pages).run()
