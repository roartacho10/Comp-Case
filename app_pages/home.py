import streamlit as st

from src.ui import synthetic_data_banner
from src.periods import OUTCOME_WINDOW_MONTHS

synthetic_data_banner()
W = OUTCOME_WINDOW_MONTHS

st.title("Retenção com aprendizado")
st.write(
    "Protótipo de um sistema que identifica onde a empresa corre maior risco de perder valor por turnover voluntário "
    "evitável, leva ao gestor o contexto e a ação com maior retorno esperado, e aprende com o resultado de cada decisão."
)
st.markdown("**Sinal → caso → intervenção → resultado → aprendizado**")

st.subheader("Como navegar")
st.markdown(
    f"""
1. **Caso do gestor.** Escolha uma das três pessoas e leia a mensagem que o gestor recebe: o que chamou atenção, o motivo
   mais provável, o que os dados sugerem e as opções lado a lado. Registre a decisão e a sua previsão.
2. **Avançar {W} meses**, na barra lateral. O sistema simula o que acontece depois das decisões, nos três casos e em
   todos os outros casos abertos da empresa.
3. **Retorno e aprendizado.** O retorno para cada gestor, as previsões comparadas com o resultado e o que o sistema
   aprendeu.
4. **Visão da liderança.** Onde está o risco, quanto valor está em jogo e o que está sendo feito, sem nomes.
5. **Resultado em {W} meses.** Saídas evitadas, valor preservado e quanto cada real investido retornou.

Para começar de novo, use **Reiniciar** na barra lateral.
"""
)

st.subheader("As três pessoas do roteiro")
st.markdown(
    """
| Pessoa | Situação | O que observar |
|---|---|---|
| Mariana Costa · Engenharia | Salário abaixo do mercado, sem aumento há dois anos, propostas de fora | Como o sistema compara o custo do ajuste com o custo de perder a pessoa |
| Diego Ramírez · Produto | Muito tempo sem promoção, projeto encerrado, perto de um marco de tempo de casa | Uma boa decisão nem sempre garante um bom resultado |
| Lucía Fernández · Customer Success | Muito tempo sem promoção e um pedido de crescimento sem plano | Experimente divergir da sugestão: a justificativa é registrada e entra no aprendizado |
"""
)

st.subheader("Onde entra a AI")
st.markdown(
    f"""
A AI faz o que regras não conseguem: transforma texto solto em dado e escreve para quem decide.

- Lê anotações de conversas de carreira e atas de projeto e identifica sinais (proposta externa, pedido de crescimento
  sem plano). Sem ela, esses sinais não existiriam.
- Escreve cada caso no contexto do gestor, com perguntas adaptadas à pessoa, e o retorno depois de {W} meses. Isso
  reduz o esforço de decidir e registrar, e sem decisão registrada não há aprendizado.

O cálculo fica num motor de regras transparente. Risco, valor de cada opção e recomendação vêm das taxas observadas
na rede da Comp e são reestimados a cada caso fechado: na rede, no cliente e na calibração de cada gestor. Assim os
números são auditáveis, nenhum texto cita um número que não existe, e a vantagem está nos dados e no aprendizado, não
no modelo de AI, que qualquer concorrente pode usar.

Numa versão completa, a AI também leria as justificativas de quem diverge da sugestão e as entrevistas de
desligamento, para confirmar ou corrigir a causa atribuída. O selo abaixo de cada texto indica se ele foi
**✦ escrito por AI** ou se é o **texto padrão** revisado.
"""
)

st.subheader("O que é simulado")
st.markdown(
    "Os dados são sintéticos, gerados por regras explícitas a partir de premissas editáveis (página **Como os dados "
    "foram gerados**). O Slack é uma imagem da conversa, sem integração. A rede da Comp (casos fechados em outros "
    "clientes) também é simulada. O protótipo ilustra o mecanismo; não prova o resultado."
)
