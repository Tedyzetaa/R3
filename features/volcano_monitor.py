import requests
import xml.etree.ElementTree as ET

class VolcanoMonitor:
    def __init__(self):
        # Feed Oficial do Smithsonian / USGS Weekly Volcanic Activity Report
        self.rss_url = "https://volcano.si.edu/news/WeeklyVolcanoRSS.xml"

    def get_volcano_report(self):
        """Extrai o relatório semanal de atividade vulcânica"""
        try:
            print("🌋 [MAGMA]: Conectando ao Smithsonian Global Volcanism Program...")
            response = requests.get(self.rss_url, timeout=15)
            
            # Parse do XML
            root = ET.fromstring(response.content)
            
            # Namespace do RSS (às vezes necessário, às vezes não)
            items = root.findall(".//item")[:5] # Pega os 5 destaques mais recentes
            
            texto = "🌋 *RELATÓRIO DE ATIVIDADE VULCÂNICA*\n_Fonte: Smithsonian / USGS_\n"
            
            if not items:
                return "⚠️ Nenhuma nova atividade reportada no feed global."

            for item in items:
                title = item.findtext("title", default="")
                # O título geralmente é "Volcano Name (Country) - Report Type"
                # Ex: "Etna (Italy) - New Activity"
                
                description = item.findtext("description", default="")
                # Limpa a descrição para ficar curta (primeiros 200 caracteres)
                desc_curta = description.split('.')[0] + "." if description else "Detalhes não disponíveis."
                if len(desc_curta) > 150:
                    desc_curta = desc_curta[:150] + "..."

                # Ícone baseado no status (tentativa de inferência simples)
                icone = "🌋"
                if "New Activity" in title: icone = "🔥"
                if "Eruption" in desc_curta: icone = "💥"

                texto += f"\n{icone} *{title.strip()}*\n   📝 _{desc_curta}_\n"
            
            texto += "\n📡 _Monitoramento contínuo em tempo real._"
            return texto

        except Exception as e:
            print(f"❌ Erro Magma: {e}")
            return f"⚠️ Falha na conexão com a rede vulcanológica: {e}"