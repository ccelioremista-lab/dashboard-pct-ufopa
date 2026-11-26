# Nota Técnica & Pauta de Validação — Oferta 2027.1 (v6 Otimizada)

**Programa:** Programa de Ciência e Tecnologia (PC&T / IEG / UFOPA)  
**Cursos abrangidos:** BI em Ciência e Tecnologia (`BICT24`), Engenharia Mecânica (`EMEC21`) e Engenharia Física (`EFIS17` / `EFIS23`)  
**Arquivo de referência:** `Pacote_Oficial_PCT_IEG_2027_1_Otimizado_v6.xlsx` (16 abas)  
**Base de entrada:** `dados/Sistema_Oferta_Credenciamento_PCT_2027_1-v6.xlsx`  

---

## 1. Resumo Executivo da Solução Otimizada (`v6`)

* **Total de turmas ofertadas:** 71 turmas (3.885h totais), já com 100% dos códigos e cargas horárias alinhados às 4 estruturas curriculares vigentes no SIGAA (**0 alertas `IR-16`**).
* **Erros Impeditivos (Malha Fina IR):** **0** (reduzidos de 44 para 0 pelo otimizador OR-Tools CP-SAT):
  * 0 choques na mesma turma/período (`IR-00`).
  * 0 choques de docente (`IR-03`).
  * 0 choques físicos de sala ou laboratório (`IR-04`).
  * 0 turmas sem docente (`IR-08`), sem sala (`IR-09`) ou sem horário (`IR-06`).
  * 0 docentes efetivos acima do teto regimental de 240h (`IR-14`).
* **Uso dos espaços físicos (71 turmas):**
  * **48 turmas** nas 5 salas próprias do PC&T (`206B`, `203B`, `207B`, `208B`, `209B`) — com a `209B-NSA` plenamente integrada (11 turmas, 0 choques).
  * **15 turmas** em laboratórios específicos (incluindo os novos espaços dedicados cadastrados na `v6`: `Lab de Química Geral - BMT / IEG` e `Oficina Mecânica / Lab de Manufatura (PC&T)`).
  * Apenas **8 turmas** em salas externas da CAC/IEG (`105A-NSA` e `110B-NSA`).

---

## 2. Adequações Curriculares SIGAA Incorporadas (`v4` → `v6`)

* **Inclusões de obrigatórias vigentes (5 turmas):**
  * `1º BI` (`BICT24`): `SBCT0005` — Laboratório de Química Geral (30h) → `4T34` | `Lab de Química Geral - BMT / IEG` | *Cintya de Azambuja*.
  * `1º MEC` (`EMEC21`): `CTEC0003` — Laboratório de Química Geral (30h) → `5T34` | `Lab de Química Geral - BMT / IEG` | *Cintya de Azambuja*.
  * `3º MEC` (`EMEC21`): `EMEC0008` — Oficinas (30h) → `5T12` | `Oficina Mecânica / Lab de Manufatura (PC&T)` | *Thiago Augusto de Sousa Moreira*.
  * `3º MEC` (`EMEC21`): `PCT30037` — Métodos Matemáticos I (60h) → `4T1234` | `209B-NSA` | *Josecley Fialho Góes*.
  * `5º BI` (`EFIS23`/`EFIS17` obrig.; `BICT24` opt.): `PCT30029` — Laboratório de Mecânica dos Fluidos (30h) → `6T34` | `Lab de Fenômenos de Transporte` | *Lázaro João Santana da Silva*.
* **Correções de código, nomenclatura e transição curricular:**
  * `5º MEC`: `EFIS0036` (60h) substituído por `EMEC0018` — *Processo de Fabricação I* (45h); corrigido `EMEC019` → `EMEC0019`.
  * `7º MEC`: substituído código inexistente `EMEC0030` por `PCT30060` — *Eletrônica Básica* (60h).
  * `7º EF`: atualizado para `SFIS0006` — *Processamento Digital de Sinais* (60h, coorte regular `2024.1` na `EFIS23`).
  * `3º BI`, `5º BI`, `9º EF`: nomenclaturas oficializadas (`Conservação dos Recursos Ambientais`, `Ciências e Tecnologia dos Materiais`, `Tópicos Especiais em Engenharia Física III`).
  * `5º BI`: `PCT30051` — *Laboratório de Física IV* (30h) pré-alocada no `Lab Beta - Rondon` (`4T12`).

---

## 3. Pontos para Validação da Coordenação / Colegiado (28 Avisos Remanescentes)

Nenhum dos 28 avisos impede a geração da grade, mas **6 pontos objetivos** pedem confirmação final antes do envio definitivo ao IEG:

1. **Unificação com diferença de CH (`IR-07` — 1 caso) e turmas condensadas (`IR-07` — 3 casos):**
   * `5º MEC` (`EMEC0018`, 45h) e `7º EF` (`EFIS0036`, 60h) foram unificadas com *Thiago Moreira* em `4M123` (45h). Confirmar se `EFIS0036` terá 1 bloco adicional (`4M4`) ou complementação assíncrona para fechar 60h.
   * Confirmar se permanecem como horários condensados/modulares: `EMEC0028` (`7º MEC`, 75h em `35M345`), `EMEC0043` (`9º MEC`, 30h em `2M12345`) e `PCT30010` (`9º MEC`, 45h em `6M12345`).
2. **Aderência de credenciamento e piso de CH (`IR-13` e `IR-15` — 3 casos):**
   * *Alex Junior de Freitas Cabral* (60h) foi sugerido para `PCT30018` (*Mecânica dos Sólidos*, `5º BI`, antes `CONCURSO`) — confirmar no Colegiado e checar complementação de horas na pós-graduação/afastamento (assim como para *Anderson Alvarenga de Moura Meneses*, também com 60h na graduação).
   * Docentes no limite de 240h (`José Roberto`, `Nelson Amorim` e `Querem Hapuque`): todos dentro do teto regimental.
3. **Colaboradores externos em Segunda/Sexta (`IR-11` — 4 casos herdados dos horários originais):**
   * *Cintya de Azambuja* (`1º BI` Seg `24T12`; `1º MEC` Sex `6M1234`), *Cássio André* (`1º MEC` Seg `2M1234`) e *Elden Marialva* (`5º MEC` Seg `2M123`). Confirmar se os colaboradores mantêm esses horários originais ou se preferem remanejar para Terça–Quinta.
4. **Turmas de 50 vagas em salas de 40 lugares (`IR-10` — 10 casos):**
   * Definir se o teto de vagas no SIGAA será ajustado para 40 alunos nessas turmas ou se haverá rodízio para a sala `206B-NSA` (55 lugares).
5. **Reservas antecipadas de laboratórios externos críticos (`IR-12` — 5 casos):**
   * Solicitar reserva prévia junto às unidades gestoras para `Lab de Informática - Sala 145 BMT II` (`1º BI` `5T1234` e `1º MEC` `4M1234`), `Sala 229 BMT - Laboratório de Desenho` (`1º BI` `3M1234` e `1º MEC` `2T1234`) e `Sala de Informática` (`3º MEC` `6T123`), além do `Lab de Química Geral - BMT / IEG` (`4T34` e `5T34`).
6. **Transição `EFIS17` → `EFIS23`:**
   * Validar a equivalência de `SFIS0006` (60h) para eventuais veteranos da `EFIS17` (`EFIS0035`, 90h) no `7º EF`, e registrar que `EFIS0004` (90h) no `9º EF` migra para `SFIS0007` (60h) apenas em `2028.1`.
