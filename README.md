# Retenção com aprendizado — protótipo

Protótipo construído para o case *Forward Deployed* da Comp. É um sistema que identifica onde a empresa corre maior risco de perder valor por turnover voluntário evitável, leva ao gestor o contexto e a ação com maior retorno esperado, e aprende com o resultado de cada decisão. O ciclo demonstrado é **sinal → caso → intervenção → resultado → aprendizado**.

> **Dados sintéticos e ilustrativos.** Todos os dados são gerados por regras explícitas de causa e efeito, com semente fixa. Não representam pessoas, empresas ou resultados reais. Ilustram o mecanismo, não provam o resultado.

**App publicado:** https://comp-case-whvmhuagjmfytrjxadlqsx.streamlit.app/

## Como navegar

1. **Caso do gestor.** Escolha uma das três pessoas e leia a mensagem que o gestor recebe no Slack (simulado): o que chamou atenção, o motivo mais provável, o que os dados sugerem e as opções lado a lado. Registre a decisão e a sua previsão.
2. **Avançar 12 meses**, na barra lateral. O sistema simula o que acontece depois das decisões, nos três casos e em todos os outros casos abertos da empresa.
3. **Retorno e aprendizado.** O retorno para cada gestor, as previsões comparadas com o resultado e o que o sistema aprendeu.
4. **Visão da liderança.** Onde está o risco, quanto valor está em jogo e o que está sendo feito, sem nomes.
5. **Resultado em 12 meses.** Saídas evitadas, valor preservado e quanto cada real investido retornou.

| Pessoa | Situação | O que observar |
|---|---|---|
| Mariana Costa · Engenharia | Salário abaixo do mercado, sem aumento há dois anos, propostas de fora | Como o sistema compara o custo do ajuste com o custo de perder a pessoa |
| Diego Ramírez · Produto | Muito tempo sem promoção, projeto encerrado, perto de um marco de tempo de casa | Uma boa decisão nem sempre garante um bom resultado |
| Lucía Fernández · Customer Success | Muito tempo sem promoção e um pedido de crescimento sem plano | Divergir da sugestão exige uma justificativa, que entra no aprendizado |

A página **Como os dados foram gerados** mostra as premissas, as checagens e as tabelas. A página `/bastidores` (fora do menu) mostra o motor de regras sem interface final.

## O que o protótipo mostra, ligado ao documento

- **Seção 4.1 (a solução):** o ciclo contínuo disparado por sinais, e não pelo calendário; a intervenção escolhida pela causa do risco; o gestor decide e registra a previsão antes de agir; o resultado ajusta as recomendações e mede a calibração de quem decide.
- **Seção 4.2 (os fluxos):** caso do gestor, retorno e aprendizado e visão da liderança, mais uma página com o resultado em 12 meses.
- **Seção 4.3 (a construção):** feita em fases, com validação antes de cada uma; histórico em [`docs/build_log.md`](docs/build_log.md).

## Como os números são calculados

O motor de regras (sem AI) lê só o que o sistema enxerga: os dados brutos do cliente e a rede de casos fechados da Comp.

- **Caso:** abre com 2 ou mais sinais da mesma causa. A causa provável é a que tem mais sinais; em empate, as duas aparecem e a decisão fica com o gestor.
- **Risco:** a taxa de saída em 12 meses, na rede, de casos com a mesma causa e o mesmo número de sinais em que nada foi feito.
- **Valor de cada opção:** o que a empresa economiza evitando a saída (reposição e substituto contratado a valor de mercado), menos o custo da opção, no tempo em que a pessoa ainda deve ficar (até 5 anos). O efeito de ações pontuais dura 12 meses; o do ajuste salarial dura enquanto ele é pago.
- **Sugestão:** a opção de maior valor, se for positivo; senão, monitorar. Para ações cujo custo o gestor conhece melhor (carreira e projeto), o sistema mostra a perda que a ação evita, que é o máximo que vale investir, também em horas do tempo do gestor. Nos totais, essas ações entram com um custo de referência de R$ 5 mil por caso.
- **Resultado:** a simulação aplica as mesmas regras do mundo aos 12 meses seguintes. Os três personagens seguem um roteiro por decisão.
- **Previsão do gestor:** uma frase, e não um percentual (quase certo que fica, provavelmente fica, provavelmente sai, quase certo que sai), convertida em chance de ficar pela escala das premissas.
- **Aprendizado:** as taxas de permanência por causa e intervenção são recalculadas com os casos novos, e as previsões de cada gestor são comparadas com o que aconteceu.

## Onde entra a AI

A AI (Claude, pela API da Anthropic, chamada pelo servidor do app) faz o que regras não conseguem: transforma texto solto em dado e escreve para quem decide.

- Lê anotações de conversas de carreira e atas de projeto e identifica sinais (proposta externa, pedido de crescimento sem plano). Sem ela, esses sinais não existiriam.
- Escreve cada caso no contexto do gestor, com perguntas adaptadas à pessoa, o retorno depois de 12 meses e os resumos para a liderança. Isso reduz o esforço de decidir e registrar, e sem decisão registrada não há aprendizado.

O cálculo fica num motor de regras transparente. Risco, valor de cada opção e recomendação vêm das taxas observadas na rede da Comp e são reestimados a cada caso fechado: na rede, no cliente e na calibração de cada gestor. Assim os números são auditáveis e a vantagem está nos dados e no aprendizado, não no modelo de AI, que qualquer concorrente pode usar. Numa versão completa, a AI também leria as justificativas de quem diverge da sugestão e as entrevistas de desligamento, para confirmar ou corrigir a causa atribuída.

A AI recebe só os fatos já calculados pelo motor. Antes de aparecer, cada texto passa por quatro checagens: formato, **todo número do texto existe nos fatos recebidos**, nenhum termo vetado (rótulos, tom de comando, jargão) e a frase "a decisão é sua" na mensagem do caso. Se falhar, se não houver chave ou se a chamada demorar, a tela usa o texto padrão revisado e diz o motivo. As regras estão em [`prompts/`](prompts/). Os textos aprovados ficam guardados no servidor, e cada sessão tem um limite de chamadas.

Para ativar, coloque a chave nos secrets do Streamlit (`ANTHROPIC_API_KEY = "..."`). Nunca no código.

## Premissas determinísticas

Toda regra do mundo sintético está em uma base editável, e nenhum número de regra fica no código:

- [`data/assumptions.csv`](data/assumptions.csv): uma premissa por linha, com o que ela é, o valor, a unidade, o racional do valor e a origem (case, documento ou premissa assumida).
- [`data/signals.csv`](data/signals.csv) e [`data/interventions.csv`](data/interventions.csv): catálogos de sinais (causa e fonte) e de intervenções (causa que atacam e regra de custo).
- [`data/personas.csv`](data/personas.csv), [`data/persona_outcomes.csv`](data/persona_outcomes.csv) e [`data/questions.csv`](data/questions.csv): os três personagens, o roteiro de cada um por decisão e as perguntas de conversa.

Os dados em `data/generated/` são **derivados** dessas tabelas e não são editados à mão: mudou a premissa, rode `scripts/generate_data.py`. Quarenta checagens comparam os dados gerados com as premissas, e um teste garante que o retrato commitado é exatamente o que as premissas atuais geram. A verdade oculta (causa de cada pessoa) fica em `data/hidden/`, visível para auditoria, mas lida só pelo gerador, pela simulação e pelas checagens; outro teste garante isso.

## Limitações e simplificações

- Dados, empresa, pessoas e rede da Comp são sintéticos. O resultado mostra o mecanismo, não prova o efeito.
- O Slack é uma imagem da conversa, sem integração; não há integração com HRIS.
- Duas causas tratáveis: remuneração e crescimento. Problemas na relação com a gestão são uma causa possível na solução, mas ficaram fora do protótipo.
- O aprendizado usa regras simples e transparentes, sem modelo treinado.
- A checagem de números garante que todo número citado pela AI existe nos fatos recebidos, mas não que ele esteja associado ao indicador certo. O risco é baixo, porque cada mensagem trata de uma pessoa e a AI reescreve um texto padrão que já traz os números no lugar; a defesa completa seria a AI devolver o texto com marcadores e o sistema inserir os números.
- A visão do colaborador, as flags de priorização e a redução de dependência ficam descritas no documento, não construídas.

## Construção em fases

| Fase | Conteúdo | Status |
|---|---|---|
| 0 | Fundação: repositório, estrutura e publicação | Concluída |
| 1 | Mundo e dados sintéticos | Concluída |
| 2 | Personagens e motor de regras | Concluída |
| 3 | Fluxo 1: caso do gestor | Concluída |
| 4 | Fluxos 2 e 3 (aprendizado, liderança) e resultado | Concluída |
| 5 | Camada de AI | Concluída |
| 6 | Testes, README e publicação final | Concluída |

## Como rodar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
python scripts/generate_data.py   # regenera os CSVs a partir das premissas e roda as checagens
pytest                            # suíte principal; o teste no navegador roda se o Playwright estiver instalado
pytest -m slow                    # testes demorados: outras sementes do mundo e todas as páginas com cada decisão
```

## Estrutura

```
app.py            # configuração e navegação
app_pages/        # uma página por fluxo, página de dados e bastidores
data/             # premissas (editáveis), dados gerados e verdade oculta
prompts/          # regras da AI
scripts/          # geração dos dados
src/              # premissas, gerador, sinais, motor, simulação, AI e interface
tests/            # testes automatizados
docs/             # log de construção
```

Código em inglês; interface em português.
