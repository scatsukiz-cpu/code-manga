"""ローカルの ComfyUI（Windows の 5070Ti や Mac）で生成する。

ComfyUI で作ったワークフローを「API形式で保存」し、次の文字列を書き込んでおく：
  {{PROMPT}} {{NEGATIVE}} {{WIDTH}} {{HEIGHT}} {{SEED}}
参照画像を使うワークフロー（IPAdapter など）なら {{REF_IMAGE}} も使える。
"""

import json
import time
import uuid
from pathlib import Path

import requests


class ComfyUIBackend:
    def __init__(self, options):
        self.server = options.get("server", "http://127.0.0.1:8188").rstrip("/")
        wf = options.get("workflow")
        if not wf:
            raise RuntimeError("backend_options.workflow に ComfyUI のワークフロー（API形式のJSON）を指定してください")
        self.workflow = Path(wf).read_text(encoding="utf-8")
        self.pixels = options.get("pixels", 1024 * 1024)
        self.timeout = options.get("timeout", 900)

    def _size(self, aspect):
        h = (self.pixels / aspect) ** 0.5
        w = h * aspect
        return max(512, round(w / 64) * 64), max(512, round(h / 64) * 64)

    def _upload(self, path):
        with open(path, "rb") as fh:
            r = requests.post(f"{self.server}/upload/image", files={"image": (path.name, fh, "image/png")},
                              data={"overwrite": "true"}, timeout=120)
        r.raise_for_status()
        return r.json()["name"]

    def generate(self, prompt, negative, aspect, refs, seed, out_path):
        w, h = self._size(aspect)
        values = {"{{PROMPT}}": prompt, "{{NEGATIVE}}": negative, "{{WIDTH}}": w, "{{HEIGHT}}": h,
                  "{{SEED}}": seed}
        if "{{REF_IMAGE}}" in self.workflow and refs:
            values["{{REF_IMAGE}}"] = self._upload(refs[0])
        wf = _fill(json.loads(self.workflow), values)

        r = requests.post(f"{self.server}/prompt", json={"prompt": wf, "client_id": uuid.uuid4().hex}, timeout=60)
        if r.status_code != 200:
            raise RuntimeError(f"ComfyUI エラー {r.status_code}: {r.text[:500]}")
        prompt_id = r.json()["prompt_id"]

        deadline = time.time() + self.timeout
        while time.time() < deadline:
            hist = requests.get(f"{self.server}/history/{prompt_id}", timeout=30).json()
            if prompt_id in hist:
                for node in hist[prompt_id]["outputs"].values():
                    for img in node.get("images", []):
                        data = requests.get(f"{self.server}/view", params=img, timeout=120).content
                        out_path.write_bytes(data)
                        return
                raise RuntimeError("ComfyUI の出力に画像がありません")
            time.sleep(2)
        raise TimeoutError("ComfyUI の生成が時間内に終わりませんでした")


def _fill(node, values):
    if isinstance(node, dict):
        return {k: _fill(v, values) for k, v in node.items()}
    if isinstance(node, list):
        return [_fill(v, values) for v in node]
    if isinstance(node, str):
        if node in values:
            return values[node]
        for k, v in values.items():
            if k in node:
                node = node.replace(k, str(v))
    return node
