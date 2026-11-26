# Dashboard de Oferta e Credenciamento Docente — PC&T / IEG / UFOPA

Sistema interativo em Python + Streamlit desenvolvido para automatizar a conferência semestral de ofertas, o equilíbrio de encargos docentes (PIT), o uso otimizado das 5 salas próprias do PC&T no NSA e a exportação sincronizada para o IEG/SIGAA.

---

## 1. Estrutura do Projeto (`dashboard_pct_ufopa/`)

* `Iniciar_Dashboard_PCT.bat` — Atalho em 1 clique (Windows) que ativa o ambiente `pct_dash`, limpa o cache do Python e abre o painel no navegador.
* `app.py` — Aplicação principal Streamlit (8 abas operacionais).
* `requirements.txt` — Dependências Python (`streamlit`, `pandas`, `openpyxl`, `plotly`, `ortools`, `langchain-groq`, `langchain-core`).
* `dados/` — Base consolidada oficial (`Sistema_Oferta_Credenciamento_PCT_2027_1-v6.xlsx`).
* `modulos/`
  * `dados.py` — Normalização, inventário de salas/laboratórios e as **4 estruturas curriculares vigentes no SIGAA** (`BICT24`, `EMEC21`, `EFIS17`, `EFIS23` — 345 componentes).
  * `visualizacoes.py` — Cálculo de encargo efetivo com deduplicação de turmas unificadas, gráficos Plotly e grade semanal das 5 salas.
  * `regras.py` — Motor da **Malha Fina IR (`IR-00` a `IR-16`)** e aplicação em memória das edições do Simulador.
  * `otimizador.py` — Solver matemático **Google OR-Tools (CP-SAT)** para zerar choques e maximizar o uso das salas próprias.
  * `exportador.py` — Geração do pacote Excel oficial para entrega ao IEG/SIGAA (até 16 abas com grades semanais sincronizadas).
  * `agente_ia.py` — Assistente da Coordenação (Modo Local offline ou Llama 3.3 70B via chave gratuita da Groq).
* `backups/` — Versões anteriores preservadas fora da pasta ativa para evitar conflitos de sincronização no Google Drive.

---

## 2. Como Abrir o Painel

### Opção A — Em 1 clique (recomendada)
1. Dê duplo clique em **`Iniciar_Dashboard_PCT.bat`** na pasta `dashboard_pct_ufopa/`.
2. Aguarde o navegador abrir em **`http://localhost:8501`**.

### Opção B — Via terminal (VS Code ou Miniconda Prompt)
```powershell
conda activate pct_dash
streamlit run app.py
```

> **Dica (Google Drive):** Se o navegador não refletir uma atualização recente da planilha ou dos módulos, encerre o servidor com `Ctrl + C` e rode novamente o `Iniciar_Dashboard_PCT.bat` (ele limpa `modulos/__pycache__` automaticamente).

---

## 3. Fluxo Semestral Recomendado para a Coordenação

1. **Carregar a planilha do semestre:** o painel abre automaticamente a base padrão da pasta `dados/` (`v6`). Para testar outra versão, basta arrastar o `.xlsx` para o campo **Upload** na barra lateral esquerda.
2. **Diagnosticar na Malha Fina (`🧾 Verificador IR`):** revisar os itens em vermelho (**🔴 ERRO IMPEDITIVO**, que bloqueiam o lançamento limpo no SIGAA) e em âmbar (**🟡 AVISO**, pontos de conferência do Colegiado).
3. **Resolver automaticamente (`🤖 Otimizador (OR-Tools)`):**
   * Marque ou desmarque a alocação automática de docentes pendentes conforme a pauta do Colegiado.
   * Clique em **🚀 Otimizar Grade Agora**, revise o log **Antes → Depois** e clique em **✅ Aplicar Solução Otimizada em Todo o Dashboard**.
4. **Fazer ajustes finos (`✏️ Simulador`):** ajuste qualquer docente, sala, horário SIGAA ou número de vagas diretamente na tabela e clique em **💾 Aplicar Alterações e Revalidar Malha Fina**. *(O arquivo original na pasta `dados/` nunca é sobrescrito; use **🔄 Restaurar Planilha Original** na barra lateral para desfazer testes.)*
5. **Conferir PIT e Salas (`📊 Encargo & PIT` e `🏫 5 Salas PC&T`):** valide o piso (120h), o teto (240h), a deduplicação de unificadas e o mapa semanal sem choques das 5 salas próprias (`206B` = 55 lug.; `203B`, `207B`, `208B`, `209B` = 40 lug.).
6. **Exportar entrega oficial (`📥 Exportar IEG (.xlsx)`):** gere e baixe o arquivo `.xlsx` pronto para encaminhamento ao IEG e lançamento no SIGAA.

---

## 4. Referência Rápida da Malha Fina IR

| Regra | Severidade | O que verifica |
| :--- | :--- | :--- |
| `IR-00` | 🔴 Erro Impeditivo | Choque de horários entre disciplinas do mesmo curso/período. |
| `IR-01` | 🔴 Erro Impeditivo | Turma unificável alocada em salas físicas diferentes. |
| `IR-02` | 🟡 Aviso | Turma unificada confirmada (CH contabilizada apenas 1x no PIT). |
| `IR-03` | 🔴 Erro Impeditivo | Choque de horário de docente em disciplinas distintas. |
| `IR-04` | 🔴 Erro Impeditivo | Sobreposição física de sala ou laboratório no mesmo horário. |
| `IR-06` | 🔴 Erro Impeditivo | Componente listado na oferta sem horário definido na grade. |
| `IR-07` | 🟡 Aviso | Divergência entre CH da tabela e quantidade de blocos SIGAA (turmas condensadas/modulares). |
| `IR-08` | 🔴 Erro Impeditivo | Turma sem docente (`CONCURSO` ou `A definir`), com sugestão automática por saldo. |
| `IR-09` | 🔴 Erro Impeditivo | Turma com sala `A DEFINIR`. |
| `IR-10` | 🟡 Aviso | Número de vagas superior à capacidade oficial da sala. |
| `IR-11` | 🟡 Aviso | Colaborador externo alocado na Segunda ou Sexta-feira (preferência Ter–Qui). |
| `IR-12` | 🟡 Aviso | Dependência de laboratório externo crítico (Informática / Desenho). |
| `IR-13` | 🟡 Aviso | Docente efetivo abaixo do piso de 120h na graduação (checar Pós/afastamento). |
| `IR-14` | 🔴 Erro Impeditivo | Docente efetivo acima do teto regimental de 240h na graduação. |
| `IR-15` | 🟡 Aviso | Componente ainda não cadastrado na matriz de credenciamento do docente. |
| `IR-16` | 🟡 Aviso | Código ou CH divergente das 4 estruturas curriculares vigentes no SIGAA. |
