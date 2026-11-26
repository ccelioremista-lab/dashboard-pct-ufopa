"""
modulos/agente_ia.py
Assistente IA da Coordenação (LangChain + Groq) — PC&T / UFOPA (Etapa 6)

Responsabilidades:
1. Montar um contexto compacto e fiel à oferta ativa (KPIs, Malha Fina IR, Encargo Docente,
   ocupação das 5 salas do PC&T e matriz de credenciamento).
2. Responder perguntas da Coordenação usando LangChain + Groq (Llama 3.3 70B) quando a
   GROQ_API_KEY for informada.
3. Oferecer um modo Assistente Local (sem chave de API) para consultas rápidas imediatas.
"""

from __future__ import annotations

import os

import pandas as pd

from modulos.dados import SALAS_PCT, norm
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

    bloco_kpis = (
        f"RESUMO DA OFERTA ATIVA (PC&T / IEG / UFOPA):\n"
        f"- Total de turmas: {len(df_oferta)} | CH total: {int(df_oferta['CH_Total'].sum())}h\n"
        f"- Erros Impeditivos (IR): {resumo_ir['erros']} | Avisos (IR): {resumo_ir['avisos']}\n"
        f"- Choques: {resumo_ir['choques_turma']} turma, {resumo_ir['choques_docente']} docente, {resumo_ir['choques_sala']} sala\n"
        f"- Sem docente: {resumo_ir['sem_docente']} | Sem sala: {resumo_ir['sem_sala']}\n"
        f"- Faixa regimental: piso {piso_ch}h, teto {teto_ch}h\n"
    )

    erros_top = df_pend[df_pend["Severidade"].str.contains("ERRO")].head(20)
    bloco_erros = (
        "PRINCIPAIS ERROS IMPEDITIVOS (MALHA FINA IR):\n"
        + (erros_top[["Código_Regra", "Alvo", "Descrição", "Ação_Recomendada"]].to_string(index=False)
           if not erros_top.empty else "Nenhum erro impeditivo ativo!")
    )

    efetivos = df_enc[df_enc["Vínculo"] == "PC&T (Permanente)"][["Docente", "CH_Efetiva", "Saldo_Teto", "Status_Encargo"]]
    bloco_enc = "ENCARGO EFETIVO DOS 19 DOCENTES PC&T:\n" + efetivos.to_string(index=False)

    salas_5 = df_ocup[df_ocup["Espaço / Sala"].isin(SALAS_PCT)][
        ["Espaço / Sala", "Capacidade", "Turmas", "Slots_Ocupados", "Livres_Diurno", "Choques_Slot"]
    ]
    bloco_salas = "OCUPAÇÃO DAS 5 SALAS PRÓPRIAS DO PC&T:\n" + salas_5.to_string(index=False)

    return f"{bloco_kpis}\n{bloco_salas}\n\n{bloco_enc}\n\n{bloco_erros}"


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

    return (
        "Estou no **Modo Local** (sem chave Groq). Posso responder instantaneamente sobre:\n"
        "- *'Resumo dos erros da Malha Fina'*\n"
        "- *'Como estão as 5 salas próprias do PC&T?'*\n"
        "- *'Quem pode assumir as turmas sem docente?'*\n\n"
        "Para análises livres, redação de ofícios ao IEG ou simulações em linguagem natural, "
        "informe sua **GROQ_API_KEY** gratuita no campo acima."
    )


def consultar_agente_groq(
    pergunta: str,
    df_oferta: pd.DataFrame,
    df_cred: pd.DataFrame,
    api_key: str = "",
    modelo: str = "llama-3.3-70b-versatile",
    piso_ch: int = 120,
    teto_ch: int = 240,
) -> tuple[str, str]:
    """
    Envia a pergunta ao modelo Groq via LangChain com o contexto real da oferta ativa.
    Retorna (resposta_markdown, modo_utilizado).
    """
    chave = (api_key or os.environ.get("GROQ_API_KEY", "")).strip()
    if not chave:
        return responder_modo_local(pergunta, df_oferta, df_cred, piso_ch=piso_ch, teto_ch=teto_ch), "Local (sem API)"

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_groq import ChatGroq
    except ImportError as exc:
        return (
            f"Biblioteca `langchain-groq` indisponível ({exc}). Usando modo local:\n\n"
            + responder_modo_local(pergunta, df_oferta, df_cred, piso_ch=piso_ch, teto_ch=teto_ch),
            "Fallback Local",
        )

    contexto = montar_contexto_coordenacao(df_oferta, df_cred, piso_ch=piso_ch, teto_ch=teto_ch)
    sistema = (
        "Você é o Assistente Técnico de Oferta e Credenciamento Docente do Programa de Ciência e Tecnologia "
        "(PC&T / IEG / UFOPA). Responda sempre em português do Brasil, de forma objetiva, prática e fiel "
        "aos dados reais fornecidos abaixo. Nunca invente horários, salas ou docentes que não estejam nos dados.\n\n"
        + contexto
    )

    try:
        llm = ChatGroq(api_key=chave, model=modelo, temperature=0.2)
        resp = llm.invoke([SystemMessage(content=sistema), HumanMessage(content=pergunta)])
        return str(resp.content), f"Groq ({modelo})"
    except Exception as exc:
        return f"⚠️ Erro ao consultar a API da Groq: `{exc}`", "Erro API"
