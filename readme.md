# 🚀 R2 Tactical OS

![Status](https://img.shields.io/badge/Status-Online-success)
![Version](https://img.shields.io/badge/Version-3.0-blue)
![Python](https://img.shields.io/badge/Python-3.10%2B-yellow)
![License](https://img.shields.io/badge/License-Private-red)

O **R2 Tactical OS** é um sistema centralizado de inteligência, automação e OSINT (Open-Source Intelligence). Funciona como um cérebro digital e painel de comando operado via Telegram, integrando uma rede de módulos de recolha de dados globais, processamento local de IA (LLM + RAG 100% offline) e automação de tarefas.

---

## 🏗️ Arquitetura do Sistema

O sistema está dividido em três camadas principais para garantir estabilidade, segurança e execução não-bloqueante (assíncrona):

1. **Camada 1: Cérebro Local (RAG & LLM) - `rag.py` e `start.bat`**
   - Execução de modelos GGUF via Llamafile na porta 666.
   - Base de dados vetorial ChromaDB alimentada por documentos locais (PDF/TXT) via `pdfplumber`.
   - Embeddings gerados localmente sem dependência de APIs externas (privacidade total).

2. **Camada 2: Ponte de Comunicação (API Flask) - `main.py`**
   - Interface Web (Matrix OS style) para controlo visual.
   - Rotas de API seguras para injeção de contexto e persistência de memória (`chat_memoria.json`).

3. **Camada 3: Controlo e Interface Externa (Uplink) - `uplink.py` e `telegram_uplink.py`**
   - Operação assíncrona baseada em `asyncio` e `threading`.
   - Carregamento preguiçoso (Lazy Loading) de módulos pesados.
   - Acesso restrito a um conjunto de IDs de utilizador autorizados.

---

## ⚙️ Módulos e Funcionalidades (Features)

A pasta `/features` contém o arsenal do R2, dividido nas seguintes categorias táticas:

* ☀️ **Espaço e Órbita:** Relatórios solares (NOAA), monitorização de asteroides (NASA) e rastreio da ISS em tempo real com trajetórias 3D.
* 🌍 **Superfície e Geologia:** Radar de voos, meteorologia, alertas de sismos (USGS) e atividade vulcânica (Smithsonian).
* ☢️ **Geopolítica e Inteligência:** Nível DEFCON (PizzINT), relatórios de frentes de guerra (Ucrânia, Israel, Irão, Líbano) e *Breaking News*.
* 💱 **Economia:** Cotações de mercado (USD, EUR, BTC) e Quantum Core (Automação de Trading).
* 📡 **Rede e Segurança:** Scanner de rede local (ARP), testes de velocidade, rádio scanner de transmissões globais e modo Sentinela (captura de câmara).
* 🤖 **Processamento Neural:** IA local sem censura e processamento/edição de vídeos virais (*Tesoura Neural*).

---

## 🛠️ Configuração e Instalação

### Pré-requisitos
* Python 3.10 ou superior.
* Llamafile executável (para o servidor LLM local).
* Modelos GGUF (ex: Dolphin, Phi-3.5) na pasta `/models`.

### 1. Clonar e Preparar
```bash
git clone <url-do-repositorio>
cd R2-Tactical-OS
mkdir modelos documentos temp logs
2. Instalar Dependências
Bash
pip install -r requirements.txt
3. Variáveis de Ambiente (.env)
Crie um ficheiro .env na raiz do projeto com as credenciais necessárias:

Snippet de código
TELEGRAM_TOKEN=seu_token_aqui
OPENWEATHER_API_KEY=sua_chave_aqui
NASA_API_KEY=sua_chave_aqui
# Adicione outras chaves conforme os módulos exigirem
4. Inicialização do Sistema
Ativar LLM Local: Execute o ficheiro start.bat para levantar o servidor Llamafile na porta 666.

Iniciar o Cérebro RAG (Opcional): python rag.py atualizar (apenas para indexar novos PDFs).

Ligar o Núcleo R2: Execute python uplink.py para estabelecer a ligação com o Telegram e colocar o sistema online.

⚠️ Avisos de Segurança
NUNCA faça commit dos seus ficheiros .env, .key ou da pasta banco_vetores/. (Verifique o .gitignore).

Acesso ao Telegram Uplink está restrito (Hardcoded UID no telegram_uplink.py). Mantenha os seus UIDs seguros.
