import os
from PIL import Image, ImageDraw, ImageFont

class AISubtitleGenerator:
    """
    Gerador de Legendas Neutras, Nítidas e de Alto Contraste (Rekynt Reels AI Studio).
    Utiliza fonte Truetype em negrito empacotada no projeto para leitura perfeita em qualquer sistema.
    """
    def __init__(self, temp_dir):
        self.temp_dir = temp_dir
        os.makedirs(self.temp_dir, exist_ok=True)
        
        core_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.abspath(os.path.join(core_dir, ".."))
        self.font_path = os.path.join(base_dir, "assets", "fonts", "Roboto-Bold.ttf")

    def generate_subtitle_card(self, text, filename, width=1080, height=220):
        """
        Cria um PNG transparente com legenda perfeitamente nítida, de alto contraste e legível.
        """
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        pad_x = 40
        max_text_w = width - (pad_x * 2) - 40

        font_size = 38
        font = None

        while font_size >= 20:
            try:
                if os.path.exists(self.font_path):
                    font = ImageFont.truetype(self.font_path, font_size)
                else:
                    try:
                        font = ImageFont.truetype("arialbd.ttf", font_size)
                    except Exception:
                        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
            except Exception:
                font = ImageFont.load_default()
                break

            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            if text_w <= max_text_w:
                break
            font_size -= 2

        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        # Container de leitura em Deep Slate escuro de alto contraste (opacidade 245)
        box_w = max(text_w + 80, 680)
        box_h = text_h + 36
        box_x0 = (width - box_w) / 2
        box_y0 = (height - box_h) / 2
        box_x1 = box_x0 + box_w
        box_y1 = box_y0 + box_h

        draw.rounded_rectangle(
            [(box_x0, box_y0), (box_x1, box_y1)],
            radius=16,
            fill=(15, 23, 42, 245),
            outline=(255, 107, 53, 255),
            width=3
        )

        x = (width - text_w) / 2
        y = (height - text_h) / 2 - 2

        # Sombra de leitura preta 360 graus
        for dx in [-2, 0, 2]:
            for dy in [-2, 0, 2]:
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), text, font=font, fill=(0, 0, 0, 255))

        # Texto Principal em BRANCO NÍTIDO
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))

        save_path = os.path.join(self.temp_dir, filename)
        img.save(save_path, "PNG")
        return save_path

    def get_default_caption(self):
        """
        Retorna legenda neutra imobiliária sem citar tipo de imóvel.
        """
        return ("✨ AMBIENTES INTEGRADOS E ILUMINAÇÃO NATURAL • REKYNT", "sub_main_clean.png")
