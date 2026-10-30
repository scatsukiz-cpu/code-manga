# 漫画のコマから縦動画（モーションコミック）を作る
# 画面中央にコマ（ゆっくりズーム・パン）、上下の暗い帯にナレーションとセリフを縦書きで出す
import sys, math, subprocess, random
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import engine as E

W, H, FPS = 1080, 1920, 30
P = f"{ROOT}/panels/ep01/"
OUT = f"{ROOT}/video/ep01_motion.mp4"

def ease(t): return t * t * (3 - 2 * t)

# カット：画像、秒数、ズーム（開始, 終了）、注目点の移動（開始, 終了）、文字、効果
CUTS = [
 {"title": True, "dur": 2.8},
 {"img": "p1_1", "dur": 4.5, "z": (1.0, 1.18), "c": ((.5, .5), (.3, .55)),
  "text": [(0.4, "narr", "雪の朝――"), (1.8, "narr", "三年ぶりの、\n外の世界")]},
 {"img": "p1_2", "dur": 3.0, "z": (1.05, 1.25), "c": ((.5, .45), (.55, .4)),
  "text": [(0.6, "thought", "……")]},
 {"img": "p1_3", "dur": 3.0, "z": (1.0, 1.1), "c": ((.5, .6), (.5, .5)),
  "text": [(0.4, "narr", "迎えは、\n誰もいなかった")]},
 {"img": "p2_1", "dur": 3.2, "z": (1.15, 1.0), "c": ((.6, .5), (.5, .5)),
  "text": [(0.4, "narr", "家族には、\n知らせが\nいっていたはず")]},
 {"img": "p2_2", "dur": 2.8, "z": (1.0, 1.2), "c": ((.5, .5), (.55, .55)),
  "text": [(0.5, "thought", "おばあちゃん……")]},
 {"img": "p2_3", "dur": 3.8, "z": (1.0, 1.1), "c": ((.5, .5), (.5, .45)), "flash": True,
  "text": [(0.5, "speech", "つらい時は、\nこれを握るんだよ")]},
 {"img": "p2_4", "dur": 2.4, "z": (1.0, 1.35), "c": ((.5, .5), (.6, .55))},
 {"img": "p3_1", "dur": 1.8, "z": (1.2, 1.0), "c": ((.5, .5), (.5, .5)), "shake": True, "white": True,
  "sfx": "バシャッ"},
 {"img": "p3_2", "dur": 2.6, "z": (1.0, 1.08), "c": ((.5, .4), (.5, .45))},
 {"img": "p3_3", "dur": 3.2, "z": (1.0, 1.15), "c": ((.45, .5), (.4, .45)),
  "text": [(0.8, "speech", "……止めろ")]},
 {"img": "p3_4", "dur": 2.4, "z": (1.15, 1.0), "c": ((.6, .55), (.5, .5))},
 {"img": "p4_1", "dur": 3.4, "z": (1.0, 1.12), "c": ((.5, .5), (.4, .5)),
  "text": [(0.4, "speech", "社長？"), (1.7, "speech", "……いや")]},
 {"img": "p4_2", "dur": 5.6, "z": (1.0, 1.3), "c": ((.5, .5), (.5, .4)),
  "text": [(0.8, "black", "三年前――"), (2.4, "black", "私は、\n妹の罪を\nかぶった")]},
 {"end": True, "dur": 2.2},
]

BOX_Y, BOX_H = 470, 980   # コマを置く帯

def bg_from(img):
    b = img.resize((W, H)).filter(ImageFilter.GaussianBlur(40))
    return ImageEnhance.Brightness(b).enhance(.25).convert("RGBA")

def panel_frame(img, z, c):
    # コマの帯（1080×800）に、ズームと注目点を反映して切り出す
    s = max(W / img.width, BOX_H / img.height) * z
    cw, ch = W / s, BOX_H / s
    cx = min(max(c[0] * img.width, cw / 2), img.width - cw / 2)
    cy = min(max(c[1] * img.height, ch / 2), img.height - ch / 2)
    return img.crop((int(cx - cw / 2), int(cy - ch / 2), int(cx + cw / 2), int(cy + ch / 2))).resize((W, BOX_H), Image.LANCZOS)

def text_layer(kind, text, alpha):
    size = {"narr": 60, "thought": 56, "speech": 58, "black": 62}[kind]
    if kind in ("narr", "black"):
        t = E.vtext(text, size, E.serif(size, "Bold"), fill="white")
    else:
        t = E.vtext(text, size, E.serif(size, "Bold"))
    pad = 34
    if kind == "speech" or kind == "thought":
        rx, ry = t.width * .5 * 1.35 + 30, t.height * .5 * 1.12 + 34
        im = Image.new("RGBA", (int(rx * 2 + 12), int(ry * 2 + 12)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.ellipse((6, 6, rx * 2 + 6, ry * 2 + 6), fill="white", outline="black", width=5)
        im.alpha_composite(t, (int(rx + 6 - t.width / 2), int(ry + 6 - t.height / 2)))
    else:
        im = Image.new("RGBA", (t.width + pad * 2, t.height + pad * 2), (0, 0, 0, 0))
        if kind == "black":
            ImageDraw.Draw(im).rectangle((0, 0, im.width - 1, im.height - 1), fill=(0, 0, 0, 255), outline="white", width=3)
        im.alpha_composite(t, (pad, pad))
    if alpha < 1:
        a = im.split()[3].point(lambda v: int(v * alpha)); im.putalpha(a)
    return im

def place(kind, idx):
    # ナレーションは上の帯の右から、セリフは下の帯の右から並べる
    if kind in ("narr", "black"): return ("top", idx)
    return ("bottom", idx)

def render_cut(cut, prev):
    n = int(cut["dur"] * FPS)
    if cut.get("title") or cut.get("end"):
        for i in range(n):
            f = Image.new("RGBA", (W, H), "black")
            a = min(1, i / 15) if cut.get("title") else min(1, i / 10)
            if cut.get("title"):
                t = text_layer("narr", "本物なのに、\nいらない娘", a)
                t = t.resize((int(t.width * 1.6), int(t.height * 1.6)))
                f.alpha_composite(t, ((W - t.width) // 2 + 60, 380))
                s = text_layer("narr", "第１話", a); f.alpha_composite(s, (200, 900))
            else:
                t = text_layer("narr", "つづく", a); f.alpha_composite(t, ((W - t.width) // 2, (H - t.height) // 2))
            yield f
        return
    img = Image.open(P + cut["img"] + ".png").convert("RGB")
    if cut.get("flash"):
        img = ImageEnhance.Color(img).enhance(0).convert("RGB")
        img = Image.blend(img, Image.new("RGB", img.size, (235, 225, 205)), .18)
    bg = bg_from(img)
    for i in range(n):
        t = i / max(1, n - 1); e = ease(t)
        z = cut["z"][0] + (cut["z"][1] - cut["z"][0]) * e
        (c0, c1) = cut["c"]; c = (c0[0] + (c1[0] - c0[0]) * e, c0[1] + (c1[1] - c0[1]) * e)
        f = bg.copy()
        pf = panel_frame(img, z, c)
        ox = oy = 0
        if cut.get("shake") and i < 12:
            ox, oy = random.randint(-18, 18), random.randint(-18, 18)
        f.paste(pf, (ox, BOX_Y + oy))
        d = ImageDraw.Draw(f)
        d.line((0, BOX_Y, W, BOX_Y), fill="white", width=3); d.line((0, BOX_Y + BOX_H, W, BOX_Y + BOX_H), fill="white", width=3)
        # 文字
        slots = {"top": W - 60, "bottom": W - 60}
        for (st, kind, txt) in cut.get("text", []):
            tt = i / FPS - st
            if tt < 0: continue
            lay = text_layer(kind, txt, min(1, tt / .25))
            band = "top" if kind in ("narr", "black") else "bottom"
            x = slots[band] - lay.width; slots[band] = x - 30
            y = (BOX_Y - lay.height) // 2 if band == "top" else BOX_Y + BOX_H + (H - BOX_Y - BOX_H - lay.height) // 2
            if kind in ("speech", "thought") and tt < .2:
                k = .7 + 1.5 * tt; lay = lay.resize((int(lay.width * k), int(lay.height * k)))
            f.alpha_composite(lay, (max(20, x), max(20, y)))
        if cut.get("sfx"):
            k = min(1.0, .4 + i / 6)
            s = E.vtext(cut["sfx"], int(170 * k), E.ImageFont.truetype(E.GOTH, int(170 * k)), spacing=.95, stroke=12, sfill="white")
            f.alpha_composite(s, (W - s.width - 60, BOX_Y + 40))
        if cut.get("white") and i < 5:
            f = Image.blend(f.convert("RGB"), Image.new("RGB", (W, H), "white"), 1 - i / 5).convert("RGBA")
        # 前のカットからのクロスフェード
        if prev is not None and i < 9 and not cut.get("white"):
            f = Image.blend(prev.convert("RGB"), f.convert("RGB"), (i + 1) / 9).convert("RGBA")
        yield f

def main():
    total = sum(c["dur"] for c in CUTS)
    audio = f"{ROOT}/video/wind.wav"
    # 雪の日の風の音（茶色ノイズを低域だけ残して、ゆっくり揺らす）
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"anoisesrc=color=brown:duration={total}:amplitude=0.5",
                    "-af", "lowpass=f=500,tremolo=f=0.15:d=0.6,volume=0.6,afade=t=in:d=1.5,afade=t=out:st=" + str(total - 2) + ":d=2", audio], check=True)
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-i", audio, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "medium", "-c:a", "aac", "-shortest", OUT], stdin=subprocess.PIPE)
    prev = None
    for cut in CUTS:
        last = None
        for f in render_cut(cut, prev):
            p.stdin.write(f.convert("RGB").tobytes()); last = f
        prev = last
    p.stdin.close(); p.wait()
    print("ok", OUT, round(total, 1), "s")

if __name__ == "__main__":
    main()
