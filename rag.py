import os
import logging
import warnings

# --- SILENCIA AVISOS INTERNOS DE PDFs E ENGINES ---
os.environ["TOKENIZERS_PARALLELISM"] = "false"
logging.getLogger("pypdf").setLevel(logging.ERROR)
logging.getLogger("pdfplumber").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", category=UserWarning)
# --------------------------------------------------

import glob
import sys
from openai import OpenAI
import chromadb
from chromadb.utils import embedding_functions
from langchain_text_splitters import RecursiveCharacterTextSplitter
import pdfplumber

# 1. Conectar ao servidor Llamafile (Porta 666)
client = OpenAI(
    base_url="http://127.0.0.1:666/v1",
    api_key="sk-no-key-required"
)

# 2. Configurar o Modelo de Embedding (100% Local)
embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

# 3. Inicializar o Banco de Dados Vetorial na pasta local
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "banco_vetores")

banco_ja_existe = os.path.exists(db_path) and len(os.listdir(db_path)) > 0

chroma_client = chromadb.PersistentClient(path=db_path)
collection = chroma_client.get_or_create_collection(
    name="meu_contexto_r2",
    embedding_function=embedding_func
)

# FIX: splitter criado uma única vez fora dos loops
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1400, chunk_overlap=200)


def extrair_texto_pdf(caminho_pdf):
    """Extrai texto de um PDF retornando lista de (num_pagina, texto).
    Mantém o texto completo do documento para split coerente entre páginas.
    """
    paginas = []
    try:
        with pdfplumber.open(caminho_pdf) as pdf:
            for num_pag, pagina in enumerate(pdf.pages, 1):
                texto = pagina.extract_text()
                if texto and texto.strip():
                    paginas.append((num_pag, texto))
    except Exception as e:
        print(f"Erro ao ler PDF {os.path.basename(caminho_pdf)}: {e}")
    return paginas


def carregar_e_atualizar_pasta_documentos():
    """Lê arquivos da pasta 'documentos' e alimenta o ChromaDB em lotes seguros."""
    pasta_docs = os.path.join(BASE_DIR, "documentos")

    if not os.path.exists(pasta_docs):
        os.makedirs(pasta_docs)
        print(f"Pasta 'documentos' criada em {pasta_docs}. Coloque seus PDFs nela.")
        return

    arquivos_txt = glob.glob(os.path.join(pasta_docs, "*.txt"))
    arquivos_pdf = glob.glob(os.path.join(pasta_docs, "*.pdf"))
    todos_arquivos = arquivos_txt + arquivos_pdf

    if not todos_arquivos:
        print("Nenhum arquivo .txt ou .pdf encontrado na pasta 'documentos'.")
        return

    print(f"Indexando novos arquivos... Encontrado(s) {len(todos_arquivos)} arquivo(s).")

    documentos_totais = []
    ids_totais = []
    metadatas_totais = []

    for caminho_arquivo in todos_arquivos:
        nome_arquivo = os.path.basename(caminho_arquivo)
        # FIX: contador local por arquivo — IDs estáveis independente da ordem dos arquivos
        contador_local = 0

        try:
            if caminho_arquivo.endswith('.txt'):
                # FIX: errors="replace" evita crash em TXTs com encoding inesperado
                with open(caminho_arquivo, "r", encoding="utf-8", errors="replace") as f:
                    texto_completo = f.read()

                if not texto_completo.strip():
                    continue

                for pedaco in text_splitter.split_text(texto_completo):
                    documentos_totais.append(pedaco)
                    ids_totais.append(f"{nome_arquivo}_chunk{contador_local}")
                    metadatas_totais.append({"source": nome_arquivo, "page": 1})
                    contador_local += 1

            elif caminho_arquivo.endswith('.pdf'):
                print(f"Lendo: {nome_arquivo}")
                paginas = extrair_texto_pdf(caminho_arquivo)

                if not paginas:
                    continue

                # FIX: concatena o texto completo para que o split seja coerente
                # entre páginas — chunks não serão mais truncados na virada de página
                texto_completo = "\n".join(texto for _, texto in paginas)

                # Mapa de offsets para determinar a página aproximada de cada chunk
                offset = 0
                limites_paginas = []
                for num_pag, texto in paginas:
                    limites_paginas.append((offset, num_pag))
                    offset += len(texto) + 1  # +1 pelo "\n" de separação

                pos_busca = 0
                for pedaco in text_splitter.split_text(texto_completo):
                    idx = texto_completo.find(pedaco, pos_busca)
                    if idx == -1:
                        idx = texto_completo.find(pedaco)

                    # Página do chunk = última página cujo início está antes do chunk
                    pagina_chunk = limites_paginas[0][1] if limites_paginas else 1
                    for (start, pnum) in limites_paginas:
                        if idx >= start:
                            pagina_chunk = pnum
                        else:
                            break

                    documentos_totais.append(pedaco)
                    ids_totais.append(f"{nome_arquivo}_chunk{contador_local}")
                    metadatas_totais.append({"source": nome_arquivo, "page": pagina_chunk})
                    contador_local += 1
                    pos_busca = max(0, idx)

        except Exception as e:
            print(f"Erro no arquivo {nome_arquivo}: {e}")

    total_chunks = len(documentos_totais)
    if total_chunks > 0:
        print(f"Enviando {total_chunks} pedaços para o banco de vetores...")
        tamanho_lote = 2000
        for i in range(0, total_chunks, tamanho_lote):
            collection.upsert(
                documents=documentos_totais[i:i + tamanho_lote],
                ids=ids_totais[i:i + tamanho_lote],
                metadatas=metadatas_totais[i:i + tamanho_lote]
            )
        print("Banco de dados local 100% atualizado e persistido!")
    else:
        print("Nenhum conhecimento novo para adicionar.")


def buscar_contexto(pergunta, top_k=4):
    """Busca os trechos mais relevantes e retorna o contexto e as fontes."""
    # FIX: collection.count() chamado uma única vez e armazenado
    total = collection.count()
    if total == 0:
        return "AVISO: Nenhum documento indexado.", []

    results = collection.query(
        query_texts=[pergunta],
        n_results=min(top_k, total)
    )

    contexto = ""
    fontes = []

    for i in range(len(results['ids'][0])):
        meta = results['metadatas'][0][i] or {}
        nome = meta.get('source', 'Desconhecido')
        pagina = meta.get('page', 'N/A')

        fonte_str = f"{os.path.basename(nome)} (pág. {pagina})"
        if fonte_str not in fontes:
            fontes.append(fonte_str)

        contexto += results['documents'][0][i] + "\n\n"

    return contexto, fontes


def perguntar_ia(pergunta, historico=None, temperatura=0.3, top_p=0.9, max_tokens=2048, top_k_rag=4, system_prompt_custom=""):
    """Busca o contexto, chama a IA e retorna a resposta e as fontes."""
    # FIX: argumento mutável padrão substituído por None
    if historico is None:
        historico = []

    contexto, fontes = buscar_contexto(pergunta, top_k=top_k_rag)

    # FIX: "..." só aparece se a pergunta for realmente longa
    pergunta_log = pergunta[:60] + ("..." if len(pergunta) > 60 else "")
    print(f"[RAG] Pergunta: '{pergunta_log}' | Trechos: {top_k_rag} | Ctx chars: {len(contexto)}")

    prompt_completo = f"{system_prompt_custom}\n\n--- CONTEXTO LOCAL (LIVROS/PDFs) ---\n{contexto}\n---------------------"

    messages = [{"role": "system", "content": prompt_completo}]

    for msg in historico:
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": pergunta})

    try:
        response = client.chat.completions.create(
            model="phi-3.5-mini-instruct-q4_k_m.gguf",
            messages=messages,
            temperature=temperatura,
            top_p=top_p,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content, fontes
    except Exception as e:
        return f"Erro ao conectar ao servidor local: {e}", []


# --- Inicialização Inteligente ---
if __name__ == "__main__":
    forçar_atualizacao = len(sys.argv) > 1 and sys.argv[1].lower() == "atualizar"

    if not banco_ja_existe or forçar_atualizacao:
        print("[INFO] Criando ou atualizando a base de conhecimento pré-compilada...")
        carregar_e_atualizar_pasta_documentos()
    else:
        print("[OK] Base de dados vetorial detectada! Carregando RAG pré-compilado instantaneamente...")
        print(f"[R2 INFO] {collection.count()} pedaços de conhecimento prontos para uso.")

    print("\n=========================================")
    print("      R2 TACTICAL OS - RAG OFFLINE       ")
    print("=========================================")
    print("Digite sua pergunta ou 'sair' para encerrar.\n")

    while True:
        pergunta = input("R2 >> ")
        if pergunta.lower() == 'sair':
            print("Encerrando interface de consulta.")
            break

        if not pergunta.strip():
            continue

        resposta, fontes = perguntar_ia(pergunta)
        print(f"\nResposta:\n{resposta}\n")
        # FIX: fontes exibidas no modo CLI
        if fontes:
            print(f"Fontes: {', '.join(fontes)}")
        print("-" * 40)