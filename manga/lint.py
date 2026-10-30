"""ネームの機械的なチェック。作画の前に問題を見つける。"""

import re

from . import layouts
from .prompts import SHOTS


class Report:
    def __init__(self):
        self.errors, self.warnings = [], []

    def error(self, where, msg):
        self.errors.append(f"[エラー] {where}: {msg}")

    def warn(self, where, msg):
        self.warnings.append(f"[注意] {where}: {msg}")

    def print(self):
        for line in self.errors + self.warnings:
            print(line)
        print(f"エラー {len(self.errors)} 件、注意 {len(self.warnings)} 件")


def _cid(c):
    return c["id"] if isinstance(c, dict) else c


def lint_name(project, ep, name) -> Report:
    rep = Report()
    cfg = project.config
    chars, locs, props = project.characters, project.locations, project.props

    shot_run, last_key = [], None  # 同じ構図の連続（ページをまたいで数える）
    last_state = {}  # (scene, キャラ) → 前のコマでの状態
    hook_page = None
    missing_refs = {}  # 設定画がないもの → 最初に出たコマ

    for page in name.get("pages", []):
        pno = page["page"]
        try:
            rects = layouts.panel_rects(page.get("layout"))
        except ValueError as e:
            rep.error(f"p{pno}", str(e))
            continue
        panels = page.get("panels") or []
        if len(rects) != len(panels):
            rep.error(f"p{pno}", f"コマ割り {page.get('layout')} は {len(rects)} コマですが、ネームは {len(panels)} コマです")

        page_chars = 0
        for rect, panel in zip(rects, panels):
            where = f"p{pno} k{panel.get('id')}"
            in_panel = [_cid(c) for c in panel.get("characters") or []]

            # 案1：ショット種別の指定と連続
            shot = panel.get("shot")
            if shot not in SHOTS:
                rep.error(where, f"shot が未指定か不明です（{', '.join(SHOTS)}）")
            key = (shot, panel.get("angle", "eye"))
            shot_run = shot_run + [where] if key == last_key else [where]
            last_key = key
            if len(shot_run) == 3:
                rep.warn(where, f"同じ構図（{shot}/{key[1]}）が3コマ続いています: {', '.join(shot_run)}")

            # コマの形と枠
            frame = panel.get("frame", "full")
            if frame not in ("full", "none", "fade"):
                rep.error(where, f"frame が不明です: {frame}（full / none / fade）")
            for o in panel.get("open") or []:
                edge = o if isinstance(o, str) else o.get("edge")
                if edge not in layouts.EDGES:
                    rep.error(where, f"open の辺が不明です: {edge}（top / right / bottom / left）")
            b = panel.get("break_out")
            if isinstance(b, dict):
                for side in b.get("sides") or []:
                    if side not in layouts.EDGES:
                        rep.error(where, f"break_out の向きが不明です: {side}")
            if b and not panel.get("characters"):
                rep.warn(where, "break_out（枠破り）ですが、人物がいません")
            for k in (panel.get("shape") or {}):
                if k not in layouts.EDGES:
                    rep.error(where, f"shape の辺が不明です: {k}")

            # 案4：場所
            loc = panel.get("location")
            if not loc:
                rep.warn(where, "location（場所）が未指定です")
            elif loc not in locs:
                rep.error(where, f"場所 {loc} が bible.yaml にありません")
            elif not project.ref(locs[loc].get("ref")):
                missing_refs.setdefault(f"場所 {loc}", where)

            # 案6・9：人物・衣装・小道具
            for c in panel.get("characters") or []:
                cid = _cid(c)
                if cid not in chars:
                    rep.error(where, f"人物 {cid} が bible.yaml にありません")
                    continue
                if not project.ref(chars[cid].get("ref")):
                    missing_refs.setdefault(f"人物 {cid}", where)
                if isinstance(c, dict):
                    cos = c.get("costume")
                    if cos and cos not in (chars[cid].get("costumes") or {}):
                        rep.error(where, f"{cid} の衣装 {cos} が bible.yaml にありません")
                    state, scene = c.get("state"), panel.get("scene", page.get("scene"))
                    prev = last_state.get((scene, cid))
                    if scene and prev is not None and state != prev and not c.get("state_change"):
                        rep.warn(where, f"{cid} の状態が前のコマ（{prev}）から変わっています。意図的なら state_change: true")
                    last_state[(scene, cid)] = state
            for pid in panel.get("props") or []:
                if pid not in props:
                    rep.error(where, f"小道具 {pid} が bible.yaml の props にありません")

            # 案13：デフォルメ
            if panel.get("deform") and not cfg.get("deform"):
                rep.warn(where, "deform: true ですが、この作品はデフォルメを使わない設定です")

            if panel.get("hook") and hook_page is None:
                hook_page = pno

            # 案3・8・10：台詞
            for item in panel.get("text") or []:
                kind = item.get("type", "speech")
                text = item.get("text", "")
                page_chars += len(text)
                if kind not in ("speech", "thought", "narration", "sfx"):
                    rep.error(where, f"text の type が不明です: {kind}")
                spk = item.get("speaker")
                if kind in ("speech", "thought"):
                    if not spk:
                        rep.error(where, f"話者（speaker）がありません: {text[:12]}")
                    elif spk not in chars:
                        rep.error(where, f"話者 {spk} が bible.yaml にありません")
                    elif kind == "speech" and spk not in in_panel and not panel.get("offpanel"):
                        rep.warn(where, f"{spk} はこのコマに描かれていません。しっぽの向きを offpanel: right/left/top/bottom で指定してください")
                if kind == "narration" and spk:
                    rep.warn(where, "ナレーションに話者があります。声に出す台詞なら speech にしてください")
                if len(text) > cfg["max_chars_per_balloon"]:
                    rep.warn(where, f"1つの枠の文字数が {len(text)} 字です（上限 {cfg['max_chars_per_balloon']}）")
                if spk in chars and kind == "speech":
                    for rule in chars[spk].get("speech_rules") or []:
                        if rule.get("to") and rule["to"] != item.get("to"):
                            continue
                        for word in rule.get("forbid") or []:
                            if re.search(word, text):
                                rep.warn(where, f"{spk} の口調ルール違反「{word}」: {text}（{rule.get('note', '')}）")

        if page_chars > cfg["max_chars_per_page"]:
            rep.warn(f"p{pno}", f"文字量 {page_chars} 字が上限 {cfg['max_chars_per_page']} 字を超えています")

    for what, where in missing_refs.items():
        rep.warn(where, f"{what} に設定画（ref）がありません（以降のコマも同じ）")

    # 案10：第1話は3ページ以内に関係性のフック
    if ep == 1 and (hook_page is None or hook_page > 3):
        rep.warn("第1話", "3ページ以内に hook: true のコマがありません（関係性のフックを冒頭に）")
    return rep
