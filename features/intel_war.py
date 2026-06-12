import os
import requests
import random
import time
import re
import feedparser
import cloudscraper
from playwright.sync_api import sync_playwright

class IntelWar:
    def __init__(self):
        # 🛰️ DICIONÁRIO DE INTELIGÊNCIA (ALVOS ESTRATÉGICOS)
        self.urls = {
            "global": "https://liveuamap.com/",
            "ucrania": "https://ukraine.liveuamap.com/",
            "israel": "https://israelpalestine.liveuamap.com/",
            "iran": "https://iran.liveuamap.com/",
            "libano": "https://lebanon.liveuamap.com/",
            "defcon": "https://www.defconlevel.com/",
            "pizzint": "https://www.pizzint.watch/"
        }

        # Fallback RSS (Google News) — mesmo padrão do liveuamap_intel.py
        self.feeds_backup = {
            "global":  "https://news.google.com/rss/search?q=guerra+conflito+internacional&hl=pt-BR&gl=BR&ceid=BR:pt-419",
            "ucrania": "https://news.google.com/rss/search?q=Guerra+Ucrânia+front&hl=pt-BR&gl=BR&ceid=BR:pt-419",
            "israel":  "https://news.google.com/rss/search?q=Guerra+Israel+Gaza&hl=pt-BR&gl=BR&ceid=BR:pt-419",
            "iran":    "https://news.google.com/rss/search?q=Irã+tensão+conflito&hl=pt-BR&gl=BR&ceid=BR:pt-419",
            "libano":  "https://news.google.com/rss/search?q=Líbano+Hezbollah+Israel&hl=pt-BR&gl=BR&ceid=BR:pt-419",
        }

        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
        ]

    def _obter_chave_segura(self, texto_usuario):
        """Mapeia o comando do usuário para uma chave do dicionário"""
        if not texto_usuario: return "global"

        texto = texto_usuario.lower().strip()
        mapa = {
            "ucrânia": "ucrania", "ucrania": "ucrania", "ukraine": "ucrania",
            "israel": "israel", "gaza": "israel", "palestina": "israel",
            "irã": "iran", "ira": "iran", "iran": "iran",
            "líbano": "libano", "libano": "libano", "lebanon": "libano", "hezbollah": "libano",
            "defcon": "defcon", "pizzint": "pizzint", "global": "global", "mundo": "global"
        }
        return mapa.get(texto, "global")

    def _sanitizar_md(self, texto: str) -> str:
        """Remove caracteres que quebram o parser Markdown legado do Telegram."""
        return re.sub(r'[*_`\[\]]', '', texto)

    def _entries_para_blocos(self, entries, limite=5):
        blocos = []
        for entry in entries[:limite]:
            titulo = self._sanitizar_md(
                entry.title.replace("&quot;", '"').replace("&#39;", "'")
                            .replace("<b>", "").replace("</b>", "")
                            .strip()
            )
            link = getattr(entry, "link", "").strip()
            if not titulo:
                continue
            if link:
                blocos.append(f"• {titulo}\n  🔗 {link}")
            else:
                blocos.append(f"• {titulo}")
        return blocos

    def _obter_headlines_rss(self, chave: str, url_base: str, limite: int = 5) -> str:
        """
        Busca manchetes + links via RSS do liveuamap.
        Se falhar/vazio, cai pro Google News RSS daquela região.
        """
        rss_url = url_base.rstrip("/") + "/rss"

        # ── Tentativa 1: cloudscraper no RSS do liveuamap ──
        try:
            scraper = cloudscraper.create_scraper()
            response = scraper.get(rss_url, timeout=12)
            print(f"🔎 [INTEL-RSS] {rss_url} → status {response.status_code}, "
                  f"tamanho {len(response.content)} bytes")
            if response.status_code == 200 and response.content:
                feed = feedparser.parse(response.content)
                print(f"🔎 [INTEL-RSS] entries encontradas: {len(feed.entries)}")
                if feed.entries:
                    blocos = self._entries_para_blocos(feed.entries, limite)
                    if blocos:
                        return "\n".join(blocos)
        except Exception as e:
            print(f"⚠️ [INTEL-RSS] cloudscraper falhou: {e}")

        # ── Tentativa 2: requests puro no RSS do liveuamap ──
        try:
            response = requests.get(
                rss_url,
                headers={"User-Agent": random.choice(self.user_agents)},
                timeout=12
            )
            print(f"🔎 [INTEL-RSS] (fallback requests) {rss_url} → status {response.status_code}")
            if response.status_code == 200 and response.content:
                feed = feedparser.parse(response.content)
                if feed.entries:
                    blocos = self._entries_para_blocos(feed.entries, limite)
                    if blocos:
                        return "\n".join(blocos)
        except Exception as e:
            print(f"⚠️ [INTEL-RSS] requests falhou: {e}")

        # ── Tentativa 3: Google News RSS (fallback final) ──
        backup_url = self.feeds_backup.get(chave, self.feeds_backup["global"])
        try:
            response = requests.get(backup_url, timeout=12)
            print(f"🔎 [INTEL-RSS] (GOOGLE) {backup_url} → status {response.status_code}")
            if response.status_code == 200 and response.content:
                feed = feedparser.parse(response.content)
                if feed.entries:
                    blocos = self._entries_para_blocos(feed.entries, limite)
                    if blocos:
                        return "📰 [GOOGLE INTEL]\n" + "\n".join(blocos)
        except Exception as e:
            print(f"⚠️ [INTEL-RSS] Google News falhou: {e}")

        return ""

    def get_war_report_with_screenshot(self, setor_input="global"):
        """Captura visual dos fronts de batalha + manchetes com links via RSS"""
        chave = self._obter_chave_segura(setor_input)
        url = self.urls.get(chave, self.urls["global"])

        pasta_raiz = os.path.dirname(os.path.abspath(__file__))      # C:\IA\features
        pasta_base = os.path.dirname(pasta_raiz)                      # C:\IA
        pasta_temp = os.path.join(pasta_base, "temp")
        os.makedirs(pasta_temp, exist_ok=True)

        screenshot_path = os.path.join(pasta_temp, f"intel_{chave}.png")

        headlines = ""
        if "liveuamap" in url:
            headlines = self._obter_headlines_rss(chave, url, limite=5)

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={"width": 1280, "height": 720},
                    user_agent=random.choice(self.user_agents)
                )
                page = context.new_page()

                print(f"🛰️ [INTEL]: Infiltrando no setor {chave.upper()}...")
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                time.sleep(6)

                try: page.locator("button:has-text('Accept'), .popup-close").click(timeout=2000)
                except: pass

                page.screenshot(path=screenshot_path)
                browser.close()
                return headlines, screenshot_path
        except Exception as e:
            print(f"❌ Erro na extração visual: {e}")
            return headlines or f"⚠️ Falha técnica: {str(e)}", None

    def get_pizzint_text_only(self):
        """Extração de dados brutos (Sem Print) para PIZZINT"""
        headers = {'User-Agent': random.choice(self.user_agents)}
        try:
            response = requests.get(self.urls["pizzint"], headers=headers, timeout=10)
            html = response.text

            defcon_match = re.search(r'DEFCON\s+(\d+)', html)
            status = f"DEFCON {defcon_match.group(1)}" if defcon_match else "Status Oculto"

            orders_match = re.search(r'(\d+)\s+Orders', html)
            pedidos = orders_match.group(1) if orders_match else "0"

            return f"🚨 *PIZZINT WATCH MONITOR*\n🔹 {status}\n🔹 Atividade: {pedidos} ordens ativas."
        except:
            return "⚠️ PIZZINT: Erro de interceptação de dados."