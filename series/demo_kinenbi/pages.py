from compose import *
P="panels/"
def new(): return Image.new("RGBA",(PW,PH),"white")
def save(pg,n): pg.convert("RGB").save(f"pages/page{n}.png"); print("page",n)

# ---------- page 1 ----------
pg=new()
draw_panel(pg,[(0,0),(1200,0),(1200,500),(0,500)],P+"p1_1.png",fy=.55,frame="none")
ImageDraw.Draw(pg).line([(0,500),(1200,500)],fill="black",width=5)
draw_panel(pg,[(530,530),(1150,530),(1150,1020),(480,1050)],P+"p1_2.png",fx=.2)
draw_panel(pg,[(50,530),(506,530),(456,1052),(50,1070)],P+"p1_3.png",fy=.15)
draw_panel(pg,[(50,1100),(1150,1050),(1150,1650),(50,1650)],P+"p1_4.png",fy=.3)
balloon(pg,1100,150,"結婚三周年の夜――",30,kind="box")
balloon(pg,930,660,"今日は…\n来てくれるよね",32,tail=(700,640))
balloon(pg,100,640,"三時間後",28,kind="box")
balloon(pg,270,950,"ただいま\n電話に出ることが\nできません…",22,kind="phone")
balloon(pg,1060,1230,"お客様…\nそろそろ閉店の\nお時間でして…",28)
balloon(pg,470,1420,"……はい",30,tail=(600,1380))
save(pg,1)

# ---------- page 2 ----------
pg=new()
draw_panel(pg,[(50,50),(1150,50),(1150,450),(50,450)],P+"p2_1.png",fy=.5)
draw_panel(pg,[(50,480),(1150,480),(1150,1190),(50,1190)],None,bg=(28,28,32))
# speed lines in dark panel
import math,random; random.seed(3)
sl=Image.new("RGBA",(PW,PH),(0,0,0,0)); d=ImageDraw.Draw(sl)
for i in range(140):
    a=random.uniform(0,2*math.pi); r0=random.uniform(380,420)
    d.line([(600+r0*math.cos(a),835+r0*.8*math.sin(a)),(600+900*math.cos(a),835+900*math.sin(a))],fill=(70,70,78),width=random.choice([1,2,3]))
clip=Image.new("L",(PW,PH),0); ImageDraw.Draw(clip).rectangle((52,482,1148,1188),fill=255)
pg.paste(sl,(0,0),Image.composite(sl.split()[3],Image.new("L",(PW,PH),0),clip)); d=ImageDraw.Draw(pg)
draw_panel(pg,[(50,480),(1150,480),(1150,1190),(50,1190)],None,frame="line_only") if False else d.rectangle((50,480,1150,1190),outline="black",width=5)
draw_panel(pg,[(50,1240),(1150,1205),(1150,1650),(50,1650)],P+"p2_3.png",fy=.2)
# phone breaking out of panel
px0,py0,pw,ph=300,510,600,780
d.rounded_rectangle((px0,py0,px0+pw,py0+ph),radius=60,fill=(15,15,15),outline="black",width=4)
sx0,sy0,sx1,sy1=px0+22,py0+40,px0+pw-22,py0+ph-40
d.rounded_rectangle((sx0,sy0,sx1,sy1),radius=36,fill="white")
G=lambda s:ImageFont.truetype(GOTH,s)
d.ellipse((sx0+20,sy0+22,sx0+76,sy0+78),fill=(200,200,200))
av=cover(Image.open(P+"p2_2.png").convert("RGB"),56,56,.3,.3); mm=Image.new("L",(56,56),0); ImageDraw.Draw(mm).ellipse((0,0,56,56),fill=255); pg.paste(av,(sx0+20,sy0+22),mm)
d.text((sx0+90,sy0+24),"蘇婉 Su Wan",font=G(26),fill="black"); d.text((sx0+90,sy0+56),"22:14",font=G(20),fill=(120,120,120))
ph_img=cover(Image.open(P+"p2_2.png").convert("RGB"),sx1-sx0,430,.5,.4); pg.paste(ph_img,(sx0,sy0+96))
ty=sy0+96+430+14
d.text((sx0+20,ty),"♡ 2,481   コメント 312",font=G(22),fill=(60,60,60))
EM=ImageFont.truetype(EMF,109)
def em(ch,s):
    e=Image.new("RGBA",(140,140),(0,0,0,0)); ImageDraw.Draw(e).text((0,0),ch,font=EM,embedded_color=True); return e.crop(e.getbbox()).resize((s,s),Image.LANCZOS)
d.text((sx0+20,ty+38),"誕生日に、いちばん会いたい人が",font=G(25),fill="black")
d.text((sx0+20,ty+72),"来てくれた",font=G(25),fill="black"); e=em("🎂",28); pg.alpha_composite(e,(int(sx0+20+G(25).getlength("来てくれた"))+4,ty+70))
d.text((sx0+20,ty+106),"#ずっと変わらない #初恋",font=G(23),fill=(30,90,170))
balloon(pg,1070,700,"夫の初恋の人\n――蘇婉",28,kind="box")
sfx(pg,960,80,"ブブッ",80)
balloon(pg,1010,1420,"……そっか",32)
balloon(pg,170,1470,"今日は\n私たちの\n記念日なのに",28,kind="box")
save(pg,2)

# ---------- page 3 ----------
pg=new()
draw_panel(pg,[(50,50),(1150,50),(1150,600),(50,600)],P+"p3_1.png",fy=.4,frame="fade")
draw_panel(pg,[(700,630),(1150,630),(1150,1080),(650,1062)],P+"p3_2.png",fy=.5)
draw_panel(pg,[(50,630),(676,630),(626,1061),(50,1040)],P+"p3_3.png",fx=.6)
draw_panel(pg,[(50,1070),(1150,1110),(1150,1650),(50,1650)],P+"p3_4.png",fy=.5)
balloon(pg,140,300,"一生、\n君を大事にする",30,tail=(290,190))
balloon(pg,1085,790,"三年間\nずっと待ってた",28,kind="box")
balloon(pg,110,800,"でも――\nもう、待たない",28,kind="box")
balloon(pg,920,1300,"さようなら、\n景深",32,tail=(660,1230))
save(pg,3)

# ---------- page 4 ----------
pg=new()
draw_panel(pg,[(50,50),(1150,50),(1150,500),(50,500)],P+"p4_1.png",fy=0)
draw_panel(pg,[(50,530),(1150,530),(1150,880),(50,950)],P+"p4_2.png",fy=.5)
draw_panel(pg,[(0,990),(1200,915),(1200,1700),(0,1700)],P+"p4_3.png",fy=.3,frame="none")
ImageDraw.Draw(pg).line([(0,990),(1200,915)],fill="black",width=5)
balloon(pg,1040,260,"林夏、昨夜は\n急用が――",32,tail=(780,200))
balloon(pg,1080,660,"……林夏？",28)
balloon(pg,1030,1120,"……は？",40,tail=(840,1180))
balloon(pg,150,1460,"彼はまだ知らない。\n彼女が、本当は\n誰の娘なのかを――",30,kind="box")
save(pg,4)
