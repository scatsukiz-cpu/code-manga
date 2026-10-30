"""ページのコマ割りテンプレート。

日本式（右綴じ）なので、段は上から下、段の中のコマは右から左の順に番号が付く。
コマ枠の縦横比をここで先に決め、作画はその比率で生成する（改善案7）。
"""

from dataclasses import dataclass

# B5判に近い縦横比（182:257）。単位はピクセル。
PAGE_W = 1200
PAGE_H = 1700
MARGIN_X = 70
MARGIN_TOP = 80
MARGIN_BOTTOM = 110  # ページ下部はノンブルやタイトル表記のために空けておく（改善案8）
GUTTER_X = 22  # 横に並んだコマの間
GUTTER_Y = 34  # 段の間


@dataclass
class Rect:
    x: int
    y: int
    w: int
    h: int

    @property
    def aspect(self) -> float:
        return self.w / self.h

    def box(self):
        return (self.x, self.y, self.x + self.w, self.y + self.h)


# 段（tier）ごとに、高さの比率と、右から順に並べたコマの幅の比率を書く。
TEMPLATES = {
    "1": [{"h": 1, "cols": [1]}],
    "2": [{"h": 1, "cols": [1]}, {"h": 1, "cols": [1]}],
    "2c": [{"h": 1, "cols": [1, 1]}],
    "3": [{"h": 1, "cols": [1]}, {"h": 1, "cols": [1]}, {"h": 1, "cols": [1]}],
    "3a": [{"h": 1, "cols": [1]}, {"h": 1.2, "cols": [1, 1]}],
    "3b": [{"h": 1.6, "cols": [1]}, {"h": 1, "cols": [1, 1.3]}],
    "4": [{"h": 1, "cols": [1]}, {"h": 1, "cols": [1.3, 1]}, {"h": 1.3, "cols": [1]}],
    "4a": [{"h": 1, "cols": [1, 1]}, {"h": 1, "cols": [1, 1]}],
    "4b": [{"h": 1.4, "cols": [1]}, {"h": 1, "cols": [1, 1.2, 1]}],
    "5": [{"h": 1, "cols": [1]}, {"h": 1, "cols": [1, 1.4]}, {"h": 1, "cols": [1.4, 1]}],
    "5a": [{"h": 1.2, "cols": [1.5, 1]}, {"h": 1, "cols": [1]}, {"h": 1, "cols": [1, 1.5]}],
    "6": [{"h": 1, "cols": [1, 1]}, {"h": 1, "cols": [1, 1]}, {"h": 1, "cols": [1, 1]}],
}


def _split(total, weights, gap):
    usable = total - gap * (len(weights) - 1)
    s = sum(weights)
    sizes = [round(usable * w / s) for w in weights]
    sizes[-1] = usable - sum(sizes[:-1])
    return sizes


def panel_rects(layout) -> list[Rect]:
    """テンプレート名、または {"tiers": [...]} からコマ枠を読み順で返す。"""
    if isinstance(layout, dict):
        tiers = layout["tiers"]
    elif str(layout) in TEMPLATES:
        tiers = TEMPLATES[str(layout)]
    else:
        raise ValueError(f"不明なコマ割りテンプレート: {layout}（使えるもの: {', '.join(TEMPLATES)}）")

    inner_w = PAGE_W - MARGIN_X * 2
    inner_h = PAGE_H - MARGIN_TOP - MARGIN_BOTTOM
    heights = _split(inner_h, [t["h"] for t in tiers], GUTTER_Y)

    rects = []
    y = MARGIN_TOP
    for tier, th in zip(tiers, heights):
        widths = _split(inner_w, tier["cols"], GUTTER_X)
        x_right = PAGE_W - MARGIN_X  # 右から並べる
        for cw in widths:
            rects.append(Rect(x_right - cw, y, cw, th))
            x_right -= cw + GUTTER_X
        y += th + GUTTER_Y
    return rects


def bleed_rect(r: Rect) -> Rect:
    """タチキリ：ページの外枠に接している辺を、紙の端まで伸ばす。"""
    x0, y0, x1, y1 = r.box()
    if x0 <= MARGIN_X:
        x0 = 0
    if x1 >= PAGE_W - MARGIN_X:
        x1 = PAGE_W
    if y0 <= MARGIN_TOP:
        y0 = 0
    if y1 >= PAGE_H - MARGIN_BOTTOM:
        y1 = PAGE_H
    return Rect(x0, y0, x1 - x0, y1 - y0)
