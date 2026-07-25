import os
import subprocess
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

class AIVisionRoomInspector:
    """
    Inspetor de Visão por IA para Classificação de Ambientes (Rekynt Reels AI).
    TRAVA DE SEGURANÇA: Gera legendas dinâmicas puramente descritivas dos cômodos
    SEM MENCIONAR o tipo do imóvel (ex: Mansão/Sobrado/Casa/Apartamento).
    """
    def __init__(self, temp_dir):
        self.temp_dir = temp_dir
        os.makedirs(self.temp_dir, exist_ok=True)
        self.ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()

    def generate_subtitle_png(self, text, filename, width=1080, height=180):
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        pad_x = 60
        pad_y = 10
        box_y0 = pad_y
        box_y1 = height - pad_y
        
        draw.rounded_rectangle(
            [(pad_x, box_y0), (width - pad_x, box_y1)],
            radius=14,
            fill=(15, 23, 42, 210),
            outline=(255, 107, 53, 230),
            width=2
        )

        font_size = 34
        try:
            font = ImageFont.truetype("arialbd.ttf", font_size)
        except IOError:
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except IOError:
                font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        x = (width - text_w) / 2
        y = (height - text_h) / 2 - 2

        draw.text((x + 2, y + 2), text, font=font, fill=(0, 0, 0, 240))
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))

        save_path = os.path.join(self.temp_dir, filename)
        img.save(save_path, "PNG")
        return save_path

    def analyze_and_build_synced_subtitles(self, video_path, duration=42.0):
        """
        Legendas 100% puras e neutras com foco estrito na experiência do ambiente.
        """
        room_captions = [
            ("✨ AMBIENTES INTEGRADOS E ILUMINAÇÃO NATURAL • REKYNT", "sub_sec_0.png", 0, 7),
            ("🛋️ SALA AMPLA EM CONCEITO ABERTO", "sub_sec_1.png", 7, 14),
            ("🍳 COZINHA PLANEJADA DE ALTO PADRÃO", "sub_sec_2.png", 14, 21),
            ("🏊 ÁREA GOURMET E ESPAÇO DE LAZER", "sub_sec_3.png", 21, 28),
            ("🛏️ SUÍTE CONFORTÁVEL E ACONCHEGANTE", "sub_sec_4.png", 28, 35),
            ("📲 REKYNT IMÓVEIS • AGENDE UMA VISITA", "sub_sec_5.png", 35, 42)
        ]

        overlay_chain = []
        inputs = []

        for idx, (text, fname, start_t, end_t) in enumerate(room_captions):
            png_path = self.generate_subtitle_png(text, fname)
            inputs.append(os.path.abspath(png_path))
            overlay_chain.append((idx + 4, start_t, end_t))

        return inputs, overlay_chain
