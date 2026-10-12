Tarefa: escrever a mensagem de um caso para quem decide, no Slack.

O pacote traz os fatos do caso e um "texto_de_referencia" já aprovado. Reescreva com as suas palavras, mantendo todos os fatos e números, sem perder nenhuma informação da sugestão. Pode deixar mais natural e mais claro. Adapte as 3 perguntas de conversa ao contexto da pessoa (use as anotações do pacote), mantendo-as abertas, sem induzir resposta e sem mencionar números, riscos ou o sistema.

Formato da resposta (JSON):
{
  "intro": "saudação e motivo da mensagem, 1 a 2 frases",
  "signals": ["um item por sinal: rótulo em negrito com **, dois-pontos e a evidência em linguagem simples"],
  "risk": "o que aconteceu em casos parecidos, 1 a 2 frases",
  "cause": "o motivo mais provável e que vale confirmar na conversa, 1 a 2 frases",
  "suggestion": "o que os dados sugerem, com custo, comparação com o custo de perder a pessoa e saldo (ou até quanto compensa); deve conter a frase 'A decisão é sua'",
  "questions": ["pergunta 1", "pergunta 2", "pergunta 3"],
  "closing": "como registrar a decisão e quando volta o resultado, 1 frase"
}
Limite: cerca de 220 palavras no total.
