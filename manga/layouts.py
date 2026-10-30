"""ページのコマ割り。

日本式（右綴じ）なので、段は上から下、段の中のコマは右から左の順に番号が付く。
コマ枠の縦横比をここで先に決め、作画はその比率で生成する（改善案7）。

コマは四角形（4つの角）で表す。ページの col_tilt / row_tilt で境目を斜めにすると、
隣り合うコマの辺が一緒に傾くので、間（ガター）の幅は保たれる。
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

EDGES = ("top", "right", "bottom", "left")


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


@dataclass
class Shape:
    """コマの形。points は 左上・右上・右下・左下 の順。"""

    points: list

    @property
    def bbox(self) -> Rect:
        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        x0, y0 = round(min(xs)), round(min(ys))
        return Rect(x0, y0, round(max(xs)) - x0, round(max(ys)) - y0)

    @property
    def inner(self) -> Rect:
        """形の内側に収まる長方形。写植の配置に使う。"""
        tl, tr, br, bl = self.points
        x0, x1 = max(tl[0], bl[0]), min(tr[0], br[0])
        y0, y1 = max(tl[1], tr[1]), min(bl[1], br[1])
        return Rect(round(x0), round(y0), round(x1 - x0), round(y1 - y0))

    @property
    def aspect(self) -> float:
        return self.bbox.aspect

    def edge(self, name):
        i = EDGES.index(name)
        return self.points[i], self.points[(i + 1) % 4]


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


def _tiers(layout):
    if isinstance(layout, dict):
        return layout["tiers"]
    if str(layout) in TEMPLATES:
        return TEMPLATES[str(layout)]
    raise ValueError(f"不明なコマ割りテンプレート: {layout}（使えるもの: {', '.join(TEMPLATES)}）")


def _per(value, i):
    """数値ならすべてに、リストなら i 番目を使う。"""
    if isinstance(value, list):
        return value[i] if i < len(value) and value[i] is not None else 0
    return value or 0


def panel_rects(layout) -> list[Rect]:
    """傾きを入れる前の、長方形のコマ枠を読み順で返す。"""
    tiers = _tiers(layout)
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


def page_shapes(page) -> list[Shape]:
    """ページのコマの形を読み順で返す。

    col_tilt：段の中の縦の境目の傾き（px）。正なら上が左へ、下が右へずれる。数値か段ごとのリスト。
    row_tilt：段と段の境目の傾き（px）。正なら右側が下がる。数値か境目ごとのリスト。
    コマの shape: {top: dy, bottom: dy, left: dx, right: dx} で、外枠の辺も個別に傾けられる。
    """
    layout = page.get("layout")
    tiers = _tiers(layout)
    rects = panel_rects(layout)
    col_tilt, row_tilt = page.get("col_tilt", 0), page.get("row_tilt", 0)
    inner_w = PAGE_W - MARGIN_X * 2

    shapes, tier_of, idx = [], [], 0
    for ti, tier in enumerate(tiers):
        n = len(tier["cols"])
        t = _per(col_tilt, ti)
        for ci in range(n):
            r = rects[idx]
            tl, tr = [r.x, r.y], [r.x + r.w, r.y]
            br, bl = [r.x + r.w, r.y + r.h], [r.x, r.y + r.h]
            if ci > 0:  # 右隣との境目＝このコマの右辺
                tr[0] -= t / 2
                br[0] += t / 2
            if ci < n - 1:  # 左隣との境目＝このコマの左辺
                tl[0] -= t / 2
                bl[0] += t / 2
            shapes.append(Shape([tl, tr, br, bl]))
            tier_of.append(ti)
            idx += 1

    def drop(x, t):  # 段の境目の、x 位置でのずれ
        return t * ((x - MARGIN_X) / inner_w - 0.5)

    for shape, ti in zip(shapes, tier_of):
        tl, tr, br, bl = shape.points
        below = _per(row_tilt, ti) if ti < len(tiers) - 1 else 0
        above = _per(row_tilt, ti - 1) if ti > 0 else 0
        for p in (bl, br):
            p[1] += drop(p[0], below)
        for p in (tl, tr):
            p[1] += drop(p[0], above)
    return shapes


def apply_shape_overrides(shape: Shape, panel) -> Shape:
    """コマ単位の shape 指定で、辺の片側だけを動かして傾ける。"""
    spec = panel.get("shape") or {}
    tl, tr, br, bl = [list(p) for p in shape.points]
    if spec.get("top"):  # 正なら右上が下がる
        tr[1] += spec["top"]
    if spec.get("bottom"):  # 正なら右下が下がる
        br[1] += spec["bottom"]
    if spec.get("right"):  # 正なら右下が左へ
        br[0] -= spec["right"]
    if spec.get("left"):  # 正なら左下が右へ
        bl[0] += spec["left"]
    return Shape([tl, tr, br, bl])


def bleed_shape(shape: Shape) -> Shape:
    """タチキリ：ページの外枠に接している角を、紙の端まで伸ばす。"""
    pts = []
    for x, y in shape.points:
        if x <= MARGIN_X + 1:
            x = 0
        elif x >= PAGE_W - MARGIN_X - 1:
            x = PAGE_W
        if y <= MARGIN_TOP + 1:
            y = 0
        elif y >= PAGE_H - MARGIN_BOTTOM - 1:
            y = PAGE_H
        pts.append([x, y])
    return Shape(pts)


def panel_shapes(page) -> list[Shape]:
    """傾き・個別の形・タチキリをすべて反映したコマの形。"""
    out = []
    for shape, panel in zip(page_shapes(page), page.get("panels") or []):
        shape = apply_shape_overrides(shape, panel)
        if panel.get("bleed"):
            shape = bleed_shape(shape)
        out.append(shape)
    return out
