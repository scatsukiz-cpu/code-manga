"""コマ画像をページに組み、写植を載せる。"""

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

from . import layouts, lettering

BORDER = 4
PAD = 14  # コマ枠の内側の余白
GAP = 10  # 吹き出し同士の間


def fit_cover(img, w, h, focus=(0.5, 0.4)):
    """コマ枠を必ず絵で埋める（改善案7）。はみ出た分は focus を中心に切り抜く。"""
    scale = max(w / img.width, h / img.height)
    img = img.resize((max(w, round(img.width * scale)), max(h, round(img.height * scale))), Image.LANCZOS)
    fx, fy = focus
    left = min(max(0, round(img.width * fx - w / 2)), img.width - w)
    top = min(max(0, round(img.height * fy - h / 2)), img.height - h)
    return img.crop((left, top, left + w, top + h))


FRAMES = ("full", "none", "fade")
SIDES = layouts.EDGES


def frame_mode(panel):
    """枠の種類：full（実線）/ none（枠なし）/ fade（枠なしで周りをぼかす）。"""
    if panel.get("borderless"):
        return "none"
    return panel.get("frame", "full")


def break_out(panel):
    """枠破り（人物などが枠からはみ出す）の指定。{sides: [top, ...], margin: px}"""
    b = panel.get("break_out")
    if not b:
        return None
    if b is True:
        b = {}
    return {"sides": b.get("sides", ["top"]), "margin": b.get("margin", 90)}


def image_box(shape, panel) -> layouts.Rect:
    """コマ画像を置く範囲。枠破りのときは、はみ出す側へ広げる。"""
    r = shape.bbox
    b = break_out(panel)
    if not b:
        return r
    m = b["margin"]
    x0, y0, x1, y1 = r.box()
    if "top" in b["sides"]:
        y0 = max(0, y0 - m)
    if "bottom" in b["sides"]:
        y1 = min(layouts.PAGE_H, y1 + m)
    if "left" in b["sides"]:
        x0 = max(0, x0 - m)
    if "right" in b["sides"]:
        x1 = min(layouts.PAGE_W, x1 + m)
    return layouts.Rect(x0, y0, x1 - x0, y1 - y0)


def foreground_mask(path, img):
    """枠破り用の前景（人物）のマスク。img は生成されたままのコマ画像。

    コマ画像と同じ場所に pXX_kYY_mask.png（白＝前景）があればそれを使う。
    なければ rembg（pip install rembg）で背景を抜いて保存する。どちらもなければ None。
    """
    mask_path = path.with_name(path.stem + "_mask.png")
    if mask_path.exists():
        return Image.open(mask_path).convert("L").resize(img.size)
    try:
        from rembg import remove
    except ImportError:
        return None
    mask = remove(img, only_mask=True).convert("L")
    mask.save(mask_path)
    return mask


def _open_ranges(panel):
    """枠の一部を描かない指定。open: [top, {edge: left, from: 0.2, to: 0.6}]"""
    ranges = {}
    for o in panel.get("open") or []:
        if isinstance(o, str):
            ranges.setdefault(o, []).append((0.0, 1.0))
        else:
            ranges.setdefault(o["edge"], []).append((o.get("from", 0.0), o.get("to", 1.0)))
    return ranges


def draw_frame(canvas, shape, panel):
    d = ImageDraw.Draw(canvas)
    opened = _open_ranges(panel)
    if not opened:
        d.polygon([tuple(p) for p in shape.points], outline="black", width=BORDER)
        return
    for name in SIDES:
        (x0, y0), (x1, y1) = shape.edge(name)
        # 辺を 0〜1 で表し、開ける範囲を除いた部分だけ描く
        cuts = sorted(opened.get(name, []))
        segs, t = [], 0.0
        for a, b in cuts:
            if a > t:
                segs.append((t, a))
            t = max(t, b)
        if t < 1.0:
            segs.append((t, 1.0))
        for a, b in segs:
            pa = (x0 + (x1 - x0) * a, y0 + (y1 - y0) * a)
            pb = (x0 + (x1 - x0) * b, y0 + (y1 - y0) * b)
            d.line([pa, pb], fill="black", width=BORDER)
            for q, at_corner in ((pa, a == 0.0), (pb, b == 1.0)):
                if at_corner:  # 角の欠けを埋める
                    r = BORDER / 2
                    d.rectangle((q[0] - r, q[1] - r, q[0] + r, q[1] + r), fill="black")


def compose_page(project, ep, page):
    cfg = project.config
    canvas = Image.new("RGB", (layouts.PAGE_W, layouts.PAGE_H), "white")
    shapes = layouts.panel_shapes(page)
    panels = page["panels"]
    pops = []  # 枠破り：枠線を描いたあとで前景を上に重ねる

    for shape, panel in zip(shapes, panels):
        box = image_box(shape, panel)
        mode = frame_mode(panel)
        mask = Image.new("L", canvas.size, 0)
        ImageDraw.Draw(mask).polygon([tuple(p) for p in shape.points], fill=255)
        if mode == "fade":
            radius = panel.get("fade", 40)
            mask = mask.filter(ImageFilter.GaussianBlur(radius / 2))

        path = project.panel_path(ep, page["page"], panel["id"])
        if path.exists():
            img = Image.open(path).convert("RGB")
            if cfg.get("grayscale", True):
                img = ImageOps.grayscale(img).convert("RGB")
            focus = tuple(panel.get("focus_point", (0.5, 0.4)))
            fg = foreground_mask(path, img) if break_out(panel) else None
            img = fit_cover(img, box.w, box.h, focus)
            layer = Image.new("RGB", canvas.size, "white")
            layer.paste(img, (box.x, box.y))
            canvas.paste(layer, (0, 0), mask)
            if break_out(panel):
                if fg is not None:
                    pops.append((shape, img, fit_cover(fg, box.w, box.h, focus), box, break_out(panel)))
                else:
                    print(f"p{page['page']} k{panel['id']}: 枠破りの前景マスクがありません"
                          f"（{path.stem}_mask.png を置くか、pip install rembg）")
        else:
            gray = Image.new("RGB", canvas.size, (235, 235, 235))
            canvas.paste(gray, (0, 0), mask)
            inner = shape.inner
            ImageDraw.Draw(canvas).text((inner.x + 20, inner.y + 20), f"未生成 p{page['page']} k{panel['id']}",
                                        font=lettering.load_font(cfg.get("font"), 28), fill=(120, 120, 120))
        if mode == "full":
            draw_frame(canvas, shape, panel)

    for shape, img, fg, box, b in pops:
        # 前景を重ねてよいのは、コマの中と、指定した辺の外側だけ
        clip = Image.new("L", canvas.size, 0)
        d = ImageDraw.Draw(clip)
        d.polygon([tuple(p) for p in shape.points], fill=255)
        m = b["margin"]
        for side in b["sides"]:
            (x0, y0), (x1, y1) = shape.edge(side)
            dx, dy = {"top": (0, -m), "bottom": (0, m), "left": (-m, 0), "right": (m, 0)}[side]
            d.polygon([(x0, y0), (x1, y1), (x1 + dx, y1 + dy), (x0 + dx, y0 + dy)], fill=255)
        layer_fg = Image.new("L", canvas.size, 0)
        layer_fg.paste(fg, (box.x, box.y))
        layer = Image.new("RGB", canvas.size, "white")
        layer.paste(img, (box.x, box.y))
        canvas.paste(layer, (0, 0), ImageChops.multiply(layer_fg, clip))

    for shape, panel in zip(shapes, panels):
        letter_panel(canvas, project, shape.inner, panel)

    nombre = lettering.load_font(cfg.get("font"), 22)
    ImageDraw.Draw(canvas).text((layouts.PAGE_W / 2, layouts.PAGE_H - 50), str(page["page"]), font=nombre,
                                fill="black", anchor="mm")
    return canvas


def _speaker_point(rect, panel, speaker):
    """しっぽの向け先。話者がコマにいなければ、コマの外へ向ける（改善案8）。"""
    chars = panel.get("characters") or []
    ids = [c["id"] if isinstance(c, dict) else c for c in chars]
    if speaker in ids:
        c = chars[ids.index(speaker)]
        pos = c.get("position", "center") if isinstance(c, dict) else "center"
        fx = {"right": 0.75, "center": 0.5, "left": 0.25}.get(pos, 0.5)
        return rect.x + rect.w * fx, rect.y + rect.h * 0.62
    side = panel.get("offpanel", "right")
    return {
        "right": (rect.x + rect.w + 60, rect.y + rect.h * 0.4),
        "left": (rect.x - 60, rect.y + rect.h * 0.4),
        "top": (rect.x + rect.w * 0.6, rect.y - 60),
        "bottom": (rect.x + rect.w * 0.5, rect.y + rect.h + 60),
    }[side]


def letter_panel(canvas, project, rect, panel):
    cfg = project.config
    items = panel.get("text") or []
    if not items:
        return
    d = ImageDraw.Draw(canvas)
    base = cfg.get("font_size", 30)
    cursor_x = rect.x + rect.w - PAD
    cursor_y = rect.y + PAD
    row_bottom = cursor_y

    for item in items:
        kind = item.get("type", "speech")
        size = item.get("size", base * (3 if kind == "sfx" else 1))
        font = lettering.load_font(cfg.get("font_bold") if kind == "sfx" else cfg.get("font"), size)
        adv = round(size * 1.04)
        max_len = max(3, min(item.get("max_len", 9), int((rect.h * 0.62 - 2 * PAD) / adv)))
        vt = lettering.VerticalText(item["text"], font, max_len)

        if kind in ("speech", "thought") and not (kind == "thought" and cfg.get("thought_style") == "box"):
            bw, bh = vt.width * 1.45 + 30, vt.height * 1.3 + 30
            bw = max(bw, bh * 0.5)  # 細すぎる楕円は文字が枠にかかる
        elif kind == "sfx":
            bw, bh = vt.width + 10, vt.height + 10
        else:
            bw, bh = vt.width + 26, vt.height + 26

        if "at" in item:  # コマ内の位置を割合で指定した場合（中心）
            fx, fy = item["at"]
            x1 = rect.x + rect.w * fx + bw / 2
            y0 = rect.y + rect.h * fy - bh / 2
        else:
            if cursor_x - bw < rect.x + PAD and cursor_x < rect.x + rect.w - PAD:
                cursor_x = rect.x + rect.w - PAD  # 左に入らなければ次の段へ
                cursor_y = row_bottom + GAP
            x1, y0 = cursor_x, cursor_y
        x0 = max(rect.x + PAD, x1 - bw)
        x1 = x0 + bw
        y0 = min(max(rect.y + PAD, y0), rect.y + rect.h - PAD - bh)
        box = (x0, y0, x1, y0 + bh)

        if kind == "speech":
            lettering.draw_speech(d, box, _speaker_point(rect, panel, item.get("speaker")),
                                  shout=item.get("style") == "shout")
        elif kind == "thought":
            if cfg.get("thought_style") == "box":
                lettering.draw_box(d, box)
            else:
                lettering.draw_cloud(d, box, _speaker_point(rect, panel, item.get("speaker")))
        elif kind == "narration":
            lettering.draw_box(d, box)

        tx = round((x0 + x1) / 2 - vt.width / 2)
        ty = round((box[1] + box[3]) / 2 - vt.height / 2)
        if kind == "sfx":
            vt.draw(canvas, tx, ty, fill=(0, 0, 0), stroke=max(3, size // 10), stroke_fill=(255, 255, 255))
        else:
            vt.draw(canvas, tx, ty, fill=(0, 0, 0))

        if "at" not in item:
            cursor_x = x0 - GAP
            row_bottom = max(row_bottom, box[3])
