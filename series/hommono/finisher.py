# コマがそろった話から順にページを組む（何度実行してもよい）
import os, importlib, engine as E
done = []
for n in range(1, 61):
    tag = f"ep{n:02d}"; EP = importlib.import_module(f"names.{tag}").EP
    if os.path.exists(f"{E.ROOT}/out/{tag}/page4.png"): continue
    ok = True
    for pi, pg in enumerate(EP["pages"]):
        for ki, p in enumerate(pg["panels"]):
            if p.get("blank"): continue
            if p.get("reuse"):
                rt, rp = p["reuse"].split(":")
                if not os.path.exists(f"{E.ROOT}/panels/{rt}/{rp}.png"): ok = False
            elif not os.path.exists(f"{E.ROOT}/panels/{tag}/p{pi+1}_{ki+1}.png"): ok = False
    if ok:
        E.build(importlib.import_module(f"names.{tag}"), only_compose=True); done.append(n)
print("composed", done)
