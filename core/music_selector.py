import os
import random

class AIMusicSelector:
    """
    Seletor Inteligente de Trilhas Sonoras para Imóveis (Rekynt Reels AI).
    Garante variabilidade de áudio entre os 6 corretores da Rekynt.
    """
    def __init__(self, audio_dir):
        self.audio_dir = audio_dir

    def get_track_for_style(self, style="luxo"):
        """
        Retorna o caminho do arquivo MP3 com base na categoria imobiliária.
        Categorias disponíveis: 'luxo', 'urbano', 'familia', 'viral'
        """
        style = style.lower()
        mapping = {
            "luxo": "luxo_mansoes.mp3",
            "urbano": "moderno_urbano.mp3",
            "familia": "condominio_familia.mp3",
            "viral": "viral_tour.mp3"
        }

        filename = mapping.get(style, "luxo_mansoes.mp3")
        path = os.path.join(self.audio_dir, filename)

        if os.path.exists(path):
            return path
        
        # Se não encontrar, escolhe aleatoriamente qualquer MP3 disponível na pasta audio
        available = [f for f in os.listdir(self.audio_dir) if f.endswith(('.mp3', '.wav'))]
        if available:
            chosen = random.choice(available)
            return os.path.join(self.audio_dir, chosen)
        
        return os.path.join(self.audio_dir, "luxo_mansoes.mp3")
