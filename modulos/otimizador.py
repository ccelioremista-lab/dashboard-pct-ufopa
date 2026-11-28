"""
modulos/otimizador.py
Motor de Otimização Automática com OR-Tools (CP-SAT) — PC&T / UFOPA

Responsabilidades:
1. Resolver automaticamente choques de turma (IR-00), docente (IR-03) e sala (IR-04).
2. Alinhar turmas unificadas na mesma sala física e mesmo horário (IR-01), suportando
   unificações de CH distinta (ex.: EMEC0018 45h em 4M123 + EFIS0036 60h em 4M1234)
   e validando a lotação somada do grupo.
3. Preencher horários ausentes (IR-06) e alocar todas as salas 'A DEFINIR' (IR-09),
   priorizando as 5 salas próprias do PC&T (206B=55; 203B, 207B, 208B, 209B=40)
   e minimizando a dependência de salas externas CAC/IEG (105A/110B).
4. Alocar docentes habilitados (PPC/Histórico, respeitando níveis I/II/III) às turmas
   sem docente (IR-08), respeitando o teto regimental (240h) e equilibrando o encargo.
5. Suportar faixas de CH de 15h a 120h, restrição condicional Terça–Quinta para
   colaboradores externos e normalização opcional de horários condensados (IR-07).
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from ortools.sat.python import cp_model

from modulos.dados import (
    LAB_ROOMS,
    SALAS_EXTERNAS_NSA,
    SALAS_INVENTARIO,
    SALAS_PCT,
    enriquecer_oferta,
    expandir_horario_sigaa,
    extrair_dias_sigaa,
    norm,
)
from modulos.regras import (
    disciplinas_compativeis,
    eh_sem_docente,
    eh_sem_sala,
    executar_malha_fina_ir,
)


def _compactar_slots_sigaa(slots: list[str]) -> str:
    """Compacta uma lista de slots individuais (ex.: ['4M1','4M2','4M3']) em código SIGAA ('4M123')."""
    if not slots:
        return "SEM HORÁRIO NA GRADE"

    por_dia_turno: dict[tuple[str, str], list[str]] = {}
    for sl in sorted(set(slots)):
        if len(sl) == 3:
            por_dia_turno.setdefault((sl[0], sl[1]), []).append(sl[2])

    # Agrupa dias que possuem exatamente o mesmo turno e sequência de horários
    por_turno_horas: dict[tuple[str, str], list[str]] = {}
    for (dia, turno), horas in sorted(por_dia_turno.items()):
        h_str = "".join(sorted(horas))
        por_turno_horas.setdefault((turno, h_str), []).append(dia)

    blocos = []
    for (turno, h_str), dias in sorted(
        por_turno_horas.items(), key=lambda x: ("".join(sorted(x[1])), x[0][0], x[0][1])
    ):
        blocos.append(f"{''.join(sorted(dias))}{turno}{h_str}")
    return " / ".join(blocos)


def _derivar_subhorario(horario_mestre: str, ch_membro: int, ch_max: int) -> str:
    """
    Para grupos unificados com CH distintas (ex.: 45h e 60h), deriva um sub-horário
    exato para o componente menor a partir dos primeiros slots do horário mestre.
    """
    if ch_membro >= ch_max:
        return horario_mestre
    slots_mestre = expandir_horario_sigaa(horario_mestre)
    qtd_alvo = max(1, int(ch_membro) // 15)
    if len(slots_mestre) <= qtd_alvo:
        return horario_mestre
    return _compactar_slots_sigaa(slots_mestre[:qtd_alvo])


def _gerar_horarios_candidatos(
    ch_total: int,
    horario_atual: str,
    incluir_horario_atual: bool = True,
    preferir_blocos_continuos: bool = False,
) -> list[str]:
    """Gera lista ordenada de códigos SIGAA candidatos compatíveis com a CH da turma (15h a 120h)."""
    base_por_ch = {
        15: [
            "3M1", "4M1", "5M1", "3T1", "4T1", "5T1",
            "2M1", "6M1", "2T1", "6T1",
        ],
        30: [
            "3M12", "4M12", "5M12", "3M34", "4M34", "5M34",
            "3T12", "4T12", "5T12", "3T34", "4T34", "5T34",
            "2M12", "6M12", "2M34", "6M34", "2T12", "6T12", "2T34", "6T34",
        ],
        45: [
            "3M123", "4M123", "5M123", "3T123", "4T123", "5T123",
            "3T234", "4T234", "5T234", "3M345", "4M345", "5M345",
            "2M123", "6M123", "2T123", "6T123",
        ],
        60: [
            "4M1234", "3M1234", "5M1234", "3T1234", "4T1234", "5T1234",
            "35M12", "35M34", "35T12", "35T34",
            "24M12", "24M34", "24T12", "24T34",
            "2M1234", "6M1234", "2T1234", "6T1234",
            "46M12", "46M34", "46T12", "46T34",
        ] if preferir_blocos_continuos else [
            "35M12", "35M34", "35T12", "35T34",
            "3M1234", "4M1234", "5M1234", "3T1234", "4T1234", "5T1234",
            "24M12", "24M34", "24T12", "24T34",
            "2M1234", "6M1234", "2T1234", "6T1234",
            "46M12", "46M34", "46T12", "46T34",
        ],
        75: [
            "35M12 / 5M3", "35M34 / 5M5", "35T12 / 5T3", "35T34 / 4T3",
            "4M12345", "3M12345", "5M12345",
            "24M12 / 4M3", "24M34 / 4M5", "24T12 / 4T3", "24T34 / 4T5",
        ],
        90: [
            "35M123", "35M345", "35T123", "35T345",
            "24M123", "24M345", "24T123", "24T345",
            "46M123", "46T123",
        ],
        120: [
            "35M1234", "35T1234", "24M1234", "24T1234",
            "2345M12", "2345M34", "2345T12", "2345T34",
            "3456M12", "3456M34", "3456T12", "3456T34",
            "46M1234", "46T1234",
        ],
    }

    candidatos: list[str] = []
    if (
        incluir_horario_atual
        and horario_atual
        and "SEM HORÁRIO" not in horario_atual.upper()
        and len(expandir_horario_sigaa(horario_atual)) > 0
    ):
        candidatos.append(horario_atual)

    padroes = list(base_por_ch.get(int(ch_total), base_por_ch[60]))
    if horario_atual and any("N" in sl for sl in expandir_horario_sigaa(horario_atual)):
        noite_por_ch = {
            60: ["2N1234", "3N1234", "4N1234", "5N1234", "35N12", "24N12"],
            90: ["3N1234 / 5N12", "2N1234 / 6N12", "35N123", "24N123"],
            120: ["35N1234", "24N1234", "2345N12", "2345N34"],
        }
        padroes = noite_por_ch.get(int(ch_total), []) + padroes

    for p in padroes:
        if p not in candidatos:
            candidatos.append(p)
    return candidatos


def _docentes_candidatos_para_turma(
    disciplina: str,
    df_cred: pd.DataFrame,
    ch_atual_doc: dict[str, int],
    ch_turma: int,
    teto_ch: int,
) -> list[str]:
    """Seleciona docentes habilitados (PPC/Histórico) com saldo <= teto para turmas pendentes."""
    dn = norm(disciplina)
    efetivos = sorted(
        df_cred[df_cred["Vínculo"] == "PC&T (Permanente)"]["Docente"].dropna().unique().tolist()
    )
    colabs = sorted(
        df_cred[df_cred["Vínculo"] == "Colaborador Externo"]["Docente"].dropna().unique().tolist()
    )

    habilitados_ef = []
    habilitados_col = []
    for _, r in df_cred.iterrows():
        if disciplinas_compativeis(disciplina, str(r["Componente Curricular Habilitado"])):
            doc = r["Docente"]
            if doc in efetivos and doc not in habilitados_ef:
                habilitados_ef.append(doc)
            elif doc in colabs and doc not in habilitados_col:
                habilitados_col.append(doc)

    # Afinidade por palavras-chave para disciplinas sem match literal na matriz (ex.: Mecânica dos Sólidos)
    if not habilitados_ef and not habilitados_col:
        palavras_chave = [w for w in dn.split() if len(w) >= 5 and w not in ("geral", "basica", "aplicada")]
        for _, r in df_cred.iterrows():
            comp_n = norm(r["Componente Curricular Habilitado"])
            if any(w in comp_n for w in palavras_chave) or (
                "solidos" in dn and "resistencia dos materiais" in comp_n
            ):
                doc = r["Docente"]
                if doc in efetivos and doc not in habilitados_ef:
                    habilitados_ef.append(doc)

    habilitados_ef.sort(key=lambda d: (ch_atual_doc.get(d, 0), d))
    habilitados_col.sort(key=lambda d: (ch_atual_doc.get(d, 0), d))

    validos = [d for d in habilitados_ef if ch_atual_doc.get(d, 0) + ch_turma <= teto_ch]
    validos += habilitados_col

    if not validos:
        validos = [
            d for d in sorted(efetivos, key=lambda x: (ch_atual_doc.get(x, 0), x))
            if ch_atual_doc.get(d, 0) + ch_turma <= teto_ch
        ][:4]

    return validos


def otimizar_oferta_ortools(
    df_oferta: pd.DataFrame,
    df_cred: pd.DataFrame,
    piso_ch: int = 120,
    teto_ch: int = 240,
    alocar_docentes_pendentes: bool = True,
    evitar_seg_sex_colab: bool = True,
    forcar_ter_qui_colab: bool = False,
    priorizar_206b_grandes: bool = True,
    normalizar_horarios_condensados: bool = False,
    tempo_limite_seg: float = 10.0,
) -> dict[str, Any]:
    """
    Executa o solver Google OR-Tools CP-SAT para gerar uma grade livre de choques,
    maximizar o uso das 5 salas próprias do PC&T e minimizar avisos da Malha Fina IR.
    """
    df_orig = df_oferta.copy().reset_index(drop=True)
    _, df_enc_antes, _, resumo_antes = executar_malha_fina_ir(
        df_orig, df_cred, piso_ch=piso_ch, teto_ch=teto_ch
    )

    vinculo_map = df_cred.drop_duplicates("Docente").set_index("Docente")["Vínculo"].to_dict()
    ch_atual_map = df_enc_antes.set_index("Docente")["CH_Efetiva"].to_dict()

    # 1. Agrupa turmas unificadas (mesmo docente + mesma família + sobreposição de slots)
    #    Ordenando cada grupo pela maior CH primeiro (ex.: EFIS0036 60h antes de EMEC0018 45h)
    grupos: list[list[int]] = []
    idx_para_grupo: dict[int, int] = {}

    for idx, row in df_orig.iterrows():
        if idx in idx_para_grupo:
            continue
        doc = str(row["Docente_Alocado"]).strip()
        fam = row.get("Família_Unificação", norm(row["Componente_Curricular"]))
        slots_i = set(expandir_horario_sigaa(row["Horário_SIGAA"]))
        membros = [idx]

        if not eh_sem_docente(doc) and slots_i:
            for j, rj in df_orig.iterrows():
                if j <= idx or j in idx_para_grupo:
                    continue
                if (
                    str(rj["Docente_Alocado"]).strip() == doc
                    and rj.get("Família_Unificação", norm(rj["Componente_Curricular"])) == fam
                    and (slots_i & set(expandir_horario_sigaa(rj["Horário_SIGAA"])))
                ):
                    membros.append(j)

        membros.sort(key=lambda m: (-int(df_orig.loc[m, "CH_Total"]), m))
        gid = len(grupos)
        grupos.append(membros)
        for m in membros:
            idx_para_grupo[m] = gid

    # 2. Construção do modelo CP-SAT
    model = cp_model.CpModel()

    h_cands: dict[int, list[str]] = {}
    s_cands: dict[int, list[str]] = {}
    d_cands: dict[int, list[str]] = {}

    h_vars: dict[int, list[cp_model.IntVar]] = {}
    s_vars: dict[int, list[cp_model.IntVar]] = {}
    d_vars: dict[int, list[cp_model.IntVar]] = {}

    penalidades: list[cp_model.LinearExpr] = []

    for gid, membros in enumerate(grupos):
        r0 = df_orig.loc[membros[0]]  # membro de maior CH no grupo
        ch_max = int(r0["CH_Total"])
        ch_mista = len({int(df_orig.loc[m, "CH_Total"]) for m in membros}) > 1
        hor_atual = str(r0["Horário_SIGAA"]).strip()
        sala_atual = str(r0["Sala_Alocada"]).strip()
        doc_atual = str(r0["Docente_Alocado"]).strip()
        total_vagas = sum(int(df_orig.loc[m, "Vagas"]) for m in membros)

        # --- Docentes candidatos ---
        if alocar_docentes_pendentes and eh_sem_docente(doc_atual):
            dc = _docentes_candidatos_para_turma(
                r0["Componente_Curricular"], df_cred, ch_atual_map, ch_max, teto_ch
            )
            if not dc:
                dc = [doc_atual]
        else:
            dc = [doc_atual]

        d_cands[gid] = dc
        d_vars[gid] = [model.NewBoolVar(f"d_{gid}_{i}") for i in range(len(dc))]
        model.AddExactlyOne(d_vars[gid])

        if len(dc) > 1:
            for i, d_nome in enumerate(dc):
                peso_ch = int(ch_atual_map.get(d_nome, 0) // 15)
                penalidades.append(
                    d_vars[gid][i]
                    * (peso_ch + (15 if vinculo_map.get(d_nome) != "PC&T (Permanente)" else 0))
                )

        # Variável auxiliar indicando se o docente selecionado no grupo é Colaborador Externo
        idxs_colab = [i for i, d_c in enumerate(dc) if vinculo_map.get(d_c) == "Colaborador Externo"]
        colab_var: cp_model.IntVar | None = None
        if idxs_colab and len(idxs_colab) < len(dc):
            colab_var = model.NewBoolVar(f"is_colab_{gid}")
            model.Add(colab_var == sum(d_vars[gid][i] for i in idxs_colab))
        sempre_colab = len(idxs_colab) == len(dc) and len(dc) > 0

        # --- Horários candidatos ---
        slots_orig = expandir_horario_sigaa(hor_atual)
        ch_atual_bate = len(slots_orig) * 15 == ch_max
        manter_hor_atual = ch_atual_bate or (not ch_mista and not normalizar_horarios_condensados)

        hc = _gerar_horarios_candidatos(
            ch_max,
            hor_atual,
            incluir_horario_atual=manter_hor_atual,
            preferir_blocos_continuos=ch_mista,
        )
        h_cands[gid] = hc
        h_vars[gid] = [model.NewBoolVar(f"h_{gid}_{i}") for i in range(len(hc))]
        model.AddExactlyOne(h_vars[gid])

        peso_colab_seg_sex = 2000 if forcar_ter_qui_colab else (60 if evitar_seg_sex_colab else 0)

        for i, h_code in enumerate(hc):
            slots_cand = set(expandir_horario_sigaa(h_code))
            if h_code != hor_atual:
                if slots_orig and slots_cand.issubset(set(slots_orig)):
                    penalidades.append(h_vars[gid][i] * 5)
                elif slots_orig and len(slots_cand & set(slots_orig)) >= max(2, len(slots_cand) - 1):
                    penalidades.append(h_vars[gid][i] * 40)
                else:
                    penalidades.append(h_vars[gid][i] * 250)

            # Em grupos de CH mista (45h + 60h), prioriza blocos contínuos num mesmo dia
            if ch_mista and len(extrair_dias_sigaa(h_code)) > 1:
                penalidades.append(h_vars[gid][i] * 45)

            # Regra Segunda/Sexta somente quando o docente escolhido for Colaborador Externo
            if peso_colab_seg_sex > 0:
                dias = extrair_dias_sigaa(h_code)
                if "2" in dias or "6" in dias:
                    if sempre_colab:
                        penalidades.append(h_vars[gid][i] * peso_colab_seg_sex)
                    elif colab_var is not None:
                        viol_colab = model.NewBoolVar(f"vc_{gid}_{i}")
                        model.AddMultiplicationEquality(viol_colab, [colab_var, h_vars[gid][i]])
                        penalidades.append(viol_colab * peso_colab_seg_sex)

        # --- Salas candidatas ---
        if sala_atual in LAB_ROOMS:
            sc = [sala_atual]
        else:
            sc = list(SALAS_PCT) + list(SALAS_EXTERNAS_NSA)
            if sala_atual not in sc and not eh_sem_sala(sala_atual):
                sc.append(sala_atual)

        s_cands[gid] = sc
        s_vars[gid] = [model.NewBoolVar(f"s_{gid}_{i}") for i in range(len(sc))]
        model.AddExactlyOne(s_vars[gid])

        for i, s_nome in enumerate(sc):
            cap = SALAS_INVENTARIO.get(s_nome, {}).get("Capacidade", 40)
            if s_nome in SALAS_EXTERNAS_NSA:
                penalidades.append(s_vars[gid][i] * 80)
            elif s_nome != sala_atual and not eh_sem_sala(sala_atual):
                penalidades.append(s_vars[gid][i] * 5)

            # Priorização reforçada da 206B-NSA (55 lug.) para turmas (ou unificadas) com > 40 vagas
            if s_nome not in LAB_ROOMS and cap > 0:
                if total_vagas > cap:
                    peso_lotacao = 140 if priorizar_206b_grandes else 30
                    penalidades.append(s_vars[gid][i] * peso_lotacao)
                elif priorizar_206b_grandes and s_nome == "206B-NSA" and total_vagas <= 40:
                    penalidades.append(s_vars[gid][i] * 20)

    # 3. Restrições Duras de Não-Sobreposição (IR-00, IR-03, IR-04) e Teto CH (IR-14)
    grupo_usa_slot: dict[tuple[int, str], cp_model.IntVar] = {}
    membro_usa_slot: dict[tuple[int, str], cp_model.IntVar] = {}
    todos_slots: set[str] = set()

    for gid, membros in enumerate(grupos):
        ch_max = int(df_orig.loc[membros[0], "CH_Total"])
        slot_to_hvars: dict[str, list[cp_model.IntVar]] = {}
        for i, h_code in enumerate(h_cands[gid]):
            for sl in expandir_horario_sigaa(h_code):
                todos_slots.add(sl)
                slot_to_hvars.setdefault(sl, []).append(h_vars[gid][i])
        for sl, vlist in slot_to_hvars.items():
            if len(vlist) == 1:
                grupo_usa_slot[(gid, sl)] = vlist[0]
            else:
                aux = model.NewBoolVar(f"gs_{gid}_{sl}")
                model.Add(aux == sum(vlist))
                grupo_usa_slot[(gid, sl)] = aux

        # Slots efetivamente ocupados por cada membro (exato para CH mista)
        for m in membros:
            ch_m = int(df_orig.loc[m, "CH_Total"])
            if ch_m >= ch_max:
                for sl in slot_to_hvars:
                    membro_usa_slot[(m, sl)] = grupo_usa_slot[(gid, sl)]
            else:
                m_slot_map: dict[str, list[cp_model.IntVar]] = {}
                for i, h_code in enumerate(h_cands[gid]):
                    sub_h = _derivar_subhorario(h_code, ch_m, ch_max)
                    for sl in expandir_horario_sigaa(sub_h):
                        todos_slots.add(sl)
                        m_slot_map.setdefault(sl, []).append(h_vars[gid][i])
                for sl, vlist in m_slot_map.items():
                    if len(vlist) == 1:
                        membro_usa_slot[(m, sl)] = vlist[0]
                    else:
                        aux_m = model.NewBoolVar(f"ms_{m}_{sl}")
                        model.Add(aux_m == sum(vlist))
                        membro_usa_slot[(m, sl)] = aux_m

    # 3a. IR-00: Zero choques na mesma turma / período (Aba_Origem)
    abas_membros: dict[str, list[int]] = {}
    for idx in range(len(df_orig)):
        aba = str(df_orig.loc[idx, "Aba_Origem"])
        abas_membros.setdefault(aba, []).append(idx)

    for aba, mids in abas_membros.items():
        if len(mids) <= 1:
            continue
        for sl in todos_slots:
            ativos = [membro_usa_slot[(m, sl)] for m in mids if (m, sl) in membro_usa_slot]
            if len(ativos) > 1:
                model.Add(sum(ativos) <= 1)

    # 3b. IR-03: Zero choques de Docente
    doc_grupos: dict[str, list[tuple[int, int]]] = {}
    for gid in range(len(grupos)):
        for di, d_nome in enumerate(d_cands[gid]):
            if not eh_sem_docente(d_nome):
                doc_grupos.setdefault(d_nome, []).append((gid, di))

    for d_nome, pares in doc_grupos.items():
        if len(pares) <= 1:
            continue
        for sl in todos_slots:
            ativos = []
            for gid, di in pares:
                if (gid, sl) not in grupo_usa_slot:
                    continue
                if len(d_cands[gid]) == 1:
                    ativos.append(grupo_usa_slot[(gid, sl)])
                else:
                    prod = model.NewBoolVar(f"ds_{gid}_{di}_{sl}")
                    model.AddMultiplicationEquality(prod, [d_vars[gid][di], grupo_usa_slot[(gid, sl)]])
                    ativos.append(prod)
            if len(ativos) > 1:
                model.Add(sum(ativos) <= 1)

    # 3c. IR-14: Teto regimental de CH + balanceamento suave de carga (sem travar docentes já sobrecarregados)
    for d_nome, pares in doc_grupos.items():
        if vinculo_map.get(d_nome) != "PC&T (Permanente)":
            continue
        pares_variaveis = [(gid, di) for gid, di in pares if len(d_cands[gid]) > 1]
        if not pares_variaveis:
            continue

        ch_fixa = sum(
            int(df_orig.loc[grupos[gid][0], "CH_Total"])
            for gid, _ in pares
            if len(d_cands[gid]) == 1
        )
        if ch_fixa >= teto_ch:
            for gid, di in pares_variaveis:
                model.Add(d_vars[gid][di] == 0)
            continue

        termos_ch = [
            d_vars[gid][di] * int(df_orig.loc[grupos[gid][0], "CH_Total"])
            for gid, di in pares
        ]
        tag_doc = norm(d_nome).replace(" ", "_")[:18]
        ch_total_var = model.NewIntVar(0, teto_ch, f"chdoc_{tag_doc}")
        model.Add(ch_total_var == sum(termos_ch))

        # Penalidade suave se ficar abaixo do piso (120h)
        deficit_piso = model.NewIntVar(0, piso_ch, f"def_{tag_doc}")
        model.Add(deficit_piso >= piso_ch - ch_total_var)
        penalidades.append(deficit_piso * 6)

        # Penalidade suave acima de 195h para equilibrar carga entre os efetivos
        alvo_eq = min(teto_ch, max(piso_ch + 60, 195))
        excesso_eq = model.NewIntVar(0, teto_ch, f"exc_{tag_doc}")
        model.Add(excesso_eq >= ch_total_var - alvo_eq)
        penalidades.append(excesso_eq * 2)

    # 3d. IR-04: Zero choques físicos de Sala / Laboratório
    sala_grupos: dict[str, list[tuple[int, int]]] = {}
    for gid in range(len(grupos)):
        for si, s_nome in enumerate(s_cands[gid]):
            sala_grupos.setdefault(s_nome, []).append((gid, si))

    for s_nome, pares in sala_grupos.items():
        if len(pares) <= 1:
            continue
        for sl in todos_slots:
            ativos = []
            for gid, si in pares:
                if (gid, sl) not in grupo_usa_slot:
                    continue
                if len(s_cands[gid]) == 1:
                    ativos.append(grupo_usa_slot[(gid, sl)])
                else:
                    prod = model.NewBoolVar(f"ss_{gid}_{si}_{sl}")
                    model.AddMultiplicationEquality(prod, [s_vars[gid][si], grupo_usa_slot[(gid, sl)]])
                    ativos.append(prod)
            if len(ativos) > 1:
                model.Add(sum(ativos) <= 1)

    # 3e. Dicas iniciais (warm-start) para acelerar convergência do CP-SAT
    for gid, membros in enumerate(grupos):
        r0 = df_orig.loc[membros[0]]
        hor_atual = str(r0["Horário_SIGAA"]).strip()
        total_vagas = sum(int(df_orig.loc[m, "Vagas"]) for m in membros)
        if hor_atual in h_cands[gid]:
            idx_h = h_cands[gid].index(hor_atual)
            model.AddHint(h_vars[gid][idx_h], 1)
        if priorizar_206b_grandes and total_vagas > 40 and "206B-NSA" in s_cands[gid]:
            model.AddHint(s_vars[gid][s_cands[gid].index("206B-NSA")], 1)

    # 4. Função Objetivo e Resolução
    model.Minimize(sum(penalidades))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(tempo_limite_seg)
    solver.parameters.num_search_workers = 8
    status = solver.Solve(model)
    status_nome = solver.StatusName(status)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {
            "sucesso": False,
            "status_solver": status_nome,
            "df_otimizado": df_orig,
            "df_log": pd.DataFrame(),
            "resumo_antes": resumo_antes,
            "resumo_depois": resumo_antes,
            "tempo_seg": round(solver.WallTime(), 2),
        }

    # 5. Extrai solução e monta log 'Antes -> Depois'
    df_otim = df_orig.copy()
    log_rows = []

    for gid, membros in enumerate(grupos):
        ch_max = int(df_orig.loc[membros[0], "CH_Total"])
        h_mestre = next(h_cands[gid][i] for i, v in enumerate(h_vars[gid]) if solver.Value(v) == 1)
        s_escolhida = next(s_cands[gid][i] for i, v in enumerate(s_vars[gid]) if solver.Value(v) == 1)
        d_escolhido = next(d_cands[gid][i] for i, v in enumerate(d_vars[gid]) if solver.Value(v) == 1)

        for idx in membros:
            ch_m = int(df_orig.loc[idx, "CH_Total"])
            h_escolhido = _derivar_subhorario(h_mestre, ch_m, ch_max)

            h_old = str(df_orig.loc[idx, "Horário_SIGAA"]).strip()
            s_old = str(df_orig.loc[idx, "Sala_Alocada"]).strip()
            d_old = str(df_orig.loc[idx, "Docente_Alocado"]).strip()

            mudancas = []
            if h_escolhido != h_old:
                df_otim.loc[idx, "Horário_SIGAA"] = h_escolhido
                mudancas.append(f"Horário: {h_old} → {h_escolhido}")
            if s_escolhida != s_old:
                df_otim.loc[idx, "Sala_Alocada"] = s_escolhida
                mudancas.append(f"Sala: {s_old} → {s_escolhida}")
            if d_escolhido != d_old:
                df_otim.loc[idx, "Docente_Alocado"] = d_escolhido
                mudancas.append(f"Docente: {d_old} → {d_escolhido}")

            if mudancas:
                log_rows.append({
                    "Turma": df_orig.loc[idx, "Aba_Origem"],
                    "Código": df_orig.loc[idx, "Código_SIGAA"],
                    "Disciplina": df_orig.loc[idx, "Componente_Curricular"],
                    "Alterações_Aplicadas": " | ".join(mudancas),
                })

    df_otim = enriquecer_oferta(df_otim)
    _, _, _, resumo_depois = executar_malha_fina_ir(df_otim, df_cred, piso_ch=piso_ch, teto_ch=teto_ch)

    return {
        "sucesso": True,
        "status_solver": status_nome,
        "df_otimizado": df_otim,
        "df_log": pd.DataFrame(log_rows),
        "resumo_antes": resumo_antes,
        "resumo_depois": resumo_depois,
        "tempo_seg": round(solver.WallTime(), 2),
    }