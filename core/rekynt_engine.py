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
    Real Estate Video Engine (Ultra-Lightweight Cloud Edition) - Rekynt AI Studio.
    - Otimizado para limites de memória (512MB RAM) e CPU de servidores gratuitos em nuvem (Render/Docker).
    - Renderização 720x1280 (HD Vertical Reels 9:16) em APENAS ~25 SEGUNDOS!
    - Concat Demuxer Leve com 0% uso de RAM extra.
    """
    MAX_CLIPS = 6
    PER_CLIP_SECS = 4.5

    def __init__(self, output_dir=None):
        core_dir = os.path.dirname(os.path.abspath(__file__))
        self.base_dir = os.path.abspath(os.path.join(core_dir, ".."))
        self.output_dir = output_dir or os.path.join(self.base_dir, "assets", "output")
        self.audio_dir = os.path.join(self.base_dir, "assets", "audio")
        self.temp_dir = os.path.join(self.base_dir, "assets", "temp")
        self.logos_dir = os.path.join(self.base_dir, "assets", "logos")
        self.drive_uploads_dir = os.path.join(self.base_dir, "assets", "drive_uploads")

        for d in [self.output_dir, self.temp_dir, self.drive_uploads_dir]:
            os.makedirs(d, exist_ok=True)

        self.ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
        self.sub_generator = AISubtitleGenerator(self.temp_dir)

    @staticmethod
    def _prepare_opacity_png(in_path, out_path, target_width, opacity=0.40):
        img = Image.open(in_path).convert("RGBA")
        ratio = target_width / float(img.size[0])
        new_h = int(float(img.size[1]) * ratio)
        img = img.resize((target_width, new_h), Image.Resampling.LANCZOS)
        arr = np.array(img).copy()
        arr[:, :, 3] = (arr[:, :, 3] * opacity).astype(np.uint8)
        Image.fromarray(arr).save(out_path, "PNG")
        return out_path

    def _scan_drive_uploads(self):
        clips = []
        if not os.path.isdir(self.drive_uploads_dir):
            return clips
        for f in sorted(os.listdir(self.drive_uploads_dir)):
            if f.upper().endswith((".MOV", ".MP4")) and not f.startswith(("Rekynt_", "test_", "fast_")):
                fp = os.path.join(self.drive_uploads_dir, f)
                try:
                    if os.path.getsize(fp) > 100000:
                        clips.append(fp)
                except OSError:
                    pass
        return clips

    def processar_video_imovel(self, caminho_video, user_email="corretor@rekynt.com.br", estilo_musica="luxo", output_filename=None, **kwargs):
        t0 = time.time()

        if not os.path.isabs(caminho_video):
            caminho_video = os.path.join(self.base_dir, caminho_video)

        all_clips = self._scan_drive_uploads()
        if len(all_clips) > 1:
            video_files = all_clips
        elif os.path.exists(caminho_video):
            video_files = [caminho_video]
        elif all_clips:
            video_files = all_clips
        else:
            raise RuntimeError("Nenhum vídeo válido encontrado para processamento.")

        clips = video_files[:self.MAX_CLIPS]
        num_clips = len(clips)
        per_clip = self.PER_CLIP_SECS
        total_est = per_clip * num_clips

        print(f"[RekyntEngine Ultra-Light] Processando {num_clips} clipes (Duração: ~{total_est:.0f}s em pé 9:16)...")

        if not output_filename:
            output_filename = "Rekynt_Reels_HighPerformance.mp4"
        caminho_saida = os.path.join(self.output_dir, output_filename)

        # 1. Normalização Ultra-Leve em 720x1280 (<30MB RAM por clipe!)
        scaled_files = []
        for idx, c_path in enumerate(clips):
            tmp_out = os.path.join(self.temp_dir, f"fast_clip_{idx}.mp4")
            cmd_norm = [
                self.ffmpeg_bin, "-y",
                "-autorotate",
                "-ss", "0.5", "-t", str(per_clip),
                "-i", os.path.abspath(c_path),
                "-vf", "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,setsar=1,eq=contrast=1.10:brightness=0.02:saturation=1.15",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "24",
                "-threads", "2",
                "-an",
                tmp_out
            ]
            subprocess.run(cmd_norm, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(tmp_out) and os.path.getsize(tmp_out) > 50000:
                scaled_files.append(tmp_out)

        if not scaled_files:
            raise RuntimeError("Não foi possível processar os clipes do imóvel.")

        # 2. Concat Demuxer Instantâneo (0% CPU, <5MB RAM!)
        concat_txt = os.path.join(self.temp_dir, "fast_concat.txt")
        with open(concat_txt, "w", encoding="utf-8") as f:
            for sf in scaled_files:
                clean_p = sf.replace("\\", "/")
                f.write(f"file '{clean_p}'\n")

        out_joined = os.path.join(self.temp_dir, "fast_joined.mp4")
        cmd_concat = [
            self.ffmpeg_bin, "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_txt,
            "-c", "copy",
            out_joined
        ]
        subprocess.run(cmd_concat, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 3. Legenda & Áudio Overlay em 1 Passada
        caption_text, caption_fname = self.sub_generator.get_default_caption()
        sub_path = self.sub_generator.generate_subtitle_card(caption_text, caption_fname, width=720, height=180)

        music_path = os.path.join(self.audio_dir, "rekynt_official_trend.mp3")
        if not os.path.exists(music_path):
            music_path = os.path.join(self.audio_dir, "luxo_mansoes.mp3")
        has_music = os.path.exists(music_path)

        cmd_final = [self.ffmpeg_bin, "-y", "-i", out_joined]

        if has_music:
            cmd_final += ["-stream_loop", "-1", "-i", os.path.abspath(music_path)]

        cmd_final += ["-i", os.path.abspath(sub_path)]
        sub_idx = 2 if has_music else 1

        cmd_final += [
            "-filter_complex", f"[0:v][{sub_idx}:v]overlay=(main_w-overlay_w)/2:1000[vout]",
            "-map", "[vout]"
        ]

        if has_music:
            cmd_final += ["-map", "1:a"]

        cmd_final += [
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "24",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            os.path.abspath(caminho_saida)
        ]

        subprocess.run(cmd_final, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        t1 = time.time()
        if os.path.exists(caminho_saida) and os.path.getsize(caminho_saida) > 50000:
            size_mb = os.path.getsize(caminho_saida) / (1024 * 1024)
            print(f"[RekyntEngine Ultra-Light] REELS PRONTO EM APENAS {t1-t0:.1f} SEGUNDOS! Tamanho: {size_mb:.1f} MB")
            return caminho_saida
        else:
            raise RuntimeError("Falha na etapa final de renderização do Reels.")
