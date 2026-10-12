"""End-to-end: the demo script in a real browser, against the app served by Streamlit.

Skipped when Playwright (or its Chromium) is not available; it is a development dependency only.
"""

import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

sync_api = pytest.importorskip("playwright.sync_api")
ROOT = Path(__file__).resolve().parents[1]


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("localhost", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def base_url():
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py", "--server.port", str(port), "--server.headless", "true"],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(60):
            try:
                socket.create_connection(("localhost", port), timeout=1).close()
                break
            except OSError:
                time.sleep(0.5)
        yield f"http://localhost:{port}"
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def _settle(page, text=None):
    if text:
        page.get_by_text(text, exact=False).first.wait_for(timeout=120000)
    page.wait_for_timeout(1000)
    page.wait_for_function("!document.querySelector('[data-testid=\"stStatusWidget\"]')", timeout=120000)
    assert page.locator('[data-testid="stException"]').count() == 0


def _nav(page, label, wait):
    page.locator('[data-testid="stSidebarNav"]').get_by_text(label, exact=True).click()
    _settle(page, wait)


def _pick(page, prefix):
    box = page.locator('[data-testid="stSelectbox"]').first
    box.scroll_into_view_if_needed()
    box.click()
    page.keyboard.type(prefix)
    page.keyboard.press("Enter")
    _settle(page, "Sua decisão")


def _predict(page, text="Provavelmente fica"):
    page.get_by_text(text, exact=True).last.click()
    page.wait_for_timeout(300)


def _register(page, wait="Registrado:"):
    page.get_by_role("button", name="Registrar decisão").click()
    _settle(page, wait)


def test_demo_script(base_url):
    with sync_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as exc:  # no browser installed
            pytest.skip(f"Chromium indisponível: {exc}")
        page = browser.new_page(viewport={"width": 1280, "height": 1600})
        page.goto(base_url)
        _settle(page, "Como navegar")

        _nav(page, "1. Caso do gestor", "Sua decisão")
        _register(page, "Registre a sua previsão")        # the prediction is required
        _predict(page, "Quase certo que fica")
        _register(page)                                   # Mariana: follows the suggestion
        _pick(page, "Diego")
        _predict(page)
        _register(page)                                   # Diego: follows the suggestion
        _pick(page, "Lucía")
        page.get_by_text("Ajuste salarial", exact=True).last.click()
        _predict(page)
        _register(page, "conte em uma frase o porquê")   # diverging without a reason is blocked
        page.locator("textarea").fill("Acho que um aumento resolve.")
        page.wait_for_timeout(300)
        _register(page, "Você seguiu um caminho diferente da sugestão")

        page.get_by_role("button", name="Avançar 12 meses").click()
        _settle(page, "out/2027")

        _nav(page, "2. Retorno e aprendizado", "Retorno para quem decidiu")
        body = page.inner_text("body")
        assert "Mariana continua no time" in body
        assert "um resultado ruim não torna a decisão ruim" in body
        assert "em vez da sugestão" in body

        _nav(page, "3. Visão da liderança", "Onde está o risco")
        body = page.inner_text("[data-testid='stMain']")
        for name in ("Mariana", "Diego", "Lucía"):
            assert name not in body

        _nav(page, "4. Resultado em 12 meses", "Saídas evitadas")
        _nav(page, "Como os dados foram gerados", "premissas determinísticas")
        browser.close()
