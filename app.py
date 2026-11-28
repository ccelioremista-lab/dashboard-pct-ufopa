"""
app.py — Dashboard de Oferta e Credenciamento Docente (PC&T / IEG / UFOPA)
Etapa 7: Auditoria Individual PIT/Colegiado + Painel Visual das 5 Salas + Exportador IEG Expandido
"""

import os
import streamlit as st
import pandas as pd

from modulos.agente_ia import consultar_agente_groq
from modulos.dados import (
    SALAS_EXTERNAS_NSA,
    SALAS_INVENTARIO,
    SALAS_PCT,
    carregar_base,
    gerar_tabela_estruturas_sigaa,
    gerar_tabela_salas_inventario,
    norm,
)
from modulos.exportador import construir_auditoria_docentes_pit, gerar_excel_oficial_ieg
from modulos.otimizador import otimizar_oferta_ortools
from modulos.regras import (
    SEVERIDADE_AVISO,
    SEVERIDADE_ERRO,
    aplicar_edicoes_oferta,
    estilizar_malha_fina,
    executar_malha_fina_ir,
    sugerir_docentes_habilitados,
)
from modulos.visualizacoes import (
    calcular_resumo_ocupacao_espacos,
    construir_grade_semanal_sala,
    estilizar_grade_sala,
    grafico_encargo_docente,
    grafico_ocupacao_salas,
)

# ==============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA E ESTILO VISUAL EXECUTIVO
# ==============================================================================
st.set_page_config(
    page_title="PC&T / UFOPA — Gestão de Ofertas & Otimização",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .kpi-card {
            background-color: #F8FAFC;
            border-left: 5px solid #1B365D;
            padding: 14px 16px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
            margin-bottom: 8px;
            min-height: 118px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .kpi-green {
            background-color: #F0FDF4;
            border-left-color: #15803D;
        }
        .kpi-amber {
            background-color: #FFFBEB;
            border-left-color: #B45309;
        }
        .kpi-red {
            background-color: #FEF2F2;
            border-left-color: #B91C1C;
        }
        .kpi-label {
            font-size: 0.74rem;
            font-weight: 700;
            color: #475569;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }
        .kpi-value {
            font-size: 1.70rem;
            font-weight: 800;
            color: #0F172A;
            margin-top: 2px;
            line-height: 1.15;
        }
        .kpi-sub {
            font-size: 0.77rem;
            color: #64748B;
            margin-top: 4px;
        }
        .room-box {
            background-color: #F8FAFC;
            border: 1px solid #CBD5E1;
            border-top: 4px solid #1B365D;
            border-radius: 8px;
            padding: 10px 12px;
            margin-bottom: 10px;
        }
        .room-box-free {
            border-top-color: #0F766E;
            background-color: #F0FDFA;
        }
        .room-box-alert {
            border-top-color: #B91C1C;
            background-color: #FEF2F2;
        }
        .room-title {
            font-weight: 800;
            font-size: 0.95rem;
            color: #0F172A;
        }
        .room-meta {
            font-size: 0.78rem;
            color: #475569;
            margin-top: 2px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def _obter_segredo(chave: str, padrao: str = "") -> str:
    """Lê segredos do Streamlit Cloud (st.secrets) com fallback seguro para variáveis de ambiente."""
    try:
        if chave in st.secrets:
            return str(st.secrets[chave]).strip()
    except Exception:
        pass
    return os.environ.get(chave, padrao).strip()


def _verificar_acesso_opcional():
    """
    Se SENHA_ACESSO estiver configurada em st.secrets (nuvem), exibe tela de login discreta.
    No uso local (sem SENHA_ACESSO definida), libera o dashboard imediatamente.
    """
    senha_config = _obter_segredo("SENHA_ACESSO", "")
    if not senha_config:
        return
    if st.session_state.get("autenticado_pct", False):
        return

    st.title("🔐 Acesso Restrito — Coordenação PC&T / UFOPA")
    st.caption("Dashboard de Oferta Semestral, Encargo Docente (PIT) e Otimização de Salas.")
    with st.form("form_login_pct", clear_on_submit=False):
        senha_digitada = st.text_input("Senha institucional de acesso:", type="password")
        entrar = st.form_submit_button("Entrar no Dashboard", type="primary")
        if entrar:
            if senha_digitada == senha_config:
                st.session_state["autenticado_pct"] = True
                st.rerun()
            else:
                st.error("Senha incorreta. Solicite a senha vigente à Coordenação do PC&T.")
    st.stop()


_verificar_acesso_opcional()


def render_kpi(col, titulo: str, valor, subtitulo: str = "", variante: str = ""):
    classe = f"kpi-card {variante}".strip()
    col.markdown(
        f"""
        <div class="{classe}">
            <div class="kpi-label">{titulo}</div>
            <div class="kpi-value">{valor}</div>
            <div class="kpi-sub">{subtitulo}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ==============================================================================
# 2. CARREGAMENTO COM SESSION_STATE (SIMULADOR + OTIMIZADOR)
# ==============================================================================
with st.sidebar:
    st.header("⚙️ Painel de Controle")

    semestre_opcao = st.radio(
        "📅 Semestre Letivo (Modo Anual):",
        [
            "2027.1 (Ímpares: 1º, 3º, 5º, 7º, 9º)",
            "2027.2 (Pares: 2º, 4º, 6º, 8º)",
        ],
        index=0,
        help="Alterna automaticamente entre as bases oficiais dos semestres ímpares e pares (4 matrizes SIGAA).",
    )
    semestre_cod = "2027.2" if "2027.2" in semestre_opcao else "2027.1"

    arquivo_upload = st.file_uploader(
        "Carregar outra planilha (.xlsx)",
        type=["xlsx"],
        help="Opcional: substitui temporariamente a planilha padrão da pasta dados/.",
    )

    chave_fonte = (
        f"upload::{arquivo_upload.name}"
        if arquivo_upload is not None
        else f"padrao::{semestre_cod}"
    )
    if (
        "df_oferta_ativa" not in st.session_state
        or st.session_state.get("chave_fonte_ativa") != chave_fonte
    ):
        df_of_init, df_cr_init, origem_init = carregar_base(
            arquivo_upload=arquivo_upload, semestre=semestre_cod
        )
        st.session_state["df_oferta_ativa"] = df_of_init
        st.session_state["df_cred_ativa"] = df_cr_init
        st.session_state["origem_ativa"] = origem_init
        st.session_state["chave_fonte_ativa"] = chave_fonte
        st.session_state["total_edicoes_manuais"] = 0
        st.session_state["otimizacao_aplicada"] = False
        st.session_state.pop("ultimo_resultado_otim", None)
        st.session_state.pop("excel_ieg_pronto", None)

    df_oferta = st.session_state["df_oferta_ativa"]
    df_cred = st.session_state["df_cred_ativa"]
    origem = st.session_state["origem_ativa"]

    st.caption(f"📂 **Origem:** {origem}")
    if st.session_state.get("otimizacao_aplicada") or st.session_state.get("total_edicoes_manuais", 0) > 0:
        tag_estado = (
            "🤖 Solução OR-Tools aplicada em memória."
            if st.session_state.get("otimizacao_aplicada")
            else f"✏️ {st.session_state['total_edicoes_manuais']} ajuste(s) simulado(s) em memória."
        )
        st.info(tag_estado)
        if st.button("🔄 Restaurar Planilha Original", width="stretch"):
            df_of_reset, df_cr_reset, origem_reset = carregar_base(
                arquivo_upload=arquivo_upload, semestre=semestre_cod
            )
            st.session_state["df_oferta_ativa"] = df_of_reset
            st.session_state["df_cred_ativa"] = df_cr_reset
            st.session_state["origem_ativa"] = origem_reset
            st.session_state["total_edicoes_manuais"] = 0
            st.session_state["otimizacao_aplicada"] = False
            st.session_state.pop("ultimo_resultado_otim", None)
            st.session_state.pop("excel_ieg_pronto", None)
            st.rerun()

    st.divider()
    st.subheader("📐 Parâmetros Regimentais")
    col_p1, col_p2 = st.columns(2)
    piso_ch = col_p1.number_input("Piso (h)", min_value=60, max_value=180, value=120, step=15)
    teto_ch = col_p2.number_input("Teto (h)", min_value=180, max_value=360, value=240, step=15)

    st.divider()
    st.subheader("🔎 Filtros da Oferta")

    cursos_disponiveis = sorted(df_oferta["Curso"].dropna().unique().tolist())
    cursos_sel = st.multiselect("Curso", cursos_disponiveis, default=cursos_disponiveis)

    periodos_disponiveis = sorted(df_oferta["Período"].dropna().astype(str).unique().tolist())
    periodos_sel = st.multiselect("Período", periodos_disponiveis, default=periodos_disponiveis)

    gestoes_disponiveis = sorted(df_oferta["Gestão_Sala"].dropna().unique().tolist())
    gestoes_sel = st.multiselect("Gestão do Espaço", gestoes_disponiveis, default=gestoes_disponiveis)

    docentes_disponiveis = ["Todos"] + sorted(df_oferta["Docente_Alocado"].dropna().unique().tolist())
    docente_sel = st.selectbox("Filtrar por Docente", docentes_disponiveis)

    apenas_pendencias = st.toggle("Mostrar apenas pendências (Sem Docente ou Sem Sala)", value=False)
    busca_texto = st.text_input("Buscar disciplina ou código SIGAA", placeholder="Ex.: Cálculo, PCT300...")


# ==============================================================================
# 3. FILTROS DINÂMICOS E MOTOR MALHA FINA IR (TEMPO REAL)
# ==============================================================================
df_filtrado = df_oferta.copy()

if cursos_sel:
    df_filtrado = df_filtrado[df_filtrado["Curso"].isin(cursos_sel)]
else:
    df_filtrado = df_filtrado.iloc[0:0]

if periodos_sel:
    df_filtrado = df_filtrado[df_filtrado["Período"].astype(str).isin(periodos_sel)]
else:
    df_filtrado = df_filtrado.iloc[0:0]

if gestoes_sel:
    df_filtrado = df_filtrado[df_filtrado["Gestão_Sala"].isin(gestoes_sel)]
else:
    df_filtrado = df_filtrado.iloc[0:0]

if docente_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Docente_Alocado"] == docente_sel]

if apenas_pendencias:
    cond_doc = df_filtrado["Docente_Alocado"].isin(["CONCURSO", "A definir"])
    cond_sala = df_filtrado["Sala_Alocada"] == "A DEFINIR"
    df_filtrado = df_filtrado[cond_doc | cond_sala]

if busca_texto.strip():
    termo = norm(busca_texto)
    cond_disc = df_filtrado["Componente_Curricular"].apply(lambda x: termo in norm(x))
    cond_cod = df_filtrado["Código_SIGAA"].apply(lambda x: termo in norm(x))
    df_filtrado = df_filtrado[cond_disc | cond_cod]

df_pendencias, df_encargo, unif_secundarias, resumo_ir = executar_malha_fina_ir(
    df_oferta, df_cred, piso_ch=piso_ch, teto_ch=teto_ch
)
df_ocupacao = calcular_resumo_ocupacao_espacos(df_oferta, unif_secundarias)
df_pit = construir_auditoria_docentes_pit(df_oferta, df_encargo, piso_ch=piso_ch, teto_ch=teto_ch)


# ==============================================================================
# 4. CABEÇALHO EXECUTIVO E CARTÕES DE KPIs
# ==============================================================================
st.title("🎓 Dashboard de Oferta e Credenciamento — PC&T / UFOPA")
st.caption(
    f"v7.1 (Modo Anual & Cloud • {semestre_cod}) • Matrizes SIGAA + Malha Fina IR + Otimizador OR-Tools + Auditoria PIT + Exportador IEG | "
    f"Faixa regimental: {piso_ch}h a {teto_ch}h"
)

total_turmas = len(df_filtrado)
ch_total = int(df_filtrado["CH_Total"].sum()) if total_turmas > 0 else 0
salas_ext = int(df_oferta["Sala_Alocada"].isin(SALAS_EXTERNAS_NSA).sum())
choques_salas_total = int(df_ocupacao["Choques_Slot"].sum())

k1, k2, k3, k4, k5 = st.columns(5)
render_kpi(
    k1,
    "Turmas no Recorte",
    total_turmas,
    f"de {len(df_oferta)} turmas totais ({ch_total}h)",
)
render_kpi(
    k2,
    "🔴 Erros Impeditivos (IR)",
    resumo_ir["erros"],
    f"Choques: {resumo_ir['choques_turma']} turma | {resumo_ir['choques_docente']} doc | {resumo_ir['choques_sala']} sala",
    variante="kpi-green" if resumo_ir["erros"] == 0 else "kpi-red",
)
render_kpi(
    k3,
    "🟡 Avisos de Atenção",
    resumo_ir["avisos"],
    "Lotação, Colab Seg/Sex, Labs, Piso CH",
    variante="kpi-green" if resumo_ir["avisos"] == 0 else "kpi-amber",
)
render_kpi(
    k4,
    "Sem Docente / Sem Sala",
    f"{resumo_ir['sem_docente']} / {resumo_ir['sem_sala']}",
    "CONCURSO-A definir | Sala A DEFINIR",
    variante="kpi-green" if (resumo_ir["sem_docente"] == 0 and resumo_ir["sem_sala"] == 0) else "kpi-red",
)
render_kpi(
    k5,
    "Salas Externas / Choques",
    f"{salas_ext} / {choques_salas_total}",
    "105A-110B | slots sobrepostos",
    variante="kpi-green" if (salas_ext == 0 and choques_salas_total == 0) else "kpi-amber",
)

st.write("")


# ==============================================================================
# 5. ABAS DO DASHBOARD (ETAPA 7)
# ==============================================================================
(
    aba_ir,
    aba_otim,
    aba_simulador,
    aba_encargo,
    aba_grade_salas,
    aba_exportar,
    aba_ia,
    aba_consulta,
) = st.tabs([
    f"🧾 Verificador IR ({resumo_ir['erros']}🔴 / {resumo_ir['avisos']}🟡)",
    "🤖 Otimizador (OR-Tools)",
    "✏️ Simulador",
    "📊 Encargo & PIT",
    "🏫 5 Salas PC&T",
    "📥 Exportar IEG (.xlsx)",
    "💬 Agente IA",
    "📋 Oferta & Credenciamento",
])

# ------------------------------------------------------------------------------
# ABA 1: VERIFICADOR ESTILO "MALHA FINA DO IMPOSTO DE RENDA"
# ------------------------------------------------------------------------------
with aba_ir:
    st.subheader("Malha Fina da Oferta — Diagnóstico Automático de Pendências")
    st.caption(
        "🔴 Erros Impeditivos bloqueiam o lançamento limpo no SIGAA; "
        "🟡 Avisos pedem conferência da Coordenação."
    )

    col_ir1, col_ir2, col_ir3 = st.columns([1.4, 1.4, 1.2])
    filtro_sev = col_ir1.radio("Severidade:", ["Todos", SEVERIDADE_ERRO, SEVERIDADE_AVISO], horizontal=True)
    eixos_disp = ["Todos"] + sorted(df_pendencias["Eixo"].unique().tolist()) if not df_pendencias.empty else ["Todos"]
    filtro_eixo = col_ir2.selectbox("Filtrar por Eixo / Categoria:", eixos_disp)
    busca_ir = col_ir3.text_input("Buscar na Malha Fina:", placeholder="Ex.: 206B, Gilson, IR-04...")

    df_ir_view = df_pendencias.copy()
    if filtro_sev != "Todos":
        df_ir_view = df_ir_view[df_ir_view["Severidade"] == filtro_sev]
    if filtro_eixo != "Todos":
        df_ir_view = df_ir_view[df_ir_view["Eixo"] == filtro_eixo]
    if busca_ir.strip():
        t_ir = norm(busca_ir)
        df_ir_view = df_ir_view[
            df_ir_view["Código_Regra"].apply(lambda x: t_ir in norm(x))
            | df_ir_view["Alvo"].apply(lambda x: t_ir in norm(x))
            | df_ir_view["Descrição"].apply(lambda x: t_ir in norm(x))
        ]

    if df_ir_view.empty:
        st.success("✅ Nenhuma pendência encontrada para este filtro!")
    else:
        st.dataframe(
            estilizar_malha_fina(df_ir_view),
            width="stretch",
            hide_index=True,
            column_config={"Código_Regra": "Regra", "Ação_Recomendada": "Ação Recomendada"},
        )
        csv_ir = df_ir_view.to_csv(index=False, sep=";", encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(
            "⬇️ Exportar Relatório da Malha Fina (.csv)",
            data=csv_ir,
            file_name="malha_fina_ir_pct.csv",
            mime="text/csv",
        )

    if not df_pendencias.empty:
        with st.expander("📊 Ver contagem de pendências agrupadas por regra"):
            resumo_regras = (
                df_pendencias.groupby(["Severidade", "Código_Regra", "Eixo"], as_index=False)
                .size()
                .rename(columns={"size": "Ocorrências", "Código_Regra": "Regra"})
                .sort_values(by=["Severidade", "Ocorrências"], ascending=[True, False])
            )
            st.dataframe(resumo_regras, width="stretch", hide_index=True)

# ------------------------------------------------------------------------------
# ABA 2: OTIMIZADOR AUTOMÁTICO COM GOOGLE OR-TOOLS (CP-SAT)
# ------------------------------------------------------------------------------
with aba_otim:
    st.subheader("Otimizador Matemático de Horários e Salas — Google OR-Tools (CP-SAT)")
    st.caption(
        "Resolve automaticamente choques de turma, docente e sala, alinha turmas unificadas, "
        "preenche horários/salas pendentes e prioriza as 5 salas próprias do PC&T (preservando ao máximo a grade original)."
    )

    col_o1, col_o2, col_o3 = st.columns([1.25, 1.35, 1.0])
    opt_docentes = col_o1.checkbox(
        "Alocar automaticamente docentes habilitados (CONCURSO / A definir)",
        value=True,
    )
    opt_forcar_ter_qui = col_o2.checkbox(
        "Forçar Terça–Quinta para colaboradores externos (mover aulas de Seg/Sex)",
        value=True,
        help="Remaneja aulas de colaboradores externos que caem em segunda ou sexta-feira para zerar avisos IR-11.",
    )
    opt_tempo = col_o3.slider("Tempo máximo do solver (s)", min_value=3, max_value=20, value=10)

    col_o4, col_o5 = st.columns([1.25, 2.35])
    opt_priorizar_206b = col_o4.checkbox(
        "Priorizar sala 206B-NSA (55 lug.) para turmas de 50 vagas",
        value=True,
        help="Reserva a sala 206B-NSA preferencialmente para turmas com mais de 40 vagas (reduz avisos IR-10).",
    )
    opt_norm_cond = col_o5.checkbox(
        "Normalizar horários condensados divergentes da CH oficial (IR-07)",
        value=False,
        help="Quando marcado, ajusta também turmas condensadas (ex.: EMEC0028, EMEC0043, PCT30010) ao número exato de blocos da CH.",
    )

    if st.button("🚀 Otimizar Grade Agora (OR-Tools CP-SAT)", type="primary"):
        with st.spinner(f"Executando otimização matemática CP-SAT nas {len(df_oferta)} turmas..."):
            resultado = otimizar_oferta_ortools(
                df_oferta,
                df_cred,
                piso_ch=piso_ch,
                teto_ch=teto_ch,
                alocar_docentes_pendentes=opt_docentes,
                evitar_seg_sex_colab=True,
                forcar_ter_qui_colab=opt_forcar_ter_qui,
                priorizar_206b_grandes=opt_priorizar_206b,
                normalizar_horarios_condensados=opt_norm_cond,
                tempo_limite_seg=float(opt_tempo),
            )
            st.session_state["ultimo_resultado_otim"] = resultado

    if "ultimo_resultado_otim" in st.session_state:
        res = st.session_state["ultimo_resultado_otim"]
        if not res["sucesso"]:
            st.error(f"Não foi possível encontrar solução viável ({res['status_solver']}). Tente aumentar o tempo limite.")
        else:
            r_ant = res["resumo_antes"]
            r_dep = res["resumo_depois"]
            df_ot = res["df_otimizado"]

            st.success(
                f"✅ Otimização concluída em **{res['tempo_seg']}s** (`{res['status_solver']}`): "
                f"**Erros Impeditivos reduzidos de {r_ant['erros']} → {r_dep['erros']}**!"
            )

            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Erros Impeditivos (IR)", r_dep["erros"], delta=r_dep["erros"] - r_ant["erros"], delta_color="inverse")
            m2.metric("Avisos (IR)", r_dep["avisos"], delta=r_dep["avisos"] - r_ant["avisos"], delta_color="inverse")
            m3.metric("Choques de Sala", r_dep["choques_sala"], delta=r_dep["choques_sala"] - r_ant["choques_sala"], delta_color="inverse")
            m4.metric("Sem Sala (A DEFINIR)", r_dep["sem_sala"], delta=r_dep["sem_sala"] - r_ant["sem_sala"], delta_color="inverse")
            salas_pct_ot = int(df_ot["Sala_Alocada"].isin(SALAS_PCT).sum())
            salas_pct_ant = int(df_oferta["Sala_Alocada"].isin(SALAS_PCT).sum())
            m5.metric("Turmas nas 5 Salas PC&T", salas_pct_ot, delta=salas_pct_ot - salas_pct_ant)

            col_ap1, col_ap2 = st.columns([1.6, 2.4])
            if col_ap1.button("✅ Aplicar Solução Otimizada em Todo o Dashboard", type="primary", width="stretch"):
                st.session_state["df_oferta_ativa"] = df_ot
                st.session_state["otimizacao_aplicada"] = True
                st.rerun()
            col_ap2.caption("Após aplicar, você ainda pode fazer ajustes finos no Simulador e baixar o Excel oficial do IEG.")

            st.subheader(f"Registro de Alterações (Antes → Depois) — {len(res['df_log'])} turma(s)")
            if res["df_log"].empty:
                st.info("A grade atual já estava otimizada sem necessidade de ajustes.")
            else:
                st.dataframe(res["df_log"], width="stretch", hide_index=True)

# ------------------------------------------------------------------------------
# ABA 3: SIMULADOR INTERATIVO DE ALOCAÇÃO
# ------------------------------------------------------------------------------
with aba_simulador:
    st.subheader("Simulador Interativo — Ajuste Docente, Sala, Horário SIGAA ou Vagas")
    st.caption(
        "Edite diretamente nas células abaixo e clique em **Aplicar Alterações** para revalidar "
        "instantaneamente a Malha Fina IR, o gráfico de encargo e a grade das 5 salas."
    )

    col_sim1, col_sim2, col_sim3 = st.columns([1.2, 1.2, 1.6])
    curso_sim = col_sim1.selectbox("Curso no editor:", ["Todos"] + cursos_disponiveis, key="sim_curso")
    aba_opcoes = ["Todas"] + sorted(df_oferta["Aba_Origem"].dropna().unique().tolist())
    aba_sim = col_sim2.selectbox("Turma / Período:", aba_opcoes, key="sim_aba")
    so_pend_sim = col_sim3.checkbox("Filtrar apenas turmas sem docente, sem sala ou sem horário", value=False)

    df_sim_base = df_oferta.copy()
    if curso_sim != "Todos":
        df_sim_base = df_sim_base[df_sim_base["Curso"] == curso_sim]
    if aba_sim != "Todas":
        df_sim_base = df_sim_base[df_sim_base["Aba_Origem"] == aba_sim]
    if so_pend_sim:
        df_sim_base = df_sim_base[
            df_sim_base["Docente_Alocado"].isin(["CONCURSO", "A definir"])
            | (df_sim_base["Sala_Alocada"] == "A DEFINIR")
            | df_sim_base["Horário_SIGAA"].str.upper().str.contains("SEM HORÁRIO", na=True)
        ]

    colunas_editor = [
        "Aba_Origem",
        "Código_SIGAA",
        "Componente_Curricular",
        "CH_Total",
        "Vagas",
        "Horário_SIGAA",
        "Sala_Alocada",
        "Docente_Alocado",
    ]
    opcoes_docentes = sorted(df_cred["Docente"].dropna().unique().tolist()) + ["CONCURSO", "A definir"]
    opcoes_salas_ed = list(SALAS_INVENTARIO.keys())
    for s_extra in df_oferta["Sala_Alocada"].dropna().unique():
        if s_extra not in opcoes_salas_ed:
            opcoes_salas_ed.append(s_extra)

    df_editado = st.data_editor(
        df_sim_base[colunas_editor],
        width="stretch",
        hide_index=True,
        disabled=["Aba_Origem", "Código_SIGAA", "Componente_Curricular", "CH_Total"],
        column_config={
            "Aba_Origem": "Turma",
            "Código_SIGAA": "Código",
            "Componente_Curricular": "Disciplina",
            "CH_Total": st.column_config.NumberColumn("CH (h)", format="%d h"),
            "Vagas": st.column_config.NumberColumn("Vagas", min_value=5, max_value=100, step=5),
            "Horário_SIGAA": st.column_config.TextColumn("Horário SIGAA (ex.: 24M12)"),
            "Sala_Alocada": st.column_config.SelectboxColumn("Sala / Laboratório", options=opcoes_salas_ed, required=True),
            "Docente_Alocado": st.column_config.SelectboxColumn("Docente", options=opcoes_docentes, required=True),
        },
        key="editor_simulador_pct",
    )

    if st.button("💾 Aplicar Alterações e Revalidar Malha Fina", type="primary"):
        df_atualizado, qtd_alt = aplicar_edicoes_oferta(df_oferta, df_editado)
        if qtd_alt > 0:
            st.session_state["df_oferta_ativa"] = df_atualizado
            st.session_state["total_edicoes_manuais"] = st.session_state.get("total_edicoes_manuais", 0) + qtd_alt
            st.success(f"✅ {qtd_alt} turma(s) atualizada(s)! Malha Fina IR recalculada.")
            st.rerun()
        else:
            st.info("Nenhuma alteração detectada nas células editadas.")

    with st.expander("💡 Consulta rápida: sugerir docentes habilitados com saldo para qualquer disciplina"):
        discs_todas = sorted(df_oferta["Componente_Curricular"].dropna().unique().tolist())
        disc_escolhida = st.selectbox("Escolha a disciplina:", discs_todas, key="sug_disc")
        sugestoes = sugerir_docentes_habilitados(disc_escolhida, df_cred, df_encargo, teto_ch=teto_ch, limite=5)
        if sugestoes:
            for item in sugestoes:
                st.write(f"• {item}")
        else:
            st.warning("Nenhum docente cadastrado na matriz para esta disciplina.")

# ------------------------------------------------------------------------------
# ABA 4: GRÁFICO DE ENCARGO DOCENTE + AUDITORIA PIT / COLEGIADO
# ------------------------------------------------------------------------------
with aba_encargo:
    st.subheader("Distribuição de Carga Horária Efetiva na Graduação")
    col_e1, col_e2 = st.columns([2, 1])
    exibir_apenas_efetivos = col_e1.radio(
        "Escopo do gráfico:",
        ["Somente 19 Efetivos PC&T", "Todos (Efetivos + 4 Colaboradores Externos)"],
        horizontal=True,
    ) == "Somente 19 Efetivos PC&T"
    col_e2.info(f"ℹ️ **{len(unif_secundarias)} turma(s) unificada(s)** deduplicada(s) no cálculo efetivo.")

    fig_enc = grafico_encargo_docente(
        df_encargo,
        piso_ch=piso_ch,
        teto_ch=teto_ch,
        apenas_efetivos=exibir_apenas_efetivos,
    )
    st.plotly_chart(fig_enc, width="stretch")

    st.divider()
    st.subheader("📑 Auditoria Individual para PIT e Colegiado")
    st.caption(
        "Consolida CH efetiva (com deduplicação de unificadas), saldo até o teto e ocorrências em Seg/Sex "
        "para conferência do Plano Individual de Trabalho (PIT) e deliberação em Colegiado."
    )
    doc_foco = st.selectbox(
        "Inspecionar ficha individual de um docente (opcional):",
        ["Todos os docentes"] + sorted(df_pit["Docente"].unique().tolist()),
        key="foco_pit",
    )
    df_pit_view = df_pit.copy()
    if exibir_apenas_efetivos and doc_foco == "Todos os docentes":
        df_pit_view = df_pit_view[df_pit_view["Vínculo"] == "PC&T (Permanente)"]
    if doc_foco != "Todos os docentes":
        df_pit_view = df_pit_view[df_pit_view["Docente"] == doc_foco]

    st.dataframe(
        df_pit_view,
        width="stretch",
        hide_index=True,
        column_config={
            "CH_Efetiva_PIT": st.column_config.NumberColumn("CH Efetiva (PIT)", format="%d h"),
            "CH_Bruta_Turmas": st.column_config.NumberColumn("CH Bruta", format="%d h"),
            "Saldo_Até_Teto": st.column_config.NumberColumn("Saldo p/ Teto", format="%d h"),
        },
    )

# ------------------------------------------------------------------------------
# ABA 5: GRADE VISUAL DAS 5 SALAS DO PC&T
# ------------------------------------------------------------------------------
with aba_grade_salas:
    st.subheader("Mapa Visual Semanal — As 5 Salas Próprias do PC&T (NSA)")

    # Cartões rápidos das 5 salas sob gestão direta do PC&T
    df_5_salas = df_ocupacao[df_ocupacao["Espaço / Sala"].isin(SALAS_PCT)].copy()
    cols_5 = st.columns(5)
    for idx_s, sala_id in enumerate(SALAS_PCT):
        row_s = df_5_salas[df_5_salas["Espaço / Sala"] == sala_id]
        if row_s.empty:
            continue
        rs = row_s.iloc[0]
        choq_s = int(rs["Choques_Slot"])
        ocup_s = int(rs["Slots_Ocupados"])
        livres_s = int(rs["Livres_Diurno"])
        cap_s = int(rs["Capacidade"])
        box_cls = "room-box room-box-alert" if choq_s > 0 else ("room-box room-box-free" if ocup_s == 0 else "room-box")
        status_txt = f"🔴 {choq_s} choque(s)" if choq_s > 0 else ("🟢 100% livre (diurno)" if ocup_s == 0 else f"✅ {livres_s} livres (diurno)")
        cols_5[idx_s].markdown(
            f"""
            <div class="{box_cls}">
                <div class="room-title">{sala_id} ({cap_s} lug.)</div>
                <div class="room-meta">{int(rs['Turmas'])} turma(s) • {ocup_s} slots</div>
                <div class="room-meta"><b>{status_txt}</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.dataframe(
        df_5_salas,
        width="stretch",
        hide_index=True,
        column_config={
            "Capacidade": st.column_config.NumberColumn("Capacidade", format="%d lug."),
            "Slots_Ocupados": "Slots Ocupados",
            "Livres_Diurno": "Janelas Livres (Diurno)",
            "Ocupação_Diurna_%": st.column_config.ProgressColumn(
                "Ocupação Diurna", min_value=0, max_value=100, format="%.1f%%"
            ),
            "Choques_Slot": "Choques (Slots)",
            "Maior_Turma": "Maior Turma (Vagas)",
        },
    )

    st.divider()
    col_s1, col_s2 = st.columns([2, 1])
    opcoes_salas = SALAS_PCT + [s for s in df_ocupacao["Espaço / Sala"].tolist() if s not in SALAS_PCT]
    sala_sel = col_s1.selectbox(
        "Selecione uma sala ou laboratório para inspecionar a grade semanal:",
        opcoes_salas,
        index=0,
    )
    info_sala = SALAS_INVENTARIO.get(sala_sel, {"Gestao": "Externa", "Capacidade": 40})
    df_grade, qtd_ocup, qtd_choq = construir_grade_semanal_sala(df_oferta, sala_sel, unif_secundarias)

    if qtd_choq > 0:
        col_s2.error(f"🔴 **{qtd_choq} slot(s) com choque físico** em {sala_sel} ({info_sala['Capacidade']} lug.)")
    else:
        col_s2.success(f"✅ Zero choques em {sala_sel} ({qtd_ocup} slots ocupados | {info_sala['Capacidade']} lug.)")

    st.dataframe(estilizar_grade_sala(df_grade), width="stretch", hide_index=True)

    st.divider()
    st.subheader("Ocupação Geral de Salas e Laboratórios (Slots Semanais)")
    fig_salas = grafico_ocupacao_salas(df_ocupacao)
    st.plotly_chart(fig_salas, width="stretch")

    with st.expander("📋 Inventário completo de espaços e capacidades"):
        st.dataframe(gerar_tabela_salas_inventario(), width="stretch", hide_index=True)

# ------------------------------------------------------------------------------
# ABA 6: EXPORTAÇÃO OFICIAL SINCRONIZADA PARA O IEG
# ------------------------------------------------------------------------------
with aba_exportar:
    st.subheader("Exportador Oficial para Entrega ao IEG / SIGAA (.xlsx)")
    abas_atuais_txt = ", ".join(f"`{a}`" for a in sorted(df_oferta["Aba_Origem"].dropna().unique().tolist()))
    st.markdown(
        f"""
        Gera uma pasta de trabalho Excel estilizada e sincronizada com o estado atual do dashboard (**{semestre_cod}**,
        incluindo qualquer ajuste feito no **Simulador** ou no **Otimizador OR-Tools**):
- **Abas executivas:** `Resumo_Malha_Fina_IR`, `Encargo_Docente`, `Auditoria_Docentes_PIT`, `Mapa_Salas_PCT`, `Oferta_Consolidada` e `Log_Otimizacao` (quando aplicável).
- **Abas oficiais por período/curso ({df_oferta['Aba_Origem'].nunique()} abas):** {abas_atuais_txt} — cada uma já com a **tabela de oferta + grade semanal sincronizada**.
        """
    )

    nome_padrao_exp = (
        "Pacote_Oficial_PCT_IEG_2027_2_Otimizado_v1.xlsx"
        if semestre_cod == "2027.2"
        else "Pacote_Oficial_PCT_IEG_2027_1_Otimizado_v6_1.xlsx"
    )
    nome_arquivo_exp = st.text_input(
        "Nome do arquivo para download:",
        value=nome_padrao_exp,
        key=f"nome_exp_{semestre_cod}",
    )
    if not nome_arquivo_exp.lower().endswith(".xlsx"):
        nome_arquivo_exp += ".xlsx"

    log_atual = (
        st.session_state["ultimo_resultado_otim"].get("df_log")
        if st.session_state.get("otimizacao_aplicada") and "ultimo_resultado_otim" in st.session_state
        else None
    )

    if st.button("📦 Gerar Planilha Oficial do IEG (.xlsx)", type="primary"):
        with st.spinner("Montando as abas estilizadas e sincronizando grades semanais..."):
            bytes_xlsx = gerar_excel_oficial_ieg(
                df_oferta,
                df_cred,
                piso_ch=piso_ch,
                teto_ch=teto_ch,
                df_log_otim=log_atual,
                semestre=semestre_cod,
            )
            st.session_state["excel_ieg_pronto"] = bytes_xlsx
            st.session_state["excel_ieg_nome"] = nome_arquivo_exp

    if "excel_ieg_pronto" in st.session_state:
        st.success("✅ Planilha oficial gerada com sucesso! Clique abaixo para salvar no seu computador.")
        st.download_button(
            "⬇️ Baixar Planilha Oficial IEG (.xlsx)",
            data=st.session_state["excel_ieg_pronto"],
            file_name=st.session_state.get("excel_ieg_nome", "Oferta_Oficial_PCT_IEG.xlsx"),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# ------------------------------------------------------------------------------
# ABA 7: AGENTE IA DA COORDENAÇÃO (LANGCHAIN + GROQ + FALLBACK LOCAL)
# ------------------------------------------------------------------------------
with aba_ia:
    st.subheader("Assistente IA da Coordenação — PC&T / UFOPA")
    st.caption(
        "Faça perguntas sobre a oferta ativa, choques, encargo docente ou peça rascunhos de ofícios ao IEG. "
        "Sem chave Groq, responde em Modo Local; com a chave ativa na nuvem, seleciona automaticamente o melhor modelo disponível."
    )

    if "chat_pct_historico" not in st.session_state:
        st.session_state["chat_pct_historico"] = []

    groq_key_secret = _obter_segredo("GROQ_API_KEY", "")
    col_status, col_limpar = st.columns([4, 1])

    if groq_key_secret:
        col_status.success("🔑 Assistente IA conectado automaticamente via Groq (nuvem).")
        with st.expander("⚙️ Configurações avançadas (substituir chave Groq)", expanded=False):
            groq_key_manual = st.text_input(
                "Substituir chave Groq (opcional):",
                value="",
                type="password",
                placeholder="Deixe vazio para usar a chave configurada na nuvem",
            )
        groq_key = groq_key_manual.strip() or groq_key_secret
    else:
        groq_key = col_status.text_input(
            "GROQ_API_KEY (opcional — gratuita em console.groq.com):",
            value="",
            type="password",
            placeholder="gsk_...",
        )

    if col_limpar.button("🗑️ Limpar chat", width="stretch"):
        st.session_state["chat_pct_historico"] = []
        st.rerun()

    st.caption("Sugestões rápidas:")
    b1, b2, b3, b4 = st.columns(4)
    pergunta_rapida = None
    if b1.button("📋 Malha Fina", width="stretch"):
        pergunta_rapida = "Faça um resumo objetivo dos erros impeditivos da Malha Fina atual."
    if b2.button("🏫 5 Salas PC&T", width="stretch"):
        pergunta_rapida = "Como está a ocupação e quais janelas livres existem nas 5 salas próprias do PC&T?"
    if b3.button("👨‍🏫 Sem docente", width="stretch"):
        pergunta_rapida = "Quem pode assumir as turmas sem docente considerando habilitação e saldo até 240h?"
    if b4.button("📄 Ofício IEG", width="stretch"):
        pergunta_rapida = (
            "Redija um rascunho de ofício oficial à Direção do IEG encaminhando o panorama "
            "da oferta ativa do PC&T, destacando eventuais pendências de docentes ou salas externas no NSA."
        )

    for msg in st.session_state["chat_pct_historico"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    pergunta_usuario = st.chat_input("Digite sua pergunta sobre a oferta do PC&T...") or pergunta_rapida
    if pergunta_usuario:
        st.session_state["chat_pct_historico"].append({"role": "user", "content": pergunta_usuario})
        with st.chat_message("user"):
            st.markdown(pergunta_usuario)

        with st.chat_message("assistant"):
            with st.spinner("Consultando dados da oferta ativa..."):
                resposta, modo = consultar_agente_groq(
                    pergunta_usuario,
                    df_oferta,
                    df_cred,
                    api_key=groq_key,
                    piso_ch=piso_ch,
                    teto_ch=teto_ch,
                )
                texto_final = f"{resposta}\n\n*— Respondido via `{modo}`*"
                st.markdown(texto_final)
                st.session_state["chat_pct_historico"].append({"role": "assistant", "content": texto_final})

# ------------------------------------------------------------------------------
# ABA 8: CONSULTA DE OFERTA FILTRADA, RESUMO POR CURSO E CREDENCIAMENTO
# ------------------------------------------------------------------------------
with aba_consulta:
    sub1, sub2, sub3, sub4 = st.tabs([
        f"📋 Oferta Filtrada ({total_turmas})",
        "📈 Resumo por Curso",
        "📚 Matriz de Credenciamento",
        "🏛️ Estruturas Curriculares SIGAA (4 Matrizes)",
    ])

    with sub1:
        if df_filtrado.empty:
            st.info("Nenhuma turma encontrada para a combinação atual de filtros.")
        else:
            colunas_exibir = [
                "Aba_Origem", "Curso", "Período", "Código_SIGAA", "Componente_Curricular",
                "Matriz_SIGAA", "Natureza_SIGAA",
                "CH_Total", "Vagas", "Horário_SIGAA", "Sala_Alocada", "Capacidade_Sala",
                "Gestão_Sala", "Docente_Alocado",
            ]
            colunas_existentes = [c for c in colunas_exibir if c in df_filtrado.columns]
            st.dataframe(
                df_filtrado[colunas_existentes],
                width="stretch",
                hide_index=True,
                column_config={
                    "Aba_Origem": "Turma",
                    "Código_SIGAA": "Código",
                    "Componente_Curricular": "Disciplina",
                    "CH_Total": st.column_config.NumberColumn("CH (h)", format="%d h"),
                    "Capacidade_Sala": st.column_config.NumberColumn("Cap. Sala", format="%d"),
                    "Horário_SIGAA": "Horário SIGAA",
                    "Sala_Alocada": "Sala / Laboratório",
                    "Gestão_Sala": "Gestão",
                    "Docente_Alocado": "Docente",
                },
            )
            csv_bytes = df_filtrado[colunas_existentes].to_csv(index=False, sep=";", encoding="utf-8-sig").encode("utf-8-sig")
            st.download_button(
                "⬇️ Baixar recorte filtrado (.csv)",
                data=csv_bytes,
                file_name="recorte_oferta_pct.csv",
                mime="text/csv",
            )

    with sub2:
        if df_filtrado.empty:
            st.info("Ajuste os filtros na barra lateral para visualizar o resumo.")
        else:
            df_aux = df_filtrado.copy()
            df_aux["_sem_doc"] = df_aux["Docente_Alocado"].isin(["CONCURSO", "A definir"]).astype(int)
            df_aux["_sem_sala"] = (df_aux["Sala_Alocada"] == "A DEFINIR").astype(int)
            df_aux["_ext_cac"] = df_aux["Sala_Alocada"].isin(SALAS_EXTERNAS_NSA).astype(int)
            resumo = (
                df_aux.groupby(["Curso", "Aba_Origem"], as_index=False)
                .agg(
                    Turmas=("Código_SIGAA", "count"),
                    CH_Total=("CH_Total", "sum"),
                    Sem_Docente=("_sem_doc", "sum"),
                    Sem_Sala=("_sem_sala", "sum"),
                    Salas_Externas_CAC=("_ext_cac", "sum"),
                )
                .rename(columns={"Aba_Origem": "Período / Aba", "CH_Total": "CH Total (h)"})
            )
            st.dataframe(resumo, width="stretch", hide_index=True)

    with sub3:
        col_c1, col_c2 = st.columns(2)
        filtro_vinculo = col_c1.multiselect(
            "Vínculo",
            sorted(df_cred["Vínculo"].unique().tolist()),
            default=sorted(df_cred["Vínculo"].unique().tolist()),
        )
        busca_cred = col_c2.text_input("Buscar por docente ou disciplina habilitada", placeholder="Ex.: Termodinâmica, Diego...")
        df_cred_view = df_cred[df_cred["Vínculo"].isin(filtro_vinculo)].copy()
        if busca_cred.strip():
            t_c = norm(busca_cred)
            df_cred_view = df_cred_view[
                df_cred_view["Docente"].apply(lambda x: t_c in norm(x))
                | df_cred_view["Componente Curricular Habilitado"].apply(lambda x: t_c in norm(x))
            ]
        st.dataframe(df_cred_view, width="stretch", hide_index=True)

    with sub4:
        st.subheader("Estruturas Curriculares Vigentes no SIGAA (BICT24, EMEC21, EFIS17 e EFIS23)")
        st.caption("Base oficial extraída dos currículos do Portal do Coordenador SIGAA para alimentação das planilhas de oferta.")
        df_est_all = gerar_tabela_estruturas_sigaa()
        c_s1, c_s2, c_s3 = st.columns([1.2, 1.2, 1.6])
        matrizes_sel = c_s1.multiselect(
            "Matriz Curricular:",
            ["BICT24", "EMEC21", "EFIS17", "EFIS23"],
            default=["BICT24", "EMEC21", "EFIS17", "EFIS23"],
        )
        nat_sel = c_s2.multiselect(
            "Natureza:",
            ["OBRIGATÓRIO", "OPTATIVO"],
            default=["OBRIGATÓRIO", "OPTATIVO"],
        )
        busca_sigaa = c_s3.text_input("Buscar código ou disciplina SIGAA:", placeholder="Ex.: EMEC0018, SFIS0007, SBCT...")

        df_est_view = df_est_all[
            df_est_all["Matriz"].isin(matrizes_sel) & df_est_all["Natureza"].isin(nat_sel)
        ].copy()
        if busca_sigaa.strip():
            ts = norm(busca_sigaa)
            df_est_view = df_est_view[
                df_est_view["Código_SIGAA"].apply(lambda x: ts in norm(x))
                | df_est_view["Componente_Curricular"].apply(lambda x: ts in norm(x))
            ]
        st.dataframe(
            df_est_view,
            width="stretch",
            hide_index=True,
            column_config={
                "Código_SIGAA": "Código SIGAA",
                "Componente_Curricular": "Componente Curricular",
                "CH_SIGAA": st.column_config.NumberColumn("CH Oficial", format="%d h"),
            },
        )