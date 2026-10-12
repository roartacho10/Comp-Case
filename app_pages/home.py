import streamlit as st

from src.app_data import assumptions
from src.ui import synthetic_data_banner

synthetic_data_banner()
W = assumptions().int("outcome.window_months")

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
    "A AI lê a anotação da conversa de carreira e escreve as mensagens para quem decide, a partir dos números que o "
    "motor de regras já calculou. Ela não calcula nem decide. Cada texto passa por checagens antes de aparecer; o selo "
    "abaixo do texto indica se ele foi **✦ escrito por AI** ou se é o **texto padrão** revisado."
)

st.subheader("O que é simulado")
st.markdown(
    "Os dados são sintéticos, gerados por regras explícitas a partir de premissas editáveis (página **Como os dados "
    "foram gerados**). O Slack é uma imagem da conversa, sem integração. A rede da Comp (casos fechados em outros "
    "clientes) também é simulada. O protótipo ilustra o mecanismo; não prova o resultado."
)
