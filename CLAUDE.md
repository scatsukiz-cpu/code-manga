# code-manga：プロットから日本式コマ割り漫画を作る

作者からプロット（原案）を受け取ったら、Claude Code が一人で最後まで漫画を完成させる。
縦読み（Webtoon）ではなく、右綴じ・右から左に読むページ単位の漫画を作る。

## 役割分担

- **Claude Code（あなた）**：台本、ネーム（コマ割り・構図・台詞）、設定資料、完成チェックの指示。
- **コード（`python -m manga`）**：コマ枠の計算、画像生成の呼び出し、絵の切り抜き、写植（縦書き・吹き出し）、PDF化。
- **画像生成**：`project.yaml` の `backend` で切り替える。
  - `placeholder`：ダミー画像。キーなしで工程を確認できる
  - `openai`：環境変数 `OPENAI_API_KEY`
  - `xai`：環境変数 `XAI_API_KEY`
  - `comfyui`：ローカルの ComfyUI（Windows 5070Ti / Mac M2 Max）。クラウドからは届かないので、作者のPCで実行する

## 作品フォルダ

```
projects/<作品>/
  project.yaml   作品の設定（ジャンル、デフォルメの有無、画風、画像生成の担当、文字量の上限）
  plot.md        作者の原案。書き換えない。「固定する場面」の節を持つ
  script.md      台本。冒頭に「固定する場面」を書き出す
  bible.yaml     設定資料：人物（外見・衣装・デフォルメ・口調ルール）、場所、小道具、モブ
  refs/          設定画
  name/epNN.yaml ネーム
  out/epNN/      生成物（panels/ pages/ review/ epNN.pdf）。git には入れない
```

見本は `projects/sample/`。新しい作品はこれを複製して始める。

## 工程

1. **原案の整理**：plot.md に作者の原案をそのまま置く。作者が残したい見せ場を「固定する場面」として書き出し、作者に確認する。誇張してよい場面には印を付ける。
2. **設定資料**：bible.yaml を書く。`appearance` と `desc` は画像生成に渡すので英語で書く。
   - 人物ごとに `costumes`（衣装・ウィッグ）と、ギャグ作品なら `deform_ref`
   - 人物ごと・相手ごとの `speech_rules`（使わない言葉）
   - 舞台になる場所はすべて `locations` に入れ、設定画を作る
   - 話に出る小道具はすべて `props` に入れる（材質まで書く。例：wooden practice sword）
3. **台本**：script.md を書く。改稿したら **script-guardian エージェント** で原案と照合し、fail なら直す。
   - 現実の安全性や実現性を理由に、コメディの誇張を弱めない。弱めるなら理由を書く
   - 原案にない細部を盛りすぎない
4. **設定画**：`python -m manga refs projects/<作品>` で、まだない設定画を生成する。出来を Read で見て、ダメなら `--force` で作り直すか、作者に差し替えてもらう。
5. **ネーム**：name/epNN.yaml を書く（書き方は下）。書いたら `python -m manga lint projects/<作品> <話>` を通す。エラーは必ず直す。注意は理由があれば残してよい。
6. **作画**：`python -m manga gen projects/<作品> <話>`。既にあるコマは飛ばすので、途中で止まっても再実行すればよい。API の場合は先に `prompts` でプロンプトを確認し、枚数と費用の目安を作者に伝えてから実行する。
7. **写植・組版**：`python -m manga compose projects/<作品> <話>`。
8. **チェック**：`python -m manga review projects/<作品> <話>` で資料を作り、**ページごとに page-checker エージェント** に判定させる（自分で判定しない）。fail のコマは、`redraw` なら `gen --pages N --panels K --force`、`reletter` ならネームを直して `compose`。全ページ pass まで繰り返す。同じコマを3回作り直しても通らなければ、作者に相談する。
9. **書き出し**：`python -m manga export projects/<作品> <話>` で PDF にする。

## ネームの書き方

ページごとに `layout`（コマ割りテンプレート）を選び、読む順（右上→左下）にコマを並べる。

| layout | 形 |
|---|---|
| `1` | 1ページ1コマ（見開きや大ゴマ） |
| `2` / `2c` | 横2段 / 縦長2コマ |
| `3` / `3a` / `3b` | 3段 / 上1・下2 / 上の大ゴマ＋下2 |
| `4` / `4a` / `4b` | 1・2・1 / 2×2 / 大ゴマ＋下3 |
| `5` / `5a` | 5コマの2種 |
| `6` | 2×3 |

テンプレートにない形は `layout: {tiers: [{h: 1, cols: [1, 2]}, ...]}` で書ける（`cols` は右から順の幅の比）。

コマの項目：

- `shot`（必須）：`long` / `full` / `middle` / `bust` / `up` / `detail`。`angle`：`eye` / `high` / `low` / `back`
  - 会話場面でもバストアップを続けない。同じ構図が3コマ続くと lint が注意を出す。引き・手元・俯瞰を混ぜる
- `detail`：`main`（見せたいコマ。背景は省略される）/ `normal` / `low`（流すコマ）
- `deform: true`：ギャグ顔・ちび絵にするコマ。ギャグ作品では積極的に使う。絵の美しさで見せるコマでは使わない
- `location`、`characters`（`id`、`costume`、`expression`、`pose`、`position`: right/center/left、`state`）、`mobs`（`level`: named / crowd）、`props`
  - `state` は「眼鏡なし」など。同じ `scene` の中で変わると lint が注意を出す。意図的なら `state_change: true`
- `must`：台本で必須の絵の条件（例：唇の間に隙間）。英語で書く。チェックで必ず確認される
- `prompt`：画像生成への追加指示（英語）。`action` は人間用のメモ（日本語）
- `bleed: true`：タチキリ。`borderless: true`：枠線なし。`focus_point: [x, y]`：切り抜きの中心
- `hook: true`：関係性のフック。第1話は3ページ以内に必要
- `text`：読む順に並べる
  - `{type: speech, speaker: id, to: 相手, text: "台詞"}`。`style: shout` でギザギザ
  - `{type: thought, speaker: id, text: "心の声"}`
  - `{type: narration, text: "ナレーション"}`
  - `{type: sfx, text: "ドン", at: [x, y]}`（描き文字）
  - 改行 `\n` で縦書きの列を区切る。1つの枠は短く。`at: [x, y]` でコマ内の位置を指定できる
  - 話者がコマにいない台詞は、コマに `offpanel: right/left/top/bottom` を書く

## 守ること

- plot.md は書き換えない。
- 1ページの文字量は `max_chars_per_page` 以内。知識語りは削らず、ページを分けて配置する。
- モブは主役より目立たせない。名前のある脇役は `named`、群衆は `crowd`。主要キャラと似た髪型のモブを作らない。
- 完成ページの合否は、作画した本人（あなた）ではなく page-checker エージェントに判定させる。
