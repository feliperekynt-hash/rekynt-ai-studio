import os
import glob
import hashlib

class AIMusicRotary:
    """
    Gerenciador de Rotação de Trilhas Exclusivas por Corretor e Vídeo (Rekynt Reels AI).
    Garante que cada vídeo dos 6 corretores tenha uma música inédita e contextual.
    """
    def __init__(self, audio_dir):
        self.audio_dir = audio_dir

    def get_exclusive_track(self, user_email="corretor@rekynt.com.br", video_filename="video.mp4", style="luxo"):
        """
        Calcula um hash determinístico para escolher uma música exclusiva da biblioteca.
        """
        available_tracks = sorted(glob.glob(os.path.join(self.audio_dir, "*.mp3")) + glob.glob(os.path.join(self.audio_dir, "*.wav")))
        
        if not available_tracks:
            return os.path.join(self.audio_dir, "rekynt_official_trend.mp3")

        official_track = os.path.join(self.audio_dir, "rekynt_official_trend.mp3")
        if style == "oficial" and os.path.exists(official_track):
            return official_track

        combined_seed = f"{user_email.lower().strip()}_{video_filename.strip()}_{style.lower().strip()}"
        hash_val = int(hashlib.md5(combined_seed.encode('utf-8')).hexdigest(), 16)

        chosen_idx = hash_val % len(available_tracks)
        chosen_track = available_tracks[chosen_idx]
        
        print(f"[AIMusicRotary] Semente: '{combined_seed}' -> Trilha selecionada #{chosen_idx+1}: {os.path.basename(chosen_track)}")
        return chosen_track
