from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import json
import rag

# Inicializa o Flask mapeando as pastas estáticas conforme a arquitetura do Matrix OS
app = Flask(__name__, template_folder="templates", static_folder="static")

HISTORICO_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat_memoria.json")

def get_historico():
    """Carrega o histórico persistente do arquivo JSON no servidor."""
    if os.path.exists(HISTORICO_FILE):
        try:
            with open(HISTORICO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []

def salvar_historico(novo_historico):
    """Persiste o histórico no disco em formato JSON."""
    with open(HISTORICO_FILE, "w", encoding="utf-8") as f:
        json.dump(novo_historico, f, ensure_ascii=False, indent=4)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    dados = request.json
    pergunta = dados.get('pergunta')
    
    # Carrega memória persistente do servidor
    memoria_completa = get_historico()

    # Parâmetros vindos dos sliders customizados da interface Matrix
    temperatura = float(dados.get('temperatura', 0.3))
    top_p = float(dados.get('top_p', 0.9))
    max_tokens = int(dados.get('max_tokens', 2048))
    top_k_rag = int(dados.get('top_k_rag', 4))
    system_prompt = dados.get('system_prompt', "")

    # A IA recebe os últimos 10 turnos (mensagens anteriores) para manter contexto.
    # Não incluímos a 'pergunta' atual aqui porque o rag.py a anexa manualmente no final do prompt.
    resposta, fontes = rag.perguntar_ia(
        pergunta=pergunta,
        historico=memoria_completa[-10:],
        temperatura=temperatura,
        top_p=top_p,
        max_tokens=max_tokens,
        top_k_rag=top_k_rag,
        system_prompt_custom=system_prompt
    )
    
    # Atualiza a memória com o novo par de mensagens e persiste no disco
    memoria_completa.append({"role": "user", "content": pergunta})
    memoria_completa.append({"role": "assistant", "content": resposta})
    salvar_historico(memoria_completa)
    
    return jsonify({
        "resposta": resposta,
        "fontes": fontes
    })

@app.route('/api/atualizar', methods=['POST'])
def atualizar_banco():
    try:
        rag.carregar_e_atualizar_pasta_documentos()
        return jsonify({"status": "sucesso"})
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)})

@app.route('/api/reset', methods=['POST'])
def reset_memoria():
    """Reseta o arquivo de memória no servidor."""
    try:
        if os.path.exists(HISTORICO_FILE):
            os.remove(HISTORICO_FILE)
        return jsonify({"status": "Memória tática limpa"})
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)})

# Nova rota para carregar o histórico inicial na interface
@app.route('/api/historico', methods=['GET'])
def get_chat_historico():
    """Retorna o histórico completo do chat."""
    return jsonify(get_historico())

# BUG-M05: favicon (evita 404)
@app.route('/favicon.ico')
def favicon():
    ico_path = os.path.join(app.static_folder, 'favicon.ico')
    if os.path.exists(ico_path):
        return send_from_directory(app.static_folder, 'favicon.ico', mimetype='image/x-icon')
    return ('', 204)
from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import json
import requests as req  # FIX: import movido para o topo
import rag

app = Flask(__name__, template_folder="templates", static_folder="static")

HISTORICO_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat_memoria.json")
HISTORICO_MAX = 100  # FIX: limite de mensagens mantidas no disco


def get_historico():
    """Carrega o histórico persistente do arquivo JSON no servidor."""
    if os.path.exists(HISTORICO_FILE):
        try:
            with open(HISTORICO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []


def salvar_historico(novo_historico):
    """Persiste os últimos HISTORICO_MAX registros no disco."""
    # FIX: try/except evita crash silencioso por disco cheio ou permissão negada
    try:
        with open(HISTORICO_FILE, "w", encoding="utf-8") as f:
            # FIX: limita o arquivo para não crescer indefinidamente
            json.dump(novo_historico[-HISTORICO_MAX:], f, ensure_ascii=False, indent=4)
    except IOError as e:
        print(f"[AVISO] Falha ao salvar histórico: {e}")


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/api/chat', methods=['POST'])
def chat():
    dados = request.json
    pergunta = dados.get('pergunta')

    # FIX: valida 'pergunta' antes de propagar — evita erro 500 obscuro no ChromaDB
    if not pergunta or not str(pergunta).strip():
        return jsonify({"erro": "Campo 'pergunta' ausente ou vazio."}), 400

    memoria_completa = get_historico()

    temperatura = float(dados.get('temperatura', 0.3))
    top_p = float(dados.get('top_p', 0.9))
    max_tokens = int(dados.get('max_tokens', 2048))
    top_k_rag = int(dados.get('top_k_rag', 4))
    system_prompt = dados.get('system_prompt', "")

    resposta, fontes = rag.perguntar_ia(
        pergunta=pergunta,
        historico=memoria_completa[-10:],
        temperatura=temperatura,
        top_p=top_p,
        max_tokens=max_tokens,
        top_k_rag=top_k_rag,
        system_prompt_custom=system_prompt
    )

    memoria_completa.append({"role": "user", "content": pergunta})
    memoria_completa.append({"role": "assistant", "content": resposta})
    salvar_historico(memoria_completa)

    return jsonify({
        "resposta": resposta,
        "fontes": fontes
    })


@app.route('/api/atualizar', methods=['POST'])
def atualizar_banco():
    try:
        rag.carregar_e_atualizar_pasta_documentos()
        return jsonify({"status": "sucesso"})
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)})


@app.route('/api/reset', methods=['POST'])
def reset_memoria():
    """Reseta o arquivo de memória no servidor."""
    try:
        if os.path.exists(HISTORICO_FILE):
            os.remove(HISTORICO_FILE)
        return jsonify({"status": "Memória tática limpa"})
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)})


@app.route('/api/historico', methods=['GET'])
def get_chat_historico():
    """Retorna o histórico completo do chat."""
    return jsonify(get_historico())


@app.route('/favicon.ico')
def favicon():
    ico_path = os.path.join(app.static_folder, 'favicon.ico')
    if os.path.exists(ico_path):
        return send_from_directory(app.static_folder, 'favicon.ico', mimetype='image/x-icon')
    return ('', 204)


@app.route('/api/status', methods=['GET'])
def status():
    try:
        r = req.get('http://127.0.0.1:666/v1/models', timeout=2)
        return jsonify({"ok": r.status_code == 200})
    except Exception:
        return jsonify({"ok": False})


if __name__ == '__main__':
    print("==================================================")
    print("       R2 TACTICAL OS - APILINK ONLINE           ")
    print("       Acesse: http://127.0.0.1:5000              ")
    print("==================================================")
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)
# BUG-M06: rota de status do Llamafile
@app.route('/api/status', methods=['GET'])
def status():
    try:
        import requests as req
        r = req.get('http://127.0.0.1:666/v1/models', timeout=2)
        return jsonify({"ok": r.status_code == 200})
    except:
        return jsonify({"ok": False})

if __name__ == '__main__':
    print("==================================================")
    # R2 Core Boot up sequence
    print("       R2 TACTICAL OS - APILINK ONLINE           ")
    print("       Acesse: http://127.0.0.1:5000              ")
    print("==================================================")
    # BUG-M02: debug controlado por env var
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)