# Retenção com aprendizado — protótipo

Protótipo construído para o case *Forward Deployed* da Comp. Demonstra o ciclo central da solução proposta: **sinal → caso → intervenção → resultado → aprendizado**, aplicado a decisões de retenção.

> **Dados sintéticos e ilustrativos.** Todos os dados são gerados por regras explícitas de causa e efeito, com semente fixa. Não representam pessoas, empresas ou resultados reais. Ilustram o mecanismo, não provam o resultado.

**App publicado:** https://comp-case-whvmhuagjmfytrjxadlqsx.streamlit.app/

## Status

Construção em fases, cada uma revisada e aprovada antes da seguinte. O histórico detalhado está em [`docs/build_log.md`](docs/build_log.md).

| Fase | Conteúdo | Status |
|---|---|---|
| 0 | Fundação: repositório, estrutura e publicação | Concluída |
| 1 | Mundo e dados sintéticos | Em validação |
| 2 | Personagens e motor de regras | A fazer |
| 3 | Fluxo 1: caso do gestor | A fazer |
| 4 | Fluxos 2 e 3: aprendizado e liderança | A fazer |
| 5 | Camada de AI | A fazer |
| 6 | Testes, README e publicação final | A fazer |

## Como rodar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
python scripts/generate_data.py   # regenera os CSVs a partir das premissas e roda as checagens
pytest
```

## Premissas determinísticas

Toda regra do mundo sintético está em uma base editável, e nenhum número de regra fica no código:

- [`data/assumptions.csv`](data/assumptions.csv): uma premissa por linha (grupo, chave, valor, unidade, descrição e origem: case, documento ou premissa assumida).
- [`data/signals.csv`](data/signals.csv): catálogo de sinais (causa a que pertencem, nível pessoa ou time, fonte).
- [`data/interventions.csv`](data/interventions.csv): catálogo de intervenções (causa que atacam e regra de custo).

Os dados em `data/generated/` são **derivados** dessas tabelas e não são editados à mão: mudou a premissa, rode `scripts/generate_data.py`. Um teste garante que o retrato commitado é exatamente o que as premissas atuais geram. A verdade oculta (causa de cada pessoa) fica em `data/hidden/`, visível para auditoria, mas nunca lida pelo sistema; outro teste garante isso.

## Estrutura

```
app.py            # configuração e navegação
app_pages/        # uma página por fluxo + página de dados
data/             # premissas (editáveis), dados gerados e verdade oculta
scripts/          # geração dos dados
src/              # lógica (premissas, gerador, sinais, checagens) e componentes de interface
tests/            # testes automatizados
docs/             # log de construção
```

Código em inglês; interface em português.
