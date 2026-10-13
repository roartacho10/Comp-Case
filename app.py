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
# A session that was open during an update must not reuse results computed by the previous version.
if st.session_state.get("code_fingerprint") != _fingerprint:
    st.session_state.pop("results_cache", None)
    st.session_state["code_fingerprint"] = _fingerprint

from src.app_data import assumptions  # noqa: E402  (imported after the reload guard)
from src.state import demo_sidebar  # noqa: E402
from src.ui import apply_style  # noqa: E402

apply_style()

# The app shows the product as each user would see it; the sidebar is the demo script (src/state.py).
# How it works lives in the guide; data generation and the engine stay on hidden pages for auditors.
pages = dict(
    home=st.Page("app_pages/home.py", title="Início", default=True),
    caso=st.Page("app_pages/manager_case.py", title="Caso do gestor", url_path="caso"),
    lideranca=st.Page("app_pages/leadership.py", title="Painel da liderança", url_path="lideranca"),
    retorno=st.Page("app_pages/learning.py", title="Retorno aos gestores", url_path="retorno"),
    dados=st.Page("app_pages/data.py", title="Como os dados foram gerados", url_path="dados"),
    bastidores=st.Page("app_pages/engine_debug.py", title="Bastidores do motor", url_path="bastidores"),
)
current = st.navigation(list(pages.values()), position="hidden")
demo_sidebar(assumptions(), pages, current)
current.run()
