"""ネームの1コマから、画像生成用のプロンプトと参照画像を組み立てる。"""

SHOTS = {
    "long": "extreme long shot, establishing shot, small figures in a wide environment",
    "full": "full body shot",
    "middle": "medium shot, waist up",
    "bust": "bust shot, chest up",
    "up": "close-up on the face",
    "detail": "extreme close-up on hands or an object",
}

ANGLES = {
    "eye": "",
    "high": "high angle, bird's-eye view, looking down",
    "low": "low angle, worm's-eye view, looking up",
    "back": "seen from behind",
}

# 描き込みの強弱（改善案13）
DETAIL = {
    "main": "highly detailed main character, sharp focus",
    "normal": "",
    "low": "simplified drawing, minimal detail, quick sketchy linework",
}

# モブの段階（改善案2）。bible.yaml の mobs で上書きできる。
MOB_DEFAULTS = {
    "named": "plain-looking side characters, modest features, less attractive than the main cast",
    "crowd": "background crowd with very simple faces, minimal detail, small eyes, plain hairstyles",
}

DEFORM = "super deformed chibi, comedic exaggerated gag face, manga gag style, simplified features"

ASPECT_WORDS = [
    (2.2, "very wide panoramic composition"),
    (1.3, "wide horizontal composition"),
    (0.77, ""),
    (0.45, "tall vertical composition"),
    (0.0, "very tall narrow vertical composition"),
]


def aspect_word(aspect):
    for threshold, word in ASPECT_WORDS:
        if aspect >= threshold:
            return word
    return ""


def build(project, panel, aspect, style_extra=""):
    """(prompt, negative, refs) を返す。refs は参照画像のパスのリスト。"""
    cfg = project.config
    parts = [cfg["style"]]
    refs = []

    deform = bool(panel.get("deform")) and cfg.get("deform")
    if deform:
        parts.append(DEFORM)

    parts.append(SHOTS.get(panel.get("shot", "middle"), ""))
    parts.append(ANGLES.get(panel.get("angle", "eye"), ""))
    parts.append(DETAIL.get(panel.get("detail", "normal"), ""))
    parts.append(aspect_word(aspect))

    names = []
    for c in panel.get("characters", []) or []:
        cid = c["id"] if isinstance(c, dict) else c
        c = c if isinstance(c, dict) else {"id": cid}
        ch = project.characters.get(cid, {})
        desc = [ch.get("appearance", cid)]
        costume = c.get("costume")
        if costume:
            cos = (ch.get("costumes") or {}).get(costume, {})
            desc.append(cos.get("desc", costume))
            # 衣装・ウィッグ中は、その衣装の設定画を毎回渡す（改善案6）
            _add_ref(project, refs, cos.get("ref"))
        if deform and ch.get("deform_ref"):
            _add_ref(project, refs, ch.get("deform_ref"))
        else:
            _add_ref(project, refs, ch.get("ref"))
        for key in ("expression", "pose", "state"):
            if c.get(key):
                desc.append(str(c[key]))
        if c.get("position"):
            desc.append(f"on the {c['position']} side of the frame")
        names.append("(" + ", ".join(d for d in desc if d) + ")")
    if names:
        parts.append(f"{len(names)} character(s): " + " and ".join(names))
    else:
        parts.append("no people")

    for m in panel.get("mobs", []) or []:
        level = m.get("level", "crowd") if isinstance(m, dict) else m
        desc = (project.mobs.get(level) or {}).get("desc") or MOB_DEFAULTS.get(level, "")
        count = m.get("count") if isinstance(m, dict) else None
        parts.append(f"{count or 'some'} {desc}")

    loc_id = panel.get("location")
    if loc_id:
        loc = project.locations.get(loc_id, {})
        parts.append("background: " + loc.get("desc", loc_id))
        if panel.get("detail") == "main":
            parts.append("simplified background")
        _add_ref(project, refs, loc.get("ref"))

    for pid in panel.get("props", []) or []:
        pr = project.props.get(pid, {})
        parts.append(pr.get("desc", pid))
        _add_ref(project, refs, pr.get("ref"))

    if panel.get("prompt"):
        parts.append(panel["prompt"])
    # 台本の必須条件を作画指示に必ず転記する（改善案5）
    for must in panel.get("must", []) or []:
        parts.append(f"IMPORTANT: {must}")
    if style_extra:
        parts.append(style_extra)
    parts.append("no text, no speech bubbles, no panel borders, fill the whole frame")

    prompt = ", ".join(p for p in parts if p)
    negative = cfg.get("negative", "")
    if panel.get("negative"):
        negative = f"{negative}, {panel['negative']}"
    return prompt, negative, refs


def _add_ref(project, refs, rel):
    p = project.ref(rel)
    if p and p not in refs:
        refs.append(p)
