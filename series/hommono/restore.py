# 保存用の JPEG（assets/）から、作業用の PNG（chars/ と panels/）を作り直す
# 新しい環境で続きを作るときに、最初に1回だけ実行する
import os, glob
from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
for f in glob.glob(f"{ROOT}/assets/chars/*.jpg"):
    os.makedirs(f"{ROOT}/chars", exist_ok=True)
    out = f"{ROOT}/chars/{os.path.basename(f)[:-4]}.png"
    if not os.path.exists(out): Image.open(f).save(out)
for f in glob.glob(f"{ROOT}/assets/panels/*/*.jpg"):
    ep = os.path.basename(os.path.dirname(f))
    os.makedirs(f"{ROOT}/panels/{ep}", exist_ok=True)
    out = f"{ROOT}/panels/{ep}/{os.path.basename(f)[:-4]}.png"
    if not os.path.exists(out): Image.open(f).save(out)
# 完成済みの話は、pages/ のページをそのまま out/ に置いて「完成」として扱う
for d in glob.glob(f"{ROOT}/pages/ep*"):
    ep = os.path.basename(d)
    if not os.path.exists(f"{d}/page4.jpg"): continue
    os.makedirs(f"{ROOT}/out/{ep}", exist_ok=True)
    for i in range(1, 5):
        out = f"{ROOT}/out/{ep}/page{i}.png"
        if not os.path.exists(out): Image.open(f"{d}/page{i}.jpg").save(out)
print("restored")
