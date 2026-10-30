"""コマンド：python -m manga <命令> <作品フォルダ> <話数> [オプション]

  refs     設定画（人物・衣装・デフォルメ・場所・小道具）のうち、まだないものを生成する
  lint     ネームを機械的にチェックする
  prompts  各コマのプロンプトを表示する（生成はしない）
  gen      コマ画像を生成する（既にある画像は飛ばす。作り直しは --force）
  compose  コマをページに組み、写植を載せる
  review   別エージェントのチェック用の資料を書き出す
  export   完成ページを1つのPDFにまとめる
"""

import argparse
import sys
import time

import yaml
from PIL import Image

from . import compose, layouts, lint, prompts
from .backends import get_backend
from .project import Project


def _pages(name, only):
    pages = name.get("pages", [])
    if only:
        wanted = set(only)
        pages = [p for p in pages if p["page"] in wanted]
    return pages


def _panels(page, only):
    if not only:
        return page["panels"]
    return [k for k in page["panels"] if k["id"] in set(only)]


def _backend(proj, args):
    name = args.backend or proj.config["backend"]
    options = {"font": proj.config.get("font"), **(proj.config.get("backend_options") or {}).get(name, {})}
    if options.get("workflow"):  # ComfyUI のワークフローは作品フォルダからの相対パス
        options["workflow"] = str(proj.root / options["workflow"])
    return name, get_backend(name, options)


def _ref_jobs(proj):
    """bible.yaml の ref のうち、ファイルがないものと、そのプロンプト。"""
    style = proj.config["style"]
    sheet = "character reference sheet, full body, front view and side view, plain white background"
    for cid, ch in proj.characters.items():
        base = ch.get("appearance", cid)
        yield ch.get("ref"), f"{style}, {sheet}, {base}", 0.75
        for cos in (ch.get("costumes") or {}).values():
            yield cos.get("ref"), f"{style}, {sheet}, {base}, wearing {cos.get('desc', '')}", 0.75
        yield ch.get("deform_ref"), (f"{style}, super deformed chibi character sheet, several comedic gag faces "
                                     f"(shock, despair, anger, joy), plain white background, {base}"), 1.0
    for loc in proj.locations.values():
        yield loc.get("ref"), f"{style}, background art, no people, establishing shot, {loc.get('desc', '')}", 1.5
    for pr in proj.props.values():
        yield pr.get("ref"), f"{style}, prop design sheet, plain white background, {pr.get('desc', '')}", 1.0


def cmd_refs(proj, ep, args):
    backend_name, backend = _backend(proj, args)
    jobs = [(proj.root / rel, prompt, aspect) for rel, prompt, aspect in _ref_jobs(proj)
            if rel and (args.force or not (proj.root / rel).exists())]
    print(f"生成する設定画: {len(jobs)} 枚（担当: {backend_name}）")
    for i, (path, prompt, aspect) in enumerate(jobs, 1):
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            backend.generate(prompt, proj.config["negative"], aspect, [], i, path)
            print(f"[{i}/{len(jobs)}] {path.relative_to(proj.root)} 完了")
        except Exception as e:
            print(f"[{i}/{len(jobs)}] {path.relative_to(proj.root)} 失敗: {e}", file=sys.stderr)
    return 0


def cmd_lint(proj, ep, args):
    rep = lint.lint_name(proj, ep, proj.load_name(ep))
    rep.print()
    return 1 if rep.errors else 0


def cmd_prompts(proj, ep, args):
    name = proj.load_name(ep)
    for page in _pages(name, args.pages):
        rects = layouts.panel_rects(page["layout"])
        for rect, panel in zip(rects, page["panels"]):
            if args.panels and panel["id"] not in args.panels:
                continue
            prompt, negative, refs = prompts.build(proj, panel, rect.aspect)
            print(f"--- p{page['page']} k{panel['id']}  比率 {rect.aspect:.2f}")
            print(prompt)
            print(f"参照画像: {[str(r) for r in refs] or 'なし'}")
    return 0


def cmd_gen(proj, ep, args):
    name = proj.load_name(ep)
    rep = lint.lint_name(proj, ep, name)
    if rep.errors and not args.ignore_lint:
        rep.print()
        print("ネームにエラーがあるので生成を止めました（無視するなら --ignore-lint）")
        return 1
    backend_name, backend = _backend(proj, args)

    todo = []
    for page in _pages(name, args.pages):
        rects = layouts.panel_rects(page["layout"])
        for rect, panel in zip(rects, page["panels"]):
            if args.panels and panel["id"] not in args.panels:
                continue
            path = proj.panel_path(ep, page["page"], panel["id"])
            if path.exists() and not args.force:
                continue
            r = layouts.bleed_rect(rect) if panel.get("bleed") else rect
            todo.append((page, panel, r, path))

    print(f"生成するコマ: {len(todo)} 枚（担当: {backend_name}）")
    failed = 0
    for i, (page, panel, rect, path) in enumerate(todo, 1):
        prompt, negative, refs = prompts.build(proj, panel, rect.aspect)
        seed = panel.get("seed", ep * 100000 + page["page"] * 100 + panel["id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        t = time.time()
        try:
            backend.generate(prompt, negative, rect.aspect, refs, seed, path)
            print(f"[{i}/{len(todo)}] p{page['page']} k{panel['id']} 完了 {time.time() - t:.0f}秒")
        except Exception as e:  # 1コマの失敗で全体を止めない
            failed += 1
            print(f"[{i}/{len(todo)}] p{page['page']} k{panel['id']} 失敗: {e}", file=sys.stderr)
    return 1 if failed else 0


def cmd_compose(proj, ep, args):
    name = proj.load_name(ep)
    for page in _pages(name, args.pages):
        img = compose.compose_page(proj, ep, page)
        path = proj.page_path(ep, page["page"])
        path.parent.mkdir(parents=True, exist_ok=True)
        img.save(path)
        print(f"ページ {path}")
    return 0


CHECKLIST = """\
1. コマ枠が絵で埋まっているか。白い余白や浮いたコマがないか（案7）
2. 枠の種類が合っているか：声に出す台詞＝吹き出し、心の声・ナレーション＝四角枠（案8）
3. 吹き出しのしっぽが話者を指しているか。話者がいないコマでは外へ向いているか（案8）
4. 下の「必須条件」をすべて満たしているか（案5）
5. 人物の髪型・髪色・眼鏡・衣装が設定どおりか。別人に見えないか（案6）
6. 背景が指定の場所に見えるか（案4）
7. 小道具の材質・状態が設定どおりか。前のコマからの状態（眼鏡を外した等）を引き継いでいるか（案9）
8. モブが主要キャラより目立っていないか（案2）
9. ギャグ顔の指定（deform）があるコマは崩れているか。ないコマは崩れていないか（案13）
10. 右上から左下への読み順で、台詞の順番が自然か
"""


def cmd_review(proj, ep, args):
    name = proj.load_name(ep)
    out = proj.out_dir(ep) / "review"
    out.mkdir(parents=True, exist_ok=True)
    for page in _pages(name, args.pages):
        img = proj.page_path(ep, page["page"])
        lines = [f"# 第{ep}話 p{page['page']} チェック資料", "",
                 f"完成ページ画像: {img.resolve()}", "", "## 判定する項目", "", CHECKLIST,
                 "## ネーム（このページ）", "", "```yaml",
                 yaml.safe_dump(page, allow_unicode=True, sort_keys=False).rstrip(), "```", "",
                 "## 登場する人物・場所・小道具の設定", "", "```yaml"]
        used = {"characters": {}, "locations": {}, "props": {}}
        for k in page["panels"]:
            for c in k.get("characters") or []:
                cid = c["id"] if isinstance(c, dict) else c
                used["characters"][cid] = proj.characters.get(cid)
            if k.get("location"):
                used["locations"][k["location"]] = proj.locations.get(k["location"])
            for p in k.get("props") or []:
                used["props"][p] = proj.props.get(p)
        lines += [yaml.safe_dump(used, allow_unicode=True, sort_keys=False).rstrip(), "```", ""]
        path = out / f"p{page['page']:02d}.md"
        path.write_text("\n".join(lines), encoding="utf-8")
        print(f"チェック資料 {path}")
    return 0


def cmd_export(proj, ep, args):
    name = proj.load_name(ep)
    images = []
    for page in _pages(name, args.pages):
        p = proj.page_path(ep, page["page"])
        if not p.exists():
            print(f"ページ {p} がありません。先に compose を実行してください", file=sys.stderr)
            return 1
        images.append(Image.open(p).convert("RGB"))
    path = proj.out_dir(ep) / f"ep{ep:02d}.pdf"
    images[0].save(path, save_all=True, append_images=images[1:], resolution=150)
    print(f"PDF {path}")
    return 0


COMMANDS = {"refs": cmd_refs, "lint": cmd_lint, "prompts": cmd_prompts, "gen": cmd_gen, "compose": cmd_compose,
            "review": cmd_review, "export": cmd_export}


def _ints(s):
    out = []
    for part in s.split(","):
        if "-" in part:
            a, b = part.split("-")
            out += range(int(a), int(b) + 1)
        elif part:
            out.append(int(part))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m manga", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=COMMANDS)
    ap.add_argument("project", help="作品フォルダ（例: projects/sample）")
    ap.add_argument("episode", type=int, nargs="?", default=1, help="話数（refs では不要）")
    ap.add_argument("--pages", type=_ints, help="対象ページ（例: 1,3-5）")
    ap.add_argument("--panels", type=_ints, help="対象コマ（例: 2）")
    ap.add_argument("--backend", help="画像生成の担当を一時的に変える")
    ap.add_argument("--force", action="store_true", help="既にあるコマも作り直す")
    ap.add_argument("--ignore-lint", action="store_true")
    args = ap.parse_args(argv)
    proj = Project(args.project)
    return COMMANDS[args.command](proj, args.episode, args)
