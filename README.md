# Retenção com aprendizado — protótipo

Protótipo construído para o case *Forward Deployed* da Comp. Demonstra o ciclo central da solução proposta: **sinal → caso → intervenção → resultado → aprendizado**, aplicado a decisões de retenção.

> **Dados sintéticos e ilustrativos.** Todos os dados são gerados por regras explícitas de causa e efeito, com semente fixa. Não representam pessoas, empresas ou resultados reais. Ilustram o mecanismo, não provam o resultado.

**App publicado:** https://comp-case-whvmhuagjmfytrjxadlqsx.streamlit.app/

## Status

Construção em fases, cada uma revisada e aprovada antes da seguinte. O histórico detalhado está em [`docs/build_log.md`](docs/build_log.md).

| Fase | Conteúdo | Status |
|---|---|---|
| 0 | Fundação: repositório, estrutura e publicação | Concluída |
| 1 | Mundo e dados sintéticos | Concluída |
| 2 | Personagens e motor de regras | Concluída |
| 3 | Fluxo 1: caso do gestor | Concluída |
| 4 | Fluxos 2 e 3 (aprendizado, liderança) e resultado | Concluída |
| 5 | Camada de AI | Concluída |
| 6 | Testes, README e publicação final | A fazer |

## Como rodar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
python scripts/generate_data.py   # regenera os CSVs a partir das premissas e roda as checagens
pytest
```

## Onde entra a AI

A AI (Claude, pela API da Anthropic, chamada pelo servidor do app) **escreve e lê, mas não calcula nem decide**:

- lê a anotação da conversa de carreira e indica o sinal que ela contém;
- escreve a mensagem do caso para quem decide (com perguntas adaptadas à pessoa), o retorno após 12 meses e os resumos para a liderança.

Ela recebe só os fatos já calculados pelo motor. Antes de aparecer, cada texto passa por quatro checagens: formato, **todo número do texto existe nos fatos recebidos**, nenhum termo vetado (rótulos, tom de comando, jargão) e a frase "a decisão é sua" na mensagem do caso. Se falhar, se não houver chave ou se a chamada demorar, a tela usa o texto padrão revisado. As regras estão em [`prompts/`](prompts/).

Para ativar, coloque a chave nos secrets do Streamlit (`ANTHROPIC_API_KEY = "..."`). Nunca no código.

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
