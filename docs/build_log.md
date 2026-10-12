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

---

## Fase 2 — Personagens e motor de regras

**Objetivo:** construir o motor de regras e os três personagens, de ponta a ponta e sem AI, para validar a lógica antes da interface definitiva.

**Decisões validadas antes da execução**

| Decisão | Escolha | Racional |
|---|---|---|
| Valor esperado (VE) | Horizonte = tempo que a pessoa ainda ficaria sem ação (1 ÷ chance anual de saída), com teto de 5 anos; resultado medido em 6 meses | O valor de reter alguém se estende pelo tempo que a pessoa ainda ficaria; 6 meses é o horizonte verificável |
| Duração do efeito | Ações pontuais (carreira e projeto, escalar): 12 meses; ajuste salarial: enquanto for pago | Sem isso, uma ação de R$ 3 mil seria tratada como permanente e venceria o ajuste da Mariana |
| Custo da saída | 75% do custo anual (seção 3.3, com decomposição e fatores na explicação da premissa) + diferença de mercado paga ao substituto | O substituto é contratado pela mediana: parte do custo do ajuste seria paga de qualquer jeito |
| Risco | Chance de sair em 6 meses sem ação, nos casos monitorados da rede com mesma causa e número de sinais; com múltiplo da média da empresa | Risco é o que acontece se nada for feito |
| Empate de causa | Mostrar as duas causas e o empate; a decisão final é humana | Pedido do autor |
| Casos comparáveis | 3 mais recentes com mesma causa, nível e intervenção recomendada, incluindo quem saiu | Precedente concreto, não só sucessos |
| Quem decide | Causa gestor → gestor do gestor; demais → gestor do time | Como no documento |
| Personagens | Em `data/personas.csv` e `data/persona_outcomes.csv`, substituindo 3 colaboradores; times com 3 ou mais outros casos | Roteiro registrado e editável; calibração com mais de um caso |
| Aprendizado | Taxas antes e depois separando rede e cliente; calibração por gestor e do sistema | O ativo é a rede; o que se move é o aprendizado do cliente e de cada gestor |

**Decisão tomada durante a execução (a validar)**

- **O efeito de cada intervenção é estimado com todos os casos da mesma causa, sem separar por número de sinais; o risco continua separado.** No teste de mutabilidade (sinal com 45% em vez de 60%), a recomendação do Diego virou "monitorar" porque o subgrupo com 3 sinais tinha poucos casos e o efeito sumiu no ruído. Juntando os casos da mesma causa, o efeito fica estável e as três recomendações se mantêm nos dois cenários.

**O que foi construído**

- Personagens injetados com exatamente os 3 sinais da sua causa; o time da Lucía recebe troca de gestor há 4 meses e 3 saídas em 6 meses, herdadas pelos colegas.
- Motor: sinais com evidência, abertura de caso, causa provável com empate, risco, VE com incerteza (intervalo de 80%), recomendação, casos comparáveis e roteamento.
- Simulação dos 6 meses: decisões dos demais gestores (adesão de 60%, status quo, previsões com viés), resultados pelas regras do mundo para toda a empresa e roteiro para os personagens. A simulação é a única parte, além do gerador, que lê a verdade oculta.
- Aprendizado: taxas antes e depois (rede e cliente) e calibração de gestores e do sistema.
- Página provisória "Bastidores do motor".
- Nomes fictícios únicos (antes havia homônimos).

**Checagens**

- 45 de 45 checagens passaram, incluindo, para cada personagem: sinais encontrados, causa, recomendação e pelo menos 3 outros casos com o mesmo decisor.
- 191 casos abertos em T0; causa provável igual à verdadeira em 84%.
- Recomendações dos personagens: Mariana → ajuste salarial (VE +R$ 22 mil); Diego → carreira e projeto (+R$ 13 mil); Lucía → escalar (+R$ 11 mil).
- Testes: 25 passando, incluindo roteamento da causa gestor, recomendação com maior VE, determinismo da simulação, independência entre a escolha do personagem e o resto da empresa, roteiros dos personagens e o fluxo completo da página.
- Fluxo percorrido no navegador: Lucía com a recomendação rejeitada (ajuste salarial com justificativa) → sai no mês 5.

**Pontos levantados para o autor**

- A calibração individual dos gestores sai fraca: com permanência de ~90% em 6 meses, o viés de +15 p.p. bate no teto de 95% e, com 5 a 13 casos por gestor, o realizado é dominado pelo acaso.
- Os casos comparáveis mais recentes caem quase sempre na mesma data (a rede tem ~130 decisões por dia).

### Revisão da Fase 2

- **Calibração dos gestores reformulada (aprovada pelo autor).** "Superestimam a permanência em 15 p.p." virou "subestimam o risco de saída pela metade". O acréscimo fixo esbarrava no teto de 95%: como ~90% das pessoas em risco ficam em 6 meses, o viés quase sumia (+2 p.p.).
- Ao implementar, o mesmo efeito de teto reapareceu: com previsões limitadas a 95% e ruído de 10 p.p., o viés seguia em ~2 p.p. Teto passou a 99% e ruído a 5 p.p. (premissas), e **a calibração passou a ser mostrada em número de saídas**: nos casos abertos, os gestores esperavam 13 saídas, o sistema 22, e ocorreram 18. Em chance de ficar a diferença parece pequena (93% contra 91%), porque a maioria fica; em saídas, os gestores previram cerca de 70% do que aconteceu.

**Status:** em validação pelo autor.
