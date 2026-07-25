import os
from PIL import Image, ImageDraw, ImageFont

class AISubtitleGenerator:
    """
    Gerador de Legendas Neutras e Perfeitamente Enquadradas (Rekynt Reels AI).
    Ajuste dinâmico de fonte para ZERO corte de texto nas bordas.
    """
    def __init__(self, temp_dir):
        self.temp_dir = temp_dir
        os.makedirs(self.temp_dir, exist_ok=True)

    def generate_subtitle_card(self, text, filename, width=1080, height=180):
        """
        Cria um PNG transparente com legenda perfeitamente centralizada e ajustada.
        """
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        pad_x = 40
        max_text_w = width - (pad_x * 2) - 40

        # Encontrar o tamanho ideal de fonte para caber sem cortar
        font_size = 32
        font = None
        while font_size >= 18:
            try:
                font = ImageFont.truetype("arialbd.ttf", font_size)
            except IOError:
                try:
                    font = ImageFont.truetype("arial.ttf", font_size)
                except IOError:
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

        # Desenhar container arredondado proporcional ao texto
        box_w = max(text_w + 60, 600)
        box_x0 = (width - box_w) / 2
        box_x1 = box_x0 + box_w

        draw.rounded_rectangle(
            [(box_x0, 10), (box_x1, height - 10)],
            radius=14,
            fill=(15, 23, 42, 220), # Deep Slate translucido
            outline=(255, 107, 53, 240), # Rekynt Sunset Orange
            width=2
        )

        x = (width - text_w) / 2
        y = (height - text_h) / 2 - 2

        # Sombra de leitura nítida
        draw.text((x + 2, y + 2), text, font=font, fill=(0, 0, 0, 240))
        # Texto Principal Branco
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))

        save_path = os.path.join(self.temp_dir, filename)
        img.save(save_path, "PNG")
        return save_path

    def get_default_caption(self):
        """
        Retorna legenda neutra imobiliária sem citar tipo de imóvel.
        """
        return ("✨ AMBIENTES INTEGRADOS E ILUMINAÇÃO NATURAL • REKYNT", "sub_main_clean.png")
