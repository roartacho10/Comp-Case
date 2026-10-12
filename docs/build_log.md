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

- **Janela de resultado de 6 para 12 meses (decisão do autor).** A janela virou premissa (`outcome.window_months`) usada pela rede, pelo risco, pela simulação e pela interface. A chance de saída na janela passa a ser calculada a partir da chance anual, com ritmo constante de saídas. A rede passa a ter decisões de 12 a 24 meses atrás, porque um caso só fecha após a janela (supõe produto rodando há ~2 anos). A premissa de idade mínima das decisões da rede foi removida: agora decorre da janela.
- Resultado: na rede, a intervenção certa retém ~81% contra ~63% monitorando (antes, ~90% contra ~82%). Recomendações dos personagens mantidas: Mariana → ajuste (+R$ 29 mil), Diego → carreira e projeto (+R$ 21 mil), Lucía → escalar (+R$ 16 mil). Nos casos abertos, os gestores esperavam 22 saídas, o sistema 44, e ocorreram 34.
- Com a semente 7, o sorteio de saídas caiu abaixo da média: em 5 sementes (7 a 11), as saídas ocorridas foram 34, 46, 41, 47 e 45 (média 43, próxima das ~45 esperadas pelo sistema). Uma rodada isolada sugeria, sem razão, que o sistema exagera o risco.
- **Decisão do autor:** semente da simulação trocada para 11, representativa da média, com a escolha e os resultados das demais sementes registrados na explicação da premissa; e a tela passou a mostrar a faixa provável de saídas (80%) ao lado de cada previsão. Resultado: gestores esperavam 22 (faixa de 16 a 28), o sistema 45 (37 a 53), ocorreram 45.

**Status:** concluída e aprovada pelo autor.

---

## Fase 3 — Fluxo 1: caso do gestor

**Objetivo:** a tela em que o gestor recebe o caso, entende o que os dados indicam, decide e registra a previsão. Textos por modelo fixo (a AI entra na Fase 5, e estes modelos viram a reserva dela).

**Decisões validadas antes da execução**

| Decisão | Escolha | Racional |
|---|---|---|
| Tom | **Orientar, não mandar** (pedido do autor): a mensagem explica o que os dados indicam e o que a rede aprendeu, e termina com "a decisão é sua" | O gestor decide; o sistema traz evidência e contexto que ele não tem |
| Ordem da mensagem | Resumo → por que agora (sinais com evidência e risco) → causa provável → o que a rede aprendeu → sugestão → perguntas → opções → casos parecidos → decisão | Entender, verificar e só então escolher; as perguntas reforçam que a causa é hipótese |
| Risco | Probabilidade com faixa e base de casos, e "não é uma previsão sobre a pessoa; é o que aconteceu com pessoas em situação parecida" | Nunca rotular; estimativa não é medida |
| Perguntas | 3 perguntas abertas por causa, em tabela editável (`data/questions.csv`) | Não induzem resposta nem revelam números; editáveis como as demais premissas |
| Caso escalado | Vai para a liderança acima, explicando que os sinais apontam para a dinâmica de gestão do time e não para uma questão individual, sem adjetivos sobre o gestor | Coerente com "nunca rotular o colaborador nem o gestor" |
| Quem aparece | Só os 3 personagens, com seletor de qual caso ver | Os demais casos já foram decididos pela simulação |
| Decisão | Intervenção (sugerida pré-selecionada), causa em que acredita, previsão de 0 a 100% e justificativa obrigatória quando diverge; resposta do gestor e confirmação na conversa | A previsão alimenta a calibração; a justificativa torna a divergência aprendível |
| Visual | Conversa estilo chat corporativo marcada como "Slack (simulado)", sem marca do Slack | Integração simulada, sem imitar marca de terceiros |
| Casos parecidos | Sem a coluna de data | A data não ajudava a decisão e confundia |

**O que foi construído**

- Gerador de textos do caso (`src/case_text.py`) a partir dos números do motor, com variações para caso escalado e empate de causa.
- Página "1. Caso do gestor": seletor do caso, conversa simulada, opções com chance de ficar, custo e retorno esperado com faixas, casos parecidos, formulário de decisão e confirmação.
- Evidências dos sinais em formato brasileiro; R$ escapado no texto (o Markdown interpretava "R$ … R$" como fórmula).

**Checagens**

- Testes: 28 passando, incluindo: nenhuma mensagem usa rótulos ou tom de comando, todas dizem "a decisão é sua" e "não é uma previsão sobre", o caso escalado explica o roteamento, e divergir sem justificativa é bloqueado.
- Fluxo percorrido no navegador: caso da Mariana; caso da Lucía com ajuste salarial (bloqueado sem justificativa, registrado com justificativa, resposta e confirmação na conversa).

**Ocorrência no app publicado**

- Depois do push, a página "1. Caso do gestor" quebrou no Streamlit Cloud (`AttributeError` em `a.questions`). Causa: o servidor recarrega só os módulos cujos arquivos mudaram; módulos inalterados continuam apontando para versões antigas dos que mudaram, e o app mistura código velho e novo. Reproduzido localmente (servidor iniciado no commit da Fase 2, arquivos trocados pelos da Fase 3 com o servidor no ar).
- Correção: o `app.py` calcula uma impressão digital do código e dos dados; se mudou desde a última execução, descarta todos os módulos do projeto e o cache de dados antes de carregar as páginas. Verificado com o mesmo procedimento de reprodução: as páginas carregam sem erro.

**Status:** concluída e aprovada pelo autor.

---

## Fase 4 — Fluxos 2 e 3, controle de tempo e alinhamento visual

**Objetivo:** fechar o ciclo da solução (decisão → resultado → aprendizado) e dar à liderança a visão agregada, com a aparência alinhada à da Comp.

**Decisões validadas antes da execução**

| Decisão | Escolha | Racional |
|---|---|---|
| Estética | Alinhamento leve ao site da Comp (pedido do autor, a partir de um print): fundo claro, cartões brancos arredondados, coral como destaque, botões em pílula, fonte Inter; sem logotipo | Parecer algo desenvolvido pela Comp sem se passar por produto oficial |
| Tempo | "Avançar 12 meses" e "Reiniciar" na barra lateral, com a data atual | O tempo é estado do app inteiro |
| Retorno | Mensagem no Slack simulado para cada decisor, no tom de orientação, com resultado, previsão e calibração | O aprendizado chega a quem decidiu, no mesmo canal |
| Decisão × resultado | Matriz 2×2 (seguiu ou divergiu × ficou ou saiu), com leitura sem culpa | Decisões são avaliadas pela informação e pelo raciocínio no momento, não só pelo resultado (seção 4.1) |
| Aprendizado | Taxas da rede antes e depois e dos casos do cliente, com n | O ativo é a rede; o que se move é o aprendizado local |
| Calibração | Saídas esperadas (gestores e sistema) com faixa provável × ocorridas, no total e por decisor | Formato validado na Fase 2 |
| Liderança | Saídas e perda esperadas, mapa área × causa, times com concentração de casos (sem nomes, grupos ≥ 5), intervenções e, após 12 meses, saídas evitadas e valor preservado como estimativa | Valor em risco e resultado, sem expor pessoas; estimativa explícita |
| Bastidores | Fora do menu, acessível por link direto (`/bastidores`) | Demonstração limpa sem perder a ferramenta de defesa |

**O que foi construído**

- Tema visual em `.streamlit/config.toml` e CSS leve compartilhado (`src/ui.py`).
- Estado global (`src/state.py`): decisões dos personagens, relógio e resultados calculados uma vez por estado.
- Página "2. Retorno e aprendizado" e página "3. Visão da liderança" (`src/leadership.py` para os agregados).
- Mensagens de retorno (`outcome_message`) e matriz decisão × resultado (`quadrant`) em `src/case_text.py`.
- Nova premissa: tamanho mínimo de grupo exibido à liderança (5 pessoas).
- Roteiros dos personagens reescritos para não repetir o mês de saída nas mensagens.

**Checagens**

- Testes: 33 passando, incluindo páginas antes e depois da janela, cada personagem no seu quadrante, rótulos sem culpa e nenhum nome de pessoa na visão da liderança.
- Demonstração percorrida no navegador: decisões dos três personagens (Lucía divergindo com justificativa) → liderança em T0 → avançar 12 meses → liderança e retorno. Mariana: seguiu e ficou; Diego: seguiu e saiu; Lucía: divergiu e saiu.
- Números coerentes com a seção 3.3: perda esperada nos casos de R$ 12,3 mi (R$ 6,2 mi em saídas arrependidas); após 12 meses, ~25 saídas evitadas e ~R$ 2,7 mi preservados já descontado o custo das intervenções (3.3: ~R$ 3 mi por ano).

**Pontos levantados para o autor**

- Nos times com problema de gestão, todos os membros herdam os 2 sinais de time e abrem caso individual (4 times com 100% de casos; 13 casos para um mesmo diretor). Para a liderança é um sinal claro, mas talvez o certo seja um único caso de time, e não N casos individuais.
- Atualizar a página ou abrir o link de novo começa uma sessão nova: as decisões registradas se perdem. É o esperado num protótipo sem banco de dados; na gravação, navegar pelo menu.

### Revisão da Fase 4: Fluxo 1 mais claro para o gestor (pedidos do autor)

| Ponto do autor | Mudança |
|---|---|
| O retorno esperado parecia próximo do custo e não ficava claro por que compensa | A sugestão compara o custo da ação com o custo de perder a pessoa (reposição e substituto a valor de mercado) e só então dá o saldo, no tempo em que a pessoa ainda deve ficar. O "retorno" já era líquido do custo e cobria ~2 anos, enquanto o texto citava o custo de 12 meses |
| Números em excesso | Saíram intervalos, bases de casos e múltiplos com decimal; ficaram só os números que mudam a decisão. Risco em linguagem simples ("4 em cada 10 pessoas"). Detalhes seguem na página de bastidores |
| Casos parecidos sem contexto | Removidos da tela do gestor |
| Termos técnicos | Sinais com rótulo e evidência em linguagem direta (nova coluna `manager_label` no catálogo de sinais); "nível" → "cargo e senioridade", "causa provável" → "o motivo mais provável", "rede" → "base da Comp", "retorno esperado" → "saldo estimado" |
| Custos que o gestor conhece melhor | Valor no texto só para o ajuste salarial (dado de remuneração). Para carreira e projeto e escalar, o texto diz do que é feito o custo e até quanto vale gastar ("compensa enquanto o custo total ficar abaixo de ~R$ 26 mil"). Na tabela, sem valor de referência (pedido do autor): custo "você avalia" e saldo "compensa se custar até R$ X" |

- **Página própria para o resultado (pedido do autor):** "4. Resultado em 12 meses", separada da visão da liderança, que perdia destaque. Mostra saídas esperadas sem ação × ocorridas, saídas evitadas e valor preservado (com quanto cada R$ 1 em intervenções evitou em reposição), permanência quando a sugestão foi seguida × quando a decisão divergiu (com a ressalva de que é comparação descritiva), resultado por motivo e turnover e saídas arrependidas da empresa inteira contra os 12 meses anteriores.

**Status:** concluída e aprovada pelo autor.

---

## Fase 5 — Camada de AI

**Objetivo:** pôr a AI onde ela é estrutural (ler contexto não estruturado e escrever para quem decide), sem deixá-la calcular, decidir ou inventar.

**Decisões validadas antes da execução**

| Decisão | Escolha | Racional |
|---|---|---|
| Onde a AI escreve | Mensagem do caso, retorno após 12 meses e resumos das páginas 3 e 4 | É onde a linguagem importa; tabelas e números vêm direto do motor |
| Leitura de contexto | A AI lê a anotação da conversa de carreira e indica o sinal; a tela mostra o trecho destacado quando bate com o que o motor espera e o trecho existe literalmente na anotação | Uso estrutural da AI: texto solto vira dado (seção 4.1) |
| Perguntas | Adaptadas ao contexto da pessoa, a partir das perguntas-base | Perguntas que conversam com o que a pessoa disse funcionam melhor |
| Entrada | Só os fatos já calculados e o texto padrão aprovado como referência | A AI só pode usar o que está no pacote; isso torna a checagem possível |
| Regras | Orientar, não mandar; só números do pacote; linguagem simples; risco como "casos parecidos"; nunca rotular; nenhuma ação fora das opções (`prompts/system.md`) | As regras validadas nas Fases 3 e 4, escritas para a AI |
| Checagens | Formato; todo número do texto existe no pacote; nenhum termo vetado; "a decisão é sua" na mensagem do caso | Garantia, e não só instrução |
| Reserva | Os textos padrão revisados | Já cumprem o papel das respostas pré-geradas previstas na 4.3, sem um segundo conjunto para revisar |
| Modelo | Claude Sonnet 5.5 (`claude-sonnet-5-5`), como premissa editável | Equilíbrio entre qualidade e velocidade |
| Custo e abuso | Textos guardados no servidor por entrada; limite de 20 chamadas por sessão; 20 s por chamada | App público; demonstração rápida após a primeira visita |
| Transparência | Selo "escrito por AI" ou "texto padrão (motivo)" e seletor na barra lateral | Quem avalia vê onde a AI entra; o autor controla o risco na gravação |
| Chave | Somente nos secrets do Streamlit, colada pelo autor; nunca nesta conversa, que é parte do log | Segurança |

**O que foi construído**

- `prompts/`: regras comuns e uma instrução por tarefa (caso, retorno, resumo, leitura de anotação), versionadas e usadas como parte da chave do cache.
- `src/ai.py`: chamada à API, armazenamento das respostas validadas no servidor, limite por sessão, as quatro checagens e a reserva.
- `src/summaries.py`: resumos padrão para as páginas 3 e 4.
- Integração nas páginas 1 a 4, seletor "Textos escritos por AI ao vivo" e selos.
- Premissas de AI: modelo, tempo máximo, limite de chamadas e tamanho máximo da resposta.

**Checagens**

- Testes: 50 passando. Com um modelo simulado: saída válida aceita e reaproveitada sem nova chamada; rejeição por número inventado, termo vetado, tom de comando, frase obrigatória ausente e formato; queda para o texto padrão em tempo esgotado, resposta sem JSON, sem chave, AI desligada e limite da sessão; leitura de anotação rejeitada quando diverge ou cita trecho inexistente; o caminho real da chamada (SDK simulado) usa o modelo da premissa; páginas 1 a 4 mostram o selo de AI com chave configurada.
- App verificado no navegador sem chave: seletor desabilitado, textos padrão com o motivo.
- Teste com a API real (chave do autor nos secrets do Streamlit): ver ocorrência abaixo; após a correção, textos escritos por AI confirmados pelo autor no app publicado.

**Ocorrência no primeiro teste com a API real**

- Com a chave configurada, a página 1 caiu no texto padrão com "falha na chamada: ValueError": a resposta não chegou como JSON utilizável. Causa mais provável: o Sonnet 5.5 usa raciocínio adaptativo com esforço alto por padrão, e o raciocínio conta no limite de tamanho da resposta (1.500 tokens); o texto final pode ter vindo vazio ou cortado. O motivo exato não aparecia, porque a mensagem de erro só mostrava o tipo.
- Correção, seguindo a documentação da Anthropic: esforço baixo (`output_config.effort = low`, nova premissa), raciocínio mínimo (`thinking: between_tools`), resposta obrigada a seguir o esquema JSON de cada tarefa (`output_config.format`, saídas estruturadas) e limite de 4.000 tokens. O selo passa a mostrar o detalhe da falha (tipo, mensagem e motivo de parada), para diagnóstico direto na tela.

**Status:** concluída e aprovada pelo autor (AI funcionando com a API real no app publicado).

---

## Fase 6 — Testes, README e publicação final

**Objetivo:** fechar o protótipo para a apresentação: foco no que prova o ponto, roteiro para quem avalia, testes de ponta a ponta e documentação final.

**Decisões validadas antes da execução**

| Decisão | Escolha | Racional |
|---|---|---|
| Causa gestão | Retirada do protótipo e dos dados; o peso (~5,5% das pessoas) foi dividido entre remuneração (10% → 13%) e crescimento (8% → 10,5%), na proporção atual | Decisão do autor: é uma causa possível, mas não é necessária para provar o ponto e desviava o foco. Ela respondia por 27% dos casos, quase todos em 5 times, e alguns diretores recebiam 10 ou 11 mensagens quase iguais. Manter a fração total com causa preserva a calibração do turnover (~15%) |
| Lucía | Passa a ser um caso de crescimento com dois sinais; o roteiro mantém o papel dela (recomendação rejeitada): se o gestor dá um aumento em vez de carreira e projeto, ela sai | Mostra que dinheiro não resolve falta de perspectiva, e com números diferentes dos do Diego |
| Página inicial | Roteiro de navegação para quem avalia; o status das fases fica só no README | Quem abre o link é a Comp; o status é informação interna |
| README | Roteiro, ligação com as seções 4.1 a 4.3, cálculo dos números, limitações; também em .docx | Deixar claro o que o protótipo prova e o que não prova |
| Testes | Roteiro completo num navegador real; suíte em Python 3.12 (versão do Streamlit Cloud); varredura de segredos no histórico | Garantir que o que a Comp vai clicar funciona |
| Documento | Um documento só com mudanças e novidades em relação às seções 4.1, 4.2 e 4.3 | Pedido do autor |

**O que foi construído**

- Causa gestão retirada: sinais de time (troca de gestor, saídas no time, pulso sobre o gestor), tabela de pulso, intervenção "Escalar para a liderança", encaminhamento para a liderança acima, perguntas e textos ligados a ela. Os sinais de cada personagem passam a ser listados explicitamente em `data/personas.csv`.
- Semente da simulação revista (14): com as sementes 1 a 20, as saídas nos casos abertos variaram de 26 a 52 (média 41; o sistema esperava ~39); a 14 dá 40.
- Página inicial com roteiro; tabela de opções que quebra linha em telas menores; visão da liderança sem cortes em 1.280 px; números no padrão brasileiro.
- Teste de ponta a ponta no navegador (`tests/test_e2e_browser.py`).
- README final e versão .docx (`docs/README.docx`).

**Checagens**

- 40 checagens do mundo passando (163 casos abertos; causa provável igual à verdadeira em 92% dos casos).
- Testes: 52 passando em Python 3.13 (incluindo o navegador); 51 passando e 1 pulado (sem Playwright) em Python 3.12.
- Nenhuma chave no histórico do git.
- Capturas de tela das páginas em 1.440 e 1.280 px revisadas.

**Revisão pedida pelo autor após a aprovação**

| Ponto | Mudança | Racional |
|---|---|---|
| Previsão do gestor | Escala verbal de 4 respostas (quase certo que fica, provavelmente fica, provavelmente sai, quase certo que sai), convertida em 90%, 70%, 30% e 10% de chance de ficar (premissas `prediction.scale.*`); a resposta é obrigatória | Ninguém tem um percentual na cabeça. O binário "fica / não fica" esconderia o viés (a maioria fica, então "fica" acerta sem informação) e impediria somar previsões; a escala é o binário com um grau de confiança |
| Opções lado a lado | Colunas "Custo", "Perda que evita" e "Saldo" (saldo = perda que evita − custo, no tempo em que a pessoa deve ficar); para carreira e projeto, a perda que evita é o máximo que vale investir, também em horas do tempo do gestor (premissa `general.work_hours_per_year`) | "Compensa se custar até R$ X" não dizia com o que comparar o número |
| Custo de carreira e projeto nos totais | Explícito nas páginas 3 e 4: estimado em R$ 5 mil por caso (premissa `cost.growth`) | Para o gestor o custo é "você estima"; nos totais, o sistema usa a referência, e isso precisa estar dito |
| "Onde entra a AI" | Texto da página inicial e do README reescrito: a AI transforma texto em dado e escreve; o motor calcula e aprende com a rede, o cliente e cada gestor | Alinhado à discussão sobre o papel estrutural da AI |

Testes: 52 passando, incluindo a previsão obrigatória no formulário e no teste do navegador.

**Status:** concluída e aprovada pelo autor.

---

## Auditoria independente do código

O autor pediu a outros modelos uma auditoria do código, com um relatório de achados e um arquivo de testes que reproduz cada um. Os 15 achados se reproduziram; cada um foi avaliado e corrigido com aprovação do autor.

| Achado | Avaliação | Correção |
|---|---|---|
| Valor preservado com reposição média | Confirmado: saídas de quem ganha mais pesam mais | Soma caso a caso: (chance de sair sem ação − saiu ou não) × reposição da pessoa. Reposição evitada de R$ 4,0 para R$ 4,7 mi; valor preservado de ~R$ 2,2 para ~R$ 3,0 mi |
| Custo das intervenções no resultado | Parcial: o custo planejado é válido na decisão, não no resultado | Página 4 usa o custo pago (ajuste salarial só enquanto a pessoa ficou): R$ 1,7 mi, contra R$ 1,8 mi planejados |
| Casos sem quem decida | Confirmado: 3 diretores sem superior | Vão para o time de People (RH); a calibração cobre todos os casos |
| Aprendizado com dois critérios de causa | Confirmado | Agrupado pela causa do motor; a crença do gestor fica em `manager_cause` |
| Personagem sem decisão com previsão de 50% | Confirmado | Sem previsão; fora das saídas esperadas pelos gestores |
| Evidência de contexto repetida | Confirmado | Anotação filtrada pelo tipo de sinal e pela janela de contexto |
| Rótulo "/ano", turnover em períodos diferentes, textos fixos ("metade", "75%", "2 ou mais", "3 sinais", 365 dias) | Confirmados; só aparecem com premissas editadas | Custo anual em coluna própria; mesmo período antes e depois; textos derivados das premissas |
| Casos de borda: múltiplo de risco, "R$ 1000 mil", frase sobre gestão, "rede" no texto padrão, comentários de 6 meses | Confirmados | Corrigidos |
| Números por extenso na checagem da AI | Confirmado | Reconhecidos de dois a cem e checados como dígitos |
| AI trocar números verdadeiros entre si | Risco teórico, sem caso reproduzido | Registrado como limitação no README |
| Mapa por área e causa com células menores que o grupo mínimo | Parcial: a regra vale para times de pessoas; a contagem por área não identifica ninguém | Legenda corrigida para "times com menos de 5 pessoas" |
| Checagens que falham em 3 de 58 sementes | Variação estatística esperada | Registrado |

Os testes da auditoria entraram na suíte (`tests/test_auditoria.py`); três foram ajustados à correção escolhida. Suíte principal: 81 testes; testes demorados (outras sementes e todas as páginas com cada decisão): 37, com `pytest -m slow`. Todos passando.
