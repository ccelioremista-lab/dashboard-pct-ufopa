# 🎓 Dashboard de Oferta e Credenciamento Docente — PC&T / IEG / UFOPA

Aplicação web em **Python + Streamlit** para gestão anual de ofertas semestrais, auditoria curricular oficial no **SIGAA**, equilíbrio de encargos docentes (**PIT**), otimização matemática de salas/horários (**Google OR-Tools CP-SAT**) e exportação sincronizada para o **IEG / UFOPA**.

## Principais Recursos

* **Modo Anual Integrado:** alterna em 1 clique entre **2027.1 (Semestres Ímpares)** e **2027.2 (Semestres Pares)**, ou aceita upload de qualquer nova planilha `.xlsx`.
* **4 Estruturas Curriculares Oficiais do SIGAA (345 componentes):** `BICT24`, `EMEC21`, `EFIS17` e `EFIS23` integradas à busca e à validação automática (`IR-16`).
* **Verificador Malha Fina IR (`IR-00` a `IR-16`):** identifica automaticamente choques de turma, docente e sala, turmas unificadas, piso/teto de CH (`120h`–`240h`), regra Terça–Quinta para colaboradores externos, lotação e laboratórios críticos.
* **Otimizador Matemático (Google OR-Tools CP-SAT):** resolve choques, alinha turmas unificadas (inclusive com CH distintas), prioriza as **5 salas próprias do PC&T** (`206B`, `203B`, `207B`, `208B`, `209B`) e equilibra o encargo docente.
* **Simulador Interativo + Auditoria PIT + Exportador IEG (`.xlsx`):** permite edições ao vivo e gera a planilha oficial estilizada com abas executivas e grades semanais sincronizadas por período/curso.
* **Assistente IA da Coordenação:** funciona offline (Modo Local) ou com Llama 3.3 70B via `GROQ_API_KEY`.

## Execução Local

```bash
conda activate pct_dash
pip install -r requirements.txt
streamlit run app.py
```

## Publicação no Streamlit Community Cloud

Consulte o passo a passo completo em [`Guia_Publicacao_Streamlit_Cloud.md`](Guia_Publicacao_Streamlit_Cloud.md).
