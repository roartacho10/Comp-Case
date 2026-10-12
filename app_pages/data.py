import pandas as pd
import streamlit as st

from src.app_data import load_world
from src.ui import synthetic_data_banner

synthetic_data_banner()
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
2. **Causa oculta de risco:** remuneração, crescimento, gestor, externa ou nenhuma. A causa “gestor” nasce no time: alguns gestores têm problema de relação com o time.
3. **Sinais ativos:** cada sinal aparece com uma chance maior quando a sua causa existe, no nível em que o sinal existe (pessoa ou time).
4. **Dados brutos:** salários, datas, pulsos e anotações construídos para exibir exatamente esses sinais.
5. **Histórico:** admissões, promoções, reajustes, trocas de gestor e saídas dos últimos 12 meses.
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
    st.dataframe(
        table[table["Origem"].isin(chosen)],
        hide_index=True,
        width="stretch",
        height=560,
        column_config={
            "O que é": st.column_config.TextColumn(width="large"),
            "Racional do valor": st.column_config.TextColumn(width="large"),
        },
    )
    st.caption(f"{len(table)} premissas. Editáveis em `data/assumptions.csv`; qualquer mudança regenera os dados.")
    with st.expander("Catálogo de sinais e de intervenções"):
        st.dataframe(world["signals"], hide_index=True, width="stretch")
        st.dataframe(world["interventions"], hide_index=True, width="stretch")

with tab_checks:
    passed = int(checks["ok"].sum())
    st.metric("Checagens que passaram", f"{passed} de {len(checks)}")
    st.caption("As metas são derivadas das premissas: se uma premissa muda, a meta muda junto.")
    view = checks.assign(status=checks["ok"].map({True: "✓", False: "✗"}))[
        ["status", "grupo", "checagem", "meta", "obtido", "nota"]
    ]
    st.dataframe(
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
        "pulse": "Pulso",
        "context": "Contexto (anotações e atas)",
        "network_companies": "Rede: empresas",
        "network_cases": "Rede: casos fechados",
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
    st.dataframe(df, hide_index=True, width="stretch", height=520)
