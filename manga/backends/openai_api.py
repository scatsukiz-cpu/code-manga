"""OpenAI の画像API。参照画像があるときは edits で渡す。"""

import base64

import requests

from . import require_env

SIZES = {"square": "1024x1024", "wide": "1536x1024", "tall": "1024x1536"}


class OpenAIBackend:
    def __init__(self, options):
        self.model = options.get("model", "gpt-image-1")
        self.quality = options.get("quality", "high")
        self.base = options.get("base_url", "https://api.openai.com/v1")
        self.max_refs = options.get("max_refs", 4)
        self.key = require_env("OPENAI_API_KEY")

    def generate(self, prompt, negative, aspect, refs, seed, out_path):
        size = SIZES["wide"] if aspect > 1.2 else SIZES["tall"] if aspect < 0.83 else SIZES["square"]
        if negative:
            prompt = f"{prompt}. Avoid: {negative}"
        headers = {"Authorization": f"Bearer {self.key}"}
        data = {"model": self.model, "prompt": prompt, "size": size, "quality": self.quality, "n": 1}
        refs = refs[: self.max_refs]
        if refs:
            files = [("image[]", (p.name, open(p, "rb"), "image/png")) for p in refs]
            try:
                r = requests.post(f"{self.base}/images/edits", headers=headers, data=data, files=files, timeout=600)
            finally:
                for _, (_, fh, _) in files:
                    fh.close()
        else:
            r = requests.post(f"{self.base}/images/generations", headers=headers, json=data, timeout=600)
        if r.status_code != 200:
            raise RuntimeError(f"OpenAI API エラー {r.status_code}: {r.text[:500]}")
        out_path.write_bytes(base64.b64decode(r.json()["data"][0]["b64_json"]))
