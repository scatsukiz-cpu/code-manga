"""作品フォルダの読み込み。"""

from pathlib import Path

import yaml

DEFAULTS = {
    "title": "無題",
    "genre": "",
    "deform": False,  # ギャグ顔・ちび絵を使う作品か（改善案13）
    "style": "Japanese manga, black and white, screentone, clean ink lines",
    "negative": "color, text, letters, speech bubble, watermark, signature, extra fingers",
    "backend": "placeholder",
    "backend_options": {},
    "font": None,
    "font_bold": None,
    "thought_style": "box",  # 心の声の枠：box（四角枠）または cloud（もこもこ）
    "max_chars_per_page": 220,  # 1ページの文字量の上限（改善案10）
    "max_chars_per_balloon": 45,
}


class Project:
    def __init__(self, root):
        self.root = Path(root)
        if not (self.root / "project.yaml").exists():
            raise FileNotFoundError(f"{self.root / 'project.yaml'} がありません")
        self.config = {**DEFAULTS, **(_load(self.root / "project.yaml") or {})}
        self.bible = _load(self.root / "bible.yaml") or {}

    # --- 設定資料 ---
    @property
    def characters(self) -> dict:
        return self.bible.get("characters", {}) or {}

    @property
    def locations(self) -> dict:
        return self.bible.get("locations", {}) or {}

    @property
    def props(self) -> dict:
        return self.bible.get("props", {}) or {}

    @property
    def mobs(self) -> dict:
        return self.bible.get("mobs", {}) or {}

    # --- ネーム ---
    def name_path(self, ep: int) -> Path:
        return self.root / "name" / f"ep{ep:02d}.yaml"

    def load_name(self, ep: int) -> dict:
        path = self.name_path(ep)
        if not path.exists():
            raise FileNotFoundError(f"ネーム {path} がありません")
        return _load(path)

    def out_dir(self, ep: int) -> Path:
        return self.root / "out" / f"ep{ep:02d}"

    def panel_path(self, ep: int, page: int, panel: int) -> Path:
        return self.out_dir(ep) / "panels" / f"p{page:02d}_k{panel:02d}.png"

    def page_path(self, ep: int, page: int) -> Path:
        return self.out_dir(ep) / "pages" / f"p{page:02d}.png"

    def ref(self, rel) -> Path | None:
        if not rel:
            return None
        p = self.root / rel
        return p if p.exists() else None


def _load(path):
    if not Path(path).exists():
        return None
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)
