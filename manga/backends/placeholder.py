"""APIキーなしで工程を確認するためのダミー画像。"""

import hashlib
import textwrap

from PIL import Image, ImageDraw, ImageFont


class PlaceholderBackend:
    def __init__(self, options):
        self.font_path = options.get("font")

    def generate(self, prompt, negative, aspect, refs, seed, out_path):
        w = 768
        h = max(256, round(w / aspect))
        if h > 1536:
            h, w = 1536, round(1536 * aspect)
        shade = 200 + int(hashlib.md5(prompt.encode()).hexdigest()[:2], 16) % 40
        img = Image.new("L", (w, h), shade)
        d = ImageDraw.Draw(img)
        for i in range(0, w + h, 24):
            d.line([(i, 0), (i - h, h)], fill=shade - 25, width=2)
        try:
            font = ImageFont.truetype(self.font_path, 18) if self.font_path else ImageFont.load_default(18)
        except OSError:
            font = ImageFont.load_default(18)
        text = "\n".join(textwrap.wrap(prompt, width=max(20, w // 11)))
        d.multiline_text((12, 12), text, fill=40, font=font, spacing=4)
        img.save(out_path)
