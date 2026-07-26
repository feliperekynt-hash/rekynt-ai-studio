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
    Real Estate Video Engine (Ultra-Fast Single-Pass Edition) - Rekynt AI Studio.
    - Processamento em 1 Única Passada FFmpeg: Concatena, Escala para 9:16 Vertical, Aplica Color Grading, Overlays e Áudio em ~30 segundos!
    - Autorotate Nativo: Mantém vídeos de iPhone (.MOV) 100% em pé.
    - Alta Fidelidade e Leveza para Servidores de Nuvem (Render/Docker).
    """
    MAX_CLIPS = 6
    PER_CLIP_SECS = 5.0

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
            if f.upper().endswith((".MOV", ".MP4")) and not f.startswith(("Rekynt_", "test_")):
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
            raise RuntimeError("Nenhum vídeo válido encontrado em drive_uploads.")

        clips = video_files[:self.MAX_CLIPS]
        num_clips = len(clips)
        per_clip = self.PER_CLIP_SECS
        total_est = per_clip * num_clips

        print(f"[RekyntEngine Ultra-Fast] Processando {num_clips} clipes (Duração total: ~{total_est:.0f}s)...")

        if not output_filename:
            output_filename = "Rekynt_Reels_HighPerformance.mp4"
        caminho_saida = os.path.join(self.output_dir, output_filename)

        # Overlays
        logo_main_src = os.path.join(self.logos_dir, "logo_rekynt.png")
        logo_icon_src = os.path.join(self.logos_dir, "logo_rekynt_icon.png")
        logo_main_tmp = os.path.join(self.temp_dir, "logo_main_40.png")
        logo_icon_tmp = os.path.join(self.temp_dir, "logo_icon_40.png")

        has_logo_main = os.path.exists(logo_main_src)
        has_logo_icon = os.path.exists(logo_icon_src)
        if has_logo_main:
            self._prepare_opacity_png(logo_main_src, logo_main_tmp, 280, 0.40)
        if has_logo_icon:
            self._prepare_opacity_png(logo_icon_src, logo_icon_tmp, 90, 0.40)

        caption_text, caption_fname = self.sub_generator.get_default_caption()
        sub_path = self.sub_generator.generate_subtitle_card(caption_text, caption_fname)

        music_path = os.path.join(self.audio_dir, "rekynt_official_trend.mp3")
        if not os.path.exists(music_path):
            music_path = os.path.join(self.audio_dir, "luxo_mansoes.mp3")
        has_music = os.path.exists(music_path)

        cmd = [self.ffmpeg_bin, "-y"]

        # Entradas de Vídeo
        for c in clips:
            cmd += ["-autorotate", "-ss", "0.5", "-t", str(per_clip), "-i", os.path.abspath(c)]

        # Entradas de Áudio e Imagem
        music_idx = num_clips if has_music else None
        if has_music:
            cmd += ["-stream_loop", "-1", "-i", os.path.abspath(music_path)]

        logo_main_idx = (num_clips + (1 if has_music else 0)) if has_logo_main else None
        if has_logo_main:
            cmd += ["-i", os.path.abspath(logo_main_tmp)]

        logo_icon_idx = (num_clips + (1 if has_music else 0) + (1 if has_logo_main else 0)) if has_logo_icon else None
        if has_logo_icon:
            cmd += ["-i", os.path.abspath(logo_icon_tmp)]

        sub_idx = num_clips + (1 if has_music else 0) + (1 if has_logo_main else 0) + (1 if has_logo_icon else 0)
        cmd += ["-i", os.path.abspath(sub_path)]

        # Filter Graph Single-Pass
        filter_chains = []
        for i in range(num_clips):
            filter_chains.append(
                f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,eq=contrast=1.12:brightness=0.02:saturation=1.18[v{i}]"
            )

        concat_inputs = "".join(f"[v{i}]" for i in range(num_clips))
        filter_chains.append(f"{concat_inputs}concat=n={num_clips}:v=1:a=0[vcat]")

        curr_v = "vcat"
        if logo_main_idx is not None:
            filter_chains.append(f"[{curr_v}][{logo_main_idx}:v]overlay=(main_w-overlay_w)/2:1380[vlm]")
            curr_v = "vlm"

        if logo_icon_idx is not None:
            filter_chains.append(f"[{curr_v}][{logo_icon_idx}:v]overlay=40:70[vli]")
            curr_v = "vli"

        filter_chains.append(f"[{curr_v}][{sub_idx}:v]overlay=(main_w-overlay_w)/2:1550[vout]")

        cmd += [
            "-filter_complex", ";".join(filter_chains),
            "-map", "[vout]",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
            "-pix_fmt", "yuv420p"
        ]

        if music_idx is not None:
            cmd += ["-map", f"{music_idx}:a", "-c:a", "aac", "-b:a", "128k", "-shortest"]

        cmd += [os.path.abspath(caminho_saida)]

        print(f"[RekyntEngine Ultra-Fast] Executando Single-Pass FFmpeg...")
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        t1 = time.time()
        if os.path.exists(caminho_saida) and os.path.getsize(caminho_saida) > 50000:
            size_mb = os.path.getsize(caminho_saida) / (1024 * 1024)
            print(f"[RekyntEngine Ultra-Fast] REELS CONCLUIDO EM APENAS {t1-t0:.1f} SEGUNDOS! Size: {size_mb:.1f} MB")
            return caminho_saida
        else:
            err_log = res.stderr.decode("utf-8", errors="ignore")[-300:]
            raise RuntimeError(f"Erro na renderização: {err_log}")
