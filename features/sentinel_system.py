import cv2
import time
import os

class SentinelSystem:
    def __init__(self):
        self.camera_index = 0

    def capturar_intruso(self):
        print("👁️ [DEBUG]: Iniciando módulo Sentinela...")
        cap = None
        
        # Define caminho ABSOLUTO para salvar (evita erro de pasta)
        nome_arquivo = "sentinel_capture.png"
        caminho_completo = os.path.abspath(nome_arquivo)
        
        try:
            # Tenta forçar o driver DSHOW (que funcionou no seu teste)
            print(f"👁️ [DEBUG]: Abrindo câmera {self.camera_index} (DSHOW)...")
            cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
            
            # Se falhar, tenta sem driver específico
            if not cap.isOpened():
                print("⚠️ [DEBUG]: Falha no DSHOW. Tentando driver padrão...")
                cap = cv2.VideoCapture(self.camera_index)

            if not cap.isOpened():
                return None, "❌ Erro Crítico: O Windows não liberou o acesso à câmera."

            # Configura resolução (ajuda a estabilizar)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

            print("👁️ [DEBUG]: Aquecendo sensor (Aguarde)...")
            # Lê 10 frames para limpar o buffer preto inicial
            for i in range(10):
                cap.read()
                time.sleep(0.1) # Pausa leve para o hardware respirar

            print("👁️ [DEBUG]: Capturando frame final...")
            ret, frame = cap.read()
            
            if ret and frame is not None:
                # Salva no caminho absoluto
                cv2.imwrite(caminho_completo, frame)
                print(f"✅ [DEBUG]: Foto salva em: {caminho_completo}")
                return caminho_completo, "📸 Sentinela: Imagem capturada com sucesso."
            else:
                return None, "❌ Erro: A câmera abriu, mas a imagem veio vazia (tela preta)."

        except Exception as e:
            print(f"❌ [ERRO]: {e}")
            return None, f"❌ Falha de Script: {e}"
            
        finally:
            if cap: 
                cap.release()
                print("👁️ [DEBUG]: Câmera liberada.")