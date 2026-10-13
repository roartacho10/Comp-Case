import pandas as pd
import streamlit as st

from src.app_data import load_world
from src.ui import dataframe

st.title("Como os dados foram gerados")
st.write(
    "Todos os dados do protótipo são gerados a partir de uma base de **premissas determinísticas**. "
    "Mesmas premissas e mesma semente produzem exatamente os mesmos dados. Para mudar um dado, "
    "muda-se a premissa que o gera."
)
with st.expander("A ordem de geração"):
    st.markdown(
        """
1. **Esqueleto:** país, área e nível de cada pessoa, times e gestores.
2. **Causa oculta de risco:** remuneração, crescimento, externa (mudança de cidade, de carreira, vida pessoal) ou nenhuma.
3. **Sinais ativos:** cada sinal aparece com uma chance maior quando a sua causa existe.
4. **Dados brutos:** salários, datas e anotações construídos para exibir exatamente esses sinais.
5. **Histórico:** admissões, promoções, reajustes e saídas dos últimos 12 meses.
6. **Rede da Comp:** casos fechados de outras empresas, gerados pelas mesmas regras.

A causa oculta fica fora do app: o sistema só enxerga os dados brutos e os sinais calculados a partir deles.
"""
    )

world = load_world()
checks = world["checks"]
tab_assumptions, tab_checks, tab_tables = st.tabs(["Premissas", "Checagens", "Tabelas geradas"])

with tab_assumptions:
    table = world["assumptions"].rename(
        columns=dict(
            group="Grupo", description="O que é", value="Valor", unit="Unidade",
            rationale="Racional do valor", origin="Origem", key="Chave",
        )
    )[["Grupo", "O que é", "Valor", "Unidade", "Racional do valor", "Origem", "Chave"]]
    origins = sorted(table["Origem"].unique())
    chosen = st.multiselect("Filtrar por origem", origins, default=origins)
    dataframe(
        table[table["Origem"].isin(chosen)],
        hide_index=True,
        width="stretch",
        height=560,
        column_config={
            "O que é": st.column_config.TextColumn(width="large"),
            "Racional do valor": st.column_config.TextColumn(width="large"),
        },
    )
    st.caption(f"{len(table)} premissas. Editáveis em `data/assumptions.csv`; qualquer mudança regenera os dados. "
               "Os períodos de 12 meses (resultado de cada decisão e histórico do cliente) são fixos, e não premissas: "
               "todas as taxas do sistema se referem ao mesmo ano.")
    with st.expander("Catálogo de sinais e de intervenções"):
        dataframe(world["signals"], hide_index=True, width="stretch")
        dataframe(world["interventions"], hide_index=True, width="stretch")

with tab_checks:
    passed = int(checks["ok"].sum())
    st.metric("Checagens que passaram", f"{passed} de {len(checks)}")
    st.caption("As metas são derivadas das premissas: se uma premissa muda, a meta muda junto.")
    view = checks.assign(status=checks["ok"].map({True: "✓", False: "✗"}))[
        ["status", "grupo", "checagem", "meta", "obtido", "nota"]
    ]
    dataframe(
        view,
        hide_index=True,
        width="stretch",
        height=620,
        column_config={
            "status": st.column_config.TextColumn("", width=40),
            "checagem": st.column_config.TextColumn("Checagem", width="large"),
            "nota": st.column_config.TextColumn("Nota", width="large"),
        },
    )

with tab_tables:
    labels = {
        "hris": "HRIS",
        "events": "Eventos",
        "benchmark": "Benchmark da Comp",
        "managers": "Gestores",
        "context": "Contexto (anotações e atas)",
        "network_companies": "Rede: empresas",
        "network_cases": "Rede: casos fechados",
        "personas": "Personagens",
    }
    name = st.selectbox("Tabela", list(labels), format_func=labels.get)
    df: pd.DataFrame = world["public"][name]
    sample_size = 1000
    if len(df) > sample_size:
        st.caption(
            f"{len(df):,} linhas; exibindo uma amostra de {sample_size:,}. A tabela completa está no repositório.".replace(",", ".")
        )
        df = df.head(sample_size)
    else:
        st.caption(f"{len(df):,} linhas".replace(",", "."))
    dataframe(df, hide_index=True, width="stretch", height=520)
