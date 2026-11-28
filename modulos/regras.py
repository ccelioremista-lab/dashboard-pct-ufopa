"""
modulos/regras.py
Motor de Regras e Verificador de Pendências ("Malha Fina do IR") — PC&T / UFOPA

Responsabilidades:
1. Auditar a oferta em tempo real contra todas as regras validadas pela Coordenação do PC&T:
   - IR-00: Choque de horários na mesma turma/período (prioridade absoluta)
   - IR-01 / IR-02: Consistência de turmas unificadas (sala única e deduplicação de CH)
   - IR-03: Choque de horário de docente
   - IR-04: Choque físico de sala/laboratório
   - IR-06 / IR-07: Sincronia de horário SIGAA e carga horária
   - IR-08: Turmas sem docente (CONCURSO / A definir) com sugestão de docentes habilitados
   - IR-09 / IR-10: Salas indefinidas e excesso de lotação (incluindo soma de turmas unificadas)
   - IR-11: Regra Segunda/Sexta para colaboradores externos (preferência Ter–Qui)
   - IR-12: Dependência de laboratórios externos críticos (Desenho / Informática)
   - IR-13 / IR-14: Piso (120h) e Teto (240h) de encargo docente efetivo
   - IR-15: Aderência ao credenciamento (PPCs + Histórico) com checagem estrita de níveis (I/II/III)
   - IR-16: Aderência às estruturas curriculares vigentes no SIGAA
2. Sugerir docentes habilitados priorizando efetivos com saldo suficiente até o teto regimental.
3. Aplicar edições vindas do Simulador Interativo com re-enriquecimento automático.
"""

from __future__ import annotations

import pandas as pd

from modulos.dados import (
    LAB_ROOMS,
    SALAS_INVENTARIO,
    consultar_componente_sigaa,
    enriquecer_oferta,
    expandir_horario_sigaa,
    extrair_dias_sigaa,
    norm,
)
from modulos.visualizacoes import calcular_encargo_docente

SEVERIDADE_ERRO = "🔴 ERRO IMPEDITIVO"
SEVERIDADE_AVISO = "🟡 AVISO"

_MAPA_NIVEL_DISC = {
    "i": "1",
    "1": "1",
    "ii": "2",
    "2": "2",
    "iii": "3",
    "3": "3",
    "iv": "4",
    "4": "4",
    "v": "5",
    "5": "5",
    "vi": "6",
    "6": "6",
}


def eh_sem_docente(valor: object) -> bool:
    """Identifica marcações padronizadas de turma sem docente alocado."""
    return norm(str(valor)) in ("", "concurso", "a definir", "nan", "none")


def eh_sem_sala(valor: object) -> bool:
    """Identifica marcações padronizadas de turma sem sala física definida."""
    return norm(str(valor)) in ("", "a definir", "nan", "none")


def _separar_base_nivel(texto: str) -> tuple[str, str]:
    tokens = norm(texto).split()
    if not tokens:
        return "", ""
    if len(tokens) > 1 and tokens[-1] in _MAPA_NIVEL_DISC:
        return " ".join(tokens[:-1]), _MAPA_NIVEL_DISC[tokens[-1]]
    return " ".join(tokens), ""


def disciplinas_compativeis(disc_a: str, disc_b: str) -> bool:
    """
    Compara nomes de disciplinas evitando falsos positivos entre níveis distintos
    (ex.: 'Cálculo I' não casa com 'Cálculo II', mas casa com 'Cálculo 1').
    """
    na, nb = norm(disc_a), norm(disc_b)
    if not na or not nb:
        return False
    if na == nb:
        return True

    base_a, niv_a = _separar_base_nivel(na)
    base_b, niv_b = _separar_base_nivel(nb)

    if niv_a and niv_b and niv_a != niv_b:
        return False
    if (niv_a and not niv_b and niv_a != "1") or (niv_b and not niv_a and niv_b != "1"):
        return False
    if base_a == base_b:
        return True
    return len(base_a) > 6 and len(base_b) > 6 and (base_a in base_b or base_b in base_a)


def sugerir_docentes_habilitados(
    disciplina: str,
    df_cred: pd.DataFrame,
    df_encargo: pd.DataFrame,
    teto_ch: int = 240,
    limite: int = 3,
    ch_turma: int = 0,
) -> list[str]:
    """
    Retorna até N docentes habilitados (PPC/Histórico), priorizando efetivos PC&T
    com saldo suficiente para absorver a turma sem ultrapassar o teto regimental.
    """
    if not norm(disciplina):
        return []

    habilitados = {
        r["Docente"]
        for _, r in df_cred.iterrows()
        if disciplinas_compativeis(disciplina, str(r["Componente Curricular Habilitado"]))
    }
    if not habilitados:
        return []

    cand = df_encargo[df_encargo["Docente"].isin(habilitados)].copy()
    if cand.empty:
        return []

    cand["_eh_efetivo"] = (cand["Vínculo"] == "PC&T (Permanente)").astype(int)
    cand["_saldo"] = teto_ch - cand["CH_Efetiva"]
    cand["_cabe_teto"] = (
        (cand["_eh_efetivo"] == 0) | (cand["_saldo"] >= max(0, int(ch_turma)))
    ).astype(int)

    cand = cand.sort_values(
        by=["_cabe_teto", "_eh_efetivo", "CH_Efetiva", "Docente"],
        ascending=[False, False, True, True],
    )

    sugestoes = []
    for _, row in cand.head(limite).iterrows():
        saldo = int(row["_saldo"])
        if row["Vínculo"] == "PC&T (Permanente)":
            alerta = " ⚠️ excede teto" if ch_turma > 0 and saldo < ch_turma else ""
            tag_saldo = f"saldo {saldo}h{alerta}"
        else:
            tag_saldo = "Colaborador"
        sugestoes.append(f"{row['Docente']} ({int(row['CH_Efetiva'])}h; {tag_saldo})")
    return sugestoes


def _docente_habilitado(docente: str, disciplina: str, mapa_hab: dict[str, list[str]]) -> bool:
    """Verifica se a disciplina consta na lista de habilitações (PPC + Histórico) do docente."""
    lista = mapa_hab.get(docente, [])
    if not lista:
        return False
    return any(disciplinas_compativeis(disciplina, h) for h in lista)


def executar_malha_fina_ir(
    df_oferta: pd.DataFrame,
    df_cred: pd.DataFrame,
    piso_ch: int = 120,
    teto_ch: int = 240,
) -> tuple[pd.DataFrame, pd.DataFrame, set[int], dict[str, int]]:
    """
    Executa a auditoria completa estilo 'Malha Fina do Imposto de Renda'.

    Retorna:
        df_pendencias: DataFrame ordenado com todas as pendências (Erros e Avisos).
        df_encargo: DataFrame consolidado de encargo docente efetivo.
        unif_secundarias: conjunto de índices de turmas unificadas secundárias.
        resumo_ir: dicionário com contadores rápidos para KPIs.
    """
    df_encargo, unif_secundarias = calcular_encargo_docente(
        df_oferta, df_cred, piso_ch=piso_ch, teto_ch=teto_ch
    )
    vinculo_map = df_cred.drop_duplicates("Docente").set_index("Docente")["Vínculo"].to_dict()

    mapa_hab: dict[str, list[str]] = {}
    for _, r in df_cred.iterrows():
        mapa_hab.setdefault(r["Docente"], []).append(str(r["Componente Curricular Habilitado"]))

    pendencias: list[dict[str, str]] = []
    idxs_unif_cap_checada: set[int] = set()

    # Monta tabela expandida de slots para detectar choques de turma, docente e sala
    slot_rows = []
    for idx, r in df_oferta.iterrows():
        slots = expandir_horario_sigaa(r["Horário_SIGAA"])
        fam = r.get("Família_Unificação", norm(r["Componente_Curricular"]))
        for sl in slots:
            slot_rows.append({
                "idx": idx,
                "Slot": sl,
                "Aba": str(r["Aba_Origem"]),
                "Codigo": str(r["Código_SIGAA"]),
                "Disciplina": str(r["Componente_Curricular"]),
                "Familia": fam,
                "Docente": str(r["Docente_Alocado"]).strip(),
                "Sala": str(r["Sala_Alocada"]).strip(),
                "CH": int(r["CH_Total"]),
                "Vagas": int(r["Vagas"]),
            })

    df_slots = (
        pd.DataFrame(slot_rows)
        if slot_rows
        else pd.DataFrame(
            columns=["idx", "Slot", "Aba", "Codigo", "Disciplina", "Familia", "Docente", "Sala", "CH", "Vagas"]
        )
    )

    if not df_slots.empty:
        # 1. IR-00: Choque na mesma turma / período (agrupa todos os slots em conflito)
        choques_coh: dict[tuple[str, tuple[int, ...]], dict] = {}
        for (aba, slot), grp in df_slots.groupby(["Aba", "Slot"]):
            if len(grp) > 1:
                idxs = tuple(sorted(grp["idx"].unique().tolist()))
                chave = (aba, idxs)
                if chave not in choques_coh:
                    choques_coh[chave] = {"slots": [], "grp": grp.drop_duplicates("idx")}
                choques_coh[chave]["slots"].append(slot)

        for (aba, _), info in choques_coh.items():
            slots_txt = ", ".join(sorted(set(info["slots"])))
            det = " vs ".join(
                f"{r['Disciplina']} ({r['Docente']})"
                for _, r in info["grp"].iterrows()
            )
            pendencias.append({
                "Severidade": SEVERIDADE_ERRO,
                "Código_Regra": "IR-00",
                "Eixo": "Choque de Turma/Período",
                "Alvo": f"[{aba}] {slots_txt}",
                "Descrição": f"Choque entre disciplinas do mesmo período/turma: {det}",
                "Ação_Recomendada": "Remanejar horário imediatamente (prioridade absoluta da Coordenação).",
            })

        # 2. IR-01 / IR-02 / IR-03: Choques de Docente vs Turmas Unificadas
        valid_doc = df_slots[~df_slots["Docente"].apply(eh_sem_docente)]
        conflitos_doc: dict[tuple[str, tuple[int, ...]], dict] = {}
        for (doc, slot), grp in valid_doc.groupby(["Docente", "Slot"]):
            if len(grp) > 1:
                idxs = tuple(sorted(grp["idx"].unique().tolist()))
                chave = (doc, idxs)
                if chave not in conflitos_doc:
                    conflitos_doc[chave] = {
                        "slots": [],
                        "grp": grp.drop_duplicates("idx"),
                        "mesma_fam": grp["Familia"].nunique() == 1,
                        "salas_distintas": grp["Sala"].nunique() > 1,
                    }
                conflitos_doc[chave]["slots"].append(slot)
                if grp["Sala"].nunique() > 1:
                    conflitos_doc[chave]["salas_distintas"] = True

        for (doc, _), info in conflitos_doc.items():
            slots_txt = ", ".join(sorted(set(info["slots"])))
            det = " + ".join(
                f"[{r['Aba']}] {r['Disciplina']} ({r['Sala']})"
                for _, r in info["grp"].iterrows()
            )
            if info["mesma_fam"]:
                if info["salas_distintas"]:
                    pendencias.append({
                        "Severidade": SEVERIDADE_ERRO,
                        "Código_Regra": "IR-01",
                        "Eixo": "Turma Unificada",
                        "Alvo": f"{doc} ({slots_txt})",
                        "Descrição": f"Turma unificável alocada em salas físicas diferentes: {det}",
                        "Ação_Recomendada": "Alinhar ambas na mesma sala (preferencialmente 206B-NSA se > 40 alunos).",
                    })
                else:
                    pendencias.append({
                        "Severidade": SEVERIDADE_AVISO,
                        "Código_Regra": "IR-02",
                        "Eixo": "Turma Unificada",
                        "Alvo": f"{doc} ({slots_txt})",
                        "Descrição": f"Turma unificada confirmada (CH contabilizada 1x): {det}",
                        "Ação_Recomendada": "Confirmar vinculação das turmas no lançamento do SIGAA.",
                    })
            else:
                pendencias.append({
                    "Severidade": SEVERIDADE_ERRO,
                    "Código_Regra": "IR-03",
                    "Eixo": "Choque de Docente",
                    "Alvo": f"{doc} ({slots_txt})",
                    "Descrição": f"Docente alocado em duas disciplinas distintas no mesmo horário: {det}",
                    "Ação_Recomendada": "Alterar o horário de uma das turmas ou realocar docente no Simulador.",
                })

        # 3. IR-04 (Choque físico de sala) e IR-10 combinado para turmas unificadas
        valid_sala = df_slots[~df_slots["Sala"].apply(eh_sem_sala)]
        choques_sala: dict[tuple[str, tuple[int, ...]], dict] = {}
        unif_na_sala: dict[tuple[str, tuple[int, ...]], dict] = {}

        for (sala, slot), grp in valid_sala.groupby(["Sala", "Slot"]):
            if len(grp) > 1:
                idxs = tuple(sorted(grp["idx"].unique().tolist()))
                chave = (sala, idxs)
                if grp["Docente"].nunique() == 1 and grp["Familia"].nunique() == 1:
                    if chave not in unif_na_sala:
                        unif_na_sala[chave] = {"slots": [], "grp": grp.drop_duplicates("idx")}
                    unif_na_sala[chave]["slots"].append(slot)
                else:
                    if chave not in choques_sala:
                        choques_sala[chave] = {"slots": [], "grp": grp.drop_duplicates("idx")}
                    choques_sala[chave]["slots"].append(slot)

        for (sala, _), info in choques_sala.items():
            slots_txt = ", ".join(sorted(set(info["slots"])))
            det = " vs ".join(
                f"[{r['Aba']}] {r['Disciplina']} ({r['Docente']})"
                for _, r in info["grp"].iterrows()
            )
            pendencias.append({
                "Severidade": SEVERIDADE_ERRO,
                "Código_Regra": "IR-04",
                "Eixo": "Choque Físico de Sala",
                "Alvo": f"{sala} ({slots_txt})",
                "Descrição": f"Sobreposição física de espaço no mesmo horário: {det}",
                "Ação_Recomendada": "Mover uma das turmas para sala livre do PC&T (ex.: 209B-NSA) ou outro horário.",
            })

        # Checagem de capacidade somada (IR-10) para turmas unificadas na mesma sala
        for (sala, idxs), info in unif_na_sala.items():
            idxs_unif_cap_checada.update(idxs)
            sinfo = SALAS_INVENTARIO.get(sala, {"Gestao": "Externa", "Capacidade": 40, "Gargalo": "Sim"})
            vagas_soma = int(info["grp"]["Vagas"].sum())
            if sinfo["Capacidade"] > 0 and vagas_soma > sinfo["Capacidade"] and sala not in LAB_ROOMS:
                det_u = " + ".join(
                    f"[{r['Aba']}] {r['Disciplina']} ({int(r['Vagas'])}v)"
                    for _, r in info["grp"].iterrows()
                )
                pendencias.append({
                    "Severidade": SEVERIDADE_AVISO,
                    "Código_Regra": "IR-10",
                    "Eixo": "Capacidade de Sala",
                    "Alvo": f"{sala} — Turma Unificada",
                    "Descrição": f"Soma de {vagas_soma} vagas ({det_u}) excede a capacidade oficial de {sinfo['Capacidade']} lugares.",
                    "Ação_Recomendada": "Realocar o grupo unificado para 206B-NSA (55 lug.) ou ajustar vagas no SIGAA.",
                })

    # 4. Auditoria linha a linha (IR-06 a IR-12, IR-15 e IR-16)
    for idx, r in df_oferta.iterrows():
        alvo = f"[{r['Aba_Origem']}] {r['Código_SIGAA']} - {r['Componente_Curricular']}"
        slots = expandir_horario_sigaa(r["Horário_SIGAA"])
        ch_total = int(r["CH_Total"])
        vagas = int(r["Vagas"])
        doc = str(r["Docente_Alocado"]).strip()
        sala = str(r["Sala_Alocada"]).strip()

        # IR-16: Aderência às Estruturas Curriculares Vigentes no SIGAA (BICT24, EMEC21, EFIS17, EFIS23)
        info_sigaa = consultar_componente_sigaa(r["Código_SIGAA"], r["Componente_Curricular"], r.get("Curso", ""))
        if not info_sigaa["vigente_sigaa"]:
            pendencias.append({
                "Severidade": SEVERIDADE_AVISO,
                "Código_Regra": "IR-16",
                "Eixo": "Estrutura Curricular SIGAA",
                "Alvo": alvo,
                "Descrição": f"Código '{r['Código_SIGAA']}' não localizado nas estruturas vigentes (BICT24, EMEC21, EFIS17, EFIS23).",
                "Ação_Recomendada": "Conferir código vigente no Portal do Coordenador SIGAA.",
            })
        elif info_sigaa["ch_sigaa"] > 0 and info_sigaa["ch_sigaa"] != ch_total:
            pendencias.append({
                "Severidade": SEVERIDADE_AVISO,
                "Código_Regra": "IR-16",
                "Eixo": "Estrutura Curricular SIGAA",
                "Alvo": alvo,
                "Descrição": f"CH da oferta ({ch_total}h) difere da CH oficial na matriz {info_sigaa['matrizes']} ({info_sigaa['ch_sigaa']}h).",
                "Ação_Recomendada": f"Ajustar CH para {info_sigaa['ch_sigaa']}h conforme estrutura curricular do SIGAA.",
            })

        # IR-06 / IR-07: Horário e CH
        if len(slots) == 0:
            pendencias.append({
                "Severidade": SEVERIDADE_ERRO,
                "Código_Regra": "IR-06",
                "Eixo": "Sincronia Grade × Tabela",
                "Alvo": alvo,
                "Descrição": f"Componente na tabela ({ch_total}h, {doc}) sem horário definido na grade.",
                "Ação_Recomendada": "Definir código de horário SIGAA (ex.: 24M12) no Simulador.",
            })
        elif len(slots) * 15 != ch_total:
            pendencias.append({
                "Severidade": SEVERIDADE_AVISO,
                "Código_Regra": "IR-07",
                "Eixo": "Consistência de CH",
                "Alvo": alvo,
                "Descrição": f"CH da tabela ({ch_total}h) difere dos blocos horários ({len(slots) * 15}h em {r['Horário_SIGAA']}).",
                "Ação_Recomendada": "Confirmar se é turma condensada/intensiva ou corrigir o código SIGAA.",
            })

        # IR-08: Sem Docente
        if eh_sem_docente(doc):
            sugs = sugerir_docentes_habilitados(
                r["Componente_Curricular"], df_cred, df_encargo, teto_ch=teto_ch, ch_turma=ch_total
            )
            txt_sug = "Sugestões habilitadas: " + " | ".join(sugs) if sugs else "Definir docente no Colegiado do PC&T."
            pendencias.append({
                "Severidade": SEVERIDADE_ERRO,
                "Código_Regra": "IR-08",
                "Eixo": "Alocação Docente",
                "Alvo": alvo,
                "Descrição": f"Turma de {ch_total}h ainda marcada como '{doc}'.",
                "Ação_Recomendada": txt_sug,
            })
        else:
            # IR-15: Aderência ao credenciamento (para efetivos PC&T)
            if vinculo_map.get(doc) == "PC&T (Permanente)" and not _docente_habilitado(
                doc, r["Componente_Curricular"], mapa_hab
            ):
                pendencias.append({
                    "Severidade": SEVERIDADE_AVISO,
                    "Código_Regra": "IR-15",
                    "Eixo": "Credenciamento Docente",
                    "Alvo": f"{doc} — {alvo}",
                    "Descrição": "Componente não consta ainda na matriz PPC/Histórico cadastrada para este docente.",
                    "Ação_Recomendada": "Confirmar decisão do Colegiado ou atualizar a matriz de credenciamento.",
                })

            # IR-11: Colaborador externo na Segunda ou Sexta
            if vinculo_map.get(doc) == "Colaborador Externo":
                dias = extrair_dias_sigaa(r["Horário_SIGAA"])
                viol = [nome for cod, nome in [("2", "Segunda"), ("6", "Sexta")] if cod in dias]
                if viol:
                    pendencias.append({
                        "Severidade": SEVERIDADE_AVISO,
                        "Código_Regra": "IR-11",
                        "Eixo": "Colaborador Externo",
                        "Alvo": f"{doc} [{r['Aba_Origem']}]",
                        "Descrição": f"{r['Componente_Curricular']} ({r['Horário_SIGAA']}) cai em {'/'.join(viol)}.",
                        "Ação_Recomendada": "Preferir Terça a Quinta-feira para evitar recusa do colaborador.",
                    })

        # IR-09 / IR-10 / IR-12: Salas, lotação e gargalos de laboratório
        sinfo = SALAS_INVENTARIO.get(sala, {"Gestao": "Externa", "Capacidade": 40, "Gargalo": "Sim"})
        if eh_sem_sala(sala):
            pendencias.append({
                "Severidade": SEVERIDADE_ERRO,
                "Código_Regra": "IR-09",
                "Eixo": "Espaço Físico / Salas",
                "Alvo": alvo,
                "Descrição": f"Turma ({vagas} vagas, horário {r['Horário_SIGAA']}) está sem sala definida.",
                "Ação_Recomendada": "Alocar em sala livre do PC&T (206B=55; 203B/207B/208B/209B=40).",
            })
        elif (
            idx not in idxs_unif_cap_checada
            and sinfo["Capacidade"] > 0
            and vagas > sinfo["Capacidade"]
            and sala not in LAB_ROOMS
        ):
            pendencias.append({
                "Severidade": SEVERIDADE_AVISO,
                "Código_Regra": "IR-10",
                "Eixo": "Capacidade de Sala",
                "Alvo": f"{sala} — {alvo}",
                "Descrição": f"{vagas} vagas excedem a capacidade oficial de {sinfo['Capacidade']} lugares.",
                "Ação_Recomendada": "Realocar para 206B-NSA (55 lug.) ou ajustar vagas para 40 no SIGAA.",
            })

        if sinfo.get("Gargalo") == "CRÍTICO" and not eh_sem_sala(sala):
            pendencias.append({
                "Severidade": SEVERIDADE_AVISO,
                "Código_Regra": "IR-12",
                "Eixo": "Gargalo de Laboratório",
                "Alvo": f"{sala} [{r['Aba_Origem']}]",
                "Descrição": f"{r['Componente_Curricular']} ({r['Horário_SIGAA']}) depende de agenda externa crítica.",
                "Ação_Recomendada": "Confirmar reserva antecipadamente com a unidade gestora do laboratório.",
            })

    # 5. IR-13 / IR-14: Piso e Teto de Carga Horária dos 19 Efetivos PC&T
    efetivos_df = df_encargo[df_encargo["Vínculo"] == "PC&T (Permanente)"]
    for _, erow in efetivos_df.iterrows():
        ch_ef = int(erow["CH_Efetiva"])
        doc = erow["Docente"]
        if ch_ef < piso_ch:
            pendencias.append({
                "Severidade": SEVERIDADE_AVISO,
                "Código_Regra": "IR-13",
                "Eixo": "Encargo Docente (Piso)",
                "Alvo": doc,
                "Descrição": f"Encargo efetivo na graduação é de {ch_ef}h (piso mínimo = {piso_ch}h; até 60h podem vir da Pós).",
                "Ação_Recomendada": "Confirmar horas na pós-graduação/afastamento ou alocar turma pendente.",
            })
        elif ch_ef > teto_ch:
            pendencias.append({
                "Severidade": SEVERIDADE_ERRO,
                "Código_Regra": "IR-14",
                "Eixo": "Encargo Docente (Teto)",
                "Alvo": doc,
                "Descrição": f"Sobrecarga de {ch_ef}h efetivas na graduação (acima do teto de {teto_ch}h).",
                "Ação_Recomendada": "Redistribuir uma turma para colega habilitado com saldo disponível.",
            })

    colunas_ir = ["Severidade", "Código_Regra", "Eixo", "Alvo", "Descrição", "Ação_Recomendada"]
    if pendencias:
        df_pendencias = (
            pd.DataFrame(pendencias)[colunas_ir]
            .sort_values(by=["Severidade", "Código_Regra", "Alvo"])
            .reset_index(drop=True)
        )
    else:
        df_pendencias = pd.DataFrame(columns=colunas_ir)

    n_erros = int((df_pendencias["Severidade"] == SEVERIDADE_ERRO).sum()) if not df_pendencias.empty else 0
    n_avisos = int((df_pendencias["Severidade"] == SEVERIDADE_AVISO).sum()) if not df_pendencias.empty else 0

    resumo_ir = {
        "total": len(df_pendencias),
        "erros": n_erros,
        "avisos": n_avisos,
        "choques_turma": int((df_pendencias["Código_Regra"] == "IR-00").sum()) if not df_pendencias.empty else 0,
        "choques_docente": int((df_pendencias["Código_Regra"] == "IR-03").sum()) if not df_pendencias.empty else 0,
        "choques_sala": int((df_pendencias["Código_Regra"] == "IR-04").sum()) if not df_pendencias.empty else 0,
        "sem_docente": int((df_pendencias["Código_Regra"] == "IR-08").sum()) if not df_pendencias.empty else 0,
        "sem_sala": int((df_pendencias["Código_Regra"] == "IR-09").sum()) if not df_pendencias.empty else 0,
    }

    return df_pendencias, df_encargo, unif_secundarias, resumo_ir


def estilizar_malha_fina(df_pendencias: pd.DataFrame):
    """Destaca visualmente Erros Impeditivos (vermelho) e Avisos (âmbar) na tabela IR."""
    def _cor_sev(val):
        s = str(val)
        if "ERRO" in s:
            return "background-color: #FEE2E2; color: #991B1B; font-weight: 700;"
        return "background-color: #FEF3C7; color: #92400E; font-weight: 700;"

    styler = df_pendencias.style
    if hasattr(styler, "map"):
        return styler.map(_cor_sev, subset=["Severidade"])
    return styler.applymap(_cor_sev, subset=["Severidade"])


def aplicar_edicoes_oferta(df_base: pd.DataFrame, df_editado: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """
    Aplica as alterações feitas no st.data_editor sobre o DataFrame completo da oferta
    e reexecuta o enriquecimento de metadados (capacidade, gestão, slots).
    Retorna (df_atualizado, qtd_linhas_alteradas).
    """
    df_novo = df_base.copy()
    campos_editaveis = ["Docente_Alocado", "Sala_Alocada", "Horário_SIGAA", "Vagas"]
    alteradas = 0

    for idx, row in df_editado.iterrows():
        if idx not in df_novo.index:
            continue
        mudou = False
        for campo in campos_editaveis:
            if campo not in df_editado.columns:
                continue
            val_orig = df_novo.loc[idx, campo]
            val_novo = row[campo]

            if campo == "Vagas":
                val_orig_cmp = int(val_orig)
                val_novo_cmp = int(val_novo)
            elif campo == "Horário_SIGAA":
                val_orig_cmp = str(val_orig).strip().upper()
                val_novo_cmp = str(val_novo).strip().upper()
            else:
                val_orig_cmp = str(val_orig).strip()
                val_novo_cmp = str(val_novo).strip()

            if val_orig_cmp != val_novo_cmp:
                df_novo.loc[idx, campo] = val_novo_cmp
                mudou = True
        if mudou:
            alteradas += 1

    return enriquecer_oferta(df_novo), alteradas