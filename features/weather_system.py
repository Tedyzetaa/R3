import requests

class WeatherSystem:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "http://api.openweathermap.org/data/2.5/weather"
        
        # Mapeamento de siglas
        self.estados = {
            "ac": "Acre", "al": "Alagoas", "ap": "Amapá", "am": "Amazonas",
            "ba": "Bahia", "ce": "Ceará", "df": "Distrito Federal", "es": "Espírito Santo",
            "go": "Goiás", "ma": "Maranhão", "mt": "Mato Grosso", "ms": "Mato Grosso do Sul",
            "mg": "Minas Gerais", "pa": "Pará", "pb": "Paraíba", "pr": "Paraná",
            "pe": "Pernambuco", "pi": "Piauí", "rj": "Rio de Janeiro", "rn": "Rio Grande do Norte",
            "rs": "Rio Grande do Sul", "ro": "Rondônia", "rr": "Roraima", "sc": "Santa Catarina",
            "sp": "São Paulo", "se": "Sergipe", "to": "Tocantins"
        }

    def _gerar_tentativas(self, entrada_usuario):
        """Gera lista de formatos para tentar achar a cidade"""
        partes = entrada_usuario.lower().split()
        tentativas = []

        # 1. Se tiver sigla de estado (Ex: "ivinhema ms")
        if len(partes) > 1 and partes[-1] in self.estados:
            sigla = partes[-1]
            nome_estado = self.estados[sigla]
            nome_cidade = " ".join(partes[:-1])
            
            # Prioridade: Nome completo do estado
            tentativas.append(f"{nome_cidade},{nome_estado},BR")
            # Fallback: Sigla
            tentativas.append(f"{nome_cidade},{sigla},BR")
        
        # 2. Formato Cidade + BR (Ex: "ivinhema, br")
        tentativas.append(f"{entrada_usuario},BR")
        
        # 3. Formato Cru (Ex: "ivinhema") - Última esperança
        tentativas.append(entrada_usuario)
        
        return tentativas

    def obter_clima(self, cidade_input):
        lista_tentativas = self._gerar_tentativas(cidade_input)
        
        for i, query in enumerate(lista_tentativas):
            params = {
                "q": query,
                "appid": self.api_key,
                "units": "metric",
                "lang": "pt_br"
            }

            try:
                print(f"📡 [DEBUG]: Tentativa {i+1} de varredura: '{query}'...")
                response = requests.get(self.base_url, params=params)
                dados = response.json()

                if response.status_code == 200:
                    # SUCESSO! Captura os dados
                    temp = dados['main']['temp']
                    sensacao = dados['main']['feels_like']
                    desc = dados['weather'][0]['description'].capitalize()
                    umidade = dados['main']['humidity']
                    vento = dados['wind']['speed'] * 3.6
                    cidade_real = dados['name']
                    pais = dados['sys']['country']

                    return (
                        f"🌦️ TELEMETRIA ATMOSFÉRICA: {cidade_real.upper()} ({pais})\n"
                        f"🌡️ Temperatura: {temp:.1f}°C (Sensação: {sensacao:.1f}°C)\n"
                        f"☁️ Condição: {desc}\n"
                        f"💧 Umidade: {umidade}%\n"
                        f"💨 Vento: {vento:.1f} km/h"
                    )
            except Exception:
                continue # Se der erro de conexão, tenta a próxima query

        # Se saiu do loop e não achou nada:
        return f"⚠️ Alvo '{cidade_input}' não localizado em nenhuma frequência. Tente digitar 'Ivinhema MS'."