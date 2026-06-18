import os
import math
import asyncio
import pandas as pd
import folium
from datetime import datetime

# Caminho para salvar o mapa na estrutura do seu Flask
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAP_OUTPUT_PATH = os.path.join(BASE_DIR, "static", "mapa_fusion.html")

class GeoFusionEngine:
    def __init__(self):
        pass

    def _calcular_distancia_km(self, lat1, lon1, lat2, lon2):
        """Cálculo de Haversine para distância entre dois pontos globais."""
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def _processar_fusao_sincrona(self, dados_ambientais: list, dados_geopoliticos: list, raio_critico_km: float = 500.0):
        """
        Executa a lógica pesada de correlação espacial e geração do mapa Folium.
        Executado dentro de um thread pool para não travar o loop principal.
        """
        if not dados_ambientais and not dados_geopoliticos:
            return "⚠️ Sem dados suficientes para realizar a fusão geoespacial.", None

        # Criar DataFrames para manipulação tática
        df_amb = pd.DataFrame(dados_ambientais if dados_ambientais else [
            {"tipo": "Sismo Simulado", "lat": -22.9, "lon": -43.2, "detalhe": "Magnitude 4.5", "timestamp": datetime.now()}
        ])
        df_geo = pd.DataFrame(dados_geopoliticos if dados_geopoliticos else [
            {"tipo": "Alvo/Conflito Simulado", "lat": -22.5, "lon": -43.1, "detalhe": "Movimentação de Fronteira", "timestamp": datetime.now()}
        ])

        alertas_detectados = []
        
        # Centraliza o mapa na média dos pontos disponíveis
        center_lat = pd.concat([df_amb['lat'], df_geo['lat']]).mean()
        center_lon = pd.concat([df_amb['lon'], df_geo['lon']]).mean()
        
        # Inicializa o mapa tático com tema escuro (Dark Matter) para a estética do R2
        mapa = folium.Map(
            location=[center_lat, center_lon], 
            zoom_start=4, 
            tiles="CartoDB dark_matter",
            attr="R2 Tactical OS"
        )

        # Plotar Eventos Ambientais (Ícones Azuis/Roxos)
        for _, row in df_amb.iterrows():
            folium.Marker(
                location=[row['lat'], row['lon']],
                popup=f"<b>🌍 {row['tipo']}</b><br>{row['detalhe']}",
                icon=folium.Icon(color='blue', icon='info-sign')
            ).add_to(mapa)

        # Plotar Eventos Geopolíticos / Alvos (Ícones Vermelhos)
        for _, row_geo in df_geo.iterrows():
            folium.Marker(
                location=[row_geo['lat'], row_geo['lon']],
                popup=f"<b>⚔️ {row_geo['tipo']}</b><br>{row_geo['detalhe']}",
                icon=folium.Icon(color='red', icon='exclamation-sign')
            ).add_to(mapa)

        # Cruzamento e Análise Preditiva de Proximidade (Fusão)
        for _, amb in df_amb.iterrows():
            for _, geo in df_geo.iterrows():
                dist = self._calcular_distancia_km(amb['lat'], amb['lon'], geo['lat'], geo['lon'])
                
                if dist <= raio_critico_km:
                    alertas_detectados.append({
                        "ambiental": amb['tipo'],
                        "geopolitico": geo['tipo'],
                        "distancia": round(dist, 2),
                        "lat": (amb['lat'] + geo['lat']) / 2,
                        "lon": (amb['lon'] + geo['lon']) / 2
                    })

        # Desenhar Zonas de Impacto / Hotspots no Mapa
        for alerta in alertas_detectados:
            folium.Circle(
                location=[alerta['lat'], alerta['lon']],
                radius=alerta['distancia'] * 1000, # Convertido para metros
                color='#ff3300',
                fill=True,
                fill_color='#ff3300',
                fill_opacity=0.15,
                popup=f"🚨 <b>ZONA DE IMPACTO CRÍTICO</b><br>Intersecção: {alerta['ambiental']} + {alerta['geopolitico']}<br>Distância: {alerta['distancia']} km"
            ).add_to(mapa)

        # Garante que a pasta static existe e salva o mapa
        os.makedirs(os.path.dirname(MAP_OUTPUT_PATH), exist_ok=True)
        mapa.save(MAP_OUTPUT_PATH)

        # Formatar relatório em texto para o operador no Telegram
        relatorio = f"🌐 **R2 GEO-FUSION REPORT** 🌐\n"
        relatorio += f"⏱️ _Análise executada em:_ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
        relatorio += f"📊 Pontos Analisados: Ambientais ({len(df_amb)}) | Geopolíticos ({len(df_geo)})\n"
        relatorio += f"───────────────────────\n"

        if alertas_detectados:
            relatorio += f"🚨 **{len(alertas_detectados)} CORRELAÇÕES CRÍTICAS DETECTADAS:**\n\n"
            for idx, alt in enumerate(alertas_detectados, 1):
                relatorio += f"{idx}. **ZONA CRÍTICA ({alt['distancia']} km)**\n"
                relatorio += f"   🔹 Fenômeno: {alt['ambiental']}\n"
                relatorio += f"   🎯 Alvo/Conflito: {alt['geopolitico']}\n"
                relatorio += f"   ⚠️ _Risco:_ Instabilidade operacional detectada na área.\n\n"
        else:
            relatorio += "✅ Nenhuma correlação crítica de proximidade detectada nas zonas de monitoramento atuais.\n\n"

        relatorio += "🗺️ **Mapa tático interativo gerado com sucesso em seu painel.**"
        return relatorio, MAP_OUTPUT_PATH

    async def executar_fusao(self, dados_ambientais: list, dados_geopoliticos: list, raio_km: float = 500.0):
        """Ponto de entrada assíncrono para o Uplink usar."""
        # Delega o processamento pesado para uma thread do sistema, liberando o loop do Telegram
        return await asyncio.to_thread(self._processar_fusao_sincrona, dados_ambientais, dados_geopoliticos, raio_km)