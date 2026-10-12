# Log de construção

Construção conduzida com AI (Claude), uma fase por vez. Antes de cada fase, as escolhas são validadas com o autor; ao final, a fase é revisada e só então a seguinte começa. Cada fase corresponde a um ou mais commits identificados pelo número da fase.

---

## Fase 0 — Fundação

**Objetivo:** criar o repositório, a estrutura do app e publicá-lo no Streamlit Community Cloud antes de construir qualquer lógica, para resolver cedo as dependências de infraestrutura.

**Decisões validadas antes da execução**

| Decisão | Escolha | Racional |
|---|---|---|
| Visibilidade do repositório | Público | O histórico de commits é o log compartilhado com a Comp; os dados são sintéticos e a chave da API fica nos secrets do Streamlit, fora do código |
| Repositório | `Comp-Case`, na conta do autor | App e código ficam com o autor |
| Idioma | Código em inglês, interface em português | Código legível para qualquer time de engenharia; interface no idioma da demonstração |

**O que foi construído**

- App Streamlit com navegação para os três fluxos (ainda como páginas "em construção") e página inicial com o status das fases.
- Aviso de dados sintéticos e ilustrativos em todas as páginas.
- Dependências com versões fixas (`requirements.txt`), `.gitignore` excluindo secrets.
- Teste de fumaça: todas as páginas renderizam sem erro e exibem o aviso.

**Checagens**

- `pytest`: 5 testes passando.
- App executado localmente e verificado visualmente.
- App publicado no Streamlit Community Cloud (https://comp-case-whvmhuagjmfytrjxadlqsx.streamlit.app/); autor confirmou as quatro páginas e o aviso de dados sintéticos no ar.

**Ocorrências**

- O push foi inicialmente recusado: o conector do GitHub estava ativo, mas o app do Claude no GitHub não tinha acesso de escrita ao repositório. Resolvido com a instalação do app restrita ao repositório `Comp-Case`.
- O Streamlit não encontrou a branch `main` na primeira tentativa, por ter lido o repositório ainda vazio. Resolvido ao recarregar o formulário.

**Status:** concluída e aprovada pelo autor.

---

## Fase 1 — Mundo e dados sintéticos

**Objetivo:** gerar os dados sintéticos a partir de regras explícitas e verificáveis, antes de qualquer lógica de produto, porque todas as fases seguintes dependem desses números.

**Decisões validadas antes da execução**

| Decisão | Escolha | Racional |
|---|---|---|
| Premissas | Toda regra do mundo numa base editável (`data/assumptions.csv`), lida pelo sistema; nenhum número de regra no código | Pedido do autor: poder revisar regras depois. Cada número do protótipo fica explicável por uma premissa registrada |
| Dados gerados | Derivados das premissas, nunca editados à mão | Editar dados à mão quebraria a coerência entre regra e dado |
| Edição | Por commit na base de premissas; edição dentro do app adiada | O Streamlit Cloud não persiste arquivos gravados pelo app; persistir exigiria um banco externo sem ganho relevante agora |
| Medianas de mercado | +10% sobre a 4.3 (júnior R$ 140 mil a gestor R$ 470 mil) | Com os valores originais a folha ficava em ~R$ 227 mi, abaixo dos ~R$ 250 mi da seção 3.3 |
| Ordem de geração | Causa oculta → sinais → dados brutos construídos para exibir os sinais → histórico | Coerência por construção; a checagem passa a ser exata |
| Sinal "abaixo de recém-contratados" | Trocado por "sem mudança salarial há mais de 18 meses" | Media o mesmo que o compa-ratio e contaria remuneração duas vezes |
| Sinal "tempo no nível" | Comparado a uma referência por nível (premissa), não à mediana dos pares | Evita dependência circular entre pessoas na geração |
| Causa "gestor" | Nasce no time (10% dos gestores de time têm problema de relação); sinais de time sorteados por time | Troca de gestor e saídas no time são fatos do time, não da pessoa; a visão da liderança passa a mostrar times que concentram risco |
| Formato e visibilidade | CSV no repositório; página "Como os dados foram gerados" no app | Legível no GitHub e no app sem rodar código |

**O que foi construído**

- Base de premissas com 88 regras, cada uma com origem marcada; catálogos de sinais (9) e de intervenções (4).
- Módulo único de acesso às premissas: falha se uma premissa não existir e registra quais foram lidas.
- Gerador do mundo: 1.000 colaboradores ativos, 151 saídas voluntárias nos últimos 12 meses, eventos, benchmark, gestores, pulso, anotações de contexto e a rede da Comp (30 empresas, 3.000 casos fechados).
- Recálculo dos sinais apenas a partir dos dados brutos (base do motor da Fase 2).
- 30 checagens com metas derivadas das premissas e página no app com premissas, checagens e tabelas.

**Checagens**

- 30 de 30 checagens passaram (detalhe na página "Como os dados foram gerados").
- Sinais recalculados dos dados brutos idênticos aos sorteados pelas regras em 100% das pessoas.
- Folha de R$ 247,4 mi; turnover de 15,1%; custo de reposição das saídas arrependidas de R$ 14,5 mi (seção 3.3: ~R$ 14 mi).
- 176 casos seriam abertos em T0 (~2 por gestor de time).
- Testes: 15 passando, incluindo: toda premissa é usada, mudar uma premissa mantém as checagens válidas, o retrato commitado é igual ao que as premissas geram, nenhum módulo do sistema lê a verdade oculta.

**Premissas novas, criadas durante a execução (a validar)**

- Janela de 6 meses para eventos de contexto; chance de seguir performando de 90% (causa tratada) e 75% (não tratada); dispersão de 10 p.p. nas previsões dos gestores.
- Dez detalhes de geração (faixas de datas, porte das empresas da rede, fração de anotações neutras), marcados como "detalhe de geração".

**Pontos levantados para o autor**

- A causa "gestor" fica em 4,4%, e não 5%: 10% dos times × 90% de pessoas que não são gestoras × 50%.
- Na rede, a diferença de permanência entre a intervenção certa e as demais é de poucos pontos (ex.: remuneração: ajuste 89,8% contra 87,5% monitorando), porque a chance de saída em 6 meses com causa é de 20%.

### Revisão da Fase 1

**Pedidos e decisões do autor**

| Ponto | Decisão | Racional |
|---|---|---|
| Base de premissas | Colunas "O que é" e "Racional do valor" em todas as premissas | Cada valor precisa ser explicável e defensável, não só registrado |
| Causa "gestor" | Chance por membro de time com problema de 50% para 55% | Leva a causa a ~5% da população, como na seção 4.3 (antes, 4,4%) |
| Premissas novas | Validadas | — |
| Tamanho da rede | Derivado da base de clientes da Comp: 500 clientes com média de 500 colaboradores, 12 meses de decisões com resultado conhecido | O sistema decide com dados de muitas empresas, não só do cliente do case. Com 3.000 casos, o ruído era maior que o efeito |

**Ocorrência que motivou a mudança da rede**

Ao aplicar a mudança na causa "gestor", o sorteio mudou e duas checagens da rede falharam: em "crescimento", monitorar apareceu com permanência maior que carreira e projeto. Não era erro de código, e sim ruído: com 3.000 casos e 60% de adesão à recomendação, as intervenções alternativas tinham só 50 a 130 casos, e o acaso movia as taxas em até ±8 pontos, mais do que a diferença real (~8 pontos). A revisão foi mantida fora da `main` (branch `fase-1-revisao`) até a decisão, para não publicar dados em que a rede indicava a intervenção errada.

**O que mudou**

- Rede com 500 clientes (100 a 900 colaboradores, ~251 mil no total) e 46.708 casos fechados. O tamanho é calculado, não fixado: colaboradores da rede × fração com caso aberto no cliente (18,6%) × 1 ano de decisões.
- Geração da rede reescrita para processar todos os casos de uma vez (geração completa em ~3 s).
- Tabelas da rede guardadas compactadas (`.csv.gz`), porque passam de 10 MB; o app mostra uma amostra de 1.000 linhas.

**Checagens**

- 31 de 31 checagens passaram; testes: 15 passando.
- Permanência em 6 meses na rede, intervenção certa contra monitorar: remuneração 90,0% × 81,8%; crescimento 90,5% × 82,9%; gestor 91,3% × 81,1%. Menor grupo de comparação: 922 casos.

**Status:** concluída e aprovada pelo autor.
