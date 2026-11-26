# 🚀 Guia de Publicação na Nuvem — GitHub + Streamlit Community Cloud

Este guia coloca o **Dashboard PC&T / UFOPA** no ar gratuitamente com um link direto de navegador (ex.: `https://dashboard-pct-ufopa.streamlit.app`) para acesso do Prof. Ubiraelson e do Colegiado — sem precisar instalar Python ou Miniconda.

---

## Pré-requisito (1 vez apenas)

1. Crie ou acesse sua conta gratuita no **GitHub** (`https://github.com`).
2. Verifique se o **Git** está instalado no seu Windows abrindo o terminal do VS Code e rodando `git --version`.
   * Se não estiver instalado, baixe em `https://git-scm.com/download/win` (avançar em todas as telas) e reinicie o VS Code.

---

## Passo 1 — Criar o Repositório no GitHub

1. No GitHub, clique no botão **`+`** (canto superior direito) → **New repository**.
2. Preencha:
   * **Repository name:** `dashboard-pct-ufopa`
   * **Visibilidade:** pode escolher **Private** (recomendado para manter os dados institucionais restritos — o Streamlit Community Cloud suporta repositórios privados gratuitamente!).
   * Deixe **desmarcadas** as opções de adicionar `README` ou `.gitignore` (já criamos esses arquivos prontos na pasta).
3. Clique em **Create repository** e copie a URL do repositório (ex.: `https://github.com/SEU_USUARIO/dashboard-pct-ufopa.git`).

---

## Passo 2 — Subir o Projeto do seu Computador para o GitHub

> **Atenção:** como a pasta está no Google Drive (`G:\`), recomenda-se fazer uma cópia limpa fora do Drive (ex.: `C:\Projetos\dashboard-pct-ufopa`) antes do `git init`, para evitar que o Google Drive trave arquivos internos da pasta `.git`.

No PowerShell (terminal do VS Code), execute:

```powershell
# 1. Criar cópia limpa fora do Google Drive (evita conflitos de sincronização do .git)
$origem = "G:\Meu Drive\Automação de Ofertas e Credenciamento Docente - C&T (PPCs)_Automacao_Dashboard_e_Diagnostico\dashboard_pct_ufopa"
$destino = "C:\Projetos\dashboard-pct-ufopa"
New-Item -ItemType Directory -Force -Path $destino | Out-Null
Copy-Item -Path "$origem\*" -Destination $destino -Recurse -Force

# 2. Entrar na pasta e organizar a configuração do Streamlit
cd $destino
New-Item -ItemType Directory -Force -Path ".streamlit" | Out-Null
if (Test-Path "config.toml") { Move-Item -Force "config.toml" ".streamlit\config.toml" }
if (Test-Path "gitignore.txt") { Move-Item -Force "gitignore.txt" ".gitignore" }

# 3. Inicializar o Git e enviar ao GitHub (substitua SEU_USUARIO)
git init
git branch -M main
git add .
git commit -m "Deploy inicial v7.1 - Dashboard PCT UFOPA (Modo Anual SIGAA)"
git remote add origin https://github.com/SEU_USUARIO/dashboard-pct-ufopa.git
git push -u origin main
```

*(Na primeira vez, o Git abrirá uma janela do navegador para autenticar na sua conta GitHub.)*

---

## Passo 3 — Publicar no Streamlit Community Cloud (Gratuito)

1. Acesse **`https://share.streamlit.io`** e clique em **Continue with GitHub**.
2. Clique em **Create app** → **Deploy a public app from GitHub** (funciona também com repositório privado autorizado).
3. Preencha os campos:
   * **Repository:** `SEU_USUARIO/dashboard-pct-ufopa`
   * **Branch:** `main`
   * **Main file path:** `app.py`
   * **App URL (opcional):** `dashboard-pct-ufopa`
4. Clique em **Advanced settings...** *(passo muito importante!)*:
   * **Python version:** selecione **`3.11`** (garante compatibilidade imediata e instalação rápida do `ortools`).
   * **Secrets (TOML):** cole abaixo para ativar a **proteção por senha institucional** e (opcionalmente) a chave gratuita da **Groq**:
     ```toml
     SENHA_ACESSO = "PCT-UFOPA-2027"
     GROQ_API_KEY = "gsk_cole_sua_chave_aqui_se_quiser"
     ```
     *(Se quiser deixar o link aberto sem pedir senha, basta omitir a linha `SENHA_ACESSO`.)*
5. Clique em **Save** e depois em **Deploy!**.

Em cerca de **2 a 3 minutos**, o Streamlit instalará o `requirements.txt` e abrirá o link definitivo pronto para enviar ao Prof. Ubiraelson e ao Colegiado!

---

## Como Atualizar o Dashboard no Futuro

Sempre que você atualizar uma planilha em `dados/` ou algum módulo em `modulos/`:

```powershell
cd C:\Projetos\dashboard-pct-ufopa
git add .
git commit -m "Atualizacao oferta 2027.1"
git push
```

O Streamlit Cloud detecta o `git push` e atualiza o site automaticamente em menos de 1 minuto.
