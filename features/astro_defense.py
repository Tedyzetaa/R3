import os
import requests
import datetime

class AstroDefenseSystem:
    def __init__(self):
        self.api_key = os.environ.get("NASA_API_KEY", "DEMO_KEY") 
        self.base_url = "https://api.nasa.gov/neo/rest/v1/feed"

    def get_asteroid_report(self):
        """Retorna: (Relatório Texto, ID do Alvo, Nome do Alvo)"""
        try:
            hoje = datetime.date.today().strftime("%Y-%m-%d")
            url = f"{self.base_url}?start_date={hoje}&end_date={hoje}&api_key={self.api_key}"
            
            print("☄️ [ASTRO]: Consultando API NEO (Buscando SPK-IDs)...")
            resp = requests.get(url, timeout=15)
            data = resp.json()
            
            element_count = data['element_count']
            asteroides = data['near_earth_objects'][hoje]
            
            texto = f"☄️ *DEFESA PLANETÁRIA (NASA)*\n📅 Data: {hoje}\n🛡️ Objetos: {element_count}\n"
            
            # Ordena por tamanho
            asteroides.sort(key=lambda x: x['estimated_diameter']['meters']['estimated_diameter_max'], reverse=True)
            top_3 = asteroides[:3]

            principal_id = None
            principal_nome = None

            for i, ast in enumerate(top_3):
                nome = ast['name']
                spk_id = ast['id'] # <--- O SEGREDO: O ID NUMÉRICO ÚNICO
                
                # Guarda o ID do maior asteroide para o mapa
                if i == 0: 
                    principal_id = spk_id
                    principal_nome = nome

                tamanho = ast['estimated_diameter']['meters']['estimated_diameter_max']
                perigoso = ast['is_potentially_hazardous_asteroid']
                
                # Dados de velocidade/distância
                try:
                    prox = ast['close_approach_data'][0]
                    vel = float(prox['relative_velocity']['kilometers_per_hour'])
                    dist = float(prox['miss_distance']['kilometers'])
                except Exception as e:
                    vel, dist = 0, 0
                
                icone = "⚠️" if perigoso else "🪨"
                texto += f"\n{icone} **{nome}** (ID: {spk_id})\n   📏 ~{tamanho:.0f}m | 🚀 {int(vel):,} km/h\n   📡 Dist: {int(dist):,} km\n"
            
            texto += "\n_Dados: NASA/JPL Small-Body Database_"
            
            # RETORNA A TRINCA DE DADOS
            return texto, principal_id, principal_nome

        except Exception as e:
            print(f"❌ Erro Astro: {e}")
            return f"⚠️ Falha: {e}", None, None