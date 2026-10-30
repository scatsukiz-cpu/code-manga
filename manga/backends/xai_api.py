"""xAI（Grok）の画像API。サイズ指定と参照画像は使わず、文章だけで生成する。"""

import base64

import requests

from . import require_env


class XAIBackend:
    def __init__(self, options):
        self.model = options.get("model", "grok-2-image")
        self.base = options.get("base_url", "https://api.x.ai/v1")
        self.key = require_env("XAI_API_KEY")

    def generate(self, prompt, negative, aspect, refs, seed, out_path):
        if negative:
            prompt = f"{prompt}. Avoid: {negative}"
        r = requests.post(
            f"{self.base}/images/generations",
            headers={"Authorization": f"Bearer {self.key}"},
            json={"model": self.model, "prompt": prompt, "n": 1, "response_format": "b64_json"},
            timeout=600,
        )
        if r.status_code != 200:
            raise RuntimeError(f"xAI API エラー {r.status_code}: {r.text[:500]}")
        out_path.write_bytes(base64.b64decode(r.json()["data"][0]["b64_json"]))
