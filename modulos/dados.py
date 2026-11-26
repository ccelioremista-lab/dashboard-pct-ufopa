"""
modulos/dados.py
Camada de Dados, Estruturas Curriculares Oficiais (SIGAA) e Normalização — PC&T / IEG / UFOPA

Responsabilidades:
1. Centralizar as 4 Estruturas Curriculares Oficiais vigentes no SIGAA:
   - BICT24 (BI em Ciência e Tecnologia — ingressantes a partir de 2024.1)
   - EMEC21 (Engenharia Mecânica — todos os ingressantes, matriz 2021.1)
   - EFIS17 (Engenharia Física — ingressantes no BI anteriores a 2024, matriz 2017.1)
   - EFIS23 (Engenharia Física — ingressantes a partir de 2024, matriz 2023.1)
2. Padronizar nomes de docentes (unificando grafias e removendo egressos).
3. Centralizar o inventário oficial das 5 salas próprias do PC&T (NSA) + laboratórios.
4. Mapear famílias de componentes curriculares autorizados para unificação entre cursos.
5. Expandir códigos de horário no padrão SIGAA (ex.: '24M12 / 4M3' -> slots individuais).
6. Carregar dados a partir da planilha consolidada (.xlsx) ou da base embutida de 2027.1.
"""

from __future__ import annotations

import os
import re
import unicodedata
from typing import Any

import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DADOS_DIR = os.path.join(BASE_DIR, "dados")

# ==============================================================================
# 1. NORMALIZAÇÃO DE TEXTO E CONSTANTES INSTITUCIONAIS
# ==============================================================================
def norm(texto: Any) -> str:
    """Remove acentos, espaços extras e converte para minúsculas."""
    if pd.isna(texto):
        return ""
    s = str(texto).strip().lower()
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


# Quadro de egressos (removidos definitivamente do quadro ativo do PC&T)
DOCENTES_REMOVIDOS = {
    "Bruno Apolo Miranda Figueira",
    "Kléber Agustin Sabat da Cruz",
    "Prince Azsembergh Nogueira de Carvalho",
}

# Mapeamento canônico de nomes/abreviações encontrados nas planilhas históricas
DOCENTE_CANON_MAP = {
    "carlos celio": "Carlos Célio Sousa da Cruz",
    "carlos celio sousa da cruz": "Carlos Célio Sousa da Cruz",
    "josecley fialho": "Josecley Fialho Góes",
    "josecley fialho goes": "Josecley Fialho Góes",
    "jose roberto": "José Roberto Branco Ramos Filho",
    "jose roberto branco": "José Roberto Branco Ramos Filho",
    "vicente moreira": "Vicente Moreira Rodrigues",
    "gilson fernandes": "Gilson Fernandes Braga Junior",
    "gilson dividido bi": "Gilson Fernandes Braga Junior",
    "nelson amorim": "Nelson de Souza Amorim",
    "marcel antonionni": "Marcel Antonionni de Andrade Romano",
    "marcel antonionniu": "Marcel Antonionni de Andrade Romano",
    "lazaro": "Lázaro João Santana da Silva",
    "lazaro santana": "Lázaro João Santana da Silva",
    "aldo queiroz": "Aldo Gomes Queiroz",
    "aldo gomes queiroz": "Aldo Gomes Queiroz",
    "estefany": "Estefany Miléo de Couto",
    "estefany couto": "Estefany Miléo de Couto",
    "manoel neto": "Manoel Maria Bezerra Neto",
    "manoel maria neto": "Manoel Maria Bezerra Neto",
    "manoel roberval": "Manoel Roberval Pimentel Santos",
    "querem hapuque": "Querem Hapuque Felix Rebelo",
    "thiago augusto": "Thiago Augusto de Sousa Moreira",
    "thiago moreira": "Thiago Augusto de Sousa Moreira",
    "thiago augusto de sousa moreira": "Thiago Augusto de Sousa Moreira",
    "thiago moreira (duas turmas)": "Thiago Augusto de Sousa Moreira",
    "ubiraelson de lima": "Ubiraelson de Lima Ruela",
    "ubiraelson ruela": "Ubiraelson de Lima Ruela",
    "anderson alvarenga": "Anderson Alvarenga de Moura Meneses",
    "paula renatha": "Paula Renatha Nunes da Silva",
    # Correção validada pelo coordenador: Diego Jorge Borges é docente efetivo PC&T
    "diego borges": "Diego Jorge Borges",
    "diego jorge": "Diego Jorge Borges",
    "diego jorge borges": "Diego Jorge Borges",
    "cassio andre": "Cássio André",
    "alexandro arruda": "Alexandro Arruda",
    "cintya de azambuja": "Cintya de Azambuja",
    "elden marialva": "Elden Marialva",
    "concurso": "CONCURSO",
    "a definir": "A definir",
}

# ==============================================================================
# 2. ESTRUTURAS CURRICULARES OFICIAIS DO SIGAA (BICT24, EMEC21, EFIS17, EFIS23)
# ==============================================================================
# Tuplas: (Matriz, Curso, Nível, Código_SIGAA, Componente_Curricular, CH_Total, Natureza)
ESTRUTURAS_CURRICULARES_SIGAA: list[tuple[str, str, str, str, str, int, str]] = [
    # --------------------------------------------------------------------------
    # BICT24 — Bacharelado Interdisciplinar em Ciência e Tecnologia (2024.1+)
    # --------------------------------------------------------------------------
    ("BICT24", "BI C&T", "1º", "CTEC0001", "Fundamentos de Matemática", 45, "OBRIGATÓRIO"),
    ("BICT24", "BI C&T", "1º", "CTEC0002", "Química Geral", 60, "OBRIGATÓRIO"),
    ("BICT24", "BI C&T", "1º", "CTEC0004", "Programação I", 60, "OBRIGATÓRIO"),
    ("BICT24", "BI C&T", "1º", "IEG010009", "Cálculo I", 60, "OBRIGATÓRIO"),
    ("BICT24", "BI C&T", "1º", "IEG10008", "Geometria Analítica", 60, "OBRIGATÓRIO"),
    ("BICT24", "BI C&T", "1º", "PCT30022", "Desenho Técnico", 60, "OBRIGATÓRIO"),
    ("BICT24", "BI C&T", "1º", "SBCT0005", "Laboratório de Química Geral", 30, "OBRIGATÓRIO"),
    ("BICT24", "BI C&T", "2º", "CTEC0005", "Projeto Auxiliado por Computador", 60, "OBRIGATÓRIO"),
    ("BICT24", "BI C&T", "2º", "IEG010011", "Linguagem e Comunicação", 60, "OBRIGATÓRIO"),
    ("BICT24", "BI C&T", "2º", "IEG020001", "Cálculo II", 60, "OBRIGATÓRIO"),
    ("BICT24", "BI C&T", "2º", "IEG020002", "Álgebra Linear", 60, "OBRIGATÓRIO"),
    ("BICT24", "BI C&T", "2º", "IEG030003", "Física I", 60, "OBRIGATÓRIO"),
    ("BICT24", "BI C&T", "2º", "IEG030004", "Laboratório de Física I", 30, "OBRIGATÓRIO"),
    ("BICT24", "BI C&T", "2º", "PCT30027", "Introdução à Probabilidade e Estatística", 60, "OBRIGATÓRIO"),
    ("BICT24", "BI C&T", "3º", "CTEC0006", "Metodologia Científica", 60, "OBRIGATÓRIO"),
    ("BICT24", "BI C&T", "3º", "IEG010001", "Introdução à Engenharia", 60, "OBRIGATÓRIO"),
    ("BICT24", "BI C&T", "3º", "IEG010012", "Física II", 60, "OBRIGATÓRIO"),
    ("BICT24", "BI C&T", "3º", "IEG020018", "Cálculo III", 60, "OBRIGATÓRIO"),
    ("BICT24", "BI C&T", "3º", "PCT30021", "Conservação dos Recursos Ambientais", 45, "OBRIGATÓRIO"),
    ("BICT24", "BI C&T", "3º", "PCT30033", "Laboratório de Física II", 30, "OBRIGATÓRIO"),
    ("BICT24", "BI C&T", "3º", "PCT30034", "Fundamentos da Termodinâmica", 60, "OBRIGATÓRIO"),
    ("BICT24", "BI C&T", "4º", "CTEC0007", "Fenômenos de Transporte", 60, "OBRIGATÓRIO"),
    ("BICT24", "BI C&T", "4º", "CTEC0008", "Programação II", 60, "OBRIGATÓRIO"),
    ("BICT24", "BI C&T", "4º", "CTEC0009", "Metrologia", 45, "OBRIGATÓRIO"),
    ("BICT24", "BI C&T", "4º", "EFIS0005", "Fundamentos da Administração", 60, "OBRIGATÓRIO"),
    ("BICT24", "BI C&T", "4º", "IEG020033", "Cálculo IV", 60, "OBRIGATÓRIO"),
    ("BICT24", "BI C&T", "4º", "IEG020065", "Física III", 60, "OBRIGATÓRIO"),
    ("BICT24", "BI C&T", "4º", "PCT30008", "Laboratório de Física III", 30, "OBRIGATÓRIO"),
    ("BICT24", "BI C&T", "5º", "PCT30018", "Mecânica dos Sólidos", 60, "OBRIGATÓRIO"),
    ("BICT24", "BI C&T", "5º", "PCT30038", "Cálculo Numérico", 60, "OBRIGATÓRIO"),
    ("BICT24", "BI C&T", "5º", "PCT30069", "Ciências e Tecnologia dos Materiais", 60, "OBRIGATÓRIO"),
    ("BICT24", "BI C&T", "6º", "PCT30010", "Legislação e Segurança no Trabalho", 45, "OBRIGATÓRIO"),
    ("BICT24", "BI C&T", "6º", "PCT30049", "Trabalho de Conclusão de Curso", 60, "OBRIGATÓRIO"),
    ("BICT24", "BI C&T", "6º", "SBCT0002", "Atividades de Extensão", 260, "OBRIGATÓRIO"),
    ("BICT24", "BI C&T", "6º", "SFIS0005", "Introdução à Economia", 45, "OBRIGATÓRIO"),
    # Optativas BICT24
    ("BICT24", "BI C&T", "Optativa", "ANT100030", "Relações Étnico-Raciais", 60, "OPTATIVO"),
    ("BICT24", "BI C&T", "Optativa", "AUT0002", "Processos em Engenharia", 60, "OPTATIVO"),
    ("BICT24", "BI C&T", "Optativa", "CFI010001", "Sociedade, Natureza e Desenvolvimento", 75, "OPTATIVO"),
    ("BICT24", "BI C&T", "Optativa", "CFI010002", "Estudos Integrativos da Amazônia", 75, "OPTATIVO"),
    ("BICT24", "BI C&T", "Optativa", "CFI010003", "Origem e Evolução do Conhecimento", 75, "OPTATIVO"),
    ("BICT24", "BI C&T", "Optativa", "EFIS0002", "Máquinas Elétricas", 90, "OPTATIVO"),
    ("BICT24", "BI C&T", "Optativa", "EFIS0003", "Turbomáquinas", 60, "OPTATIVO"),
    ("BICT24", "BI C&T", "Optativa", "EFIS0007", "Direitos Humanos", 60, "OPTATIVO"),
    ("BICT24", "BI C&T", "Optativa", "EFIS0008", "Libras - Língua Brasileira de Sinais", 60, "OPTATIVO"),
    ("BICT24", "BI C&T", "Optativa", "EFIS0009", "Políticas de Educação Ambiental", 60, "OPTATIVO"),
    ("BICT24", "BI C&T", "Optativa", "EFIS0016", "Elementos de Máquinas", 60, "OPTATIVO"),
    ("BICT24", "BI C&T", "Optativa", "EFIS0019", "Controle Avançado", 60, "OPTATIVO"),
    ("BICT24", "BI C&T", "Optativa", "EFIS0020", "Automação e Supervisão de Processos", 60, "OPTATIVO"),
    ("BICT24", "BI C&T", "Optativa", "EFIS0021", "Acionamentos Elétricos", 60, "OPTATIVO"),
    ("BICT24", "BI C&T", "Optativa", "EFIS0024", "Inteligência Computacional", 60, "OPTATIVO"),
    ("BICT24", "BI C&T", "Optativa", "EFIS0036", "Processos de Fabricação", 60, "OPTATIVO"),
    ("BICT24", "BI C&T", "Optativa", "ICED540011", "Educação e Relações Étnico Raciais", 60, "OPTATIVO"),
    ("BICT24", "BI C&T", "Optativa", "ICS010005", "Saber Local e Diversidade Cultural", 60, "OPTATIVO"),
    ("BICT24", "BI C&T", "Optativa", "IEG070018", "Física Moderna", 60, "OPTATIVO"),
    ("BICT24", "BI C&T", "Optativa", "IEG070054", "Métodos Matemáticos II", 60, "OPTATIVO"),
    ("BICT24", "BI C&T", "Optativa", "IEG070056", "Sistemas de Controle", 60, "OPTATIVO"),
    ("BICT24", "BI C&T", "Optativa", "IEG070107", "Teoria Eletromagnética I", 60, "OPTATIVO"),
    ("BICT24", "BI C&T", "Optativa", "IEG070109", "Modelagem Computacional I", 60, "OPTATIVO"),
    ("BICT24", "BI C&T", "Optativa", "IEG10007", "Ambiente, Tecnologia e Sociedade", 60, "OPTATIVO"),
    ("BICT24", "BI C&T", "Optativa", "PCT30017", "Mecânica dos Fluidos", 60, "OPTATIVO"),
    ("BICT24", "BI C&T", "Optativa", "PCT30029", "Laboratório de Mecânica dos Fluidos", 30, "OPTATIVO"),
    ("BICT24", "BI C&T", "Optativa", "PCT30040", "Gestão e Auditoria Ambiental", 60, "OPTATIVO"),
    ("BICT24", "BI C&T", "Optativa", "PCT30047", "Energias Renováveis e Sustentabilidade", 60, "OPTATIVO"),
    ("BICT24", "BI C&T", "Optativa", "PCT30050", "Física IV", 60, "OPTATIVO"),
    ("BICT24", "BI C&T", "Optativa", "PCT30051", "Laboratório de Física IV", 30, "OPTATIVO"),
    ("BICT24", "BI C&T", "Optativa", "PCT30052", "Termodinâmica Aplicada", 90, "OPTATIVO"),
    ("BICT24", "BI C&T", "Optativa", "PCT30053", "Circuitos Elétricos", 60, "OPTATIVO"),
    ("BICT24", "BI C&T", "Optativa", "PCT30054", "Laboratório de Circuitos Elétricos", 30, "OPTATIVO"),
    ("BICT24", "BI C&T", "Optativa", "PCT30060", "Eletrônica Básica", 60, "OPTATIVO"),
    ("BICT24", "BI C&T", "Optativa", "PCT30061", "Laboratório de Eletrônica Básica", 30, "OPTATIVO"),
    ("BICT24", "BI C&T", "Optativa", "PCT30064", "Mecânica Clássica", 60, "OPTATIVO"),
    ("BICT24", "BI C&T", "Optativa", "SBCT0003", "Processamento Digital de Sinais", 90, "OPTATIVO"),
    ("BICT24", "BI C&T", "Optativa", "SBCT0004", "Métodos Matemáticos I", 45, "OPTATIVO"),
    ("BICT24", "BI C&T", "Optativa", "SFIS0003", "Química Tecnológica", 45, "OPTATIVO"),

    # --------------------------------------------------------------------------
    # EMEC21 — Bacharelado em Engenharia Mecânica (Todos os ingressantes)
    # --------------------------------------------------------------------------
    ("EMEC21", "Eng. Mecânica", "1º", "CTEC0001", "Fundamentos de Matemática", 45, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "1º", "CTEC0002", "Química Geral", 60, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "1º", "CTEC0003", "Laboratório de Química Geral", 30, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "1º", "CTEC0004", "Programação I", 60, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "1º", "EMEC0001", "Introdução à Engenharia Mecânica", 30, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "1º", "IEG010009", "Cálculo I", 60, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "1º", "IEG10008", "Geometria Analítica", 60, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "1º", "PCT30022", "Desenho Técnico", 60, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "2º", "CTEC0006", "Metodologia Científica", 60, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "2º", "EMEC0002", "Desenho Técnico Mecânico I", 60, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "2º", "EMEC0003", "Química Tecnológica", 45, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "2º", "IEG020001", "Cálculo II", 60, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "2º", "IEG020002", "Álgebra Linear", 60, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "2º", "IEG030003", "Física I", 60, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "2º", "IEG030004", "Laboratório de Física I", 30, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "2º", "PCT30027", "Introdução à Probabilidade e Estatística", 60, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "3º", "EMEC0004", "Mecânica Geral I", 60, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "3º", "EMEC0005", "Desenho Técnico Mecânico II", 45, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "3º", "EMEC0008", "Oficinas", 30, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "3º", "IEG010012", "Física II", 60, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "3º", "IEG020018", "Cálculo III", 60, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "3º", "PCT30033", "Laboratório de Física II", 30, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "3º", "PCT30037", "Métodos Matemáticos I", 60, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "3º", "PCT30038", "Cálculo Numérico", 60, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "4º", "EMEC0009", "Física III", 60, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "4º", "EMEC0010", "Resistência dos Materiais I", 60, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "4º", "EMEC0011", "Mecânica Geral II", 60, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "4º", "EMEC0012", "Fundamentos de Engenharia Ambiental", 45, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "4º", "EMEC0013", "Engenharia Econômica", 45, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "4º", "IEG020033", "Cálculo IV", 60, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "4º", "IEG070054", "Métodos Matemáticos II", 60, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "4º", "PCT30008", "Laboratório de Física III", 30, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "5º", "EMEC0014", "Termodinâmica I", 60, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "5º", "EMEC0015", "Eletricidade Básica", 60, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "5º", "EMEC0016", "Resistência dos Materiais II", 60, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "5º", "EMEC0017", "Materiais de Construção Mecânica I", 60, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "5º", "EMEC0018", "Processo de Fabricação I", 45, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "5º", "EMEC0019", "Engenharia de Processos I", 45, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "6º", "EMEC0020", "Termodinâmica II", 60, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "6º", "EMEC0021", "Mecânica dos Fluidos I", 75, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "6º", "EMEC0022", "Transferência de Calor e Massa I", 75, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "6º", "EMEC0023", "Cinemática e Dinâmica das Máquinas", 60, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "6º", "EMEC0024", "Eletrotécnica Geral", 60, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "6º", "EMEC0025", "Materiais de Construção Mecânica II", 75, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "6º", "EMEC0026", "Processo de Fabricação II", 45, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "7º", "EMEC0027", "Mecânica dos Fluidos II", 75, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "7º", "EMEC0028", "Transferência de Calor e Massa II", 75, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "7º", "EMEC0029", "Elementos de Máquina I", 60, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "7º", "EMEC0031", "Usinagem", 60, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "7º", "PCT30060", "Eletrônica Básica", 60, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "8º", "EMEC0032", "Turbomáquinas", 60, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "8º", "EMEC0033", "Sistemas Fluidotérmicos I", 60, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "8º", "EMEC0034", "Elementos de Máquina II", 60, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "8º", "EMEC0035", "Vibrações", 60, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "8º", "EMEC0036", "Instrumentação e Controle de Processos Industriais", 60, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "8º", "EMEC0037", "Soldagem", 60, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "8º", "EMEC0038", "Engenharia de Produção I", 45, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "9º", "EMEC0039", "Sistemas Fluidotérmicos II", 60, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "9º", "EMEC0040", "Mecânica Computacional", 45, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "9º", "EMEC0041", "Engenharia de Produção II", 45, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "9º", "EMEC0043", "Seleção e Especificação de Materiais", 30, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "9º", "PCT30010", "Legislação e Segurança no Trabalho", 45, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "10º", "IEG070101", "Estágio Supervisionado", 160, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "10º", "SMEC0001", "Atividades de Extensão", 445, "OBRIGATÓRIO"),
    ("EMEC21", "Eng. Mecânica", "10º", "SPCT0049", "Trabalho de Conclusão de Curso", 60, "OBRIGATÓRIO"),
    # Optativas EMEC21
    ("EMEC21", "Eng. Mecânica", "Optativa", "ANT100030", "Relações Étnico-Raciais", 60, "OPTATIVO"),
    ("EMEC21", "Eng. Mecânica", "Optativa", "EFIS0005", "Fundamentos da Administração", 60, "OPTATIVO"),
    ("EMEC21", "Eng. Mecânica", "Optativa", "EFIS0008", "Libras Língua Brasileira de Sinais", 60, "OPTATIVO"),
    ("EMEC21", "Eng. Mecânica", "Optativa", "EFIS0014", "Tecnologia de Biocombustíveis", 60, "OPTATIVO"),
    ("EMEC21", "Eng. Mecânica", "Optativa", "EFIS0015", "Laboratório de Tecnologia de Biocombustíveis", 60, "OPTATIVO"),
    ("EMEC21", "Eng. Mecânica", "Optativa", "EFIS0051", "Biomateriais", 60, "OPTATIVO"),
    ("EMEC21", "Eng. Mecânica", "Optativa", "EMEC0044", "Métodos Computacionais para Fenômenos de Transportes", 60, "OPTATIVO"),
    ("EMEC21", "Eng. Mecânica", "Optativa", "EMEC0045", "Sistemas Híbridos", 60, "OPTATIVO"),
    ("EMEC21", "Eng. Mecânica", "Optativa", "EMEC0046", "Conversão de Energia", 60, "OPTATIVO"),
    ("EMEC21", "Eng. Mecânica", "Optativa", "EMEC0047", "Introdução ao Método de Elementos Finitos", 60, "OPTATIVO"),
    ("EMEC21", "Eng. Mecânica", "Optativa", "EMEC0048", "Gestão de Projetos", 60, "OPTATIVO"),
    ("EMEC21", "Eng. Mecânica", "Optativa", "EMEC0049", "Manutenção e Confiabilidade", 60, "OPTATIVO"),
    ("EMEC21", "Eng. Mecânica", "Optativa", "EMEC0050", "Marketing", 60, "OPTATIVO"),
    ("EMEC21", "Eng. Mecânica", "Optativa", "EMEC0051", "Pesquisa Operacional", 60, "OPTATIVO"),
    ("EMEC21", "Eng. Mecânica", "Optativa", "EMEC0052", "Sistema e Gestão da Qualidade", 60, "OPTATIVO"),
    ("EMEC21", "Eng. Mecânica", "Optativa", "EMEC0053", "Logística", 60, "OPTATIVO"),
    ("EMEC21", "Eng. Mecânica", "Optativa", "EMEC0054", "Planejamento e Controle da Produção", 60, "OPTATIVO"),
    ("EMEC21", "Eng. Mecânica", "Optativa", "EMEC0055", "Fundamentos de Mecânica das Estruturas", 60, "OPTATIVO"),
    ("EMEC21", "Eng. Mecânica", "Optativa", "EMEC0056", "Máquinas de Elevação e Transporte", 60, "OPTATIVO"),
    ("EMEC21", "Eng. Mecânica", "Optativa", "EMEC0057", "Refrigeração e Ar Condicionado", 60, "OPTATIVO"),
    ("EMEC21", "Eng. Mecânica", "Optativa", "EMEC0058", "Máquinas Térmicas de Potência", 60, "OPTATIVO"),
    ("EMEC21", "Eng. Mecânica", "Optativa", "EMEC0059", "Robótica", 45, "OPTATIVO"),
    ("EMEC21", "Eng. Mecânica", "Optativa", "EMEC0060", "Sensores e Atuadores", 60, "OPTATIVO"),
    ("EMEC21", "Eng. Mecânica", "Optativa", "EMEC0061", "Controle Digital", 60, "OPTATIVO"),
    ("EMEC21", "Eng. Mecânica", "Optativa", "EMEC0062", "Corrosão e Tratamento de Superfícies", 30, "OPTATIVO"),
    ("EMEC21", "Eng. Mecânica", "Optativa", "EMEC0063", "Materiais Compósitos", 60, "OPTATIVO"),
    ("EMEC21", "Eng. Mecânica", "Optativa", "EMEC0064", "Materiais Poliméricos", 30, "OPTATIVO"),
    ("EMEC21", "Eng. Mecânica", "Optativa", "EMEC0065", "Processos de Reciclagem e Logística Reversa", 60, "OPTATIVO"),
    ("EMEC21", "Eng. Mecânica", "Optativa", "EMEC0066", "Geração Heliotérmica", 60, "OPTATIVO"),
    ("EMEC21", "Eng. Mecânica", "Optativa", "EMEC0067", "Aerodinâmica e Aerogeradores", 60, "OPTATIVO"),
    ("EMEC21", "Eng. Mecânica", "Optativa", "EMEC0068", "Otimização de Sistemas Térmicos", 60, "OPTATIVO"),
    ("EMEC21", "Eng. Mecânica", "Optativa", "EMEC0069", "Processos de Fundição", 60, "OPTATIVO"),
    ("EMEC21", "Eng. Mecânica", "Optativa", "EMEC0070", "Mecânica da Fratura e Fadiga dos Materiais", 60, "OPTATIVO"),
    ("EMEC21", "Eng. Mecânica", "Optativa", "ICED540011", "Educação e Relações Étnico Raciais", 60, "OPTATIVO"),
    ("EMEC21", "Eng. Mecânica", "Optativa", "ICS030020", "Direitos Humanos", 60, "OPTATIVO"),
    ("EMEC21", "Eng. Mecânica", "Optativa", "IEG070108", "Combustão e Combustíveis", 60, "OPTATIVO"),
    ("EMEC21", "Eng. Mecânica", "Optativa", "IEG070114", "Energia de Biomassa", 60, "OPTATIVO"),
    ("EMEC21", "Eng. Mecânica", "Optativa", "PCT30040", "Gestão e Auditoria Ambiental", 60, "OPTATIVO"),
    ("EMEC21", "Eng. Mecânica", "Optativa", "PCT30050", "Física IV", 60, "OPTATIVO"),
    ("EMEC21", "Eng. Mecânica", "Optativa", "PCT30051", "Laboratório de Física IV", 30, "OPTATIVO"),
    ("EMEC21", "Eng. Mecânica", "Optativa", "SMEC0002", "Tópicos Especiais em Engenharia Mecânica", 60, "OPTATIVO"),
    ("EMEC21", "Eng. Mecânica", "Optativa", "SMEC0003", "Mobilidade", 60, "OPTATIVO"),

    # --------------------------------------------------------------------------
    # EFIS17 — Engenharia Física (Ingressantes no BI anteriores a 2024)
    # --------------------------------------------------------------------------
    ("EFIS17", "Eng. Física", "1º", "CTEC0001", "Fundamentos de Matemática", 45, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "1º", "CTEC0002", "Química Geral", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "1º", "CTEC0003", "Laboratório de Química Geral", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "1º", "CTEC0004", "Programação I", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "1º", "IEG010009", "Cálculo I", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "1º", "IEG10008", "Geometria Analítica", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "1º", "PCT30022", "Desenho Técnico", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "2º", "CTEC0005", "Projeto Auxiliado por Computador", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "2º", "IEG010011", "Linguagem e Comunicação", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "2º", "IEG020001", "Cálculo II", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "2º", "IEG020002", "Álgebra Linear", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "2º", "IEG030003", "Física I", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "2º", "IEG030004", "Laboratório de Física I", 30, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "2º", "PCT30027", "Introdução à Probabilidade e Estatística", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "3º", "CTEC0006", "Metodologia Científica", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "3º", "IEG010001", "Introdução à Engenharia", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "3º", "IEG010012", "Física II", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "3º", "IEG020018", "Cálculo III", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "3º", "PCT30021", "Conservação dos Recursos Ambientais", 45, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "3º", "PCT30033", "Laboratório de Física II", 30, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "3º", "PCT30034", "Fundamentos da Termodinâmica", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "4º", "CTEC0007", "Fenômenos de Transporte", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "4º", "CTEC0008", "Programação II", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "4º", "CTEC0009", "Metrologia", 45, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "4º", "IEG020033", "Cálculo IV", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "4º", "PCT30007", "Física III", 90, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "4º", "PCT30008", "Laboratório de Física III", 30, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "4º", "PCT30025", "Química Tecnológica", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "5º", "EFIS0005", "Fundamentos da Administração", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "5º", "PCT30017", "Mecânica dos Fluidos", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "5º", "PCT30018", "Mecânica dos Sólidos", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "5º", "PCT30029", "Laboratório de Mecânica dos Fluidos", 30, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "5º", "PCT30038", "Cálculo Numérico", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "5º", "PCT30047", "Energias Renováveis e Sustentabilidade", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "5º", "PCT30050", "Física IV", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "5º", "PCT30051", "Laboratório de Física IV", 30, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "6º", "PCT30010", "Legislação e Segurança no Trabalho", 45, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "6º", "PCT30037", "Métodos Matemáticos I", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "6º", "PCT30052", "Termodinâmica Aplicada", 90, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "6º", "PCT30053", "Circuitos Elétricos", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "6º", "PCT30054", "Laboratório de Circuitos Elétricos", 30, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "6º", "PCT30069", "Ciências e Tecnologia dos Materiais", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "6º", "PCT30070", "Introdução à Economia", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "7º", "EFIS0035", "Processamento Digitais de Sinais", 90, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "7º", "EFIS0036", "Processos de Fabricação", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "7º", "IEG070054", "Métodos Matemáticos II", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "7º", "PCT30060", "Eletrônica Básica", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "7º", "PCT30061", "Laboratório de Eletrônica Básica", 30, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "7º", "PCT30064", "Mecânica Clássica", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "8º", "EFIS0020", "Automação e Supervisão de Processos", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "8º", "IEG070018", "Física Moderna", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "8º", "IEG070056", "Sistemas de Controle", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "8º", "IEG070107", "Teoria Eletromagnética I", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "8º", "IEG070109", "Modelagem Computacional I", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "9º", "EFIS0001", "Mecânica Quântica I", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "9º", "EFIS0002", "Máquinas Elétricas", 90, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "9º", "EFIS0003", "Turbomáquinas", 60, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "9º", "EFIS0004", "Transferência de Calor e Massa", 90, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "10º", "IEG070101", "Estágio Supervisionado", 160, "OBRIGATÓRIO"),
    ("EFIS17", "Eng. Física", "10º", "IEG070102", "Trabalho de Conclusão de Curso", 60, "OBRIGATÓRIO"),
    # Optativas exclusivas/adicionais EFIS17
    ("EFIS17", "Eng. Física", "Optativa", "EFIS0046", "Tópicos Especiais em Engenharia Física II", 60, "OPTATIVO"),
    ("EFIS17", "Eng. Física", "Optativa", "EFIS0047", "Tópicos Especiais em Engenharia Física III", 60, "OPTATIVO"),
    ("EFIS17", "Eng. Física", "Optativa", "EFIS0048", "Tópicos Especiais em Engenharia Física IV", 60, "OPTATIVO"),

    # --------------------------------------------------------------------------
    # EFIS23 — Engenharia Física (Ingressantes a partir de 2024, matriz 2023.1)
    # --------------------------------------------------------------------------
    ("EFIS23", "Eng. Física", "1º", "CTEC0001", "Fundamentos de Matemática", 45, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "1º", "CTEC0002", "Química Geral", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "1º", "CTEC0003", "Laboratório de Química Geral", 30, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "1º", "CTEC0004", "Programação I", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "1º", "IEG010009", "Cálculo I", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "1º", "IEG10008", "Geometria Analítica", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "1º", "PCT30022", "Desenho Técnico", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "2º", "CTEC0005", "Projeto Auxiliado por Computador", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "2º", "IEG010011", "Linguagem e Comunicação", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "2º", "IEG020001", "Cálculo II", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "2º", "IEG020002", "Álgebra Linear", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "2º", "IEG030003", "Física I", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "2º", "IEG030004", "Laboratório de Física I", 30, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "2º", "PCT30027", "Introdução à Probabilidade e Estatística", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "3º", "CTEC0006", "Metodologia Científica", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "3º", "IEG010001", "Introdução à Engenharia", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "3º", "IEG010012", "Física II", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "3º", "IEG020018", "Cálculo III", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "3º", "PCT30021", "Conservação dos Recursos Ambientais", 45, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "3º", "PCT30033", "Laboratório de Física II", 30, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "3º", "PCT30034", "Fundamentos da Termodinâmica", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "4º", "CTEC0007", "Fenômenos de Transporte", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "4º", "CTEC0008", "Programação II", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "4º", "CTEC0009", "Metrologia", 45, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "4º", "IEG020033", "Cálculo IV", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "4º", "PCT30008", "Laboratório de Física III", 30, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "4º", "SFIS0002", "Física III", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "4º", "SFIS0003", "Química Tecnológica", 45, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "5º", "EFIS0005", "Fundamentos da Administração", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "5º", "PCT30017", "Mecânica dos Fluidos", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "5º", "PCT30018", "Mecânica dos Sólidos", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "5º", "PCT30029", "Laboratório de Mecânica dos Fluidos", 30, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "5º", "PCT30038", "Cálculo Numérico", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "5º", "PCT30047", "Energias Renováveis e Sustentabilidade", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "5º", "PCT30050", "Física IV", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "5º", "PCT30051", "Laboratório de Física IV", 30, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "6º", "PCT30010", "Legislação e Segurança no Trabalho", 45, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "6º", "PCT30037", "Métodos Matemáticos I", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "6º", "PCT30053", "Circuitos Elétricos", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "6º", "PCT30054", "Laboratório de Circuitos Elétricos", 30, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "6º", "PCT30069", "Ciências e Tecnologia dos Materiais", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "6º", "SFIS0004", "Termodinâmica Aplicada", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "6º", "SFIS0005", "Introdução à Economia", 45, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "7º", "EFIS0036", "Processos de Fabricação", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "7º", "IEG070054", "Métodos Matemáticos II", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "7º", "PCT30060", "Eletrônica Básica", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "7º", "PCT30061", "Laboratório de Eletrônica Básica", 30, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "7º", "PCT30064", "Mecânica Clássica", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "7º", "SFIS0006", "Processamento Digital de Sinais", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "8º", "EFIS0020", "Automação e Supervisão de Processos", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "8º", "IEG070018", "Física Moderna", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "8º", "IEG070056", "Sistemas de Controle", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "8º", "IEG070107", "Teoria Eletromagnética I", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "8º", "IEG070109", "Modelagem Computacional I", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "9º", "EFIS0001", "Mecânica Quântica I", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "9º", "EFIS0003", "Turbomáquinas", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "9º", "SFIS0007", "Transferência de Calor e Massa", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "10º", "IEG070101", "Estágio Supervisionado", 160, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "10º", "IEG070102", "Trabalho de Conclusão de Curso", 60, "OBRIGATÓRIO"),
    ("EFIS23", "Eng. Física", "10º", "SFIS0001", "Atividades de Extensão", 420, "OBRIGATÓRIO"),
    # Optativas EFIS23
    ("EFIS23", "Eng. Física", "Optativa", "ANT100030", "Relações Étnico-Raciais", 60, "OPTATIVO"),
    ("EFIS23", "Eng. Física", "Optativa", "CFI010001", "Sociedade, Natureza e Desenvolvimento", 75, "OPTATIVO"),
    ("EFIS23", "Eng. Física", "Optativa", "CFI010002", "Estudos Integrativos da Amazônia", 75, "OPTATIVO"),
    ("EFIS23", "Eng. Física", "Optativa", "CFI010003", "Origem e Evolução do Conhecimento", 75, "OPTATIVO"),
    ("EFIS23", "Eng. Física", "Optativa", "CFI010004", "Lógica, Linguagem e Comunicação", 90, "OPTATIVO"),
    ("EFIS23", "Eng. Física", "Optativa", "CFI010005", "Seminários Integradores", 40, "OPTATIVO"),
    ("EFIS23", "Eng. Física", "Optativa", "CFI010006", "Interação na Base Real", 45, "OPTATIVO"),
    ("EFIS23", "Eng. Física", "Optativa", "EFIS0002", "Máquinas Elétricas", 90, "OPTATIVO"),
    ("EFIS23", "Eng. Física", "Optativa", "EFIS0007", "Direitos Humanos", 60, "OPTATIVO"),
    ("EFIS23", "Eng. Física", "Optativa", "EFIS0008", "Libras - Língua Brasileira de Sinais", 60, "OPTATIVO"),
    ("EFIS23", "Eng. Física", "Optativa", "EFIS0009", "Políticas de Educação Ambiental", 60, "OPTATIVO"),
    ("EFIS23", "Eng. Física", "Optativa", "EFIS0012", "Energia Eólica", 60, "OPTATIVO"),
    ("EFIS23", "Eng. Física", "Optativa", "EFIS0013", "Pequenas Centrais Hidrelétricas", 60, "OPTATIVO"),
    ("EFIS23", "Eng. Física", "Optativa", "EFIS0014", "Tecnologia de Biocombustíveis", 60, "OPTATIVO"),
    ("EFIS23", "Eng. Física", "Optativa", "EFIS0015", "Laboratório de Tecnologia de Biocombustíveis", 60, "OPTATIVO"),
    ("EFIS23", "Eng. Física", "Optativa", "EFIS0016", "Elementos de Máquinas", 60, "OPTATIVO"),
    ("EFIS23", "Eng. Física", "Optativa", "EFIS0019", "Controle Avançado", 60, "OPTATIVO"),
    ("EFIS23", "Eng. Física", "Optativa", "EFIS0021", "Acionamentos Elétricos", 60, "OPTATIVO"),
    ("EFIS23", "Eng. Física", "Optativa", "EFIS0022", "Microprocessadores e Microcontroladores", 60, "OPTATIVO"),
    ("EFIS23", "Eng. Física", "Optativa", "EFIS0023", "Laboratório de Microprocessadores e Microcontroladores", 60, "OPTATIVO"),
    ("EFIS23", "Eng. Física", "Optativa", "EFIS0024", "Inteligência Computacional", 60, "OPTATIVO"),
    ("EFIS23", "Eng. Física", "Optativa", "EFIS0025", "Modelagem e Identificação de Sistemas", 60, "OPTATIVO"),
    ("EFIS23", "Eng. Física", "Optativa", "EFIS0041", "Máquinas Térmicas de Potência", 60, "OPTATIVO"),
    ("EFIS23", "Eng. Física", "Optativa", "EFIS0042", "Geração, Transmissão e Distribuição da Energia", 60, "OPTATIVO"),
    ("EFIS23", "Eng. Física", "Optativa", "EFIS0043", "Projeto de Energia Solar", 60, "OPTATIVO"),
    ("EFIS23", "Eng. Física", "Optativa", "EFIS0044", "Eletrônica de Potência", 60, "OPTATIVO"),
    ("EFIS23", "Eng. Física", "Optativa", "EFIS0045", "Tópicos Especiais em Engenharia Física I", 60, "OPTATIVO"),
    ("EFIS23", "Eng. Física", "Optativa", "EFIS0049", "Caracterização de Materiais", 60, "OPTATIVO"),
    ("EFIS23", "Eng. Física", "Optativa", "EFIS0050", "Tecnologia de Materiais Cerâmicos", 60, "OPTATIVO"),
    ("EFIS23", "Eng. Física", "Optativa", "EFIS0051", "Biomateriais", 60, "OPTATIVO"),
    ("EFIS23", "Eng. Física", "Optativa", "EFIS0052", "Síntese dos Materiais", 60, "OPTATIVO"),
    ("EFIS23", "Eng. Física", "Optativa", "EFIS0053", "Tecnologia da Madeira", 60, "OPTATIVO"),
    ("EFIS23", "Eng. Física", "Optativa", "ICED540011", "Educação e Relações Étnico Raciais", 60, "OPTATIVO"),
    ("EFIS23", "Eng. Física", "Optativa", "ICS010005", "Saber Local e Diversidade Cultural", 60, "OPTATIVO"),
    ("EFIS23", "Eng. Física", "Optativa", "IEG070055", "Energia Solar Fotovoltaica", 45, "OPTATIVO"),
    ("EFIS23", "Eng. Física", "Optativa", "IEG070108", "Combustão e Combustíveis", 60, "OPTATIVO"),
    ("EFIS23", "Eng. Física", "Optativa", "IEG070114", "Energia de Biomassa", 60, "OPTATIVO"),
    ("EFIS23", "Eng. Física", "Optativa", "IEG070115", "Eletrotécnica Geral", 60, "OPTATIVO"),
    ("EFIS23", "Eng. Física", "Optativa", "IEG070116", "Química dos Materiais", 60, "OPTATIVO"),
    ("EFIS23", "Eng. Física", "Optativa", "PCT30039", "Gestão da Qualidade", 60, "OPTATIVO"),
    ("EFIS23", "Eng. Física", "Optativa", "PCT30040", "Gestão e Auditoria Ambiental", 60, "OPTATIVO"),
]


def gerar_tabela_estruturas_sigaa() -> pd.DataFrame:
    """Retorna todas as estruturas curriculares oficiais do SIGAA (BICT24, EMEC21, EFIS17, EFIS23)."""
    return pd.DataFrame(
        ESTRUTURAS_CURRICULARES_SIGAA,
        columns=[
            "Matriz",
            "Curso",
            "Nível",
            "Código_SIGAA",
            "Componente_Curricular",
            "CH_SIGAA",
            "Natureza",
        ],
    )


def consultar_componente_sigaa(codigo: Any, nome: Any = "", curso: Any = "") -> dict[str, Any]:
    """
    Consulta um componente curricular nas 4 estruturas curriculares oficiais do SIGAA.
    Retorna metadados de vigência, matrizes onde aparece, natureza e CH oficial.
    """
    cod_clean = str(codigo).strip().upper() if not pd.isna(codigo) else ""
    nome_n = norm(nome)
    curso_n = norm(curso)

    df_est = gerar_tabela_estruturas_sigaa()
    matches = df_est[df_est["Código_SIGAA"].str.upper() == cod_clean] if cod_clean else df_est.iloc[0:0]

    if matches.empty and nome_n:
        matches = df_est[df_est["Componente_Curricular"].apply(lambda x: norm(x) == nome_n)]

    if matches.empty:
        return {
            "vigente_sigaa": False,
            "matrizes": "Não localizado no SIGAA",
            "natureza": "Não cadastrado",
            "ch_sigaa": 0,
            "niveis": "—",
        }

    # Prioriza o curso específico da oferta, se informado
    sub_curso = matches[matches["Curso"].apply(lambda c: curso_n in norm(c) or norm(c) in curso_n)] if curso_n else matches
    alvo = sub_curso if not sub_curso.empty else matches

    matrizes_str = ", ".join(sorted(alvo["Matriz"].unique().tolist()))
    naturezas_str = "/".join(sorted(alvo["Natureza"].unique().tolist()))
    niveis_str = ", ".join(sorted(alvo["Nível"].unique().tolist(), key=lambda x: (not x[0].isdigit(), x)))
    ch_oficial = int(alvo["CH_SIGAA"].iloc[0])

    return {
        "vigente_sigaa": True,
        "matrizes": matrizes_str,
        "natureza": naturezas_str,
        "ch_sigaa": ch_oficial,
        "niveis": niveis_str,
    }


# ==============================================================================
# 3. INVENTÁRIO OFICIAL DE SALAS E LABORATÓRIOS (VALIDADO PELA COORDENAÇÃO)
# ==============================================================================
SALAS_PCT = ["206B-NSA", "203B-NSA", "207B-NSA", "208B-NSA", "209B-NSA"]
SALAS_EXTERNAS_NSA = ["105A-NSA", "110B-NSA"]

SALAS_INVENTARIO = {
    # 5 salas sob gestão direta do PC&T (NSA)
    "206B-NSA": {"Gestao": "PC&T (Gestão Direta)", "Tipo": "Sala de Aula NSA", "Capacidade": 55, "Gargalo": "Não"},
    "203B-NSA": {"Gestao": "PC&T (Gestão Direta)", "Tipo": "Sala de Aula NSA", "Capacidade": 40, "Gargalo": "Não"},
    "207B-NSA": {"Gestao": "PC&T (Gestão Direta)", "Tipo": "Sala de Aula NSA", "Capacidade": 40, "Gargalo": "Não"},
    "208B-NSA": {"Gestao": "PC&T (Gestão Direta)", "Tipo": "Sala de Aula NSA", "Capacidade": 40, "Gargalo": "Não"},
    "209B-NSA": {"Gestao": "PC&T (Gestão Direta)", "Tipo": "Sala de Aula NSA", "Capacidade": 40, "Gargalo": "Não"},
    # Laboratórios próprios do PC&T
    "Lab de Sinais e Sistemas": {"Gestao": "PC&T (Lab Próprio)", "Tipo": "Laboratório PC&T", "Capacidade": 20, "Gargalo": "Não"},
    "Laboratório de Síntese de Materiais": {"Gestao": "PC&T (Lab Próprio)", "Tipo": "Laboratório PC&T", "Capacidade": 15, "Gargalo": "Não"},
    "Lab de Fenômenos de Transporte": {"Gestao": "PC&T (Lab Próprio)", "Tipo": "Laboratório PC&T", "Capacidade": 25, "Gargalo": "Não"},
    "Lab de Sistemas de Energia": {"Gestao": "PC&T (Lab Próprio)", "Tipo": "Laboratório PC&T", "Capacidade": 25, "Gargalo": "Não"},
    "Oficina Mecânica / Lab de Manufatura (PC&T)": {"Gestao": "PC&T (Lab Próprio)", "Tipo": "Laboratório PC&T", "Capacidade": 25, "Gargalo": "Não"},
    # Salas e laboratórios dependentes de reserva externa
    "105A-NSA": {"Gestao": "Externa (CAC / IEG)", "Tipo": "Sala de Aula NSA", "Capacidade": 40, "Gargalo": "Sim"},
    "110B-NSA": {"Gestao": "Externa (CAC / IEG)", "Tipo": "Sala de Aula NSA", "Capacidade": 40, "Gargalo": "Sim"},
    "Lab de Informática - Sala 145 BMT II": {"Gestao": "Externa (IEG / Computação)", "Tipo": "Lab Informática", "Capacidade": 40, "Gargalo": "CRÍTICO"},
    "Sala de Informática": {"Gestao": "Externa (IEG / Computação)", "Tipo": "Lab Informática", "Capacidade": 30, "Gargalo": "CRÍTICO"},
    "Sala 229 BMT - Laboratório de Desenho": {"Gestao": "Externa (IBEF / IEG)", "Tipo": "Lab Desenho", "Capacidade": 50, "Gargalo": "CRÍTICO"},
    "Lab Alpha - Rondon": {"Gestao": "Externa (ICED - Rondon)", "Tipo": "Lab Física", "Capacidade": 25, "Gargalo": "Sim"},
    "Lab Beta - Rondon": {"Gestao": "Externa (ICED - Rondon)", "Tipo": "Lab Física", "Capacidade": 25, "Gargalo": "Sim"},
    "Lab de Química Geral - BMT / IEG": {"Gestao": "Externa (IEG / Química)", "Tipo": "Lab Química", "Capacidade": 25, "Gargalo": "Sim"},
    "A DEFINIR": {"Gestao": "Pendente de Alocação", "Tipo": "Indefinido", "Capacidade": 0, "Gargalo": "CRÍTICO"},
}

LAB_ROOMS = {
    nome for nome, info in SALAS_INVENTARIO.items()
    if "Lab" in info["Tipo"] or "Laboratório" in info["Tipo"]
}

# ==============================================================================
# 4. FAMÍLIAS DE TURMAS UNIFICÁVEIS E PARSER DE HORÁRIOS SIGAA
# ==============================================================================
FAMILIAS_UNIFICAVEIS = [
    {"eletronica basica"},
    {"processos de fabricacao", "processos de fabricacao i", "processo de fabricacao i"},
    {
        "ciencia e tecnologia dos materiais",
        "ciencias e tecnologia dos materiais",
        "materiais de construcao mecanica i",
        "materiais de construcao mecanica",
    },
    {"calculo iii"},
    {"fisica iii"},
    {"laboratorio de quimica geral"},
    {"conservacao dos recursos naturais", "conservacao dos recursos ambientais"},
]


def identificar_familia_unificacao(disciplina: str) -> str:
    """Retorna o identificador de família unificável (ex.: 'FAM_0') ou o nome normalizado."""
    dn = norm(disciplina)
    for idx, familia in enumerate(FAMILIAS_UNIFICAVEIS):
        if dn in familia:
            return f"FAM_{idx}"
    return dn


def padronizar_docente(nome: Any) -> str:
    """Converte abreviações ou variações de grafia para o nome oficial do docente."""
    if pd.isna(nome) or str(nome).strip() == "":
        return "A definir"
    chave = norm(nome)
    return DOCENTE_CANON_MAP.get(chave, str(nome).strip())


def padronizar_sala(sala: Any) -> str:
    """Padroniza a grafia de salas e laboratórios."""
    if pd.isna(sala) or str(sala).strip() == "":
        return "A DEFINIR"
    s = str(sala).strip()
    if norm(s) == "a definir":
        return "A DEFINIR"
    s = s.replace(",", "").replace("  ", " ").replace("B - ", "B-").replace(" - ", "-").replace("NSa", "NSA")
    s_cmp = norm(s).replace(" - ", "-").replace("- ", "-").replace(" -", "-")
    for chave_oficial in SALAS_INVENTARIO:
        c_cmp = norm(chave_oficial).replace(" - ", "-").replace("- ", "-").replace(" -", "-")
        if s_cmp == c_cmp:
            return chave_oficial
    return s


def expandir_horario_sigaa(horario_sigaa: Any) -> list[str]:
    """
    Expande um código SIGAA em slots individuais ordenados.
    Exemplo: '24M12 / 4M3' -> ['2M1', '2M2', '4M1', '4M2', '4M3'].
    """
    if pd.isna(horario_sigaa):
        return []
    texto = str(horario_sigaa).strip()
    if not texto or "SEM HORÁRIO" in texto.upper():
        return []

    slots = set()
    for bloco in texto.split("/"):
        bloco = bloco.strip()
        m = re.match(r"^([2-7]+)([MTN])([1-5]+)$", bloco)
        if m:
            dias, turno, horas = m.groups()
            for d in dias:
                for h in horas:
                    slots.add(f"{d}{turno}{h}")
    return sorted(slots)


def extrair_dias_sigaa(horario_sigaa: Any) -> set[str]:
    """Retorna o conjunto de códigos numéricos dos dias ('2'=Seg ... '7'=Sáb)."""
    return {slot[0] for slot in expandir_horario_sigaa(horario_sigaa)}


# ==============================================================================
# 5. BASE PADRÃO EMBUTIDA (19 EFETIVOS PC&T + 4 COLABORADORES + OFERTAS 2027.1)
# ==============================================================================
def carregar_base_embutida() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Retorna (df_oferta, df_cred) padronizados para uso imediato ou fallback."""
    ppc_cred = {
        "Aldo Gomes Queiroz": ("PC&T (Permanente)", "Doutor", "Engenharia Mecânica",
            ["Conservação dos Recursos Naturais", "Conservação dos Recursos Ambientais", "Fundamentos de Engenharia Ambiental",
             "Introdução à Engenharia", "Introdução à Engenharia Mecânica",
             "Energias Renováveis e Sustentabilidade", "Metodologia Científica", "Linguagem e Comunicação"]),
        "Alex Junior de Freitas Cabral": ("PC&T (Permanente)", "Doutor", "Física",
            ["Física I", "Física II", "Física III", "Laboratório de Física I", "Laboratório de Física II",
             "Laboratório de Física III", "Física Moderna", "Mecânica Geral I"]),
        "Anderson Alvarenga de Moura Meneses": ("PC&T (Permanente)", "Doutor", "Física / Eng. Nuclear",
            ["Programação I", "Programação II", "Introdução à Probabilidade e Estatística", "Mecânica Quântica", "Mecânica Quântica I"]),
        "Carlos Célio Sousa da Cruz": ("PC&T (Permanente)", "Doutor", "Engenharia Química",
            ["Fundamentos da Termodinâmica", "Termodinâmica I", "Termodinâmica II", "Termodinâmica Aplicada",
             "Química Tecnológica", "Fenômenos de Transportes", "Fenômenos de Transporte",
             "Transferência de Calor e Massa", "Transferência de Calor e Massa I", "Transferência de Calor e Massa II",
             "Mecânica dos Fluidos", "Mecânica dos Fluidos I", "Mecânica dos Fluidos II",
             "Engenharia de Produção I", "Engenharia de Produção II",
             "Engenharia de Processos I", "Conservação dos Recursos Naturais", "Conservação dos Recursos Ambientais", "Fundamentos de Engenharia Ambiental"]),
        "Diego Jorge Borges": ("PC&T (Permanente)", "Doutor", "Engenharia Mecânica / Materiais",
            ["Ciência e Tecnologia dos Materiais", "Ciências e Tecnologia dos Materiais",
             "Materiais de Construção Mecânica I", "Materiais de Construção Mecânica II",
             "Elementos de Máquina I", "Elementos de Máquina II", "Elementos de Máquinas I", "Elementos de Máquinas II",
             "Usinagem", "Oficinas", "Processos de Fabricação", "Processo de Fabricação I", "Processo de Fabricação II"]),
        "Estefany Miléo de Couto": ("PC&T (Permanente)", "Mestre", "Arquitetura e Urbanismo",
            ["Desenho Técnico", "Projeto Auxiliado por Computador", "Desenho Técnico Mecânico I",
             "Desenho Técnico Mecânico II", "Metodologia Científica"]),
        "Gilson Fernandes Braga Junior": ("PC&T (Permanente)", "Mestre", "Eng. Controle e Automação",
            ["Eletrônica Básica", "Laboratório de Eletrônica Básica", "Automação e Supervisão de Processos",
             "Processamento Digital de Sinais", "Processamento Digitais de Sinais",
             "Instrumentação e Controle de Processos Industriais",
             "Elementos de Máquina I", "Elementos de Máquina II", "Elementos de Máquinas I", "Elementos de Máquinas II",
             "Vibrações", "Programação I", "Eletricidade Básica"]),
        "Josecley Fialho Góes": ("PC&T (Permanente)", "Doutor", "Matemática / Mod. Computacional",
            ["Cálculo III", "Fundamentos de Matemática", "Geometria Analítica", "Álgebra Linear", "Cálculo Numérico",
             "Métodos Matemáticos I", "Métodos Matemáticos II", "Programação I", "Programação II",
             "Modelagem Computacional", "Modelagem Computacional I", "Mecânica Computacional", "Trabalho de Conclusão de Curso"]),
        "José Roberto Branco Ramos Filho": ("PC&T (Permanente)", "Doutor", "Eng. Controle / Administração",
            ["Fundamentos da Administração", "Introdução à Engenharia", "Introdução à Engenharia Mecânica",
             "Introdução à Economia", "Engenharia Econômica", "Metodologia Científica", "Conservação dos Recursos Naturais",
             "Conservação dos Recursos Ambientais", "Automação e Supervisão de Processos",
             "Engenharia de Produção I", "Engenharia de Produção II",
             "Engenharia de Processos I", "Cinemática e Dinâmica das Máquinas", "Mecânica Geral I", "Mecânica Geral II"]),
        "Lázaro João Santana da Silva": ("PC&T (Permanente)", "Mestre", "Engenharia Mecânica",
            ["Fundamentos da Termodinâmica", "Termodinâmica I", "Termodinâmica Aplicada", "Mecânica dos Fluidos",
             "Mecânica dos Fluidos I", "Mecânica dos Fluidos II", "Laboratório de Mecânica dos Fluidos", "Turbomáquinas",
             "Resistência dos Materiais I", "Resistência dos Materiais II", "Elementos de Máquina I", "Elementos de Máquina II",
             "Elementos de Máquinas I", "Elementos de Máquinas II",
             "Mecânica Geral I", "Mecânica Geral II", "Desenho Técnico"]),
        "Manoel Maria Bezerra Neto": ("PC&T (Permanente)", "Doutor", "Física",
            ["Física I", "Física II", "Física III", "Física IV", "Laboratório de Física I", "Laboratório de Física II",
             "Laboratório de Física III", "Laboratório de Física IV", "Teoria Eletromagnética", "Teoria Eletromagnética I", "Mecânica Geral I"]),
        "Manoel Roberval Pimentel Santos": ("PC&T (Permanente)", "Doutor", "Física",
            ["Física I", "Física III", "Física IV", "Laboratório de Física I", "Laboratório de Física II",
             "Laboratório de Física IV", "Teoria Eletromagnética", "Teoria Eletromagnética I"]),
        "Marcel Antonionni de Andrade Romano": ("PC&T (Permanente)", "Mestre", "Engenharia Elétrica",
            ["Circuitos Elétricos", "Laboratório de Circuitos Elétricos", "Eletrônica Básica", "Laboratório de Eletrônica Básica",
             "Processamento Digital de Sinais", "Processamento Digitais de Sinais", "Sistemas de Controle", "Máquinas Elétricas",
             "Instrumentação e Controle de Processos Industriais", "Elementos de Máquina I", "Elementos de Máquinas I",
             "Vibrações", "Programação I"]),
        "Nelson de Souza Amorim": ("PC&T (Permanente)", "Doutor", "Engenharia Química",
            ["Legislação e Segurança no Trabalho", "Combustão e Combustíveis", "Química Tecnológica", "Cálculo Numérico",
             "Fundamentos da Termodinâmica", "Termodinâmica I", "Termodinâmica II", "Transferência de Calor e Massa I",
             "Transferência de Calor e Massa II", "Mecânica dos Fluidos", "Mecânica dos Fluidos I", "Mecânica dos Fluidos II",
             "Introdução à Probabilidade e Estatística", "Tópicos Especiais de Engenharia Física",
             "Tópicos Especiais em Engenharia Física I", "Tópicos Especiais em Engenharia Física III"]),
        "Paula Renatha Nunes da Silva": ("PC&T (Permanente)", "Doutor", "Engenharia Elétrica",
            ["Circuitos Elétricos", "Laboratório de Circuitos Elétricos", "Eletrônica Básica", "Laboratório de Eletrônica Básica",
             "Sistemas de Controle", "Metrologia", "Instrumentação e Controle de Processos Industriais",
             "Elementos de Máquina I", "Elementos de Máquinas I",
             "Vibrações", "Programação I", "Física III", "Eletrotécnica Geral", "Engenharia de Produção I",
             "Engenharia de Produção II", "Máquinas Elétricas", "Automação e Supervisão de Processos"]),
        "Querem Hapuque Felix Rebelo": ("PC&T (Permanente)", "Doutor", "Física",
            ["Física I", "Física II", "Física III", "Física IV", "Laboratório de Física I", "Laboratório de Física II",
             "Laboratório de Física III", "Laboratório de Física IV", "Física Moderna", "Física Moderna I", "Mecânica Clássica",
             "Mecânica Geral I", "Síntese dos Materiais"]),
        "Thiago Augusto de Sousa Moreira": ("PC&T (Permanente)", "Mestre", "Engenharia de Materiais",
            ["Metrologia", "Ciência e Tecnologia dos Materiais", "Ciências e Tecnologia dos Materiais",
             "Metodologia Científica", "Processos de Fabricação", "Processo de Fabricação I", "Processo de Fabricação II",
             "Processos de Fabricação I", "Processos de Fabricação II", "Materiais de Construção Mecânica I",
             "Seleção e Especificação de Materiais", "Soldagem", "Usinagem", "Oficinas", "Legislação e Segurança no Trabalho"]),
        "Ubiraelson de Lima Ruela": ("PC&T (Permanente)", "Mestre", "Matemática",
            ["Cálculo I", "Cálculo II", "Cálculo III", "Cálculo IV", "Álgebra Linear", "Fundamentos de Matemática",
             "Geometria Analítica", "Métodos Matemáticos I", "Métodos Matemáticos II", "Introdução à Probabilidade e Estatística"]),
        "Vicente Moreira Rodrigues": ("PC&T (Permanente)", "Mestre", "Engenharia Mecânica",
            ["Fenômenos de Transportes", "Fenômenos de Transporte", "Fundamentos da Termodinâmica", "Turbomáquinas",
             "Mecânica dos Fluidos", "Mecânica dos Fluidos I", "Mecânica dos Fluidos II",
             "Resistência dos Materiais I", "Resistência dos Materiais II",
             "Elementos de Máquina I", "Elementos de Máquina II", "Elementos de Máquinas I", "Elementos de Máquinas II",
             "Cinemática e Dinâmica das Máquinas", "Sistemas Fluidotérmicos I", "Sistemas Fluidotérmicos II"]),
        # Colaboradores externos
        "Alexandro Arruda": ("Colaborador Externo", "Docente IEG", "Matemática", ["Cálculo I", "Fundamentos de Matemática"]),
        "Cássio André": ("Colaborador Externo", "Docente IEG", "Matemática", ["Geometria Analítica"]),
        "Cintya de Azambuja": ("Colaborador Externo", "Doutora", "Química", ["Química Geral", "Laboratório de Química Geral"]),
        "Elden Marialva": ("Colaborador Externo", "Doutor", "Engenharia / Produção",
            ["Engenharia de Processos I", "Transferência de Calor e Massa", "Engenharia de Produção II"]),
    }

    cred_rows = []
    for doc, (vinc, tit, area, discs) in sorted(ppc_cred.items()):
        for d in discs:
            cred_rows.append({
                "Docente": doc,
                "Vínculo": vinc,
                "Titulação": tit,
                "Área": area,
                "Componente Curricular Habilitado": d,
                "Origem": "PPC + Histórico PC&T" if vinc == "PC&T (Permanente)" else "Colaborador Externo",
            })
    df_cred = pd.DataFrame(cred_rows)

    oferta_init = [
        ("1º BI", "BI C&T", "1º", "IEG010009", "Cálculo I", 60, 40, "", "206B-NSA", "6M1234", "Ubiraelson de Lima Ruela"),
        ("1º BI", "BI C&T", "1º", "CTEC0001", "Fundamentos de Matemática", 45, 40, "", "A DEFINIR", "5M123", "Ubiraelson de Lima Ruela"),
        ("1º BI", "BI C&T", "1º", "CTEC0004", "Programação I", 60, 50, "", "Lab de Informática - Sala 145 BMT II", "5T1234", "Josecley Fialho Góes"),
        ("1º BI", "BI C&T", "1º", "PCT30022", "Desenho Técnico", 60, 50, "", "Sala 229 BMT - Laboratório de Desenho", "3M1234", "Estefany Miléo de Couto"),
        ("1º BI", "BI C&T", "1º", "CTEC0002", "Química Geral", 60, 50, "", "206B-NSA", "24T12", "A definir"),
        ("1º BI", "BI C&T", "1º", "IEG10008", "Geometria Analítica", 60, 50, "", "203B-NSA", "4M1234", "Cássio André"),
        ("1º BI", "BI C&T", "1º", "SBCT0005", "Laboratório de Química Geral", 30, 25, "Turma 01", "Lab de Química Geral - BMT / IEG", "SEM HORÁRIO NA GRADE", "A definir"),
        ("1º MEC", "Eng. Mecânica", "1º", "IEG010009", "Cálculo I", 60, 50, "", "206B-NSA", "3M1234", "Alexandro Arruda"),
        ("1º MEC", "Eng. Mecânica", "1º", "CTEC0004", "Programação I", 60, 50, "", "Lab de Informática - Sala 145 BMT II", "4M1234", "Marcel Antonionni de Andrade Romano"),
        ("1º MEC", "Eng. Mecânica", "1º", "CTEC0001", "Fundamentos de Matemática", 45, 50, "", "206B-NSA", "5M123", "Alexandro Arruda"),
        ("1º MEC", "Eng. Mecânica", "1º", "IEG10008", "Geometria Analítica", 60, 50, "", "206B-NSA", "2M1234", "Cássio André"),
        ("1º MEC", "Eng. Mecânica", "1º", "PCT30022", "Desenho Técnico", 60, 50, "", "Sala 229 BMT - Laboratório de Desenho", "2T1234", "Estefany Miléo de Couto"),
        ("1º MEC", "Eng. Mecânica", "1º", "CTEC0002", "Química Geral", 60, 50, "", "206B-NSA", "6M1234", "Cintya de Azambuja"),
        ("1º MEC", "Eng. Mecânica", "1º", "EMEC0001", "Introdução à Engenharia Mecânica", 30, 50, "", "206B-NSA", "3T12", "Aldo Gomes Queiroz"),
        ("1º MEC", "Eng. Mecânica", "1º", "CTEC0003", "Laboratório de Química Geral", 30, 25, "Turma 01", "Lab de Química Geral - BMT / IEG", "SEM HORÁRIO NA GRADE", "A definir"),
        ("3º BI", "BI C&T", "3º", "CTEC0006", "Metodologia Científica", 60, 50, "", "203B-NSA", "46M12", "José Roberto Branco Ramos Filho"),
        ("3º BI", "BI C&T", "3º", "IEG010012", "Física II", 60, 50, "", "203B-NSA", "24T12", "Manoel Maria Bezerra Neto"),
        ("3º BI", "BI C&T", "3º", "PCT30033", "Laboratório de Física II", 30, 20, "Turma 01", "Lab Beta - Rondon", "5T12", "Manoel Roberval Pimentel Santos"),
        ("3º BI", "BI C&T", "3º", "IEG020018", "Cálculo III", 60, 50, "", "203B-NSA", "24T34", "Ubiraelson de Lima Ruela"),
        ("3º BI", "BI C&T", "3º", "PCT30021", "Conservação dos Recursos Ambientais", 45, 50, "", "203B-NSA", "3T234", "Carlos Célio Sousa da Cruz"),
        ("3º BI", "BI C&T", "3º", "PCT30034", "Fundamentos da Termodinâmica", 60, 50, "", "208B-NSA", "46M34", "Carlos Célio Sousa da Cruz"),
        ("3º BI", "BI C&T", "3º", "IEG010001", "Introdução à Engenharia", 60, 50, "", "203B-NSA", "35M34", "Aldo Gomes Queiroz"),
        ("3º MEC", "Eng. Mecânica", "3º", "IEG020018", "Cálculo III", 60, 50, "", "207B-NSA", "24M12", "Ubiraelson de Lima Ruela"),
        ("3º MEC", "Eng. Mecânica", "3º", "IEG010012", "Física II", 60, 50, "", "207B-NSA", "24M34", "Manoel Maria Bezerra Neto"),
        ("3º MEC", "Eng. Mecânica", "3º", "PCT30033", "Laboratório de Física II", 30, 20, "Turma 01", "Lab Alpha - Rondon", "6M12", "Querem Hapuque Felix Rebelo"),
        ("3º MEC", "Eng. Mecânica", "3º", "PCT30033", "Laboratório de Física II", 30, 20, "Turma 02", "Lab Alpha - Rondon", "6M34", "Querem Hapuque Felix Rebelo"),
        ("3º MEC", "Eng. Mecânica", "3º", "EMEC0004", "Mecânica Geral I", 60, 50, "", "207B-NSA", "35M34", "Querem Hapuque Felix Rebelo"),
        ("3º MEC", "Eng. Mecânica", "3º", "EMEC0005", "Desenho Técnico Mecânico II", 45, 50, "", "Sala de Informática", "6T123", "Estefany Miléo de Couto"),
        ("3º MEC", "Eng. Mecânica", "3º", "PCT30038", "Cálculo Numérico", 60, 25, "", "207B-NSA", "35M12", "Nelson de Souza Amorim"),
        ("3º MEC", "Eng. Mecânica", "3º", "EMEC0008", "Oficinas", 30, 25, "Turma 01", "Oficina Mecânica / Lab de Manufatura (PC&T)", "SEM HORÁRIO NA GRADE", "A definir"),
        ("3º MEC", "Eng. Mecânica", "3º", "PCT30037", "Métodos Matemáticos I", 60, 40, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("5º BI", "BI C&T", "5º", "EFIS0005", "Fundamentos da Administração", 60, 50, "", "208B-NSA", "SEM HORÁRIO NA GRADE", "José Roberto Branco Ramos Filho"),
        ("5º BI", "BI C&T", "5º", "PCT30038", "Cálculo Numérico", 60, 50, "", "208B-NSA", "24M12", "Nelson de Souza Amorim"),
        ("5º BI", "BI C&T", "5º", "PCT30017", "Mecânica dos Fluidos", 60, 40, "", "208B-NSA", "24M34", "Nelson de Souza Amorim"),
        ("5º BI", "BI C&T", "5º", "PCT30018", "Mecânica dos Sólidos", 60, 40, "", "208B-NSA", "35T12", "CONCURSO"),
        ("5º BI", "BI C&T", "5º", "PCT30047", "Energias Renováveis e Sustentabilidade", 60, 40, "", "208B-NSA", "35M12", "Aldo Gomes Queiroz"),
        ("5º BI", "BI C&T", "5º", "PCT30069", "Ciências e Tecnologia dos Materiais", 60, 30, "", "208B-NSA", "6M1234", "Diego Jorge Borges"),
        ("5º BI", "BI C&T", "5º", "PCT30050", "Física IV", 60, 30, "", "A DEFINIR", "35M34", "Manoel Roberval Pimentel Santos"),
        ("5º BI", "BI C&T", "5º", "PCT30051", "Laboratório de Física IV", 30, 20, "", "Lab Beta - Rondon", "4T12", "Manoel Roberval Pimentel Santos"),
        ("5º BI", "BI C&T", "5º", "PCT30029", "Laboratório de Mecânica dos Fluidos", 30, 20, "Turma 01", "Lab de Fenômenos de Transporte", "SEM HORÁRIO NA GRADE", "A definir"),
        ("5º MEC", "Eng. Mecânica", "5º", "EMEC0014", "Termodinâmica I", 60, 40, "", "105A-NSA", "24T34", "Lázaro João Santana da Silva"),
        ("5º MEC", "Eng. Mecânica", "5º", "EMEC0015", "Eletricidade Básica", 60, 40, "", "105A-NSA", "35T12", "Gilson Fernandes Braga Junior"),
        ("5º MEC", "Eng. Mecânica", "5º", "EMEC0016", "Resistência dos Materiais II", 60, 40, "", "105A-NSA", "24T12", "Vicente Moreira Rodrigues"),
        ("5º MEC", "Eng. Mecânica", "5º", "EMEC0017", "Materiais de Construção Mecânica I", 60, 40, "", "206B-NSA", "6M1234", "Diego Jorge Borges"),
        ("5º MEC", "Eng. Mecânica", "5º", "EMEC0018", "Processo de Fabricação I", 45, 40, "", "A DEFINIR", "4M123", "Thiago Augusto de Sousa Moreira"),
        ("5º MEC", "Eng. Mecânica", "5º", "EMEC0019", "Engenharia de Processos I", 45, 40, "", "105A-NSA", "2M123", "Elden Marialva"),
        ("7º EF", "Eng. Física", "7º", "EFIS0036", "Processos de Fabricação", 60, 40, "", "203B-NSA", "4M12345", "Thiago Augusto de Sousa Moreira"),
        ("7º EF", "Eng. Física", "7º", "PCT30060", "Eletrônica Básica", 60, 40, "", "203B-NSA", "35T12", "Marcel Antonionni de Andrade Romano"),
        ("7º EF", "Eng. Física", "7º", "PCT30061", "Laboratório de Eletrônica Básica", 30, 20, "", "Lab de Sinais e Sistemas", "4T12", "Gilson Fernandes Braga Junior"),
        ("7º EF", "Eng. Física", "7º", "PCT30064", "Mecânica Clássica", 60, 30, "", "110B-NSA", "35T34", "A definir"),
        ("7º EF", "Eng. Física", "7º", "IEG070054", "Métodos Matemáticos II", 60, 40, "", "110B-NSA", "SEM HORÁRIO NA GRADE", "Josecley Fialho Góes"),
        ("7º EF", "Eng. Física", "7º", "PCT30070", "Introdução à Economia", 60, 40, "", "A DEFINIR", "35M34", "José Roberto Branco Ramos Filho"),
        ("7º EF", "Eng. Física", "7º", "SFIS0006", "Processamento Digital de Sinais", 60, 30, "", "A DEFINIR", "2N1234", "Gilson Fernandes Braga Junior"),
        ("7º MEC", "Eng. Mecânica", "7º", "EMEC0027", "Mecânica dos Fluidos II", 75, 40, "", "110B-NSA", "24M12 / 4M3", "Vicente Moreira Rodrigues"),
        ("7º MEC", "Eng. Mecânica", "7º", "EMEC0028", "Transferência de Calor e Massa II", 75, 40, "", "110B-NSA", "35M345", "Carlos Célio Sousa da Cruz"),
        ("7º MEC", "Eng. Mecânica", "7º", "EMEC0029", "Elementos de Máquina I", 60, 40, "", "A DEFINIR", "35T34", "Diego Jorge Borges"),
        ("7º MEC", "Eng. Mecânica", "7º", "PCT30060", "Eletrônica Básica", 60, 40, "", "203B-NSA", "35T12", "Gilson Fernandes Braga Junior"),
        ("7º MEC", "Eng. Mecânica", "7º", "EMEC0031", "Usinagem", 60, 40, "", "110B-NSA", "2M34 / 4M45", "Diego Jorge Borges"),
        ("7º MEC", "Eng. Mecânica", "7º", "EMEC0023", "Cinemática e Dinâmica das Máquinas", 60, 40, "", "A DEFINIR", "35M12", "CONCURSO"),
        ("9º EF", "Eng. Física", "9º", "EFIS0001", "Mecânica Quântica I", 60, 40, "", "A DEFINIR", "35T12", "Anderson Alvarenga de Moura Meneses"),
        ("9º EF", "Eng. Física", "9º", "EFIS0002", "Máquinas Elétricas", 90, 40, "", "A DEFINIR", "24T345", "Paula Renatha Nunes da Silva"),
        ("9º EF", "Eng. Física", "9º", "EFIS0003", "Turbomáquinas", 60, 40, "", "A DEFINIR", "35T34", "Lázaro João Santana da Silva"),
        ("9º EF", "Eng. Física", "9º", "EFIS0004", "Transferência de Calor e Massa", 90, 40, "", "203B-NSA", "35M123", "Elden Marialva"),
        ("9º EF", "Eng. Física", "9º", "EFIS0020", "Automação e Supervisão de Processos", 60, 40, "", "A DEFINIR", "24T12", "Paula Renatha Nunes da Silva"),
        ("9º EF", "Eng. Física", "9º", "EFIS0052", "Síntese dos Materiais", 60, 10, "", "Laboratório de Síntese de Materiais", "4M1234", "Querem Hapuque Felix Rebelo"),
        ("9º EF", "Eng. Física", "9º", "EFIS0047", "Tópicos Especiais em Engenharia Física III", 60, 20, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "Nelson de Souza Amorim"),
        ("9º MEC", "Eng. Mecânica", "9º", "EMEC0039", "Sistemas Fluidotérmicos II", 60, 25, "", "105A-NSA", "35M34", "Vicente Moreira Rodrigues"),
        ("9º MEC", "Eng. Mecânica", "9º", "EMEC0040", "Mecânica Computacional", 45, 25, "", "A DEFINIR", "6T123", "CONCURSO"),
        ("9º MEC", "Eng. Mecânica", "9º", "EMEC0041", "Engenharia de Produção II", 45, 30, "", "105A-NSA", "4M123", "Elden Marialva"),
        ("9º MEC", "Eng. Mecânica", "9º", "PCT30010", "Legislação e Segurança no Trabalho", 45, 25, "", "105A-NSA", "6M12345", "Thiago Augusto de Sousa Moreira"),
        ("9º MEC", "Eng. Mecânica", "9º", "EMEC0043", "Seleção e Especificação de Materiais", 30, 30, "", "105A-NSA", "2M12345", "Thiago Augusto de Sousa Moreira"),
    ]
    df_of = pd.DataFrame(
        oferta_init,
        columns=[
            "Aba_Origem", "Curso", "Período", "Código_SIGAA", "Componente_Curricular",
            "CH_Total", "Vagas", "Turma", "Sala_Alocada", "Horário_SIGAA", "Docente_Alocado",
        ],
    )
    return enriquecer_oferta(df_of), df_cred

def carregar_base_embutida_2027_2() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Gera a oferta padrão de 2027.2 (Semestres Pares: 2º, 4º, 6º e 8º) diretamente
    a partir das 4 Estruturas Curriculares Oficiais vigentes no SIGAA (BICT24, EMEC21, EFIS17, EFIS23).
    """
    _, df_cred = carregar_base_embutida()

    oferta_2027_2 = [
        # 2º BI (BICT24 — 7 obrigatórias)
        ("2º BI", "BI C&T", "2º", "CTEC0005", "Projeto Auxiliado por Computador", 60, 40, "", "Lab de Informática - Sala 145 BMT II", "SEM HORÁRIO NA GRADE", "A definir"),
        ("2º BI", "BI C&T", "2º", "IEG010011", "Linguagem e Comunicação", 60, 40, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("2º BI", "BI C&T", "2º", "IEG020001", "Cálculo II", 60, 50, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("2º BI", "BI C&T", "2º", "IEG020002", "Álgebra Linear", 60, 50, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("2º BI", "BI C&T", "2º", "IEG030003", "Física I", 60, 50, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("2º BI", "BI C&T", "2º", "IEG030004", "Laboratório de Física I", 30, 20, "Turma 01", "Lab Alpha - Rondon", "SEM HORÁRIO NA GRADE", "A definir"),
        ("2º BI", "BI C&T", "2º", "PCT30027", "Introdução à Probabilidade e Estatística", 60, 40, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),

        # 2º MEC (EMEC21 — 8 obrigatórias, Lab Física I com 2 turmas práticas de 20 vagas)
        ("2º MEC", "Eng. Mecânica", "2º", "CTEC0006", "Metodologia Científica", 60, 40, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("2º MEC", "Eng. Mecânica", "2º", "EMEC0002", "Desenho Técnico Mecânico I", 60, 50, "", "Sala 229 BMT - Laboratório de Desenho", "SEM HORÁRIO NA GRADE", "A definir"),
        ("2º MEC", "Eng. Mecânica", "2º", "EMEC0003", "Química Tecnológica", 45, 40, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("2º MEC", "Eng. Mecânica", "2º", "IEG020001", "Cálculo II", 60, 50, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("2º MEC", "Eng. Mecânica", "2º", "IEG020002", "Álgebra Linear", 60, 50, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("2º MEC", "Eng. Mecânica", "2º", "IEG030003", "Física I", 60, 50, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("2º MEC", "Eng. Mecânica", "2º", "IEG030004", "Laboratório de Física I", 30, 20, "Turma 01", "Lab Beta - Rondon", "SEM HORÁRIO NA GRADE", "A definir"),
        ("2º MEC", "Eng. Mecânica", "2º", "IEG030004", "Laboratório de Física I", 30, 20, "Turma 02", "Lab Beta - Rondon", "SEM HORÁRIO NA GRADE", "A definir"),
        ("2º MEC", "Eng. Mecânica", "2º", "PCT30027", "Introdução à Probabilidade e Estatística", 60, 40, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),

        # 4º BI (BICT24 7 obrigatórias + SFIS0003 obrigatória EFIS23 / optativa BICT24)
        ("4º BI", "BI C&T", "4º", "CTEC0007", "Fenômenos de Transporte", 60, 40, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("4º BI", "BI C&T", "4º", "CTEC0008", "Programação II", 60, 40, "", "Lab de Informática - Sala 145 BMT II", "SEM HORÁRIO NA GRADE", "A definir"),
        ("4º BI", "BI C&T", "4º", "CTEC0009", "Metrologia", 45, 40, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("4º BI", "BI C&T", "4º", "EFIS0005", "Fundamentos da Administração", 60, 40, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("4º BI", "BI C&T", "4º", "IEG020033", "Cálculo IV", 60, 40, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("4º BI", "BI C&T", "4º", "IEG020065", "Física III", 60, 40, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("4º BI", "BI C&T", "4º", "PCT30008", "Laboratório de Física III", 30, 20, "Turma 01", "Lab Alpha - Rondon", "SEM HORÁRIO NA GRADE", "A definir"),
        ("4º BI", "BI C&T", "4º", "SFIS0003", "Química Tecnológica", 45, 40, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),

        # 4º MEC (EMEC21 — 8 obrigatórias)
        ("4º MEC", "Eng. Mecânica", "4º", "EMEC0009", "Física III", 60, 40, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("4º MEC", "Eng. Mecânica", "4º", "EMEC0010", "Resistência dos Materiais I", 60, 40, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("4º MEC", "Eng. Mecânica", "4º", "EMEC0011", "Mecânica Geral II", 60, 40, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("4º MEC", "Eng. Mecânica", "4º", "EMEC0012", "Fundamentos de Engenharia Ambiental", 45, 40, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("4º MEC", "Eng. Mecânica", "4º", "EMEC0013", "Engenharia Econômica", 45, 40, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("4º MEC", "Eng. Mecânica", "4º", "IEG020033", "Cálculo IV", 60, 40, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("4º MEC", "Eng. Mecânica", "4º", "IEG070054", "Métodos Matemáticos II", 60, 40, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("4º MEC", "Eng. Mecânica", "4º", "PCT30008", "Laboratório de Física III", 30, 20, "Turma 01", "Lab Beta - Rondon", "SEM HORÁRIO NA GRADE", "A definir"),

        # 6º BI (BICT24 aula + EFIS23 6º nível — exclui TCC e Extensão de orientação)
        ("6º BI", "BI C&T", "6º", "PCT30010", "Legislação e Segurança no Trabalho", 45, 40, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("6º BI", "BI C&T", "6º", "SFIS0005", "Introdução à Economia", 45, 40, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("6º BI", "BI C&T", "6º", "PCT30037", "Métodos Matemáticos I", 60, 40, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("6º BI", "BI C&T", "6º", "PCT30053", "Circuitos Elétricos", 60, 40, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("6º BI", "BI C&T", "6º", "PCT30054", "Laboratório de Circuitos Elétricos", 30, 20, "Turma 01", "Lab de Sinais e Sistemas", "SEM HORÁRIO NA GRADE", "A definir"),
        ("6º BI", "BI C&T", "6º", "PCT30069", "Ciências e Tecnologia dos Materiais", 60, 40, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("6º BI", "BI C&T", "6º", "SFIS0004", "Termodinâmica Aplicada", 60, 40, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),

        # 6º MEC (EMEC21 — 7 obrigatórias)
        ("6º MEC", "Eng. Mecânica", "6º", "EMEC0020", "Termodinâmica II", 60, 40, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("6º MEC", "Eng. Mecânica", "6º", "EMEC0021", "Mecânica dos Fluidos I", 75, 40, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("6º MEC", "Eng. Mecânica", "6º", "EMEC0022", "Transferência de Calor e Massa I", 75, 40, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("6º MEC", "Eng. Mecânica", "6º", "EMEC0023", "Cinemática e Dinâmica das Máquinas", 60, 40, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("6º MEC", "Eng. Mecânica", "6º", "EMEC0024", "Eletrotécnica Geral", 60, 40, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("6º MEC", "Eng. Mecânica", "6º", "EMEC0025", "Materiais de Construção Mecânica II", 75, 40, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("6º MEC", "Eng. Mecânica", "6º", "EMEC0026", "Processo de Fabricação II", 45, 40, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),

        # 8º EF (EFIS23 / EFIS17 — 5 obrigatórias idênticas)
        ("8º EF", "Eng. Física", "8º", "EFIS0020", "Automação e Supervisão de Processos", 60, 35, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("8º EF", "Eng. Física", "8º", "IEG070018", "Física Moderna", 60, 35, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("8º EF", "Eng. Física", "8º", "IEG070056", "Sistemas de Controle", 60, 35, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("8º EF", "Eng. Física", "8º", "IEG070107", "Teoria Eletromagnética I", 60, 35, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("8º EF", "Eng. Física", "8º", "IEG070109", "Modelagem Computacional I", 60, 35, "", "Sala de Informática", "SEM HORÁRIO NA GRADE", "A definir"),

        # 8º MEC (EMEC21 — 7 obrigatórias)
        ("8º MEC", "Eng. Mecânica", "8º", "EMEC0032", "Turbomáquinas", 60, 35, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("8º MEC", "Eng. Mecânica", "8º", "EMEC0033", "Sistemas Fluidotérmicos I", 60, 35, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("8º MEC", "Eng. Mecânica", "8º", "EMEC0034", "Elementos de Máquina II", 60, 35, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("8º MEC", "Eng. Mecânica", "8º", "EMEC0035", "Vibrações", 60, 35, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("8º MEC", "Eng. Mecânica", "8º", "EMEC0036", "Instrumentação e Controle de Processos Industriais", 60, 35, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
        ("8º MEC", "Eng. Mecânica", "8º", "EMEC0037", "Soldagem", 60, 35, "", "Oficina Mecânica / Lab de Manufatura (PC&T)", "SEM HORÁRIO NA GRADE", "A definir"),
        ("8º MEC", "Eng. Mecânica", "8º", "EMEC0038", "Engenharia de Produção I", 45, 35, "", "A DEFINIR", "SEM HORÁRIO NA GRADE", "A definir"),
    ]
    df_of = pd.DataFrame(
        oferta_2027_2,
        columns=[
            "Aba_Origem", "Curso", "Período", "Código_SIGAA", "Componente_Curricular",
            "CH_Total", "Vagas", "Turma", "Sala_Alocada", "Horário_SIGAA", "Docente_Alocado",
        ],
    )
    return enriquecer_oferta(df_of), df_cred


# ==============================================================================
# 6. LEITURA LIMPA DA PLANILHA EXCEL + ENRIQUECIMENTO COM MATRIZES SIGAA
# ==============================================================================
def _detectar_linha_cabecalho(xls: pd.ExcelFile, sheet_name: str, coluna_alvo: str) -> int:
    """Encontra automaticamente em qual linha (0 a 5) está o cabeçalho da aba."""
    amostra = pd.read_excel(xls, sheet_name=sheet_name, header=None, nrows=6)
    alvo_n = norm(coluna_alvo)
    for r_idx in range(len(amostra)):
        valores = [norm(v) for v in amostra.iloc[r_idx].tolist()]
        if alvo_n in valores:
            return r_idx
    return 0


def enriquecer_oferta(df_of: pd.DataFrame) -> pd.DataFrame:
    """Padroniza colunas, nomes, salas e vincula códigos vigentes das estruturas SIGAA."""
    df = df_of.copy()

    renomear = {
        "Sala_Padronizada": "Sala_Alocada",
        "Local/Sala": "Sala_Alocada",
        "Docente(s)": "Docente_Alocado",
        "Código da Disciplina": "Código_SIGAA",
        "Nomenclatura da Disciplina": "Componente_Curricular",
        "Carga Horária": "CH_Total",
        "Número de Vagas": "Vagas",
    }
    df = df.rename(columns={k: v for k, v in renomear.items() if k in df.columns and v not in df.columns})

    if "Turma" not in df.columns:
        df["Turma"] = ""

    df["Turma"] = df["Turma"].fillna("").astype(str).str.strip()
    df["Código_SIGAA"] = df["Código_SIGAA"].fillna("").astype(str).str.strip().str.upper()
    df["CH_Total"] = (
        df["CH_Total"].astype(str).str.replace("h", "", case=False, regex=False).str.strip().astype(int)
    )
    df["Vagas"] = pd.to_numeric(df["Vagas"], errors="coerce").fillna(40).astype(int)
    df["Docente_Alocado"] = df["Docente_Alocado"].apply(padronizar_docente)
    df["Sala_Alocada"] = df["Sala_Alocada"].apply(padronizar_sala)
    df["Horário_SIGAA"] = df["Horário_SIGAA"].fillna("SEM HORÁRIO NA GRADE").astype(str).str.strip()

    # Metadados derivados do inventário oficial de salas e famílias unificáveis
    df["Gestão_Sala"] = df["Sala_Alocada"].apply(
        lambda s: SALAS_INVENTARIO.get(s, {}).get("Gestao", "Externa (Não Cadastrada)")
    )
    df["Capacidade_Sala"] = df["Sala_Alocada"].apply(
        lambda s: SALAS_INVENTARIO.get(s, {}).get("Capacidade", 0)
    )
    df["Família_Unificação"] = df["Componente_Curricular"].apply(identificar_familia_unificacao)
    df["Qtd_Slots"] = df["Horário_SIGAA"].apply(lambda h: len(expandir_horario_sigaa(h)))

    # Cruzamento automático com as 4 estruturas curriculares oficiais do SIGAA
    infos_sigaa = [
        consultar_componente_sigaa(r["Código_SIGAA"], r["Componente_Curricular"], r.get("Curso", ""))
        for _, r in df.iterrows()
    ]
    df["Vigente_SIGAA"] = [x["vigente_sigaa"] for x in infos_sigaa]
    df["Matriz_SIGAA"] = [x["matrizes"] for x in infos_sigaa]
    df["Natureza_SIGAA"] = [x["natureza"] for x in infos_sigaa]
    df["CH_Oficial_SIGAA"] = [x["ch_sigaa"] for x in infos_sigaa]

    return df.reset_index(drop=True)


def carregar_dados_planilha(fonte_excel: Any) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Lê a planilha consolidada (.xlsx) e aplica limpeza + filtro do quadro ativo."""
    xls = pd.ExcelFile(fonte_excel)

    aba_oferta = next((s for s in xls.sheet_names if "oferta" in norm(s)), xls.sheet_names[0])
    skip_of = _detectar_linha_cabecalho(xls, aba_oferta, "Código_SIGAA")
    df_of_raw = pd.read_excel(xls, sheet_name=aba_oferta, skiprows=skip_of)
    df_of = enriquecer_oferta(df_of_raw)

    aba_cred = next((s for s in xls.sheet_names if "credenciamento" in norm(s)), None)
    if aba_cred:
        skip_cr = _detectar_linha_cabecalho(xls, aba_cred, "Docente")
        df_cred = pd.read_excel(xls, sheet_name=aba_cred, skiprows=skip_cr)
        df_cred["Docente"] = df_cred["Docente"].apply(padronizar_docente)
        df_cred = df_cred[~df_cred["Docente"].isin(DOCENTES_REMOVIDOS)].reset_index(drop=True)
    else:
        _, df_cred = carregar_base_embutida()

    return df_of, df_cred


def carregar_base(
    caminho_padrao: str | None = None,
    arquivo_upload: Any = None,
    semestre: str = "2027.1",
) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    """
    Ponto de entrada único para o app.py (Modo Anual: 2027.1 Ímpares e 2027.2 Pares):
    1. Usa o arquivo enviado pelo usuário (se houver);
    2. Senão, carrega a planilha mais recente do semestre escolhido na pasta 'dados/';
    3. Caso não exista no disco, usa a base embutida correspondente do SIGAA.
    """
    if arquivo_upload is not None:
        df_of, df_cred = carregar_dados_planilha(arquivo_upload)
        return df_of, df_cred, f"Upload: {getattr(arquivo_upload, 'name', 'planilha.xlsx')}"

    if caminho_padrao and os.path.exists(caminho_padrao):
        df_of, df_cred = carregar_dados_planilha(caminho_padrao)
        return df_of, df_cred, f"Arquivo local: {caminho_padrao}"

    if "2027.2" in str(semestre) or "par" in norm(semestre):
        for nome_par in (
            "Sistema_Oferta_Credenciamento_PCT_2027_2-v1.xlsx",
        ):
            caminho_p = os.path.join(DADOS_DIR, nome_par)
            if os.path.exists(caminho_p):
                df_of, df_cred = carregar_dados_planilha(caminho_p)
                return df_of, df_cred, f"Arquivo local: dados/{nome_par}"
        df_of, df_cred = carregar_base_embutida_2027_2()
        return df_of, df_cred, "Base padrão embutida (2027.2 • Pares SIGAA)"

    for nome_impar in (
        "Sistema_Oferta_Credenciamento_PCT_2027_1-v6.xlsx",
        "Sistema_Oferta_Credenciamento_PCT_2027_1-v5.xlsx",
        "Sistema_Oferta_Credenciamento_PCT_2027_1-v4.xlsx",
        "Sistema_Oferta_Credenciamento_PCT_2027_1-v3.xlsx",
    ):
        caminho_i = os.path.join(DADOS_DIR, nome_impar)
        if os.path.exists(caminho_i):
            df_of, df_cred = carregar_dados_planilha(caminho_i)
            return df_of, df_cred, f"Arquivo local: dados/{nome_impar}"

    df_of, df_cred = carregar_base_embutida()
    return df_of, df_cred, "Base padrão embutida (2027.1 • v6 SIGAA + Labs)"


def gerar_tabela_salas_inventario() -> pd.DataFrame:
    """Retorna o inventário oficial de salas e laboratórios em formato DataFrame."""
    linhas = []
    for sala, info in SALAS_INVENTARIO.items():
        if sala == "A DEFINIR":
            continue
        linhas.append({
            "Espaço / Sala": sala,
            "Gestão": info["Gestao"],
            "Tipo": info["Tipo"],
            "Capacidade": info["Capacidade"],
            "Gargalo": info["Gargalo"],
        })
    return pd.DataFrame(linhas)
