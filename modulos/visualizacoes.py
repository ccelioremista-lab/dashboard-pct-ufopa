"""
modulos/visualizacoes.py
Camada de Gráficos (Plotly) e Grade Visual das Salas — Dashboard PC&T / UFOPA (Etapa 4)

Responsabilidades:
1. Calcular o encargo efetivo docente (com deduplicação de turmas unificadas).
2. Gerar gráfico interativo Plotly de Carga Horária Docente com faixas de Piso (120h) e Teto (240h).
3. Gerar resumo e gráfico interativo de ocupação de espaços (5 salas PC&T + laboratórios).
4. Montar e estilizar a grade semanal visual (Segunda a Sexta, Manhã/Tarde/Noite) das 5 salas do PC&T,
   destacando janelas livres, turmas unificadas e choques físicos.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from modulos.dados import (
    LAB_ROOMS,
    SALAS_INVENTARIO,
    SALAS_PCT,
    expandir_horario_sigaa,
)

# ==============================================================================
# 1. DETECÇÃO DE TURMAS UNIFICADAS E CÁLCULO DE ENCARGO DOCENTE
# ==============================================================================
def identificar_turmas_unificadas_secundarias(df_oferta: pd.DataFrame) -> set[int]:
    """
    Identifica índices de turmas secundárias unificadas (mesmo docente + mesma família
    unificável + sobreposição de slots) para evitar dupla contagem no encargo efetivo.
    """
    slot_rows = []
    for idx, row in df_oferta.iterrows():
        doc = str(row["Docente_Alocado"]).strip()
        if doc in ("CONCURSO", "A definir", ""):
            continue
        fam = row.get("Família_Unificação", str(row["Componente_Curricular"]).lower())
        for sl in expandir_horario_sigaa(row["Horário_SIGAA"]):
            slot_rows.append({"idx": idx, "Docente": doc, "Familia": fam, "Slot": sl})

    if not slot_rows:
        return set()

    df_sl = pd.DataFrame(slot_rows)
    secundarias: set[int] = set()
    for (_, _, _), grp in df_sl.groupby(["Docente", "Familia", "Slot"]):
        idxs = sorted(
            grp["idx"].unique().tolist(),
            key=lambda i: (-int(df_oferta.loc[i, "CH_Total"]), i),
        )
        if len(idxs) > 1:
            for sec_idx in idxs[1:]:
                secundarias.add(sec_idx)
    return secundarias


def calcular_encargo_docente(
    df_oferta: pd.DataFrame,
    df_cred: pd.DataFrame,
    piso_ch: int = 120,
    teto_ch: int = 240,
) -> tuple[pd.DataFrame, set[int]]:
    """Calcula a carga horária bruta e efetiva (deduplicada) por docente."""
    unif_secundarias = identificar_turmas_unificadas_secundarias(df_oferta)
    docentes_base = df_cred[["Docente", "Vínculo", "Titulação", "Área"]].drop_duplicates("Docente").copy()

    linhas = []
    for _, drow in docentes_base.iterrows():
        doc = drow["Docente"]
        vinc = drow["Vínculo"]
        sub = df_oferta[df_oferta["Docente_Alocado"] == doc]
        sub_efetiva = sub[~sub.index.isin(unif_secundarias)]

        ch_bruta = int(sub["CH_Total"].sum()) if not sub.empty else 0
        ch_efetiva = int(sub_efetiva["CH_Total"].sum()) if not sub_efetiva.empty else 0
        ch_semanal = round(ch_efetiva / 15.0, 1)
        saldo_teto = teto_ch - ch_efetiva

        if vinc != "PC&T (Permanente)":
            status = "Colaborador Externo"
        elif ch_efetiva == 0:
            status = "Sem Alocação (0h)"
        elif ch_efetiva < piso_ch:
            status = f"Abaixo do Piso (<{piso_ch}h)"
        elif ch_efetiva > teto_ch:
            status = f"Sobrecarga (>{teto_ch}h)"
        elif ch_efetiva == teto_ch:
            status = f"No Limite ({teto_ch}h)"
        else:
            status = f"Regular ({piso_ch}h–{teto_ch}h)"

        discs = (
            "; ".join(
                f"{r['Código_SIGAA']} {r['Componente_Curricular']} [{r['Aba_Origem']}]"
                + (" [UNIF]" if r.name in unif_secundarias else "")
                for _, r in sub.iterrows()
            )
            if not sub.empty
            else "—"
        )

        linhas.append({
            "Docente": doc,
            "Vínculo": vinc,
            "Titulação": drow["Titulação"],
            "Área": drow["Área"],
            "Turmas_Brutas": len(sub),
            "Turmas_Efetivas": len(sub_efetiva),
            "CH_Bruta": ch_bruta,
            "CH_Efetiva": ch_efetiva,
            "CH_Semanal": ch_semanal,
            "Saldo_Teto": saldo_teto,
            "Status_Encargo": status,
            "Disciplinas_Alocadas": discs,
        })

    df_enc = (
        pd.DataFrame(linhas)
        .sort_values(by=["Vínculo", "CH_Efetiva", "Docente"], ascending=[False, False, True])
        .reset_index(drop=True)
    )
    return df_enc, unif_secundarias


# ==============================================================================
# 2. GRÁFICOS INTERATIVOS PLOTLY
# ==============================================================================
def grafico_encargo_docente(
    df_encargo: pd.DataFrame,
    piso_ch: int = 120,
    teto_ch: int = 240,
    apenas_efetivos: bool = True,
) -> go.Figure:
    """Gera gráfico de barras horizontais Plotly com faixas de Piso (120h) e Teto (240h)."""
    df_plot = df_encargo.copy()
    if apenas_efetivos:
        df_plot = df_plot[df_plot["Vínculo"] == "PC&T (Permanente)"]

    df_plot = df_plot.sort_values(by=["CH_Efetiva", "Docente"], ascending=[True, False])

    cor_map = {
        f"Regular ({piso_ch}h–{teto_ch}h)": "#15803D",
        f"No Limite ({teto_ch}h)": "#D97706",
        f"Abaixo do Piso (<{piso_ch}h)": "#F59E0B",
        f"Sobrecarga (>{teto_ch}h)": "#DC2626",
        "Sem Alocação (0h)": "#B91C1C",
        "Colaborador Externo": "#2563EB",
    }

    fig = px.bar(
        df_plot,
        x="CH_Efetiva",
        y="Docente",
        color="Status_Encargo",
        orientation="h",
        text="CH_Efetiva",
        color_discrete_map=cor_map,
        hover_data={
            "Docente": False,
            "Vínculo": True,
            "CH_Efetiva": True,
            "CH_Bruta": True,
            "CH_Semanal": True,
            "Turmas_Efetivas": True,
            "Saldo_Teto": True,
            "Status_Encargo": True,
        },
        labels={
            "CH_Efetiva": "Carga Horária Efetiva na Graduação (h/semestre)",
            "Docente": "",
            "Status_Encargo": "Situação",
        },
    )

    fig.update_traces(texttemplate="%{text}h", textposition="outside", cliponaxis=False)

    # Faixa sombreada da zona regimental ideal (Piso -> Teto)
    fig.add_vrect(
        x0=piso_ch,
        x1=teto_ch,
        fillcolor="rgba(21, 128, 61, 0.07)",
        line_width=0,
        layer="below",
    )
    fig.add_vline(
        x=piso_ch,
        line_dash="dash",
        line_color="#D97706",
        line_width=2,
        annotation_text=f"Piso ({piso_ch}h)",
        annotation_position="top",
        annotation_font_color="#B45309",
    )
    fig.add_vline(
        x=teto_ch,
        line_dash="dash",
        line_color="#B91C1C",
        line_width=2,
        annotation_text=f"Teto ({teto_ch}h)",
        annotation_position="top",
        annotation_font_color="#B91C1C",
    )

    max_x = max(teto_ch + 40, int(df_plot["CH_Efetiva"].max()) + 40 if not df_plot.empty else teto_ch + 40)
    altura = max(440, len(df_plot) * 30 + 110)

    fig.update_layout(
        height=altura,
        xaxis_range=[0, max_x],
        margin=dict(l=10, r=35, t=45, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="left", x=0),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
    )
    fig.update_xaxes(showgrid=True, gridcolor="#E2E8F0")
    fig.update_yaxes(showgrid=False)
    return fig


def calcular_resumo_ocupacao_espacos(df_oferta: pd.DataFrame, unif_secundarias: set[int]) -> pd.DataFrame:
    """Calcula estatísticas de ocupação semanal, lotação e choques por sala/laboratório."""
    df_valid = df_oferta[~df_oferta.index.isin(unif_secundarias)].copy()
    linhas = []

    salas_todas = list(SALAS_INVENTARIO.keys())
    for s in df_valid["Sala_Alocada"].dropna().unique():
        if s not in salas_todas:
            salas_todas.append(s)

    for sala in salas_todas:
        if sala == "A DEFINIR":
            continue
        info = SALAS_INVENTARIO.get(
            sala, {"Gestao": "Externa (Outra)", "Tipo": "Sala", "Capacidade": 40, "Gargalo": "Sim"}
        )
        sub = df_valid[df_valid["Sala_Alocada"] == sala]

        slot_counts: dict[str, int] = {}
        for _, r in sub.iterrows():
            for sl in expandir_horario_sigaa(r["Horário_SIGAA"]):
                slot_counts[sl] = slot_counts.get(sl, 0) + 1

        slots_unicos = len(slot_counts)
        slots_diurnos = sum(1 for sl in slot_counts if len(sl) >= 2 and sl[1] in ("M", "T"))
        choques = sum(1 for cnt in slot_counts.values() if cnt > 1)
        max_vagas = int(sub["Vagas"].max()) if not sub.empty else 0
        cap = info["Capacidade"]
        excede = "SIM" if (cap > 0 and max_vagas > cap and sala not in LAB_ROOMS) else "Não"
        taxa_diurna = round((slots_diurnos / 50.0) * 100, 1)

        linhas.append({
            "Espaço / Sala": sala,
            "Gestão": info["Gestao"],
            "Capacidade": cap,
            "Turmas": len(sub),
            "Slots_Ocupados": slots_unicos,
            "Livres_Diurno": max(0, 50 - slots_diurnos),
            "Ocupação_Diurna_%": taxa_diurna,
            "Choques_Slot": choques,
            "Maior_Turma": max_vagas,
            "Excede_Cap?": excede,
        })

    return pd.DataFrame(linhas)


def grafico_ocupacao_salas(df_ocupacao: pd.DataFrame) -> go.Figure:
    """Gera gráfico Plotly de slots semanais ocupados por sala/laboratório."""
    df_p = df_ocupacao[df_ocupacao["Slots_Ocupados"] > 0].sort_values("Slots_Ocupados", ascending=True)
    if df_p.empty:
        df_p = df_ocupacao.head(5)

    cor_gestao = {
        "PC&T (Gestão Direta)": "#1B365D",
        "PC&T (Lab Próprio)": "#0F766E",
        "Externa (CAC / IEG)": "#D97706",
        "Externa (IEG / Computação)": "#DC2626",
        "Externa (IBEF / IEG)": "#DC2626",
        "Externa (ICED - Rondon)": "#6366F1",
    }

    fig = px.bar(
        df_p,
        x="Slots_Ocupados",
        y="Espaço / Sala",
        color="Gestão",
        orientation="h",
        text="Slots_Ocupados",
        color_discrete_map=cor_gestao,
        hover_data={
            "Capacidade": True,
            "Turmas": True,
            "Ocupação_Diurna_%": True,
            "Choques_Slot": True,
            "Maior_Turma": True,
        },
        labels={"Slots_Ocupados": "Slots Semanais Ocupados", "Espaço / Sala": ""},
    )
    fig.update_traces(texttemplate="%{text} slots", textposition="outside", cliponaxis=False)
    fig.update_layout(
        height=max(360, len(df_p) * 32 + 90),
        margin=dict(l=10, r=45, t=30, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="left", x=0),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
    )
    fig.update_xaxes(showgrid=True, gridcolor="#E2E8F0")
    return fig


# ==============================================================================
# 3. GRADE VISUAL SEMANAL DAS 5 SALAS DO PC&T (E DEMAIS ESPAÇOS)
# ==============================================================================
def construir_grade_semanal_sala(
    df_oferta: pd.DataFrame,
    sala_nome: str,
    unif_secundarias: set[int],
) -> tuple[pd.DataFrame, int, int]:
    """
    Monta a matriz semanal (Horário x Segunda..Sexta) da sala escolhida.
    Retorna (df_grade, qtd_slots_ocupados, qtd_choques).
    """
    dias = [("2", "Segunda"), ("3", "Terça"), ("4", "Quarta"), ("5", "Quinta"), ("6", "Sexta")]
    horarios = [
        ("M1", "Manhã 1º (07:30)"),
        ("M2", "Manhã 2º (08:20)"),
        ("M3", "Manhã 3º (09:20)"),
        ("M4", "Manhã 4º (10:10)"),
        ("M5", "Manhã 5º (11:00)"),
        ("T1", "Tarde 1º (14:00)"),
        ("T2", "Tarde 2º (14:50)"),
        ("T3", "Tarde 3º (15:50)"),
        ("T4", "Tarde 4º (16:40)"),
        ("T5", "Tarde 5º (17:30)"),
        ("N1", "Noite 1º (18:30)"),
        ("N2", "Noite 2º (19:20)"),
        ("N3", "Noite 3º (20:20)"),
        ("N4", "Noite 4º (21:10)"),
    ]

    sub = df_oferta[(df_oferta["Sala_Alocada"] == sala_nome) & (~df_oferta.index.isin(unif_secundarias))]
    slot_entries: dict[str, list[str]] = {}
    for _, r in sub.iterrows():
        primeiro_nome = str(r["Docente_Alocado"]).split()[0]
        rotulo = f"[{r['Aba_Origem']}] {r['Componente_Curricular']} ({primeiro_nome})"
        for sl in expandir_horario_sigaa(r["Horário_SIGAA"]):
            slot_entries.setdefault(sl, []).append(rotulo)

    tem_noite = any(
        f"{dc}{hc}" in slot_entries
        for dc, _ in dias
        for hc, _ in horarios
        if hc.startswith("N")
    )

    linhas = []
    choques = 0
    for hc, hlbl in horarios:
        if hc.startswith("N") and not tem_noite:
            continue
        linha = {"Horário": hlbl}
        for dc, dlbl in dias:
            itens = slot_entries.get(f"{dc}{hc}", [])
            if not itens:
                linha[dlbl] = "— Livre —"
            elif len(itens) == 1:
                linha[dlbl] = itens[0]
            else:
                choques += 1
                linha[dlbl] = "⚠️ CHOQUE: " + " | ".join(itens)
        linhas.append(linha)

    return pd.DataFrame(linhas), len(slot_entries), choques


def estilizar_grade_sala(df_grade: pd.DataFrame):
    """Aplica cores semânticas às células da grade semanal no Streamlit."""
    def _cor_celula(val):
        texto = str(val)
        if texto == "— Livre —":
            return "background-color: #F8FAFC; color: #94A3B8; font-style: italic;"
        if texto.startswith("⚠️ CHOQUE"):
            return "background-color: #FEE2E2; color: #991B1B; font-weight: 700;"
        return "background-color: #DCFCE7; color: #14532D; font-weight: 600;"

    colunas_dias = [c for c in df_grade.columns if c != "Horário"]
    styler = df_grade.style
    if hasattr(styler, "map"):
        return styler.map(_cor_celula, subset=colunas_dias)
    return styler.applymap(_cor_celula, subset=colunas_dias)
