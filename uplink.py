#!/usr/bin/env python3
"""
R2 TACTICAL OS — MAIN CONTROLLER v3.0
Substitui o r2_server.py. Arquitetura direta: asyncio + threads.

Estrutura de arquivos esperada:
  C:\\IA\\
    main.py           ← este arquivo
    .env              ← TELEGRAM_TOKEN, OPENWEATHER_API_KEY, NASA_API_KEY
    features\\
      telegram_uplink.py
      noaa_service.py
      astro_defense.py
      ... (demais módulos)
    models\\
      dolphin-2.9-llama3-8b-Q4_K_M.gguf  ← opcional (IA local)
"""

import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
import glob
import os
import sys
import threading
import time

from dotenv import load_dotenv

# ── Path Setup ─────────────────────────────────────────────────────────────────
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))   # C:\IA
FEATURES_DIR = os.path.join(BASE_DIR, "features")

sys.path.insert(0, BASE_DIR)        # permite: from features.xxx import ...

load_dotenv(os.path.join(BASE_DIR, ".env"))

# ── Import do Uplink (único import obrigatório no startup) ────────────────────
from features.telegram_uplink import TelegramBotUplink


# ══════════════════════════════════════════════════════════════════════════════
class R2Core:
    """
    Cérebro central do R2 Tactical OS.

    Protocolo de comunicação com telegram_uplink.py:
      • self.main_loop   → asyncio event loop (lido pelo uplink)
      • self.update_queue → asyncio.Queue onde chegam os comandos
    """

    def __init__(self):
        self.main_loop:    asyncio.AbstractEventLoop = None
        self.update_queue: asyncio.Queue             = None
        self.uplink:       TelegramBotUplink         = None

        # Estado de conversa por usuário  {user_id: {'step': str}}
        self.user_states: dict = {}

        # Cache de instâncias de módulos (lazy loading)
        self._cache: dict = {}
        self._last_cleanup = 0

        print("🧠 [R2 CORE]: Núcleo inicializado.")

    # ══════════════════════════════════════════════════════════════════════════
    # SEÇÃO 1 — COMUNICAÇÃO COM TELEGRAM
    # ══════════════════════════════════════════════════════════════════════════

    def enviar(self, texto: str, user_id: int):
        """Envia mensagem Markdown para o usuário"""
        # Adicionar tratamento para escape de caracteres especiais
        texto_safe = texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        try:
            if self.uplink:
                self.uplink.enviar_mensagem_ativa(texto_safe, user_id)
        except Exception as e:
            print(f"❌ Erro envio msg: {e}")
            # Fallback com mensagem simplificada
            if self.uplink:
                self.uplink.enviar_mensagem_ativa(f"❌ Erro técnico: {str(e)[:1000]}", user_id)

    def enviar_foto(self, path: str, legenda: str, user_id: int):
        """Envia imagem ou GIF para o usuário."""
        if self.uplink and path and os.path.exists(path):
            self.uplink.enviar_foto_ativa(path, legenda, target_chat_id=user_id)

    def _em_thread(self, func, user_id: int, *args):
        """
        Executa função pesada em thread daemon separada.
        Captura exceções e notifica o usuário automaticamente.
        """
        def run():
            try:
                func(user_id, *args)
            except Exception as exc:
                self.enviar(f"❌ Erro interno: {exc}", user_id)
        threading.Thread(target=run, daemon=True).start()

    # ══════════════════════════════════════════════════════════════════════════
    # SEÇÃO 2 — ROTEADOR DE COMANDOS
    # ══════════════════════════════════════════════════════════════════════════

    async def processar_item_queue(self, cmd_data: dict):
        """Processa um item da fila de comandos vindos do Telegram."""
        comando = cmd_data.get("comando", "").strip()
        user_id = cmd_data.get("sender_id")

        # Usuário em fluxo de conversa? Entrega o texto digitado.
        if user_id in self.user_states:
            await self._continuar_fluxo(comando, user_id)
            return

        await self._despachar(comando, user_id)

    async def _continuar_fluxo(self, texto: str, user_id: int):
        """Continua fluxo multi-etapa (ex: aguardando nome de cidade)."""
        state = self.user_states.pop(user_id, {})
        step  = state.get("step")

        if   step == "aguardar_cidade_clima":  self._em_thread(self._run_clima,    user_id, texto)
        elif step == "aguardar_cidade_voos":   self._em_thread(self._run_voos,     user_id, texto)
        elif step == "aguardar_prompt_ia":     self._em_thread(self._run_ia_local, user_id, texto)
        elif step == "aguardar_url_video":     self._em_thread(self._run_video,    user_id, texto)
        else:
            self.enviar("❓ Fluxo expirado. Use /start para o menu.", user_id)

    async def _despachar(self, comando: str, user_id: int):
        """Roteamento principal: comando → handler."""

        # ── Comandos que apenas definem estado (resposta imediata, sem thread) ──
        if comando == "pedir_cidade":
            self.user_states[user_id] = {"step": "aguardar_cidade_clima"}
            self.enviar("⛈️ Digite a cidade (ex: *Ivinhema MS* ou *São Paulo SP*):", user_id)
            return

        if comando == "pedir_voos":
            self.user_states[user_id] = {"step": "aguardar_cidade_voos"}
            self.enviar("✈️ Digite a cidade para o radar (ou *Ivinhema* para a base):", user_id)
            return

        if comando == "ia_local":
            self.user_states[user_id] = {"step": "aguardar_prompt_ia"}
            self.enviar("🤖 *IA LOCAL ATIVA* — Digite sua consulta:", user_id)
            return

        if comando == "video_viral":
            self.user_states[user_id] = {"step": "aguardar_url_video"}
            self.enviar("🎬 *TESOURA NEURAL* — Cole a URL do vídeo (YouTube/etc):", user_id)
            return

        # ── Mapa de comandos → funções pesadas (rodam em thread) ──
        mapa = {
            "solar":         self._run_solar,
            "asteroides":    self._run_asteroides,
            "defcon":        self._run_defcon,
            "terremotos":    self._run_terremotos,
            "vulcao":        self._run_vulcao,
            "intel ucrania": lambda u: self._run_intel(u, "ucrania"),
            "intel israel":  lambda u: self._run_intel(u, "israel"),
            "intel iran":    lambda u: self._run_intel(u, "iran"),
            "intel libano":  lambda u: self._run_intel(u, "libano"),
            "intel_news":    self._run_news,
            "status":        self._run_status,
            "market":        self._run_market,
            "iss":           self._run_iss,
            "rede":          self._run_rede,
            "velocidade":    self._run_velocidade,
            "noticias_br":   self._run_noticias_br,
            "radio":         self._run_radio,
            "sentinela":     self._run_sentinela,
            "quantum":       self._run_quantum,
        }

        handler = mapa.get(comando)
        if handler:
            self.enviar("⏳ Processando...", user_id)
            threading.Thread(target=handler, args=(user_id,), daemon=True).start()
        else:
            self.enviar(f"❓ Comando `{comando}` não mapeado. Use /start.", user_id)

    # ══════════════════════════════════════════════════════════════════════════
    # SEÇÃO 3 — HANDLERS DE MÓDULOS
    # ══════════════════════════════════════════════════════════════════════════

    # ── ☀️ SOLAR / NOAA ──────────────────────────────────────────────────────
    def _run_solar(self, user_id: int):
        try:
            from features.noaa_service import NOAAService
            noaa  = self._get("noaa", NOAAService)
            intel = noaa.get_full_intel()

            kp   = intel.get("kp_index",   {})
            xray = intel.get("goes_xray",  {})
            wind = intel.get("solar_wind", {})
            v_km = (wind.get("velocidade_km_s") or 0)
            bz   = wind.get("campo_Bz_nT", "N/A")

            texto = (
                f"☀️ *INTELIGÊNCIA SOLAR — NOAA/NASA*\n"
                f"🔰 Estado Geral: *{intel.get('estado_geral','N/A')}*\n\n"
                f"🌡️ *GOES X-Ray (Flares)*\n"
                f"   Classe: *{xray.get('classe_flare','N/A')}* | "
                f"Alerta: {'⚠️ SIM' if xray.get('alerta') else '✅ NÃO'}\n\n"
                f"🌍 *Kp Geomagnético*\n"
                f"   Kp: `{kp.get('kp_atual','N/A')}` — {kp.get('nivel','N/A')}\n\n"
                f"💨 *Vento Solar (ACE)*\n"
                f"   Velocidade: `{v_km:.0f} km/s` | Bz: `{bz} nT`\n\n"
                f"📋 Alertas SWPC Ativos: {len(intel.get('alertas',[]))}\n"
                f"⏱️ {intel.get('timestamp_coleta','')}"
            )
            self.enviar(texto, user_id)

            # Envia imagens SDO multiespectral
            sdo = intel.get("media", {}).get("sdo_imagens", {})
            for nome, (path, _) in (sdo or {}).items():
                if path:
                    self.enviar_foto(path, f"🛰️ SDO — {nome.replace('_',' ')}", user_id)
                    time.sleep(0.6)

        except Exception as e:
            self.enviar(f"❌ Erro Solar: {e}", user_id)

    # ── ☄️ ASTEROIDES ────────────────────────────────────────────────────────
    def _run_asteroides(self, user_id: int):
        try:
            from features.astro_defense     import AstroDefenseSystem
            from features.orbital_trajectory import OrbitalTrajectorySystem

            astro = self._get("astro", AstroDefenseSystem)
            texto, ast_id, ast_nome = astro.get_asteroid_report()
            self.enviar(texto, user_id)

            if ast_id and ast_nome:
                # Screenshot da órbita 3D (TheSkyLive)
                try:
                    orbital = OrbitalTrajectorySystem()
                    shot = orbital.get_trajectory_screenshot(ast_id, ast_nome)
                    if shot:
                        self.enviar_foto(shot, f"🌌 Órbita: {ast_nome}", user_id)
                except Exception as e:
                    print(f"⚠️ Screenshot órbita: {e}")

                # GIF timelapse (JPL NASA)
                try:
                    from features.astro_timelapse import AstroTimelapseSystem
                    gif = AstroTimelapseSystem().gerar_gif_trajetoria(ast_id, ast_nome)
                    if gif:
                        self.enviar_foto(gif, f"☄️ Timelapse: {ast_nome}", user_id)
                except Exception as e:
                    print(f"⚠️ Timelapse: {e}")

        except Exception as e:
            self.enviar(f"❌ Erro Asteroides: {e}", user_id)

    # ── ⛈️ CLIMA (requer cidade via estado) ──────────────────────────────────
    def _run_clima(self, user_id: int, cidade: str):
        try:
            from features.weather_system import WeatherSystem
            api_key = os.getenv("OPENWEATHER_API_KEY", "")
            if not api_key:
                self.enviar("⚠️ Chave `OPENWEATHER_API_KEY` não configurada no `.env`.", user_id)
                return
            resultado = WeatherSystem(api_key).obter_clima(cidade)
            self.enviar(resultado, user_id)
        except Exception as e:
            self.enviar(f"❌ Erro Clima: {e}", user_id)

    # ── ✈️ RADAR DE VOOS (requer cidade via estado) ──────────────────────────
    def _run_voos(self, user_id: int, cidade: str):
        try:
            from features.air_traffic import AirTrafficControl
            radar = AirTrafficControl()
            filename, qtd, msg = radar.radar_scan(cidade or "Ivinhema")
            self.enviar(msg, user_id)
            if filename:
                self.enviar_foto(filename, f"✈️ Radar — {cidade.upper()}", user_id)
        except Exception as e:
            self.enviar(f"❌ Erro Radar de Voos: {e}", user_id)

    # ── 🍕 DEFCON / GEOPOLÍTICA ──────────────────────────────────────────────
    def _run_defcon(self, user_id: int):
        try:
            from features.pizzint_service import PizzaINTService
            pizzint = self._get("pizzint", PizzaINTService)
            status  = pizzint.get_status()
            defcon  = status.get("defcon", {})
            noticias = status.get("news", [])

            texto = (
                f"{defcon.get('label','N/A')} — *{defcon.get('descricao','N/A')}*\n"
                f"📊 Score: `{status.get('score_normalizado',0)}/100` | "
                f"Tendência: {status.get('tendencia','?')}\n"
                f"🗂️ {status.get('categorias','Nenhuma ameaça detectada')}\n\n"
                f"📰 *Últimas Inteligências:*\n"
            )
            for n in noticias[:4]:
                titulo = n.get('titulo', '')[:90]
                url    = n.get('url', '')
                texto += f"\n• {titulo}\n  🔗 {url}\n" if url else f"\n• {titulo}\n"

            texto += f"\n⏱️ {status.get('timestamp','')}"
            self.enviar(texto, user_id)

        except Exception as e:
            self.enviar(f"❌ Erro DEFCON: {e}", user_id)

    # ── 🌍 TERREMOTOS ────────────────────────────────────────────────────────
    def _run_terremotos(self, user_id: int):
        try:
            from features.geo_seismic import GeoSeismicSystem
            self.enviar(self._get("geo", GeoSeismicSystem).get_seismic_data_text(), user_id)
        except Exception as e:
            self.enviar(f"❌ Erro Sísmico: {e}", user_id)

    # ── 🌋 VULCÕES ───────────────────────────────────────────────────────────
    def _run_vulcao(self, user_id: int):
        try:
            from features.volcano_monitor import VolcanoMonitor
            self.enviar(self._get("volcano", VolcanoMonitor).get_volcano_report(), user_id)
        except Exception as e:
            self.enviar(f"❌ Erro Vulcânico: {e}", user_id)

    # ── 🛰️ INTEL GUERRA ─────────────────────────────────────────────────────
    def _run_intel(self, user_id: int, setor: str):
        try:
            from features.intel_war import IntelWar
            intel = self._get("intel_war", IntelWar)
            headlines, screenshot = intel.get_war_report_with_screenshot(setor)

            if headlines:
                self.enviar(f"🛰️ *INTEL: {setor.upper()}*\n\n{headlines}", user_id)
            if screenshot:
                self.enviar_foto(screenshot, f"🗺️ Front — {setor.upper()}", user_id)
            elif not headlines:
                self.enviar(f"⚠️ Sem dados disponíveis para {setor.upper()}.", user_id)
        except Exception as e:
            self.enviar(f"❌ Erro Intel Guerra: {e}", user_id)

    # ── 🚨 BREAKING NEWS ────────────────────────────────────────────────────
    def _run_news(self, user_id: int):
        try:
            from features.geopolitics import GeopoliticsManager
            briefing = self._get("geopolitics", GeopoliticsManager).get_briefing(limit=5)

            texto = "🚨 *BREAKING NEWS — CONFLITOS GLOBAIS*\n\n"
            for item in briefing:
                icon = "🔴" if item["priority"] == "CRÍTICO" else (
                       "🟡" if item["priority"] == "ESTRATÉGICO" else "⚪")
                texto += f"{icon} {item['title'][:100]}\n"
            self.enviar(texto, user_id)
        except Exception as e:
            self.enviar(f"❌ Erro Breaking News: {e}", user_id)

    # ── 💻 STATUS DO SISTEMA ────────────────────────────────────────────────
    def _run_status(self, user_id: int):
        try:
            import platform
            from features.system_scanner import SystemScanner
            stats = SystemScanner().get_stats()

            host = ("Nuvem (Render)"
                    if "render" in platform.node() or os.getenv("RENDER")
                    else "Local (PC)")

            texto = (
                f"💻 *DIAGNÓSTICO DE SISTEMA — R2*\n"
                f"📍 Nó: `{host}`\n"
                f"🖥️ OS: `{stats['os']}`\n"
                f"🔲 CPU: `{stats['cpu']}%`\n"
                f"🧠 RAM: `{stats['ram']}%`\n"
                f"💾 Disco: `{stats['disk']}%`\n"
                f"🎯 Status: *{stats['status']}*"
            )
            self.enviar(texto, user_id)
        except Exception as e:
            self.enviar(f"❌ Erro Status: {e}", user_id)

    # ── 💱 COTAÇÕES DE MERCADO ───────────────────────────────────────────────
    def _run_market(self, user_id: int):
        try:
            from features.market_system import MarketSystem
            self.enviar(self._get("market", MarketSystem).obter_cotacoes(), user_id)
        except Exception as e:
            self.enviar(f"❌ Erro Mercado: {e}", user_id)

    # ── 🛰️ RASTREADOR ISS ───────────────────────────────────────────────────
    def _run_iss(self, user_id: int):
        try:
            from features.orbital_system import OrbitalSystem
            filename, texto = self._get("orbital", OrbitalSystem).rastrear_iss()
            self.enviar(texto, user_id)
            if filename:
                self.enviar_foto(filename, "🛰️ Posição atual da ISS", user_id)
        except Exception as e:
            self.enviar(f"❌ Erro ISS: {e}", user_id)

    # ── 📡 SCANNER DE REDE ──────────────────────────────────────────────────
    def _run_rede(self, user_id: int):
        try:
            from features.network_scanner import NetworkScanner
            self.enviar(NetworkScanner().scan(), user_id)
        except Exception as e:
            self.enviar(f"❌ Erro Scanner de Rede: {e}", user_id)

    # ── ⚡ VELOCIDADE DE REDE ────────────────────────────────────────────────
    def _run_velocidade(self, user_id: int):
        try:
            from features.net_speed import NetSpeedModule
            self.enviar(NetSpeedModule().run_test(), user_id)
        except Exception as e:
            self.enviar(f"❌ Erro Speedtest: {e}", user_id)

    # ── 📰 NOTÍCIAS BRASIL ──────────────────────────────────────────────────
    def _run_noticias_br(self, user_id: int):
        try:
            from features.news_briefing import NewsBriefing
            self.enviar(self._get("news_briefing", NewsBriefing).get_top_headlines(), user_id)
        except Exception as e:
            self.enviar(f"❌ Erro Notícias BR: {e}", user_id)

    # ── 📻 SCANNER DE RÁDIO ─────────────────────────────────────────────────
    def _run_radio(self, user_id: int):
        try:
            from features.radio_scanner import RadioScanner
            radio    = self._get("radio", RadioScanner)
            estacoes = radio.scan_active_transmissions(mode="global", limit=8)
            self.enviar(radio.format_report(estacoes), user_id)
        except Exception as e:
            self.enviar(f"❌ Erro Rádio: {e}", user_id)

    # ── 👁️ SENTINELA (CÂMERA) ───────────────────────────────────────────────
    def _run_sentinela(self, user_id: int):
        try:
            from features.sentinel_system import SentinelSystem
            path, msg = SentinelSystem().capturar_intruso()
            self.enviar(msg, user_id)
            if path:
                self.enviar_foto(path, "👁️ Sentinela — Captura ao vivo", user_id)
        except Exception as e:
            self.enviar(f"❌ Erro Sentinela: {e}", user_id)

    # ── 🤖 IA LOCAL (DOLPHIN) ───────────────────────────────────────────────
    def _run_ia_local(self, user_id: int, prompt: str):
        try:
            from features.local_brain import LocalLlamaBrain
            from features.eu import CORTEX_EU

            brain  = self._get("local_brain", LocalLlamaBrain)
            cortex = CORTEX_EU()
            self.enviar("🧠 *Dolphin processando...*", user_id)
            resposta = brain.think(prompt, system_prompt=cortex.injetar_consciencia())
            self.enviar(f"🤖 *R2 IA:*\n{resposta}", user_id)

        except FileNotFoundError:
            self.enviar("⚠️ Modelo GGUF não encontrado em `models/`.", user_id)
        except Exception as e:
            self.enviar(f"❌ Erro IA Local: {e}", user_id)

    # ── 🎬 PROCESSAR VÍDEO VIRAL ────────────────────────────────────────────
    def _run_video(self, user_id: int, url: str):
        try:
            from features.video_colab import VideoSurgeon
            surgeon = self._get("video_surgeon", VideoSurgeon)
            self.enviar("✂️ *Tesoura Neural V3* — Iniciando processamento...", user_id)

            config  = {"url": url, "color": "#ffffff", "size": 24,
                       "style": "outline", "active": True, "autoPos": True}
            caminho = surgeon.processar_alvo(
                config,
                callback=lambda msg: self.enviar(msg, user_id)
            )
            if caminho:
                self.enviar(f"✅ Vídeo processado!\nCaminho: `{caminho}`", user_id)
            else:
                self.enviar("❌ Falha no processamento do vídeo.", user_id)
        except Exception as e:
            self.enviar(f"❌ Erro Vídeo: {e}", user_id)

    # ── ⚛️ QUANTUM CORE (lança trade.bat) ───────────────────────────────────
    def _run_quantum(self, user_id: int):
        try:
            from features.quantum_module import QuantumCoreManager
            QuantumCoreManager().execute_trade_protocol(
                lambda msg: self.enviar(msg, user_id)
            )
        except Exception as e:
            self.enviar(f"❌ Erro Quantum: {e}", user_id)

    # ══════════════════════════════════════════════════════════════════════════
    # SEÇÃO 4 — UTILITÁRIOS
    # ══════════════════════════════════════════════════════════════════════════

    def _get(self, nome: str, cls, *args):
        """Lazy loading com cache — cria a instância uma vez, reutiliza depois."""
        if nome not in self._cache:
            self._cache[nome] = cls(*args)
        return self._cache[nome]

    def _limpar_temp(self):
        """Remove arquivos com mais de 1 hora na pasta temp/"""
        pasta_temp = os.path.join(BASE_DIR, "temp")
        if not os.path.exists(pasta_temp): return
        agora = time.time()
        for f in glob.glob(os.path.join(pasta_temp, "*")):
            if os.path.isfile(f) and (agora - os.path.getmtime(f)) > 3600:
                try: os.remove(f)
                except: pass

    # ══════════════════════════════════════════════════════════════════════════
    # SEÇÃO 5 — LOOP PRINCIPAL E INICIALIZAÇÃO
    # ══════════════════════════════════════════════════════════════════════════

    async def _loop_principal(self):
        """Consome a fila de comandos indefinidamente."""
        print("⚙️  [R2 CORE]: Loop principal ativo. Aguardando comandos...\n")
        while True:
            try:
                # Limpeza periódica (a cada 1 hora)
                if time.time() - self._last_cleanup > 3600:
                    self._limpar_temp()
                    self._last_cleanup = time.time()

                cmd_data = await asyncio.wait_for(
                    self.update_queue.get(), timeout=1.0
                )
                asyncio.create_task(self.processar_item_queue(cmd_data))
            except asyncio.TimeoutError:
                pass          # nada na fila, continua normalmente
            except Exception as e:
                print(f"❌ [LOOP ERRO]: {e}")

    def iniciar(self):
        """Ponto de entrada. Cria o loop, sobe o uplink, entra no loop principal."""

        # --- HACK PARA O RENDER: Servidor Web Fictício ---
        def start_dummy_server():
            class Handler(BaseHTTPRequestHandler):
                def do_GET(self):
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b"R2 Tactical OS - Uplink Online")
                
                # Silencia os logs do servidor HTTP para não poluir seu terminal
                def log_message(self, format, *args):
                    pass 

            # O Render injeta dinamicamente a porta na variável de ambiente PORT
            port = int(os.environ.get("PORT", 10000))
            server = HTTPServer(("0.0.0.0", port), Handler)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            print(f"✅ [WEB SERVER]: Servidor de Keep-Alive iniciado na porta {port}")

        # Inicia a porta falsa para o Render aprovar o deploy
        start_dummy_server()
        # -------------------------------------------------

        print("=" * 55)
        print("🚀 R2 TACTICAL OS — INICIANDO SISTEMAS")
        print("=" * 55)

        # Cria e registra o event loop no thread principal
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.main_loop    = loop
        self.update_queue = asyncio.Queue()

        # Levanta o bot Telegram em thread daemon
        self.uplink = TelegramBotUplink(server_ref=self)
        self.uplink.iniciar_sistema()

        print("✅ [TELEGRAM]: Uplink ativo.")
        print("✅ [R2 CORE]:  Sistema online. Use /start no Telegram.\n")

        try:
            loop.run_until_complete(self._loop_principal())
        except KeyboardInterrupt:
            print("\n⛔ [R2 TACTICAL OS]: Desligamento solicitado pelo Operador.")
        finally:
            loop.close()
            print("🔴 [R2 TACTICAL OS]: Sistema encerrado.")


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    R2Core().iniciar()
