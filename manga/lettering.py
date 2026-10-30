"""写植：縦書きの台詞と、吹き出し・四角枠の描画。

枠の種類はネームの type から機械的に決める（改善案8）。
  speech    → 吹き出し（楕円）。style: shout でギザギザ
  thought   → 心の声。project.yaml の thought_style（box / cloud）
  narration → ナレーション（四角枠）
  sfx       → 描き文字（枠なし、白フチの太字）
"""

import math

from PIL import Image, ImageDraw, ImageFont

# 縦書きで90度回す文字（長音、ダッシュ、括弧など）
ROTATE = set("ー－-―—〜～…‥「」『』（）()【】〈〉《》[]＝=→←<>:：")
SMALL = set("ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮヵヶ")
PUNCT = set("、。，．,.")
HALF_TO_FULL = str.maketrans("!?0123456789", "！？０１２３４５６７８９")
NO_COLUMN_START = set("、。」』）！？…ー・ぁぃぅぇぉっゃゅょァィゥェォッャュョ")

DEFAULT_FONTS = [
    "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
    "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "C:/Windows/Fonts/YuGothB.ttc",
    "C:/Windows/Fonts/meiryob.ttc",
    "C:/Windows/Fonts/msgothic.ttc",
]


def load_font(path, size):
    for p in [path, *DEFAULT_FONTS]:
        if not p:
            continue
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    raise RuntimeError("日本語フォントが見つかりません。project.yaml の font にフォントファイルのパスを書いてください")


def split_columns(text, max_len):
    """縦書きの行（列）に分ける。改行は列の区切り。行頭禁則を簡易的に処理する。"""
    cols = []
    for para in text.translate(HALF_TO_FULL).split("\n"):
        while len(para) > max_len:
            cut = max_len
            while cut < len(para) and para[cut] in NO_COLUMN_START and cut < max_len + 2:
                cut += 1  # 句読点や閉じ括弧はぶら下げる
            cols.append(para[:cut])
            para = para[cut:]
        if para:
            cols.append(para)
    return cols or [""]


class VerticalText:
    def __init__(self, text, font, max_len):
        self.font = font
        self.size = font.size
        self.adv = round(self.size * 1.04)
        self.col_w = round(self.size * 1.35)
        self.cols = split_columns(text, max_len)

    @property
    def width(self):
        return self.col_w * (len(self.cols) - 1) + self.size

    @property
    def height(self):
        return self.adv * max(len(c) for c in self.cols)

    def draw(self, img, x, y, fill=0, stroke=0, stroke_fill=255):
        """(x, y) はテキスト範囲の左上。列は右から左へ。"""
        d = ImageDraw.Draw(img)
        fs = self.size
        for ci, col in enumerate(self.cols):
            cx = x + self.width - fs - ci * self.col_w
            for i, ch in enumerate(col):
                cy = y + i * self.adv
                if ch in ROTATE:
                    pad = stroke + 2
                    tile = Image.new("L", (fs + pad * 2, fs + pad * 2), 0)
                    ImageDraw.Draw(tile).text((pad + fs / 2, pad + fs / 2), ch, font=self.font, fill=255,
                                              anchor="mm", stroke_width=stroke)
                    tile = tile.rotate(-90)
                    colour = Image.new(img.mode, tile.size, fill)
                    if stroke:
                        outline = Image.new("L", tile.size, 0)
                        ImageDraw.Draw(outline).text((pad + fs / 2, pad + fs / 2), ch, font=self.font, fill=255,
                                                     anchor="mm", stroke_width=stroke)
                        img.paste(Image.new(img.mode, tile.size, stroke_fill), (cx - pad, cy - pad),
                                  outline.rotate(-90))
                        inner = Image.new("L", tile.size, 0)
                        ImageDraw.Draw(inner).text((pad + fs / 2, pad + fs / 2), ch, font=self.font, fill=255,
                                                   anchor="mm")
                        tile = inner.rotate(-90)
                    img.paste(colour, (cx - pad, cy - pad), tile)
                    continue
                dx = dy = 0
                if ch in SMALL:
                    dx, dy = fs * 0.1, -fs * 0.1
                elif ch in PUNCT:
                    dx, dy = fs * 0.55, -fs * 0.55
                d.text((cx + fs / 2 + dx, cy + fs / 2 + dy), ch, font=self.font, fill=fill, anchor="mm",
                       stroke_width=stroke, stroke_fill=stroke_fill)


# --- 枠の形 ---------------------------------------------------------------

def _ellipse_point(cx, cy, rx, ry, tx, ty):
    ang = math.atan2((ty - cy) / ry, (tx - cx) / rx)
    return cx + rx * math.cos(ang), cy + ry * math.sin(ang), ang


def draw_speech(d, box, tail_to, shout=False, line=3):
    x0, y0, x1, y1 = box
    cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
    if shout:
        pts = []
        n = 28
        for i in range(n):
            a = 2 * math.pi * i / n
            k = 1.18 if i % 2 == 0 else 0.92
            pts.append((cx + rx * k * math.cos(a), cy + ry * k * math.sin(a)))
        d.polygon(pts, fill="white", outline="black", width=line)
    else:
        d.ellipse(box, fill="white", outline="black", width=line)
    if tail_to:
        tx, ty = tail_to
        ex, ey, ang = _ellipse_point(cx, cy, rx, ry, tx, ty)
        # しっぽの長さは楕円の外に最大で半径の0.9倍まで
        dist = math.hypot(tx - ex, ty - ey)
        length = min(dist, max(rx, ry) * 0.9)
        if length > 4:
            ux, uy = (tx - ex) / dist, (ty - ey) / dist
            tip = (ex + ux * length, ey + uy * length)
            spread = 0.22
            b1 = (cx + rx * 0.92 * math.cos(ang - spread), cy + ry * 0.92 * math.sin(ang - spread))
            b2 = (cx + rx * 0.92 * math.cos(ang + spread), cy + ry * 0.92 * math.sin(ang + spread))
            d.polygon([b1, tip, b2], fill="white")
            d.line([b1, tip, b2], fill="black", width=line, joint="curve")


def draw_cloud(d, box, tail_to, line=2):
    x0, y0, x1, y1 = box
    cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
    bumps = 14
    r = min(rx, ry) * 0.32
    for i in range(bumps):
        a = 2 * math.pi * i / bumps
        bx, by = cx + rx * 0.9 * math.cos(a), cy + ry * 0.9 * math.sin(a)
        d.ellipse((bx - r, by - r, bx + r, by + r), fill="white", outline="black", width=line)
    d.ellipse((x0 + r * 0.4, y0 + r * 0.4, x1 - r * 0.4, y1 - r * 0.4), fill="white")
    if tail_to:
        tx, ty = tail_to
        ex, ey, _ = _ellipse_point(cx, cy, rx, ry, tx, ty)
        for k, rr in ((0.35, r * 0.45), (0.65, r * 0.28)):
            bx, by = ex + (tx - ex) * k * 0.6, ey + (ty - ey) * k * 0.6
            d.ellipse((bx - rr, by - rr, bx + rr, by + rr), fill="white", outline="black", width=line)


def draw_box(d, box, line=2):
    d.rectangle(box, fill="white", outline="black", width=line)
