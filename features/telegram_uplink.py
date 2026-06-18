import os
import asyncio
import threading
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from features.geo_fusion import GeoFusionEngine

# --- 1. CARREGAMENTO DE CREDENCIAIS (.ENV) ---
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir    = os.path.dirname(current_dir)
env_path    = os.path.join(root_dir, ".env")

load_dotenv(env_path)
TOKEN = os.getenv("TELEGRAM_TOKEN")

# --- 2. PROTOCOLO DE SEGURANÇA ---
AUTHORIZED_USERS = {8117345546, 8379481331, 8468494394, 8576907275}


class TelegramBotUplink:
    def __init__(self, server_ref):
        self.server_ref = server_ref   # Referência ao R2Core (main.py)
        self.app        = None
        self.loop       = asyncio.new_event_loop()
        self.thread     = None
        self.geo_fusion = GeoFusionEngine()

        if not TOKEN:
            print(f"❌ [ERRO CRÍTICO]: Token não encontrado em {env_path}")
            raise ValueError("Token ausente. Configure TELEGRAM_TOKEN no .env")

    # ══════════════════════════════════════════════════════════════════════════
    # INICIALIZAÇÃO
    # ══════════════════════════════════════════════════════════════════════════

    def iniciar_sistema(self):
        if self.thread and self.thread.is_alive():
            return

        def run_bot():
            asyncio.set_event_loop(self.loop)

            self.app = (
                Application.builder()
                .token(TOKEN)
                .connect_timeout(30)
                .read_timeout(30)
                .write_timeout(30)
                .pool_timeout(30)
                .build()
            )

            self.app.add_handler(CommandHandler("start", self.start_command))
            self.app.add_handler(CommandHandler("geofusion", self.cmd_geofusion))
            self.app.add_handler(CallbackQueryHandler(self.lidar_com_botoes))
            self.app.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND, self.lidar_com_mensagem)
            )
            self.app.add_error_handler(self.error_handler)

            print("📡 [TELEGRAM]: Uplink ativo.")
            self.loop.run_until_complete(
                self.app.run_polling(
                    drop_pending_updates=True,
                    close_loop=False,
                    stop_signals=()
                )
            )

        self.thread = threading.Thread(target=run_bot, daemon=True)
        self.thread.start()

    # ══════════════════════════════════════════════════════════════════════════
    # GERENCIADOR DE ERROS DE REDE
    # ══════════════════════════════════════════════════════════════════════════

    async def error_handler(self, update, context):
        print(f"⚠️ [TELEGRAM ERROR]: {context.error}")

    # ══════════════════════════════════════════════════════════════════════════
    # MENU PRINCIPAL (/start)
    # ══════════════════════════════════════════════════════════════════════════

    async def start_command(self, update: Update, context):
        uid = update.effective_user.id
        if uid not in AUTHORIZED_USERS:
            await update.message.reply_text("⛔ ACESSO NEGADO.")
            return

        keyboard = [
            # ── ESPAÇO ──────────────────────────────────────────────────────
            [InlineKeyboardButton("☀️ RELATÓRIO SOLAR COMPLETO (NOAA)", callback_data="solar")],
            [
                InlineKeyboardButton("☄️ ASTEROIDES (NASA)", callback_data="asteroides"),
                InlineKeyboardButton("🛰️ RASTREAR ISS",      callback_data="iss"),
            ],
            # ── SUPERFÍCIE ──────────────────────────────────────────────────
            [
                InlineKeyboardButton("✈️ RADAR DE VOOS",    callback_data="pedir_voos"),
                InlineKeyboardButton("⛈️ CLIMA (CIDADE)",   callback_data="pedir_cidade"),
            ],
            # ── NOVO: PREVISÃO EM VÍDEO ────────────────────────────────────
            [
                InlineKeyboardButton("🎬 PREVISÃO 48h (VÍDEO)", callback_data="pedir_clima_video")
            ],
            # ── GEOPOLÍTICA ─────────────────────────────────────────────────
            [InlineKeyboardButton("☢️  DEFCON / GEOPOLÍTICA (PizzINT)", callback_data="defcon")],
            [
                InlineKeyboardButton("🌍 TERREMOTOS (USGS)", callback_data="terremotos"),
                InlineKeyboardButton("🌋 VULCÕES (Smithsonian)", callback_data="vulcao"),
            ],
            # ── INTEL GUERRA ────────────────────────────────────────────────
            [
                InlineKeyboardButton("🇺🇦 INTEL UCRÂNIA", callback_data="intel ucrania"),
                InlineKeyboardButton("🇮🇱 INTEL ISRAEL",  callback_data="intel israel"),
            ],
            [
                InlineKeyboardButton("🇮🇷 INTEL IRÃ",     callback_data="intel iran"),
                InlineKeyboardButton("🇱🇧 INTEL LÍBANO",  callback_data="intel libano"),
            ],
            # ── NOTÍCIAS ────────────────────────────────────────────────────
            [
                InlineKeyboardButton("🚨 BREAKING NEWS (Conflitos)", callback_data="intel_news"),
                InlineKeyboardButton("📰 NOTÍCIAS BRASIL (G1)",      callback_data="noticias_br"),
            ],
            # ── MERCADO ─────────────────────────────────────────────────────
            [InlineKeyboardButton("💱 COTAÇÕES USD / EUR / BTC", callback_data="market")],
            # ── REDE ────────────────────────────────────────────────────────
            [
                InlineKeyboardButton("📡 SCANNER DE REDE (ARP)", callback_data="rede"),
                InlineKeyboardButton("⚡ VELOCIDADE DE NET",      callback_data="velocidade"),
            ],
            # ── SISTEMAS ────────────────────────────────────────────────────
            [
                InlineKeyboardButton("📻 SCANNER DE RÁDIO",    callback_data="radio"),
                InlineKeyboardButton("👁️  SENTINELA (CÂMERA)", callback_data="sentinela"),
            ],
            # ── IA ──────────────────────────────────────────────────────────
            [InlineKeyboardButton("🤖 IA LOCAL (Dolphin Uncensored)", callback_data="ia_local")],
            # ── STATUS ──────────────────────────────────────────────────────
            [InlineKeyboardButton("💻 STATUS DO SISTEMA (PC)", callback_data="status")],
            # ── CONSULTAS BR ────────────────────────────────────────────────
            [
                InlineKeyboardButton("📮 CONSULTAR CEP",  callback_data="pedir_cep"),
                InlineKeyboardButton("🏢 CONSULTAR CNPJ", callback_data="pedir_cnpj"),
            ],
            [
                InlineKeyboardButton("🪪 CONSULTAR CPF",  callback_data="pedir_cpf"),
                InlineKeyboardButton("💳 CONSULTAR BIN",  callback_data="pedir_bin"),
            ],
        ]

        await update.message.reply_text(
            "🤖 *R2 TACTICAL OS — CONSOLE DE COMANDO*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Selecione uma operação tática:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    async def cmd_geofusion(self, update: Update, context):
        user_id = update.effective_user.id
        if user_id not in AUTHORIZED_USERS:
            await update.message.reply_text("⛔ Acesso negado. Protocolo de segurança ativo.")
            return

        mensagem_espera = await update.message.reply_text("🧬 `R2 executando algoritmos de fusão geoespacial...`", parse_mode="Markdown")

        # MOCK DE DADOS: Em produção, você puxará esses dados das suas outras features
        # ex: extrair os últimos dicionários de features/geo_seismic ou features/liveuamap_intel
        dados_ambientais_ficticios = [
            {"tipo": "Terremoto M5.1", "lat": 36.3, "lon": 68.1, "detalhe": "Profundidade 10km - Afeganistão"},
            {"tipo": "Atividade Vulcânica", "lat": 35.3, "lon": 138.7, "detalhe": "Monte Fuji - Alerta Amarelo"}
        ]
        
        dados_geopoliticos_ficticios = [
            {"tipo": "Movimentação Militar", "lat": 36.7, "lon": 68.8, "detalhe": "Aumento de tropas na fronteira norte"},
            {"tipo": "Bloqueio de Infraestrutura", "lat": 35.0, "lon": 139.0, "detalhe": "Exercício naval conjunto na costa"}
        ]

        # Executa a fusão sem travar o bot
        relatorio, mapa_path = await self.geo_fusion.executar_fusao(
            dados_ambientais_ficticios, 
            dados_geopoliticos_ficticios, 
            raio_km=200.0
        )

        # Atualiza a mensagem do operador com o relatório analítico
        await mensagem_espera.edit_text(relatorio, parse_mode="Markdown")
        
        # Se você configurou o link público no Render, pode enviar o link direto para o operador abrir o mapa no celular!
        # Exemplo: URL_REDE = os.getenv("RENDER_EXTERNAL_URL", "http://127.0.0.1:5000")
        # await update.message.reply_text(f"🔗 Acesse o mapa tático online:\n{URL_REDE}/static/mapa_fusion.html")

    # ══════════════════════════════════════════════════════════════════════════
    # PROCESSADOR DE BOTÕES
    # ══════════════════════════════════════════════════════════════════════════

    async def lidar_com_botoes(self, update: Update, context):
        query   = update.callback_query
        user_id = query.from_user.id
        comando = query.data

        try:
            await query.answer()
        except Exception:
            pass

        if user_id not in AUTHORIZED_USERS:
            try:
                await query.edit_message_text("⛔ Não autorizado.")
            except Exception:
                pass
            return

        print(f"🔘 [{user_id}] Botão: {comando}")
        self._despachar_para_core({"comando": comando, "sender_id": user_id})

    # ══════════════════════════════════════════════════════════════════════════
    # PROCESSADOR DE MENSAGENS DE TEXTO
    # ══════════════════════════════════════════════════════════════════════════

    async def lidar_com_mensagem(self, update: Update, context):
        user_id = update.effective_user.id
        if user_id not in AUTHORIZED_USERS:
            return

        texto = update.message.text
        print(f"📩 [{user_id}] Texto: {texto}")
        self._despachar_para_core({"comando": texto, "sender_id": user_id})

    # ══════════════════════════════════════════════════════════════════════════
    # PONTE THREAD-SAFE → MAIN LOOP (R2Core)
    # ══════════════════════════════════════════════════════════════════════════

    def _despachar_para_core(self, payload: dict):
        """Envia o payload para a fila do R2Core de forma thread-safe."""
        if hasattr(self.server_ref, "main_loop") and self.server_ref.main_loop:
            self.server_ref.main_loop.call_soon_threadsafe(
                self.server_ref.update_queue.put_nowait,
                payload,
            )

    # ══════════════════════════════════════════════════════════════════════════
    # ENVIOS ATIVOS (R2Core → Telegram)
    # ══════════════════════════════════════════════════════════════════════════

    def enviar_mensagem_ativa(self, texto: str, target_chat_id: int):
        if not self.app:
            return

        async def send():
            try:
                await self.app.bot.send_message(
                    chat_id=target_chat_id,
                    text=texto,
                    parse_mode="Markdown",
                )
            except Exception as e:
                print(f"⚠️ [TELEGRAM] Falha no Markdown ({e}) — reenviando como texto puro.")
                try:
                    await self.app.bot.send_message(
                        chat_id=target_chat_id,
                        text=texto,
                        parse_mode=None,
                    )
                except Exception as e2:
                    print(f"❌ Erro envio msg (fallback): {e2}")

        asyncio.run_coroutine_threadsafe(send(), self.loop)

    def enviar_foto_ativa(self, file_path: str, legenda: str = "", target_chat_id: int = None):
        if not self.app:
            return

        async def send():
            for tentativa in range(3):
                try:
                    if not os.path.exists(file_path):
                        print(f"⚠️ Arquivo não encontrado: {file_path}")
                        break
                    with open(file_path, "rb") as f:
                        if file_path.lower().endswith(".gif"):
                            await self.app.bot.send_animation(
                                chat_id=target_chat_id, animation=f, caption=legenda
                            )
                        elif file_path.lower().endswith(".mp4"):
                            await self.app.bot.send_video(
                                chat_id=target_chat_id, video=f, caption=legenda
                            )
                        else:
                            await self.app.bot.send_photo(
                                chat_id=target_chat_id, photo=f, caption=legenda
                            )
                    break
                except PermissionError:
                    import asyncio as _a
                    await _a.sleep(1)
                except Exception as e:
                    print(f"❌ Erro envio mídia (tentativa {tentativa+1}): {e}")
                    break

        asyncio.run_coroutine_threadsafe(send(), self.loop)