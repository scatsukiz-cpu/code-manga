# 1話分のネーム（names/epNN.py の EP）から、コマの生成とページの組みまでを行う
import os, sys, math, json, random, shutil
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chars import C
from gen import gen

ROOT = os.path.dirname(os.path.abspath(__file__))
PW, PH = 1200, 1600
M, G = 40, 22               # 外枠の余白、コマ間
TAIL = 40                   # 吹き出しの尻尾の長さ（縁から）
SERIF = f"{ROOT}/NotoSerifJP.ttf"
GOTH = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"
EMF = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
STATE = f"{ROOT}/state.json"

STYLE = ("Black and white Japanese manga panel, clean professional josei manga ink line art, screentone shading, "
         "dramatic cinematic composition. Single panel illustration, no panel borders. ")
NOTEXT = " Absolutely no text, no letters, no speech bubbles, no sound effects in the image."
AREA = {"tr": "top-right", "tl": "top-left", "tc": "top", "br": "bottom-right", "bl": "bottom-left",
        "r": "right side", "l": "left side", "bc": "bottom"}

def serif(size, w="SemiBold"):
    f = ImageFont.truetype(SERIF, size); f.set_variation_by_name(w); return f

# ---------------- レイアウト ----------------
def layout(rows, tilts, bleed=()):
    """rows: [(高さ比, 列数) ...] 上から。tilts: {"r": [段の境目ごとの傾き px], "c": [段ごとの縦の境目の傾き px]}
    戻り値: 読む順（上の段から、各段は右から左）のポリゴン"""
    x0, x1, y0, y1 = M, PW - M, M, PH - M
    tot = sum(r[0] for r in rows); H = y1 - y0
    bounds = []; acc = y0
    for i, r in enumerate(rows[:-1]):
        acc += H * r[0] / tot; bounds.append(acc)
    rt = tilts.get("r", [0] * len(bounds)); ct = tilts.get("c", [0] * len(rows))
    def rowline(i, off):  # i番目の境目: y = yb + t*(x-PW/2)/PW + off
        yb = bounds[i]; t = rt[i]
        return lambda x: yb + t * (x - PW / 2) / (x1 - x0) + off
    polys = []
    for ri, (h, n) in enumerate(rows):
        top = (lambda x: y0) if ri == 0 else rowline(ri - 1, G / 2)
        bot = (lambda x: y1) if ri == len(rows) - 1 else rowline(ri, -G / 2)
        if ri == 0 and "top" in bleed: top = lambda x: 0
        if ri == len(rows) - 1 and "bottom" in bleed: bot = lambda x: PH
        lx0 = 0 if "sides" in bleed else x0; lx1 = PW if "sides" in bleed else x1
        cw = (lx1 - lx0) / n; c = ct[ri] if ri < len(ct) else 0
        cols = []
        for k in range(n):  # 左から
            def vl(xb, off):
                ymid = (top(PW / 2) + bot(PW / 2)) / 2; hh = bot(PW / 2) - top(PW / 2)
                return lambda y: xb + c * (y - ymid) / max(hh, 1) * -1 + off
            L = (lambda y: lx0) if k == 0 else vl(lx0 + cw * k, G / 2)
            R = (lambda y: lx1) if k == n - 1 else vl(lx0 + cw * (k + 1), -G / 2)
            def corner(vf, hf):
                y = hf(vf(0))
                for _ in range(4): y = hf(vf(y))
                return (round(vf(y)), round(y))
            cols.append([corner(L, top), corner(R, top), corner(R, bot), corner(L, bot)])
        polys += cols[::-1]
    return polys

def auto_tilts(rows, seed, flat=False, strong=False):
    rnd = random.Random(seed)
    if flat: return {"r": [0] * (len(rows) - 1), "c": [0] * len(rows)}
    amp = 110 if strong else 60
    r = [rnd.choice([-1, 1]) * rnd.randint(amp // 2, amp) if rnd.random() < .8 else 0 for _ in rows[:-1]]
    if r and all(v == 0 for v in r): r[0] = amp
    c = [rnd.choice([-1, 1]) * rnd.randint(30, 70) if n > 1 else 0 for (h, n) in rows]
    return {"r": r, "c": c}

def bbox(poly):
    xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
    return min(xs), min(ys), max(xs), max(ys)

def size_for(poly):
    x0, y0, x1, y1 = bbox(poly); a = (x1 - x0) / max(1, (y1 - y0))
    return "1536x1024" if a > 1.25 else ("1024x1536" if a < 0.8 else "1024x1024")

# ---------------- 縦書き ----------------
ROT = "ー～〜…‥()（）「」『』-"
SMALL = "ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮ"
PUNCT = "、。，．"
def wrap(text, n=8):
    if "\n" in text: return text
    out = []; cur = ""
    for ch in text:
        cur += ch
        if len(cur) >= n and ch not in "、。…ー" : out.append(cur); cur = ""
        elif len(cur) >= n + 1: out.append(cur); cur = ""
    if cur:
        if len(cur) <= 2 and out and cur.strip("、。…！？!?") == "": out[-1] += cur
        else: out.append(cur)
    return "\n".join(out)

def vtext(text, size, font=None, spacing=1.06, colgap=1.32, fill="black", stroke=0, sfill="white"):
    font = font or serif(size)
    cols = text.split("\n"); n = max(len(c) for c in cols)
    cw = int(size * colgap); MM = size * 2
    W = cw * (len(cols) - 1) + size + MM * 2; H = int(size * spacing * n) + MM * 2
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for ci, col in enumerate(cols):
        x = W - MM - size - ci * cw
        i = 0
        while i < len(col):
            ch = col[i]
            # 「！？」「!!」などの縦中横
            if ch in "!?！？" and i + 1 < len(col) and col[i + 1] in "!?！？":
                pair = col[i:i + 2].replace("！", "!").replace("？", "?")
                g = Image.new("RGBA", (size * 2, size * 2), (0, 0, 0, 0)); gd = ImageDraw.Draw(g)
                gd.text((size, size), pair, font=serif(int(size * .8)), fill=fill, anchor="mm", stroke_width=stroke, stroke_fill=sfill)
                y = MM + int(i * size * spacing); im.alpha_composite(g, (x - size // 2, y - size // 2)); i += 2; continue
            y = MM + int(i * size * spacing)
            g = Image.new("RGBA", (size * 2, size * 2), (0, 0, 0, 0)); gd = ImageDraw.Draw(g)
            if ch in "―—":
                ext = int(size * spacing / 2) + 1
                gd.line([(size, size - ext), (size, size + ext)], fill=fill, width=max(2, size // 14))
            else:
                gd.text((size, size), ch, font=font, fill=fill, stroke_width=stroke, stroke_fill=sfill, anchor="mm")
                if ch in ROT: g = g.rotate(-90, center=(size, size))
            ox = oy = 0
            if ch in PUNCT: ox += int(size * .55); oy -= int(size * .55)
            if ch in SMALL: ox += int(size * .1); oy -= int(size * .1)
            im.alpha_composite(g, (x + ox - size // 2, y + oy - size // 2)); i += 1
    return im.crop(im.getbbox())

# ---------------- 吹き出し ----------------
DIRS = {"l": (-1, .25), "r": (1, .25), "b": (0, 1), "t": (0, -1), "bl": (-.7, .7), "br": (.7, .7),
        "tl": (-.7, -.7), "tr": (.7, -.7)}
def balloon_shape(kind, cx, cy, t, who, md):
    if kind == "box":
        md.rectangle((cx - t.width / 2 - 18, cy - t.height / 2 - 16, cx + t.width / 2 + 18, cy + t.height / 2 + 16), fill=255); return 3
    if kind == "black":
        md.rectangle((cx - t.width / 2 - 18, cy - t.height / 2 - 16, cx + t.width / 2 + 18, cy + t.height / 2 + 16), fill=255); return 0
    rx = t.width * .5 * 1.38 + 24; ry = t.height * .5 * 1.12 + 28
    if kind in ("shout", "phone"):
        pts = []; N = 44 if kind == "shout" else 40
        for i in range(N):
            a = 2 * math.pi * i / N; r = (1.18 if i % 2 == 0 else .92) if kind == "shout" else (1.0 if i % 2 == 0 else .9)
            pts.append((cx + rx * r * math.cos(a), cy + ry * r * math.sin(a)))
        md.polygon(pts, fill=255)
    else:
        md.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=255)
    if who and who in DIRS and kind in ("oval", "shout"):
        dx, dy = DIRS[who]; a = math.atan2(dy, dx)
        def edge(t_): return 1 / math.sqrt((math.cos(t_) / rx) ** 2 + (math.sin(t_) / ry) ** 2)
        k = edge(a); tip = (cx + (k + TAIL) * math.cos(a), cy + (k + TAIL) * math.sin(a))
        b1 = (cx + edge(a + .22) * .85 * math.cos(a + .22), cy + edge(a + .22) * .85 * math.sin(a + .22))
        b2 = (cx + edge(a - .22) * .85 * math.cos(a - .22), cy + edge(a - .22) * .85 * math.sin(a - .22))
        md.polygon([b1, tip, b2], fill=255)
    if who and kind == "thought":
        dx, dy = DIRS.get(who, (0, 1)); a = math.atan2(dy, dx)
        def edge(t_): return 1 / math.sqrt((math.cos(t_) / rx) ** 2 + (math.sin(t_) / ry) ** 2)
        k = edge(a)
        for j, r in enumerate((10, 7)):
            d = k + 16 + j * 22; md.ellipse((cx + d * math.cos(a) - r, cy + d * math.sin(a) - r, cx + d * math.cos(a) + r, cy + d * math.sin(a) + r), fill=255)
    return 4 if kind in ("oval", "shout", "thought") else 3

def measure(b):
    kind = b.get("k", "oval")
    size = b.get("size", {"box": 30, "black": 30, "phone": 26, "shout": 44}.get(kind, 36))
    font = ImageFont.truetype(GOTH, size) if kind == "shout" else None
    t = vtext(wrap(b["t"], b.get("n", 8)), size, font, fill="white" if kind == "black" else "black")
    if kind in ("box", "black"): w, h = t.width + 36, t.height + 32
    else: w, h = t.width * 1.38 + 48, t.height * 1.12 + 56
    return t, w, h

def place_balloons(page, poly, bl, area):
    if not bl: return
    x0, y0, x1, y1 = bbox(poly); pad = 26
    items = [(b,) + measure(b) for b in bl]
    total = sum(w for _, _, w, _ in items) + 14 * (len(items) - 1)
    if area in ("tl", "bl", "l"): xr = x0 + pad + total
    elif area in ("tc", "bc"): xr = (x0 + x1) / 2 + total / 2
    else: xr = x1 - pad
    xr = min(xr, x1 - pad)
    bottom = area in ("br", "bl", "bc")
    for b, t, w, h in items:  # 右から左へ
        cx = xr - w / 2
        cy = (y1 - pad - h / 2) if bottom else (y0 + pad + h / 2)
        if area in ("r", "l"): cy = (y0 + y1) / 2
        cx = max(x0 + pad + w / 2, cx); cy = max(y0 + pad + h / 2, min(y1 - pad - h / 2, cy))
        cx += b.get("dx", 0); cy += b.get("dy", 0)
        kind = b.get("k", "oval")
        m = Image.new("L", (PW, PH), 0); md = ImageDraw.Draw(m)
        bw = balloon_shape(kind, cx, cy, t, b.get("who"), md)
        if kind == "black":
            page.paste((0, 0, 0, 255), (0, 0), m)
        else:
            if bw: page.paste((0, 0, 0, 255), (0, 0), m.filter(ImageFilter.MaxFilter(bw * 2 + 1)))
            page.paste((255, 255, 255, 255), (0, 0), m)
        page.alpha_composite(t, (int(cx - t.width / 2), int(cy - t.height / 2)))
        xr = cx - w / 2 - 14

def draw_sfx(page, poly, s):
    x0, y0, x1, y1 = bbox(poly)
    size = s.get("size", 90); f = ImageFont.truetype(GOTH, size)
    t = vtext(s["t"], size, f, spacing=.95, stroke=max(5, size // 12), sfill="white")
    if s.get("rot"): t = t.rotate(s["rot"], expand=True)
    at = s.get("at", "l")
    x = {"l": x0 + 30, "r": x1 - 30 - t.width, "c": (x0 + x1 - t.width) / 2}[at[0] if at[0] in "lrc" else "c"]
    y = y0 + 30 if "b" not in at else y1 - 30 - t.height
    page.alpha_composite(t, (int(x), int(y)))

# ---------------- コマ ----------------
def cover(img, w, h, fx=.5, fy=.5):
    s = max(w / img.width, h / img.height); im = img.resize((round(img.width * s) + 1, round(img.height * s) + 1), Image.LANCZOS)
    x = int((im.width - w) * fx); y = int((im.height - h) * fy); return im.crop((x, y, x + w, y + h))

def draw_panel(page, poly, img, frame="line", fx=.5, fy=.5):
    x0, y0, x1, y1 = bbox(poly); w, h = x1 - x0, y1 - y0
    tile = cover(img, w, h, fx, fy) if img else Image.new("RGB", (w, h), "black")
    m = Image.new("L", (PW, PH), 0); ImageDraw.Draw(m).polygon(poly, fill=255)
    if frame == "fade":
        m = Image.new("L", (PW, PH), 0)
        ImageDraw.Draw(m).polygon([(x0 + 40, y0 + 40), (x1 - 40, y0 + 40), (x1 - 40, y1 - 40), (x0 + 40, y1 - 40)], fill=255)
        m = m.filter(ImageFilter.GaussianBlur(28))
    layer = Image.new("RGBA", (PW, PH), "white"); layer.paste(tile, (x0, y0))
    page.paste(layer, (0, 0), m)
    if frame == "line": ImageDraw.Draw(page).line(poly + [poly[0]], fill="black", width=5, joint="curve")

def panel_prompt(p):
    chars = p.get("c", [])
    s = STYLE
    if p.get("flash"): s += "Flashback scene: soft, slightly faded, dreamy tone. "
    if chars:
        s += "Characters (match the attached reference sheets exactly): " + "; ".join(f"{C[k][0]} = {C[k][1]}" for k in chars) + ". "
    s += "Scene: " + p["p"] + " "
    a = p.get("a", "tr")
    if p.get("b") and a:
        s += f" Keep the {AREA[a]} area of the frame as simple empty background (no faces, no important details) to leave room for speech balloons."
    s += "" if p.get("text_ok") else NOTEXT
    return s

def state():
    try: return json.load(open(STATE))
    except Exception: return {"flat_run": 0, "done": []}

def build(ep_mod, only_compose=False, workers=6):
    EP = ep_mod.EP; n = EP["n"]; tag = f"ep{n:02d}"
    pdir = f"{ROOT}/panels/{tag}"; odir = f"{ROOT}/out/{tag}"
    os.makedirs(pdir, exist_ok=True); os.makedirs(odir, exist_ok=True)
    st = state()
    # レイアウト決定（水平だけのページが3ページ続かないように）
    plan = []; flat_run = st.get("flat_run", 0)
    for pi, pg in enumerate(EP["pages"]):
        rows = pg["rows"]
        flat = pg.get("flat", False)
        if flat and flat_run >= 2: flat = False
        tl = pg.get("tilts") or auto_tilts(rows, n * 10 + pi, flat, pg.get("strong", False))
        is_flat = all(v == 0 for v in tl.get("r", [])) and not any(tl.get("c", []))
        flat_run = flat_run + 1 if is_flat else 0
        polys = layout(rows, tl, tuple(pg.get("bleed", ())))
        assert len(polys) == len(pg["panels"]), f"{tag} page{pi+1}: {len(polys)} slots vs {len(pg['panels'])} panels"
        plan.append(polys)
    # 生成
    jobs = []
    for pi, pg in enumerate(EP["pages"]):
        for ki, p in enumerate(pg["panels"]):
            pid = f"p{pi+1}_{ki+1}"; out = f"{pdir}/{pid}.png"
            if p.get("reuse"):
                rt, rp = p["reuse"].split(":"); src = f"{ROOT}/panels/{rt}/{rp}.png"
                if not os.path.exists(out) and os.path.exists(src): shutil.copy(src, out)
                continue
            if p.get("blank") or os.path.exists(out) or only_compose: continue
            refs = [f"{ROOT}/chars/{k}.png" for k in p.get("c", [])][:4]
            jobs.append((out, p.get("size") or size_for(plan[pi][ki]), panel_prompt(p), refs))
    def run(j): return j[0], gen(*j)
    log = []
    with ThreadPoolExecutor(workers) as ex:
        for out, r in ex.map(run, jobs):
            if r != "ok": log.append(f"{os.path.basename(out)} {r}")
    # 組み
    for pi, pg in enumerate(EP["pages"]):
        page = Image.new("RGBA", (PW, PH), "white")
        for ki, p in enumerate(pg["panels"]):
            out = f"{pdir}/p{pi+1}_{ki+1}.png"
            img = Image.open(out).convert("RGB") if os.path.exists(out) and not p.get("blank") else None
            if img is None and not p.get("blank"): img = Image.new("RGB", (100, 100), (90, 90, 90))
            draw_panel(page, plan[pi][ki], img, p.get("frame", "line"), p.get("fx", .5), p.get("fy", .5))
        for ki, p in enumerate(pg["panels"]):
            place_balloons(page, plan[pi][ki], p.get("b", []), p.get("a", "tr"))
            for s in p.get("sfx", []): draw_sfx(page, plan[pi][ki], s)
        d = ImageDraw.Draw(page)
        if pi == 0:
            f = serif(30, "Bold"); lab = f"第{n}話"
            d.rectangle((PW - M - 150, 4, PW - M, 36), fill="black"); d.text((PW - M - 75, 20), lab, font=f, fill="white", anchor="mm")
        if pi == len(EP["pages"]) - 1 and n < 60:
            d.text((M + 4, PH - 20), "つづく", font=serif(24), fill="black", anchor="lm")
        if n == 60 and pi == len(EP["pages"]) - 1:
            d.text((M + 4, PH - 20), "完", font=serif(28, "Bold"), fill="black", anchor="lm")
        page.convert("RGB").save(f"{odir}/page{pi+1}.png")
    open(f"{odir}/post.txt", "w").write(f"『本物なのに、いらない娘』第{n}話\n{EP['hook']}\n\n#漫画が読めるハッシュタグ #真偽千金\n")
    if not only_compose:
        st["flat_run"] = flat_run
        if n not in st["done"]: st["done"].append(n)
        json.dump(st, open(STATE, "w"))
    return log

if __name__ == "__main__":
    import importlib
    only = "--compose" in sys.argv
    for a in sys.argv[1:]:
        if a.startswith("--"): continue
        mod = importlib.import_module(f"names.ep{int(a):02d}")
        importlib.reload(mod)
        print(f"ep{int(a):02d}", build(mod, only))
