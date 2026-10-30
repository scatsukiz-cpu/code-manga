# 複数話のコマをまとめて並列生成する（ページ組みは engine.py --compose で順番に行う）
import sys, os, importlib
from concurrent.futures import ThreadPoolExecutor
import engine as E
eps = [int(a) for a in sys.argv[1:] if not a.startswith("-")]
W = int(os.environ.get("W", "10"))
jobs = []
for n in eps:
    EP = importlib.import_module(f"names.ep{n:02d}").EP; tag = f"ep{n:02d}"
    pdir = f"{E.ROOT}/panels/{tag}"; os.makedirs(pdir, exist_ok=True)
    for pi, pg in enumerate(EP["pages"]):
        rows = pg["rows"]
        polys = E.layout(rows, pg.get("tilts") or E.auto_tilts(rows, n * 10 + pi, pg.get("flat", False), pg.get("strong", False)), tuple(pg.get("bleed", ())))
        assert len(polys) == len(pg["panels"]), f"{tag} page{pi+1}: {len(polys)} vs {len(pg['panels'])}"
        for ki, p in enumerate(pg["panels"]):
            out = f"{pdir}/p{pi+1}_{ki+1}.png"
            if p.get("reuse") or p.get("blank") or os.path.exists(out): continue
            refs = [f"{E.ROOT}/chars/{k}.png" for k in p.get("c", [])][:4]
            jobs.append((out, p.get("size") or E.size_for(polys[ki]), E.panel_prompt(p), refs))
print(len(jobs), "jobs", flush=True)
def run(j): return j[0], E.gen(*j)
with ThreadPoolExecutor(W) as ex:
    for out, r in ex.map(run, jobs):
        if r != "ok": print("FAIL", out, r, flush=True)
print("done", flush=True)
