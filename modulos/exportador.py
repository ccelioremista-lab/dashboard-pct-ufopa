"""
modulos/exportador.py
Exportador Oficial Sincronizado para o IEG / SIGAA (.xlsx) — PC&T / UFOPA

Gera uma pasta de trabalho Excel estilizada com openpyxl contendo:
1. Resumo_Malha_Fina_IR (KPIs + Malha Fina IR atualizada)
2. Encargo_Docente (Efetivos + Colaboradores com deduplicação de turmas unificadas)
3. Auditoria_Docentes_PIT (diagnóstico de piso 120h, teto 240h, pendências e regra seg/sex)
4. Mapa_Salas_PCT (ocupação e lotação somada das 5 salas próprias + demais espaços)
5. Oferta_Consolidada (todas as turmas padronizadas e sincronizadas)
6. Log_Otimizacao (quando houver histórico de alterações Antes -> Depois)
7. Abas oficiais do IEG por curso/período (ex.: 1º BI ... 9º MEC ou 2º BI ... 8º MEC),
   cada uma contendo a tabela de disciplinas E a grade semanal sincronizada (Segunda a Sexta).
"""

from __future__ import annotations

import re
from io import BytesIO
from typing import Optional

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from modulos.dados import (
    SALAS_EXTERNAS_NSA,
    SALAS_PCT,
    expandir_horario_sigaa,
    extrair_dias_sigaa,
)
from modulos.regras import executar_malha_fina_ir
from modulos.visualizacoes import calcular_resumo_ocupacao_espacos

ORDEM_ABAS_IEG = [
    "1º BI", "1º MEC",
    "2º BI", "2º MEC",
    "3º BI", "3º MEC",
    "4º BI", "4º MEC",
    "5º BI", "5º MEC",
    "6º BI", "6º MEC",
    "7º EF", "7º MEC",
    "8º EF", "8º MEC",
    "9º EF", "9º MEC",
    "10º EF", "10º MEC",
]

FILL_NAVY = PatternFill("solid", fgColor="1B365D")
FILL_SUB = PatternFill("solid", fgColor="E2E8F0")
FILL_ZEBRA = PatternFill("solid", fgColor="F8FAFC")
FILL_GREEN = PatternFill("solid", fgColor="DCFCE7")
FILL_AMBER = PatternFill("solid", fgColor="FEF3C7")
FILL_RED = PatternFill("solid", fgColor="FEE2E2")

FONT_TITLE = Font(name="Calibri", size=13, bold=True, color="FFFFFF")
FONT_HEADER = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
FONT_SUB = Font(name="Calibri", size=10, bold=True, color="1E293B")
FONT_BODY = Font(name="Calibri", size=10, color="0F172A")
FONT_BOLD = Font(name="Calibri", size=10, bold=True, color="0F172A")

THIN_SIDE = Side(border_style="thin", color="CBD5E1")
BORDER_ALL = Border(left=THIN_SIDE, right=THIN_SIDE, top=THIN_SIDE, bottom=THIN_SIDE)


def _sanitizar_nome_aba(nome: str) -> str:
    limpo = re.sub(r"[\[\]:*?/\\]", "-", str(nome)).strip()
    return (limpo or "Aba")[:31]


def _valor_excel(val):
    if pd.isna(val):
        return ""
    if hasattr(val, "item"):
        return val.item()
    return val


def _configurar_impressao(ws):
    ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0


def _autoajustar_colunas(ws, max_width: int = 46):
    celulas_mescladas_horiz: set[tuple[int, int]] = set()
    for rng in ws.merged_cells.ranges:
        if rng.max_col > rng.min_col:
            for r in range(rng.min_row, rng.max_row + 1):
                for c in range(rng.min_col, rng.max_col + 1):
                    celulas_mescladas_horiz.add((r, c))

    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = 0
        for cell in col:
            if (cell.row, cell.column) in celulas_mescladas_horiz:
                continue
            val = "" if cell.value is None else str(cell.value)
            for linha in val.split("\n"):
                max_len = max(max_len, len(linha))
        ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), max_width)


def _escrever_tabela(
    ws,
    df: pd.DataFrame,
    start_row: int = 1,
    freeze_header: bool = True,
    add_filter: bool = True,
):
    headers = list(df.columns)
    for c_idx, h in enumerate(headers, start=1):
        cell = ws.cell(row=start_row, column=c_idx, value=h)
        cell.font = FONT_HEADER
        cell.fill = FILL_NAVY
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER_ALL
    ws.row_dimensions[start_row].height = 24

    for r_offset, (_, row) in enumerate(df.iterrows(), start=1):
        r_num = start_row + r_offset
        zebra = (r_offset % 2 == 0)
        for c_idx, h in enumerate(headers, start=1):
            val = _valor_excel(row[h])
            cell = ws.cell(row=r_num, column=c_idx, value=val)
            cell.font = FONT_BODY
            cell.border = BORDER_ALL
            cell.alignment = Alignment(
                horizontal="center" if isinstance(val, (int, float)) else "left",
                vertical="center",
                wrap_text=True,
            )
            if zebra:
                cell.fill = FILL_ZEBRA

            sval = str(val)
            eh_alerta_cap = (h == "Excede_Cap?" and sval == "SIM")
            eh_choque_num = (h == "Choques_Slot" and isinstance(val, (int, float)) and val > 0)

            if (
                "ERRO IMPEDITIVO" in sval
                or "Sobrecarga" in sval
                or "CRÍTICO" in sval
                or eh_alerta_cap
                or eh_choque_num
            ):
                cell.fill = FILL_RED
                cell.font = Font(name="Calibri", size=10, bold=True, color="991B1B")
            elif (
                "AVISO" in sval
                or "Abaixo do Piso" in sval
                or "No Limite" in sval
                or "ATENÇÃO" in sval
                or "Sem Alocação" in sval
            ):
                cell.fill = FILL_AMBER
                cell.font = Font(name="Calibri", size=10, bold=True, color="92400E")
            elif "Regular" in sval or sval.startswith("CONFORME"):
                cell.fill = FILL_GREEN
                cell.font = Font(name="Calibri", size=10, bold=True, color="166534")

    if freeze_header:
        ws.freeze_panes = ws.cell(row=start_row + 1, column=1)
    if add_filter and headers:
        ws.auto_filter.ref = f"A{start_row}:{get_column_letter(len(headers))}{start_row + len(df)}"
    return start_row + len(df) + 2


def construir_auditoria_docentes_pit(
    df_oferta: pd.DataFrame,
    df_enc: pd.DataFrame,
    piso_ch: int = 120,
    teto_ch: int = 240,
) -> pd.DataFrame:
    """Gera a planilha de auditoria individual por docente para conferência do PIT e do Colegiado."""
    doc_col_limpa = df_oferta["Docente_Alocado"].astype(str).str.strip()
    linhas = []

    for _, erow in df_enc.iterrows():
        doc = str(erow["Docente"]).strip()
        vinc = str(erow["Vínculo"]).strip()
        ch_ef = int(erow["CH_Efetiva"])
        ch_br = int(erow["CH_Bruta"])
        saldo = int(erow["Saldo_Teto"])

        sub = df_oferta[doc_col_limpa == doc]
        dias_seg_sex = []
        for _, r in sub.iterrows():
            ds = extrair_dias_sigaa(r["Horário_SIGAA"])
            viol = [lbl for cod, lbl in [("2", "Seg"), ("6", "Sex")] if cod in ds]
            if viol:
                dias_seg_sex.append(f"{r['Componente_Curricular']} ({'/'.join(viol)})")

        if vinc == "PC&T (Permanente)":
            if ch_ef > teto_ch:
                diag_pit = f"CRÍTICO: Acima do teto ({ch_ef}h > {teto_ch}h)"
            elif ch_ef < piso_ch:
                diag_pit = f"ATENÇÃO: Abaixo do piso ({ch_ef}h < {piso_ch}h; checar Pós/afastamento)"
            else:
                diag_pit = "CONFORME: Dentro da faixa regimental"
        elif vinc == "Colaborador Externo":
            diag_pit = "ATENÇÃO: Restrição Seg/Sex" if dias_seg_sex else "CONFORME: Apenas Ter–Qui"
        else:
            diag_pit = "ATENÇÃO: Docente fora da matriz de credenciamento"

        linhas.append({
            "Docente": doc,
            "Vínculo": vinc,
            "CH_Efetiva_PIT": ch_ef,
            "CH_Bruta_Turmas": ch_br,
            "Saldo_Até_Teto": saldo if vinc == "PC&T (Permanente)" else 0,
            "Status_Encargo": erow["Status_Encargo"],
            "Diagnóstico_PIT": diag_pit,
            "Ocorrências_Seg_Sex": "; ".join(dias_seg_sex) if dias_seg_sex else "—",
            "Disciplinas_Alocadas": erow["Disciplinas_Alocadas"],
        })

    return pd.DataFrame(linhas)


def _escrever_aba_periodo_ieg(ws, aba_nome: str, df_sub: pd.DataFrame, semestre: str = "2027.1"):
    """Monta uma aba oficial do IEG: cabeçalho + tabela de oferta + grade semanal sincronizada."""
    curso_nome = str(df_sub["Curso"].iloc[0]) if not df_sub.empty else ""
    cols = [
        ("Código_SIGAA", "Código"),
        ("Componente_Curricular", "Componente Curricular"),
        ("CH_Total", "CH (h)"),
        ("Vagas", "Vagas"),
        ("Turma", "Turma"),
        ("Horário_SIGAA", "Horário SIGAA"),
        ("Sala_Alocada", "Sala / Laboratório"),
        ("Docente_Alocado", "Docente"),
    ]
    df_tab = df_sub[[c[0] for c in cols if c[0] in df_sub.columns]].rename(columns=dict(cols))
    n_cols_banner = max(6, len(df_tab.columns))

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=n_cols_banner)
    titulo = ws["A1"]
    titulo.value = f"OFERTA {semestre} — PC&T / IEG / UFOPA — {aba_nome} ({curso_nome})"
    titulo.font = FONT_TITLE
    titulo.fill = FILL_NAVY
    titulo.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    prox_row = _escrever_tabela(ws, df_tab, start_row=3, freeze_header=False, add_filter=False)

    ws.merge_cells(start_row=prox_row, start_column=1, end_row=prox_row, end_column=6)
    sub_cell = ws.cell(row=prox_row, column=1, value=f"GRADE HORÁRIA SEMANAL SINCRONIZADA — {aba_nome} ({semestre})")
    sub_cell.font = FONT_SUB
    sub_cell.fill = FILL_SUB
    sub_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[prox_row].height = 22

    slot_map: dict[str, list[str]] = {}
    for _, r in df_sub.iterrows():
        partes_doc = str(r["Docente_Alocado"]).strip().split()
        p_doc = partes_doc[0] if partes_doc else "Sem docente"
        rotulo = f"{r['Componente_Curricular']}\n({p_doc} | {r['Sala_Alocada']})"
        for sl in expandir_horario_sigaa(r["Horário_SIGAA"]):
            slot_map.setdefault(sl, []).append(rotulo)

    dias = [("2", "Segunda"), ("3", "Terça"), ("4", "Quarta"), ("5", "Quinta"), ("6", "Sexta")]
    horarios = [
        ("M1", "07:30 - 08:20 (M1)"), ("M2", "08:20 - 09:10 (M2)"),
        ("M3", "09:20 - 10:10 (M3)"), ("M4", "10:10 - 11:00 (M4)"), ("M5", "11:00 - 11:50 (M5)"),
        ("T1", "14:00 - 14:50 (T1)"), ("T2", "14:50 - 15:40 (T2)"),
        ("T3", "15:50 - 16:40 (T3)"), ("T4", "16:40 - 17:30 (T4)"), ("T5", "17:30 - 18:20 (T5)"),
        ("N1", "18:30 - 19:20 (N1)"), ("N2", "19:20 - 20:10 (N2)"),
        ("N3", "20:20 - 21:10 (N3)"), ("N4", "21:10 - 22:00 (N4)"),
    ]
    tem_noite = any(f"{dc}{hc}" in slot_map for dc, _ in dias for hc, _ in horarios if hc.startswith("N"))

    header_row = prox_row + 1
    ws.cell(row=header_row, column=1, value="Horário").font = FONT_HEADER
    ws.cell(row=header_row, column=1).fill = FILL_NAVY
    ws.cell(row=header_row, column=1).alignment = Alignment(horizontal="center", vertical="center")
    ws.cell(row=header_row, column=1).border = BORDER_ALL

    for idx_d, (_, dlbl) in enumerate(dias, start=2):
        c = ws.cell(row=header_row, column=idx_d, value=dlbl)
        c.font = FONT_HEADER
        c.fill = FILL_NAVY
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = BORDER_ALL
    ws.row_dimensions[header_row].height = 22

    cur_r = header_row + 1
    for hc, hlbl in horarios:
        if hc.startswith("N") and not tem_noite:
            continue
        c_h = ws.cell(row=cur_r, column=1, value=hlbl)
        c_h.font = FONT_BOLD
        c_h.fill = FILL_SUB
        c_h.alignment = Alignment(horizontal="center", vertical="center")
        c_h.border = BORDER_ALL

        for idx_d, (dc, _) in enumerate(dias, start=2):
            itens = slot_map.get(f"{dc}{hc}", [])
            c = ws.cell(row=cur_r, column=idx_d)
            c.border = BORDER_ALL
            c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            if not itens:
                c.value = ""
            elif len(itens) == 1:
                c.value = itens[0]
                c.font = FONT_BODY
                c.fill = FILL_GREEN
            else:
                c.value = "CHOQUE: " + " // ".join(itens)
                c.font = Font(name="Calibri", size=9, bold=True, color="991B1B")
                c.fill = FILL_RED
        ws.row_dimensions[cur_r].height = 32
        cur_r += 1

    ws.freeze_panes = "A4"
    _autoajustar_colunas(ws, max_width=38)
    _configurar_impressao(ws)


def gerar_excel_oficial_ieg(
    df_oferta: pd.DataFrame,
    df_cred: pd.DataFrame,
    piso_ch: int = 120,
    teto_ch: int = 240,
    df_log_otim: Optional[pd.DataFrame] = None,
    semestre: str = "2027.1",
) -> bytes:
    """Gera o arquivo Excel (.xlsx) completo em memória pronto para download no Streamlit."""
    df_pend, df_enc, unif_sec, resumo_ir = executar_malha_fina_ir(
        df_oferta, df_cred, piso_ch=piso_ch, teto_ch=teto_ch
    )
    df_ocup = calcular_resumo_ocupacao_espacos(df_oferta, unif_sec)
    df_pit = construir_auditoria_docentes_pit(df_oferta, df_enc, piso_ch=piso_ch, teto_ch=teto_ch)

    salas_pct_cnt = int(df_oferta["Sala_Alocada"].isin(SALAS_PCT).sum())
    salas_ext_cnt = int(df_oferta["Sala_Alocada"].isin(SALAS_EXTERNAS_NSA).sum())

    wb = Workbook()

    ws_res = wb.active
    ws_res.title = "Resumo_Malha_Fina_IR"
    ws_res.merge_cells("A1:F1")
    ws_res["A1"].value = f"PAINEL EXECUTIVO & MALHA FINA IR — OFERTA {semestre} • PC&T / IEG / UFOPA"
    ws_res["A1"].font = FONT_TITLE
    ws_res["A1"].fill = FILL_NAVY
    ws_res["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws_res.row_dimensions[1].height = 28

    kpis_df = pd.DataFrame([
        {"Indicador": "Semestre Letivo", "Valor": semestre},
        {"Indicador": "Total de Turmas", "Valor": len(df_oferta)},
        {"Indicador": "Carga Horária Total (h)", "Valor": int(df_oferta["CH_Total"].sum())},
        {"Indicador": "Erros Impeditivos (IR)", "Valor": resumo_ir["erros"]},
        {"Indicador": "Avisos de Atenção (IR)", "Valor": resumo_ir["avisos"]},
        {
            "Indicador": "Choques (Turma / Docente / Sala)",
            "Valor": f"{resumo_ir['choques_turma']} / {resumo_ir['choques_docente']} / {resumo_ir['choques_sala']}",
        },
        {"Indicador": "Turmas nas 5 Salas Próprias PC&T", "Valor": salas_pct_cnt},
        {"Indicador": "Turmas em Salas Externas NSA (105A–110B)", "Valor": salas_ext_cnt},
        {"Indicador": "Turmas sem Docente", "Valor": resumo_ir["sem_docente"]},
        {"Indicador": "Turmas sem Sala (A DEFINIR)", "Valor": resumo_ir["sem_sala"]},
    ])
    prox = _escrever_tabela(ws_res, kpis_df, start_row=3, freeze_header=False, add_filter=False)
    if not df_pend.empty:
        _escrever_tabela(ws_res, df_pend, start_row=prox, freeze_header=False, add_filter=True)
    else:
        ws_res.merge_cells(start_row=prox, start_column=1, end_row=prox, end_column=6)
        ok_cell = ws_res.cell(row=prox, column=1, value="✅ Nenhuma pendência ativa na Malha Fina IR!")
        ok_cell.font = Font(name="Calibri", size=11, bold=True, color="166534")
        ok_cell.fill = FILL_GREEN
        ok_cell.alignment = Alignment(horizontal="center", vertical="center")
        ws_res.row_dimensions[prox].height = 24
    _autoajustar_colunas(ws_res, max_width=48)
    _configurar_impressao(ws_res)

    ws_enc = wb.create_sheet("Encargo_Docente")
    _escrever_tabela(ws_enc, df_enc, start_row=1)
    _autoajustar_colunas(ws_enc, max_width=45)
    _configurar_impressao(ws_enc)

    ws_pit = wb.create_sheet("Auditoria_Docentes_PIT")
    _escrever_tabela(ws_pit, df_pit, start_row=1)
    _autoajustar_colunas(ws_pit, max_width=46)
    _configurar_impressao(ws_pit)

    ws_salas = wb.create_sheet("Mapa_Salas_PCT")
    _escrever_tabela(ws_salas, df_ocup, start_row=1)
    _autoajustar_colunas(ws_salas, max_width=36)
    _configurar_impressao(ws_salas)

    ws_cons = wb.create_sheet("Oferta_Consolidada")
    cols_cons = [
        "Aba_Origem", "Curso", "Período", "Código_SIGAA", "Componente_Curricular",
        "CH_Total", "Vagas", "Horário_SIGAA", "Sala_Alocada", "Gestão_Sala", "Docente_Alocado",
    ]
    _escrever_tabela(ws_cons, df_oferta[[c for c in cols_cons if c in df_oferta.columns]], start_row=1)
    _autoajustar_colunas(ws_cons, max_width=40)
    _configurar_impressao(ws_cons)

    if df_log_otim is not None and not df_log_otim.empty:
        ws_log = wb.create_sheet("Log_Otimizacao")
        _escrever_tabela(ws_log, df_log_otim, start_row=1)
        _autoajustar_colunas(ws_log, max_width=52)
        _configurar_impressao(ws_log)

    abas_existentes = df_oferta["Aba_Origem"].dropna().unique().tolist()
    abas_ordenadas = [a for a in ORDEM_ABAS_IEG if a in abas_existentes] + [
        a for a in abas_existentes if a not in ORDEM_ABAS_IEG
    ]
    for aba in abas_ordenadas:
        ws_p = wb.create_sheet(title=_sanitizar_nome_aba(str(aba)))
        df_sub = df_oferta[df_oferta["Aba_Origem"] == aba].copy()
        _escrever_aba_periodo_ieg(ws_p, str(aba), df_sub, semestre=semestre)

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()