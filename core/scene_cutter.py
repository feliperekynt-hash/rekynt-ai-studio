import os
import subprocess
import imageio_ffmpeg

class AISceneCutter:
    """
    Fatiador Inteligente de Cenas Imobiliárias (Rekynt Reels AI).
    Extrai 6 tomadas dinâmicas das melhores partes do vídeo bruto e realiza cortes ritmados para Reels.
    """
    def __init__(self, temp_dir):
        self.temp_dir = temp_dir
        os.makedirs(self.temp_dir, exist_ok=True)
        self.ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()

    def get_video_duration(self, video_path):
        """
        Obtém a duração total do vídeo original via FFmpeg.
        """
        cmd = [self.ffmpeg_bin, '-i', video_path]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        err = res.stderr.decode('utf-8', errors='ignore')
        
        for line in err.splitlines():
            if "Duration:" in line:
                try:
                    parts = line.split("Duration:")[1].split(",")[0].strip()
                    h, m, s = parts.split(":")
                    return float(h)*3600 + float(m)*60 + float(s)
                except Exception:
                    pass
        return 42.0

    def build_multiscene_filter(self, video_path, total_duration):
        """
        Gera o filtro complexo do FFmpeg para extrair 6 tomadas dinâmicas de 4.0s espalhadas pelo vídeo do imóvel.
        """
        clip_len = 4.0
        num_clips = 6

        if total_duration <= (clip_len * num_clips):
            step = clip_len
        else:
            step = (total_duration - clip_len) / float(num_clips - 1)

        starts = [i * step for i in range(num_clips)]
        
        select_exprs = []
        for start_t in starts:
            end_t = start_t + clip_len
            select_exprs.append(f"between(t,{start_t:.2f},{end_t:.2f})")
        
        combined_select = "+".join(select_exprs)
        filter_str = f"[0:v]select='{combined_select}',setpts=N/FRAME_RATE/TB[sliced]"
        return filter_str
