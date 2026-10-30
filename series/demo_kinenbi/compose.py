import sys, json
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
PW,PH=1200,1700
SERIF="fonts/NotoSerifJP.ttf"; GOTH="/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"
EMF="/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
def serif(size,w="SemiBold"):
    f=ImageFont.truetype(SERIF,size); f.set_variation_by_name(w); return f

def cover(img,w,h,fx=0.5,fy=0.5):
    s=max(w/img.width,h/img.height); im=img.resize((round(img.width*s)+1,round(img.height*s)+1),Image.LANCZOS)
    x=int((im.width-w)*fx); y=int((im.height-h)*fy); return im.crop((x,y,x+w,y+h))

def draw_panel(page,poly,src,fx=.5,fy=.5,frame="line",bg=None):
    xs=[p[0] for p in poly]; ys=[p[1] for p in poly]
    x0,y0,x1,y1=min(xs),min(ys),max(xs),max(ys); w,h=x1-x0,y1-y0
    if src: tile=cover(Image.open(src).convert("RGB"),w,h,fx,fy)
    else: tile=Image.new("RGB",(w,h),bg or "white")
    m=Image.new("L",(PW,PH),0); ImageDraw.Draw(m).polygon(poly,fill=255)
    if frame=="fade":
        m=Image.new("L",(PW,PH),0); ImageDraw.Draw(m).polygon([(x0+40,y0+40),(x1-40,y0+40),(x1-40,y1-40),(x0+40,y1-40)],fill=255)
        m=m.filter(ImageFilter.GaussianBlur(28))
    layer=Image.new("RGB",(PW,PH),"white"); layer.paste(tile,(x0,y0))
    page.paste(layer,(0,0),m)
    if frame=="line": ImageDraw.Draw(page).line(poly+[poly[0]],fill="black",width=5,joint="curve")

# ---- vertical text ----
ROT="ー～〜…―—‥()（）「」『』"
SMALL="ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮ"
PUNCT="、。，．"
def vtext_img(text,size,font=None,spacing=1.08,colgap=1.35,fill="black",stroke=0,sfill="white"):
    font=font or serif(size)
    cols=text.split("\n"); n=max(len(c) for c in cols)
    cw=int(size*colgap); M=size*2
    W=cw*(len(cols)-1)+size+M*2; H=int(size*spacing*n)+M*2
    im=Image.new("RGBA",(W,H),(0,0,0,0))
    for ci,col in enumerate(cols):
        x=W-M-size-ci*cw
        for i,ch in enumerate(col):
            y=M+int(i*size*spacing)
            g=Image.new("RGBA",(size*2,size*2),(0,0,0,0)); gd=ImageDraw.Draw(g)
            if ch in "―—":
                ext=int(size*spacing/2)+1
                gd.line([(size,size-ext),(size,size+ext)],fill=fill,width=max(2,size//14))
                im.alpha_composite(g,(x-size//2,y-size//2)); continue
            gd.text((size,size),ch,font=font,fill=fill,stroke_width=stroke,stroke_fill=sfill,anchor="mm")
            if ch in ROT: g=g.rotate(-90,center=(size,size))
            ox,oy=0,0
            if ch in PUNCT: ox+=int(size*.55); oy-=int(size*.55)
            if ch in SMALL: ox+=int(size*.1); oy-=int(size*.1)
            im.alpha_composite(g,(x+ox-size//2,y+oy-size//2))
    return im.crop(im.getbbox())

TAIL=42
def balloon(page,cx,cy,text,size=34,tail=None,kind="oval",font=None):
    import math
    t=vtext_img(text,size,font); d=ImageDraw.Draw(page)
    m=Image.new("L",(PW,PH),0); md=ImageDraw.Draw(m)
    if kind=="oval":
        rx=t.width*0.5*1.42+22; ry=t.height*0.5*1.18+26
        md.ellipse((cx-rx,cy-ry,cx+rx,cy+ry),fill=255)
        if tail:
            # 尻尾は話者の方向を示すだけの最小限の長さ（縁から TAIL px）
            tx,ty=tail; a=math.atan2(ty-cy,tx-cx)
            def edge(t): return 1/math.sqrt((math.cos(t)/rx)**2+(math.sin(t)/ry)**2)
            k=edge(a); L=min(TAIL,max(0,math.hypot(tx-cx,ty-cy)-k))
            tip=(cx+(k+L)*math.cos(a),cy+(k+L)*math.sin(a))
            b1=(cx+edge(a+.22)*.85*math.cos(a+.22),cy+edge(a+.22)*.85*math.sin(a+.22))
            b2=(cx+edge(a-.22)*.85*math.cos(a-.22),cy+edge(a-.22)*.85*math.sin(a-.22))
            md.polygon([b1,tip,b2],fill=255)
        bw=4
    elif kind=="box":
        md.rectangle((cx-t.width/2-18,cy-t.height/2-16,cx+t.width/2+18,cy+t.height/2+16),fill=255); bw=3
    elif kind=="phone":
        rx=t.width*0.5+40; ry=t.height*0.5+36; pts=[]
        for i in range(40):
            a=2*math.pi*i/40; r=1.0 if i%2==0 else 0.88
            pts.append((cx+rx*r*math.cos(a),cy+ry*r*math.sin(a)))
        md.polygon(pts,fill=255); bw=3
    else: bw=0
    if bw:
        outer=m.filter(ImageFilter.MaxFilter(bw*2+1))
        page.paste((0,0,0,255),(0,0),outer); page.paste((255,255,255,255),(0,0),m)
    page.alpha_composite(t,(int(cx-t.width/2),int(cy-t.height/2)))

def sfx(page,x,y,text,size=90):
    f=ImageFont.truetype(GOTH,size)
    t=vtext_img(text,size,f,spacing=0.95,fill="black",stroke=7,sfill="white")
    page.alpha_composite(t,(x,y))
