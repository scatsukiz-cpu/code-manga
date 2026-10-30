# code-manga

プロットを渡すと、Claude Code が日本式のコマ割り漫画（右綴じ・縦書き）を最後まで作るための仕組み。
工程の詳細は [CLAUDE.md](CLAUDE.md)。

## できること

- ネーム（YAML）から、コマ枠の比率に合わせて画像を生成し、枠を絵で埋めて組む
- 長方形以外のコマ：斜めの境目、辺ごとの傾き、枠の一部を開ける、枠なし・ぼかし枠、人物の枠破り
- 縦書きの写植。台詞＝吹き出し、心の声・ナレーション＝四角枠、描き文字、しっぽの向きを自動で決める
- ネームのチェック：構図の連続、設定にない場所・小道具・衣装、話者の抜け、口調ルール、文字量、第1話のフック
- 完成ページを、作画と別のエージェントに判定させるための資料づくり
- 画像生成の担当を切り替え：ダミー / OpenAI / xAI（Grok）/ ローカルの ComfyUI

## 準備

```bash
pip install -r requirements.txt
```

API を使う場合は、キーを環境変数に入れる（リポジトリには書かない）。

```bash
export OPENAI_API_KEY=...   # または XAI_API_KEY
```

クラウドの Claude Code で使う場合は、環境の設定の「環境変数」に登録する。

## 使い方

```bash
python -m manga refs     projects/sample      # 設定画を生成
python -m manga lint     projects/sample 1    # ネームのチェック
python -m manga prompts  projects/sample 1    # プロンプトの確認（生成しない）
python -m manga gen      projects/sample 1    # コマ画像を生成
python -m manga compose  projects/sample 1    # ページに組んで写植
python -m manga review   projects/sample 1    # チェック資料
python -m manga export   projects/sample 1    # PDF
```

`--pages 2,4-6`、`--panels 3`、`--force`（作り直し）、`--backend openai`（担当の一時変更）が使える。

## ローカルの ComfyUI を使う

1. ComfyUI でワークフローを作り、「API形式で保存（Export (API)）」する。
2. プロンプト・ネガティブ・幅・高さ・シードの入力欄を、それぞれ `{{PROMPT}}` `{{NEGATIVE}}` `{{WIDTH}}` `{{HEIGHT}}` `{{SEED}}` に書き換える。参照画像を使うなら画像読み込みのファイル名を `{{REF_IMAGE}}` にする。
3. `projects/<作品>/workflows/` などに置き、`project.yaml` の `backend: comfyui` と `backend_options.comfyui.workflow` を設定する。
4. ComfyUI を起動したPC（またはそこにつながるPC）で `python -m manga gen ...` を実行する。別のPCの ComfyUI を使うなら `server: http://<そのPCのIP>:8188` にし、ComfyUI を `--listen` で起動する。

クラウドの Claude Code からは自宅のPCに直接つながらないので、ComfyUI を使う工程は手元のPCで実行する。
