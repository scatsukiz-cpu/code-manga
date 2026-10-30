"""コマ画像をページに組み、写植を載せる。"""

from PIL import Image, ImageDraw, ImageOps

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


def compose_page(project, ep, page):
    cfg = project.config
    canvas = Image.new("RGB", (layouts.PAGE_W, layouts.PAGE_H), "white")
    rects = layouts.panel_rects(page["layout"])
    panels = page["panels"]

    for rect, panel in zip(rects, panels):
        r = layouts.bleed_rect(rect) if panel.get("bleed") else rect
        path = project.panel_path(ep, page["page"], panel["id"])
        if path.exists():
            img = Image.open(path).convert("RGB")
            if cfg.get("grayscale", True):
                img = ImageOps.grayscale(img).convert("RGB")
            canvas.paste(fit_cover(img, r.w, r.h, tuple(panel.get("focus_point", (0.5, 0.4)))), (r.x, r.y))
        else:
            d = ImageDraw.Draw(canvas)
            d.rectangle(r.box(), fill=(235, 235, 235))
            d.text((r.x + 20, r.y + 20), f"未生成 p{page['page']} k{panel['id']}",
                   font=lettering.load_font(cfg.get("font"), 28), fill=(120, 120, 120))
        if not panel.get("borderless"):
            ImageDraw.Draw(canvas).rectangle(r.box(), outline="black", width=BORDER)

    for rect, panel in zip(rects, panels):
        letter_panel(canvas, project, rect, panel)

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
