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
    Rekynt AI Studio — Motor de Edição Profissional de Reels Imobiliários 9:16.

    Pipeline Completo:
      1. Escaneia TODOS os clipes disponíveis em drive_uploads (não apenas o selecionado).
      2. Usa segmentos longos de cada clipe (7-12s) para criar um Reels de 30-60 segundos.
      3. Aplica Color Grading cinematográfico premium (eq + unsharp).
      4. Transições fade-in/fade-out suaves entre cada cena.
      5. Autorotate nativo do FFmpeg para vídeos de iPhone em pé (9:16).
      6. Overlay de logos Rekynt com 40% de opacidade.
      7. Legenda neutra nítida no terço inferior (Regra de Ouro: sem tipo de imóvel).
      8. Trilha sonora imobiliária de alto padrão.
    """

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

    # ──────────────────────────────────────────
    # Utilitários
    # ──────────────────────────────────────────

    @staticmethod
    def _prepare_opacity_png(in_path, out_path, target_width, opacity=0.40):
        """Redimensiona e aplica opacidade a um logo PNG."""
        img = Image.open(in_path).convert("RGBA")
        ratio = target_width / float(img.size[0])
        new_h = int(float(img.size[1]) * ratio)
        img = img.resize((target_width, new_h), Image.Resampling.LANCZOS)

        arr = np.array(img).copy()
        arr[:, :, 3] = (arr[:, :, 3] * opacity).astype(np.uint8)

        Image.fromarray(arr).save(out_path, "PNG")
        return out_path

    def _scan_drive_uploads(self):
        """Escaneia a pasta drive_uploads e retorna todos os clipes válidos (>.1MB)."""
        clips = []
        if not os.path.isdir(self.drive_uploads_dir):
            return clips
        for f in sorted(os.listdir(self.drive_uploads_dir)):
            if f.upper().endswith((".MOV", ".MP4")) and not f.startswith(("Rekynt_", "test_")):
                fp = os.path.join(self.drive_uploads_dir, f)
                try:
                    if os.path.getsize(fp) > 100_000:
                        clips.append(fp)
                except OSError:
                    pass
        return clips

    # ──────────────────────────────────────────
    # Pipeline Principal
    # ──────────────────────────────────────────

    def processar_video_imovel(
        self,
        caminho_video,
        user_email="corretor@rekynt.com.br",
        estilo_musica="luxo",
        output_filename=None,
        **kwargs,
    ):
        t0 = time.time()

        # ── 1. Resolver caminho e coletar TODOS os clipes ─────────────
        if not os.path.isabs(caminho_video):
            caminho_video = os.path.join(self.base_dir, caminho_video)

        all_clips = self._scan_drive_uploads()

        print(f"[RekyntEngine] Clipes encontrados em drive_uploads: {len(all_clips)}")
        for c in all_clips:
            print(f"  -> {os.path.basename(c)}  ({os.path.getsize(c) // 1024} KB)")

        # Lógica de seleção: SEMPRE usar todos os clipes disponíveis
        # para montar o tour completo. Só usa um clipe isolado se
        # realmente for o único na pasta.
        if len(all_clips) > 1:
            video_files = all_clips
        elif os.path.exists(caminho_video):
            video_files = [caminho_video]
        elif all_clips:
            video_files = all_clips
        else:
            raise RuntimeError(
                "Nenhum arquivo de vídeo encontrado em drive_uploads. "
                "Envie os vídeos pelo botão do celular ou pelo Google Drive."
            )

        clips_to_process = video_files[:10]
        num_clips = len(clips_to_process)

        # ── 2. Calcular duração ideal por clipe ───────────────────────
        # Meta: Reels de 30-60 segundos.
        if num_clips == 1:
            per_clip_secs = 30.0
        elif num_clips == 2:
            per_clip_secs = 15.0
        elif num_clips <= 4:
            per_clip_secs = 10.0
        elif num_clips <= 7:
            per_clip_secs = 7.0
        else:
            per_clip_secs = 5.0

        fade_dur = 0.5
        estimated_total = per_clip_secs * num_clips
        print(
            f"[RekyntEngine] Montando Reels 9:16 com {num_clips} cenas "
            f"× {per_clip_secs}s = ~{estimated_total:.0f}s"
        )

        if not output_filename:
            output_filename = "Rekynt_Reels_HighPerformance.mp4"
        caminho_saida = os.path.join(self.output_dir, output_filename)

        # ── 3. Normalizar cada clipe (escala, cor, fade) ──────────────
        vf_base = (
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,setsar=1,"
            "eq=contrast=1.15:brightness=0.03:saturation=1.20,"
            "unsharp=5:5:0.6:5:5:0"
        )

        scaled_clips = []
        for i, clip_path in enumerate(clips_to_process):
            tmp_out = os.path.join(self.temp_dir, f"clip_norm_{i}.mp4")

            fade_out_start = max(0, per_clip_secs - fade_dur - 0.1)
            vf_full = (
                f"{vf_base},"
                f"fade=in:st=0:d={fade_dur},"
                f"fade=out:st={fade_out_start}:d={fade_dur}"
            )

            cmd = [
                self.ffmpeg_bin, "-y",
                "-autorotate",
                "-ss", "0.3",
                "-t", str(per_clip_secs),
                "-i", os.path.abspath(clip_path),
                "-vf", vf_full,
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-pix_fmt", "yuv420p",
                "-an",
                tmp_out,
            ]

            print(f"[RekyntEngine] Normalizando clipe {i+1}/{num_clips}: {os.path.basename(clip_path)} ({per_clip_secs}s)...")
            res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            if res.returncode == 0 and os.path.exists(tmp_out) and os.path.getsize(tmp_out) > 1000:
                scaled_clips.append(tmp_out)
            else:
                stderr_text = res.stderr.decode("utf-8", errors="ignore")[-300:]
                print(f"[RekyntEngine] AVISO: Falha ao normalizar clipe {i+1}: {stderr_text}")

        if not scaled_clips:
            raise RuntimeError("Não foi possível normalizar nenhum clipe do imóvel.")

        print(f"[RekyntEngine] {len(scaled_clips)}/{num_clips} clipes normalizados com sucesso.")

        # ── 4. Concatenar clipes com Concat Demuxer ───────────────────
        concat_txt = os.path.join(self.temp_dir, "concat_list.txt")
        with open(concat_txt, "w", encoding="utf-8") as f:
            for clip in scaled_clips:
                f.write(f"file '{clip.replace(chr(92), '/')}'\n")

        out_joined = os.path.join(self.temp_dir, "tour_joined.mp4")
        cmd_concat = [
            self.ffmpeg_bin, "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_txt,
            "-c", "copy",
            out_joined,
        ]
        subprocess.run(cmd_concat, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if not os.path.exists(out_joined) or os.path.getsize(out_joined) < 10_000:
            raise RuntimeError("Falha ao concatenar os clipes do imóvel.")

        # ── 5. Preparar overlays (logos + legenda) ────────────────────
        logo_main_src = os.path.join(self.logos_dir, "logo_rekynt.png")
        logo_icon_src = os.path.join(self.logos_dir, "logo_rekynt_icon.png")
        logo_main_tmp = os.path.join(self.temp_dir, "logo_main_40.png")
        logo_icon_tmp = os.path.join(self.temp_dir, "logo_icon_40.png")

        has_logo_main = os.path.exists(logo_main_src)
        has_logo_icon = os.path.exists(logo_icon_src)

        if has_logo_main:
            self._prepare_opacity_png(logo_main_src, logo_main_tmp, target_width=280, opacity=0.40)
        if has_logo_icon:
            self._prepare_opacity_png(logo_icon_src, logo_icon_tmp, target_width=90, opacity=0.40)

        caption_text, caption_fname = self.sub_generator.get_default_caption()
        sub_path = self.sub_generator.generate_subtitle_card(caption_text, caption_fname)

        # ── 6. Trilha sonora ──────────────────────────────────────────
        caminho_musica = os.path.join(self.audio_dir, "rekynt_official_trend.mp3")
        if not os.path.exists(caminho_musica):
            caminho_musica = os.path.join(self.audio_dir, "luxo_mansoes.mp3")
        has_music = os.path.exists(caminho_musica)

        # ── 7. Pipeline final: overlays + trilha ──────────────────────
        cmd_final = [self.ffmpeg_bin, "-y", "-i", out_joined]

        if has_music:
            cmd_final += ["-stream_loop", "-1", "-i", os.path.abspath(caminho_musica)]

        overlay_inputs = []
        filter_parts = []
        input_idx = 2 if has_music else 1
        current_label = "0:v"

        if has_logo_main:
            cmd_final += ["-i", os.path.abspath(logo_main_tmp)]
            next_label = f"v{len(filter_parts)}"
            filter_parts.append(
                f"[{current_label}][{input_idx}:v]overlay=(main_w-overlay_w)/2:1380[{next_label}]"
            )
            current_label = next_label
            input_idx += 1

        if has_logo_icon:
            cmd_final += ["-i", os.path.abspath(logo_icon_tmp)]
            next_label = f"v{len(filter_parts)}"
            filter_parts.append(
                f"[{current_label}][{input_idx}:v]overlay=40:70[{next_label}]"
            )
            current_label = next_label
            input_idx += 1

        # Legenda (sempre disponível)
        cmd_final += ["-i", os.path.abspath(sub_path)]
        next_label = "vout"
        filter_parts.append(
            f"[{current_label}][{input_idx}:v]overlay=(main_w-overlay_w)/2:1650[{next_label}]"
        )

        if filter_parts:
            cmd_final += ["-filter_complex", ";".join(filter_parts)]
            cmd_final += ["-map", "[vout]"]
        else:
            cmd_final += ["-map", "0:v"]

        if has_music:
            cmd_final += ["-map", "1:a"]

        cmd_final += [
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p",
        ]
        if has_music:
            cmd_final += ["-c:a", "aac", "-b:a", "192k"]

        cmd_final += ["-shortest", os.path.abspath(caminho_saida)]

        print("[RekyntEngine] Renderizando Reels Final 9:16 com overlays e trilha...")
        res = subprocess.run(cmd_final, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

        t1 = time.time()
        if res.returncode == 0 and os.path.exists(caminho_saida) and os.path.getsize(caminho_saida) > 50_000:
            print(
                f"[RekyntEngine] REELS FINALIZADO COM SUCESSO em {t1-t0:.1f}s! "
                f"Duracao estimada: ~{estimated_total:.0f}s | Arquivo: {caminho_saida}"
            )
            return caminho_saida
        else:
            err_msg = res.stderr.decode("utf-8", errors="ignore")[-500:]
            print(f"[RekyntEngine] ERRO FFmpeg: {err_msg}")
            raise RuntimeError(f"Erro na renderização final: {err_msg[:200]}")
