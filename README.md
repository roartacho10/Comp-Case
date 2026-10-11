# Retenção com aprendizado — protótipo

Protótipo construído para o case *Forward Deployed* da Comp. Demonstra o ciclo central da solução proposta: **sinal → caso → intervenção → resultado → aprendizado**, aplicado a decisões de retenção.

> **Dados sintéticos e ilustrativos.** Todos os dados são gerados por regras explícitas de causa e efeito, com semente fixa. Não representam pessoas, empresas ou resultados reais. Ilustram o mecanismo, não provam o resultado.

## Status

Construção em fases, cada uma revisada e aprovada antes da seguinte. O histórico detalhado está em [`docs/build_log.md`](docs/build_log.md).

| Fase | Conteúdo | Status |
|---|---|---|
| 0 | Fundação: repositório, estrutura e publicação | Em validação |
| 1 | Mundo e dados sintéticos | A fazer |
| 2 | Personagens e motor de regras | A fazer |
| 3 | Fluxo 1: caso do gestor | A fazer |
| 4 | Fluxos 2 e 3: aprendizado e liderança | A fazer |
| 5 | Camada de AI | A fazer |
| 6 | Testes, README e publicação final | A fazer |

## Como rodar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
pytest
```

## Estrutura

```
app.py            # configuração e navegação
app_pages/        # uma página por fluxo
src/              # lógica (dados, motor, AI) e componentes de interface
tests/            # testes automatizados
docs/             # log de construção
```

Código em inglês; interface em português.
