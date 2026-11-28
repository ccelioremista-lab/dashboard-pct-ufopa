"""
modulos/agente_ia.py
Assistente IA da Coordenação (LangChain + Groq) — PC&T / UFOPA

Responsabilidades:
1. Montar um contexto compacto e fiel à oferta ativa (KPIs, Malha Fina IR, Encargo Docente,
   ocupação das 5 salas do PC&T, salas externas no NSA e sugestões para turmas sem docente).
2. Responder perguntas da Coordenação usando LangChain + Groq com detecção automática do
   modelo ativo na conta quando a GROQ_API_KEY estiver configurada.
3. Oferecer um modo Assistente Local (sem chave de API) para consultas rápidas imediatas.
"""

from __future__ import annotations

import os

import pandas as pd

from modulos.dados import SALAS_EXTERNAS_NSA, SALAS_PCT, norm
from modulos.regras import executar_malha_fina_ir, sugerir_docentes_habilitados
from modulos.visualizacoes import calcular_resumo_ocupacao_espacos


def montar_contexto_coordenacao(
    df_oferta: pd.DataFrame,
    df_cred: pd.DataFrame,
    piso_ch: int = 120,
    teto_ch: int = 240,
) -> str:
    """Resume o estado atual da oferta em texto estruturado para o LLM."""
    df_pend, df_enc, unif_sec, resumo_ir = executar_malha_fina_ir(
        df_oferta, df_cred, piso_ch=piso_ch, teto_ch=teto_ch
    )
    df_ocup = calcular_resumo_ocupacao_espacos(df_oferta, unif_sec)

    turmas_ext = df_oferta[df_oferta["Sala_Alocada"].isin(SALAS_EXTERNAS_NSA)]
    sem_doc = df_oferta[df_oferta["Docente_Alocado"].isin(["CONCURSO", "A definir"])]

    bloco_kpis = (
        f"RESUMO DA OFERTA ATIVA (PC&T / IEG / UFOPA):\n"
        f"- Total de turmas: {len(df_oferta)} | CH total: {int(df_oferta['CH_Total'].sum())}h\n"
        f"- Erros Impeditivos (IR): {resumo_ir['erros']} | Avisos (IR): {resumo_ir['avisos']}\n"
        f"- Choques: {resumo_ir['choques_turma']} turma, {resumo_ir['choques_docente']} docente, {resumo_ir['choques_sala']} sala\n"
        f"- Sem docente: {resumo_ir['sem_docente']} | Sem sala: {resumo_ir['sem_sala']}\n"
        f"- Turmas em salas externas no NSA (105A–110B): {len(turmas_ext)}\n"
        f"- Faixa regimental: piso {piso_ch}h, teto {teto_ch}h\n"
    )

    erros_top = df_pend[df_pend["Severidade"].str.contains("ERRO")].head(20)
    bloco_erros = (
        "PRINCIPAIS ERROS IMPEDITIVOS (MALHA FINA IR):\n"
        + (
            erros_top[["Código_Regra", "Alvo", "Descrição", "Ação_Recomendada"]].to_string(index=False)
            if not erros_top.empty
            else "Nenhum erro impeditivo ativo!"
        )
    )

    efetivos = df_enc[df_enc["Vínculo"] == "PC&T (Permanente)"][
        ["Docente", "CH_Efetiva", "Saldo_Teto", "Status_Encargo"]
    ]
    bloco_enc = "ENCARGO EFETIVO DOS 19 DOCENTES PC&T:\n" + efetivos.to_string(index=False)

    salas_5 = df_ocup[df_ocup["Espaço / Sala"].isin(SALAS_PCT)][
        ["Espaço / Sala", "Capacidade", "Turmas", "Slots_Ocupados", "Livres_Diurno", "Choques_Slot"]
    ]
    bloco_salas = "OCUPAÇÃO DAS 5 SALAS PRÓPRIAS DO PC&T:\n" + salas_5.to_string(index=False)

    if not turmas_ext.empty:
        bloco_ext = (
            "TURMAS EM SALAS EXTERNAS DO NSA (SOLICITAÇÃO/CONFIRMAÇÃO CAC/IEG):\n"
            + turmas_ext[
                ["Aba_Origem", "Código_SIGAA", "Componente_Curricular", "Horário_SIGAA", "Sala_Alocada", "Vagas"]
            ].to_string(index=False)
        )
    else:
        bloco_ext = "TURMAS EM SALAS EXTERNAS DO NSA:\nNenhuma turma alocada em sala externa."

    if not sem_doc.empty:
        linhas_sem_doc = ["TURMAS SEM DOCENTE E CANDIDATOS HABILITADOS (COM SALDO ATÉ O TETO):"]
        for _, r in sem_doc.iterrows():
            sugs = sugerir_docentes_habilitados(
                r["Componente_Curricular"], df_cred, df_enc, teto_ch=teto_ch, limite=4
            )
            txt_sugs = " | ".join(sugs) if sugs else "Sem correspondência exata na matriz PPC."
            linhas_sem_doc.append(
                f"- [{r['Aba_Origem']}] {r['Código_SIGAA']} - {r['Componente_Curricular']} "
                f"({int(r['CH_Total'])}h, {r['Horário_SIGAA']}): {txt_sugs}"
            )
        bloco_sem_doc = "\n".join(linhas_sem_doc)
    else:
        bloco_sem_doc = "TURMAS SEM DOCENTE:\nTodas as turmas possuem docente alocado."

    return (
        f"{bloco_kpis}\n"
        f"{bloco_salas}\n\n"
        f"{bloco_ext}\n\n"
        f"{bloco_sem_doc}\n\n"
        f"{bloco_enc}\n\n"
        f"{bloco_erros}"
    )


def responder_modo_local(
    pergunta: str,
    df_oferta: pd.DataFrame,
    df_cred: pd.DataFrame,
    piso_ch: int = 120,
    teto_ch: int = 240,
) -> str:
    """Responde consultas frequentes localmente sem exigir chave da Groq."""
    p = norm(pergunta)
    df_pend, df_enc, unif_sec, resumo_ir = executar_malha_fina_ir(
        df_oferta, df_cred, piso_ch=piso_ch, teto_ch=teto_ch
    )
    df_ocup = calcular_resumo_ocupacao_espacos(df_oferta, unif_sec)

    if any(k in p for k in ("erro", "malha", "pendencia", "choque", "resumo")):
        top = df_pend[df_pend["Severidade"].str.contains("ERRO")].head(8)
        linhas = [
            f"**Diagnóstico Atual (Modo Local):** `{resumo_ir['erros']}` erro(s) impeditivo(s) e `{resumo_ir['avisos']}` aviso(s).",
            f"- Choques: `{resumo_ir['choques_turma']}` turma | `{resumo_ir['choques_docente']}` docente | `{resumo_ir['choques_sala']}` sala",
            f"- Sem docente: `{resumo_ir['sem_docente']}` | Sem sala: `{resumo_ir['sem_sala']}`",
        ]
        if not top.empty:
            linhas.append("\n**Primeiros erros impeditivos:**")
            for _, r in top.iterrows():
                linhas.append(f"- **{r['Código_Regra']}** (`{r['Alvo']}`): {r['Descrição']}")
        return "\n".join(linhas)

    if any(k in p for k in ("sala", "209", "206", "203", "207", "208", "livre")):
        salas_5 = df_ocup[df_ocup["Espaço / Sala"].isin(SALAS_PCT)]
        linhas = ["**Situação das 5 Salas Próprias do PC&T (Modo Local):**"]
        for _, r in salas_5.iterrows():
            linhas.append(
                f"- **{r['Espaço / Sala']}** ({r['Capacidade']} lug.): `{r['Slots_Ocupados']}` slots ocupados, "
                f"`{r['Livres_Diurno']}` janelas diurnas livres, `{r['Choques_Slot']}` choque(s)."
            )
        return "\n".join(linhas)

    if any(k in p for k in ("quem pode", "suger", "concurso", "definir", "docente", "saldo")):
        sem_doc = df_oferta[df_oferta["Docente_Alocado"].isin(["CONCURSO", "A definir"])]
        if sem_doc.empty:
            return "✅ Todas as turmas da oferta ativa já possuem docente alocado!"
        linhas = ["**Sugestões de Docentes Habilitados para Turmas sem Docente (Modo Local):**"]
        for _, r in sem_doc.iterrows():
            sugs = sugerir_docentes_habilitados(r["Componente_Curricular"], df_cred, df_enc, teto_ch=teto_ch)
            txt = " | ".join(sugs) if sugs else "Sem correspondência exata na matriz PPC."
            linhas.append(f"- **[{r['Aba_Origem']}] {r['Componente_Curricular']}** ({r['CH_Total']}h): {txt}")
        return "\n".join(linhas)

    if "oficio" in p:
        salas_ext = int(df_oferta["Sala_Alocada"].isin(SALAS_EXTERNAS_NSA).sum())
        return (
            "**Rascunho Rápido de Ofício (Modo Local):**\n\n"
            "Ofício nº ___/2026 - Coordenação do PC&T/IEG/UFOPA\n"
            "Santarém-PA, ___ de ________ de 2026.\n\n"
            "À Direção do Instituto de Engenharia e Geociências — IEG/UFOPA\n"
            "Assunto: Encaminhamento do panorama da oferta ativa do PC&T.\n\n"
            f"Encaminhamos o panorama atual contendo **{len(df_oferta)} turmas**, "
            f"**{resumo_ir['erros']} erro(s) impeditivo(s)**, **{resumo_ir['sem_docente']} turma(s) sem docente** "
            f"e **{salas_ext} turma(s) em salas externas do NSA**.\n\n"
            "Para redação completa e detalhada, configure uma `GROQ_API_KEY` gratuita."
        )

    return (
        "Estou no **Modo Local** (sem chave Groq). Posso responder instantaneamente sobre:\n"
        "- *'Resumo dos erros da Malha Fina'*\n"
        "- *'Como estão as 5 salas próprias do PC&T?'*\n"
        "- *'Quem pode assumir as turmas sem docente?'*\n"
        "- *'Rascunho de ofício ao IEG'*\n\n"
        "Para análises livres, redação completa de ofícios ao IEG ou simulações em linguagem natural, "
        "informe sua **GROQ_API_KEY** gratuita nas configurações acima."
    )


def consultar_agente_groq(
    pergunta: str,
    df_oferta: pd.DataFrame,
    df_cred: pd.DataFrame,
    api_key: str = "",
    modelo: str = "",
    piso_ch: int = 120,
    teto_ch: int = 240,
) -> tuple[str, str]:
    """
    Envia a pergunta ao modelo Groq via LangChain com detecção automática de modelo ativo.
    Retorna (resposta_markdown, modo_utilizado).
    """
    chave = (api_key or os.environ.get("GROQ_API_KEY", "")).strip()
    if not chave:
        return responder_modo_local(pergunta, df_oferta, df_cred, piso_ch, teto_ch), "Modo Local"

    try:
        from groq import Groq
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_groq import ChatGroq
    except ImportError as exc:
        return (
            f"⚠️ Dependência ausente (`{exc}`). Rode `pip install langchain-groq groq`.",
            "Erro Dependência",
        )

    # Descobre dinamicamente os modelos de texto habilitados na sua conta Groq
    modelos_tentativa: list[str] = []
    filtros_excluir = ("whisper", "guard", "tts", "safeguard", "playai", "orpheus")
    try:
        cliente_nativo = Groq(api_key=chave)
        ativos = [
            m.id
            for m in cliente_nativo.models.list().data
            if getattr(m, "active", True)
            and not any(x in m.id.lower() for x in filtros_excluir)
        ]
        # Prioriza modelos Llama, GPT-OSS, Qwen ou Gemma disponíveis na conta
        prioritarios = [m for m in ativos if any(k in m.lower() for k in ("llama", "gpt-oss", "qwen", "gemma"))]
        outros = [m for m in ativos if m not in prioritarios]
        if modelo.strip() and modelo.strip() in ativos:
            modelos_tentativa.append(modelo.strip())
        for candidato in prioritarios + outros:
            if candidato not in modelos_tentativa:
                modelos_tentativa.append(candidato)
    except Exception:
        if modelo.strip():
            modelos_tentativa.append(modelo.strip())

    if not modelos_tentativa:
        return (
            "⚠️ Não foi possível listar modelos ativos na sua conta Groq. Verifique a chave em console.groq.com.",
            "Erro API",
        )

    contexto = montar_contexto_coordenacao(df_oferta, df_cred, piso_ch=piso_ch, teto_ch=teto_ch)
    mensagens = [
        SystemMessage(
            content=(
                "Você é o Assistente Oficial da Coordenação do Programa em Ciência e Tecnologia (PC&T) "
                "do Instituto de Engenharia e Geociências (IEG/UFOPA — Santarém-PA).\n"
                "Diretrizes obrigatórias:\n"
                "1. Responda sempre em português do Brasil, de forma objetiva, técnica e fiel aos dados fornecidos.\n"
                "2. Nunca invente docentes, disciplinas, códigos ou salas que não estejam no contexto abaixo; "
                "se um dado não constar, informe explicitamente.\n"
                "3. Cite os códigos das regras da Malha Fina (IR-01 a IR-04), cargas horárias (piso/teto) e nomes "
                "exatos das salas (próprias do PC&T e blocos do NSA) sempre que aplicável.\n"
                "4. Quando solicitado um ofício, memorando ou encaminhamento ao IEG, redija no padrão institucional "
                "da UFOPA: cabeçalho ('Ofício nº ___/2026 - Coordenação do PC&T/IEG/UFOPA', Santarém-PA), "
                "destinatário ('À Direção do Instituto de Engenharia e Geociências — IEG/UFOPA'), Assunto, "
                "corpo técnico com os números reais da oferta ativa e fecho formal da Coordenação do PC&T.\n\n"
                f"{contexto}"
            )
        ),
        HumanMessage(content=pergunta),
    ]

    ultimo_erro = None
    for modelo_atual in modelos_tentativa:
        try:
            llm = ChatGroq(api_key=chave, model=modelo_atual, temperature=0.2)
            resposta = llm.invoke(mensagens)
            return resposta.content, f"Groq ({modelo_atual})"
        except Exception as exc:
            ultimo_erro = exc
            if "model_not_found" in str(exc) or "404" in str(exc):
                continue
            return f"⚠️ Erro ao consultar a API da Groq: {exc}", "Erro API"

    return (
        f"⚠️ Nenhum modelo da conta Groq aceitou a requisição. Modelos testados: `{modelos_tentativa}`. Último erro: {ultimo_erro}",
        "Erro API",
    )