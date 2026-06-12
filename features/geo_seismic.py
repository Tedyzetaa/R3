import requests
import datetime

class GeoSeismicSystem:
    def __init__(self):
        # Fonte de Dados: USGS (United States Geological Survey)
        # Feed: Terremotos acima de M2.5 nas últimas 24h
        self.url_api = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson"

    def get_seismic_data_text(self):
        """Busca dados sísmicos em tempo real e formata relatório de texto"""
        try:
            print("🌋 [GEO]: Consultando sensores USGS...")
            resp = requests.get(self.url_api, timeout=10)
            data = resp.json()
            
            # Pegamos os 5 eventos mais recentes
            quakes = data['features'][:5]
            
            # Cabeçalho do Relatório
            texto = "🌋 *MONITOR SÍSMICO GLOBAL*\n_Últimos eventos significativos (M2.5+)_:\n"
            
            for q in quakes:
                mag = q['properties']['mag']
                local = q['properties']['place']
                ts = int(q['properties']['time']) / 1000
                
                # Data e Hora Legível
                data_hora = datetime.datetime.fromtimestamp(ts).strftime('%d/%m %H:%M')
                
                # Sistema de Cores por Intensidade
                icone = "🟢" # Leve
                if mag >= 4.5: icone = "🟡" # Moderado
                if mag >= 5.5: icone = "🟠" # Forte
                if mag >= 6.5: icone = "🔴" # Severo/Crítico
                
                texto += f"\n{icone} **M{mag:.1f}** — {local}\n   🕒 {data_hora} (Ref)\n"
            
            texto += "\n_Fonte: USGS Real-time Network_"
            return texto
            
        except Exception as e:
            print(f"⚠️ Erro API Texto: {e}")
            return f"⚠️ Falha na conexão com sensores geológicos: {e}"