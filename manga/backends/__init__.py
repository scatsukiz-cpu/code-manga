"""画像生成の担当を差し替えるための窓口。

どの担当も generate(prompt, negative, aspect, refs, seed, out_path) を持つ。
生成する画像の比率はコマ枠に近づけ、最後の切り抜きは compose 側で行う。
"""

import os


def get_backend(name, options=None):
    options = options or {}
    if name == "placeholder":
        from .placeholder import PlaceholderBackend
        return PlaceholderBackend(options)
    if name == "openai":
        from .openai_api import OpenAIBackend
        return OpenAIBackend(options)
    if name == "xai":
        from .xai_api import XAIBackend
        return XAIBackend(options)
    if name == "comfyui":
        from .comfyui import ComfyUIBackend
        return ComfyUIBackend(options)
    raise ValueError(f"不明な画像生成の担当: {name}（placeholder / openai / xai / comfyui）")


def require_env(key):
    value = os.environ.get(key)
    if not value:
        raise RuntimeError(f"環境変数 {key} が設定されていません")
    return value
