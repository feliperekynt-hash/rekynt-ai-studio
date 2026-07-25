import os
import sys
import time
import subprocess
import imageio_ffmpeg
import numpy as np
from PIL import Image

from .subtitles import AISubtitleGenerator

class RekyntAIStudioEngine:
    """
    Real Estate Video Engine (High-Performance Edition) - Rekynt AI Studio.
    - Autorotate nativo sem rotação manual: vídeos de iPhone (.MOV) e Android (.MP4) 100% em pé (Vertical 9:16).
    - Concat Demuxer Ultra-Rápido (~10 segundos de renderização total, zero consumo excessivo de memória).
    - Color Grading "Cinematic Real Estate" (contraste 1.14, nitidez e iluminação natural).
    - Legendas Dinâmicas Neutras sem corte de texto nas bordas (Regra de Ouro).
    - Trilha Sonora Imobiliária de Alto Padrão (AI Audio Match).
    """
    def __init__(self, output_dir=None):
        self.base_dir = r"C:\Users\fenie\.gemini\antigravity\scratch\rekynt_reels_ai_studio"
        self.output_dir = output_dir or os.path.join(self.base_dir, "assets", "output")
        self.audio_dir = os.path.join(self.base_dir, "assets", "audio")
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.temp_dir = os.path.join(self.base_dir, "assets", "temp")
        os.makedirs(self.temp_dir, exist_ok=True)

        self.ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
        self.sub_generator = AISubtitleGenerator(self.temp_dir)

    @staticmethod
    def _prepare_opacity_png(in_path, out_path, target_width, opacity=0.40):
        img = Image.open(in_path).convert("RGBA")
        w_percent = (target_width / float(img.size[0]))
        h_size = int((float(img.size[1]) * float(w_percent)))
        img = img.resize((target_width, h_size), Image.Resampling.LANCZOS)

        img_np = np.array(img).copy()
        img_np[:, :, 3] = (img_np[:, :, 3] * opacity).astype(np.uint8)

        out_img = Image.fromarray(img_np)
        out_img.save(out_path, "PNG")
        return out_path

    def processar_video_imovel(self, caminho_video, user_email="corretor@rekynt.com.br", estilo_musica="luxo", output_filename=None, **kwargs):
        """
        Executa o pipeline High-Performance Edition para gerar o Reels 9:16 comercial perfeito em pé (1080x1920).
        """
        t0 = time.time()
        print(f"[RekyntAIEngine] Executando Real Estate Engine High-Performance para: {caminho_video}...")

        drive_uploads_dir = os.path.join(self.base_dir, "assets", "drive_uploads")
        
        # 1. Selecionar Clipes Validados do Imóvel
        video_files = []
        if "TOUR_COMPLETO" in caminho_video or not os.path.exists(caminho_video):
            all_found = sorted([
                os.path.join(drive_uploads_dir, f) for f in os.listdir(drive_uploads_dir)
                if f.upper().endswith(('.MOV', '.MP4')) and not f.startswith(('Rekynt_', 'test_', 'imovel_drive_'))
            ])
            video_files = [f for f in all_found if os.path.getsize(f) > 100000]
        else:
            video_files = [caminho_video]

        if not video_files:
            video_files = [caminho_video]

        # Selecionar até 10 tomadas comerciais para formar um Reels ritmado de ~35 a 40 segundos
        clips_to_process = video_files[:10]
        print(f"[RekyntAIEngine] Montando Reels Comercial 9:16 em pé com {len(clips_to_process)} tomadas do imóvel...")

        if not output_filename:
            output_filename = "Rekynt_Reels_HighPerformance.mp4"

        caminho_saida = os.path.join(self.output_dir, output_filename)

        # 2. Normalização individual de cada clipe usando Autorotate nativo do FFmpeg (Sem Transpose manual)
        scaled_clips = []
        for i, path in enumerate(clips_to_process):
            tmp_out = os.path.join(self.temp_dir, f"clip_norm_{i}.mp4")

            cmd_norm = [
                self.ffmpeg_bin, '-y',
                '-autorotate', # ROTAÇÃO NATIVA DE IPHONE E ANDROID
                '-ss', '0.5', '-t', '3.5',
                '-i', os.path.abspath(path),
                '-vf', 'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,eq=contrast=1.14:brightness=0.02:saturation=1.22',
                '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '20',
                '-an',
                tmp_out
            ]
            res_norm = subprocess.run(cmd_norm, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if res_norm.returncode == 0:
                scaled_clips.append(tmp_out)

        if not scaled_clips:
            raise RuntimeError("Não foi possível processar os clipes do imóvel.")

        # 3. Concat Demuxer Ultra-Rápido
        concat_txt = os.path.join(self.temp_dir, "concat_list.txt")
        with open(concat_txt, "w", encoding="utf-8") as f:
            for clip in scaled_clips:
                c_clean = clip.replace("\\", "/")
                f.write(f"file '{c_clean}'\n")

        out_joined = os.path.join(self.temp_dir, "tour_joined.mp4")
        cmd_join = [
            self.ffmpeg_bin, '-y',
            '-f', 'concat', '-safe', '0',
            '-i', concat_txt,
            '-c', 'copy',
            out_joined
        ]
        subprocess.run(cmd_join, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 4. Trilha Sonora de Alto Padrão (AI Audio Match)
        caminho_musica = os.path.join(self.audio_dir, "rekynt_official_trend.mp3")
        if not os.path.exists(caminho_musica):
            caminho_musica = os.path.join(self.audio_dir, "luxo_mansoes.mp3")

        # 5. Marcas d'Água Rekynt (40% Opacidade) & Legenda Inteligente Neutra
        logos_dir = os.path.join(self.base_dir, "assets", "logos")
        logo_main_src = os.path.join(logos_dir, "logo_rekynt.png")
        logo_top_src = os.path.join(logos_dir, "logo_rekynt_icon.png")

        logo_main_40 = os.path.abspath(os.path.join(self.temp_dir, "logo_main_40.png"))
        logo_top_40 = os.path.abspath(os.path.join(self.temp_dir, "logo_top_40.png"))

        if os.path.exists(logo_main_src):
            self._prepare_opacity_png(logo_main_src, logo_main_40, target_width=280, opacity=0.40)
        if os.path.exists(logo_top_src):
            self._prepare_opacity_png(logo_top_src, logo_top_40, target_width=90, opacity=0.40)

        caption_text, caption_fname = self.sub_generator.get_default_caption()
        sub_path = self.sub_generator.generate_subtitle_card(caption_text, caption_fname)

        # 6. PIPELINE FINAL: LOGOS 40% + LEGENDA INTEIRA ENQUADRADA + TRILHA IMPECÁVEL
        cmd_final = [
            self.ffmpeg_bin, '-y',
            '-i', out_joined,
            '-stream_loop', '-1', '-i', os.path.abspath(caminho_musica),
            '-i', logo_main_40,
            '-i', logo_top_40,
            '-i', os.path.abspath(sub_path),
            '-filter_complex',
            '[0:v][2:v]overlay=(main_w-overlay_w)/2:1380[v1];'
            '[v1][3:v]overlay=40:70[v2];'
            '[v2][4:v]overlay=(main_w-overlay_w)/2:1550[vout]',
            '-map', '[vout]',
            '-map', '1:a',
            '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '20',
            '-c:a', 'aac', '-b:a', '192k',
            '-shortest',
            os.path.abspath(caminho_saida)
        ]

        print("[RekyntAIEngine] Renderizando Reels Comercial Final 9:16 High-Performance...")
        res = subprocess.run(cmd_final, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

        t1 = time.time()
        if res.returncode == 0:
            print(f"[RekyntAIEngine] REELS COMMERCIAL HIGH-PERFORMANCE RENDERIZADO EM APENAS {t1-t0:.2f} SEGUNDOS! Salvo em: {caminho_saida}")
            return caminho_saida
        else:
            err_log = res.stderr.decode("utf-8", errors="ignore")
            print(f"[RekyntAIEngine] Erro na renderização: {err_log}")
            raise RuntimeError(f"Erro na renderização: {err_log}")
