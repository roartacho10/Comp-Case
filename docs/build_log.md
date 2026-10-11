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
