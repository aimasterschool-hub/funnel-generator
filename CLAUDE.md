# funnel-generator — Claude Code 作業ガイド

## プロジェクト概要

マーケティングファネル用のLP・台本を Claude API で自動生成する Streamlit アプリ。
台本（.docx）と商品情報（.yaml）を入力として、各ファネルのセクションごとにコピーと画像指示書を生成する。

## 起動・実行

```bash
# Webアプリ起動
streamlit run app.py

# CLIで直接生成（オプトインLP）
python3 run_optin.py --script scripts/AutoEdge1話.docx

# テスト実行
python3 test_all.py
```

必要な環境変数: `ANTHROPIC_API_KEY`（ローカルは .env、本番は Streamlit Secrets）

## アーキテクチャ

```
app.py                  Streamlit UI（フロントエンド）
├── outline.py          台本 → 骨子（セクション構成）を生成・キャッシュ
├── generator.py        骨子 + 台本 → 各セクションのコピー・画像指示書を生成
├── html_builder.py     Markdownを HTMLページに変換
├── reference_loader.py 参考LP（HTML/画像）からコピーを抽出・管理
└── run_optin.py        オプトインLP専用 CLIスクリプト（config読み込み・検証も担当）

funnel_config.yaml      商品・販売者・実績データの正規情報源
scripts/                台本ファイル（.docx/.yaml）
outlines/               生成済み骨子キャッシュ（*_骨子.md）
output/                 生成済みLP（.md / .html）
references/             参考ファネル（.txt形式で抽出済みコピー）
```

## ファネル種別

| キー | 名称 |
|------|------|
| `optin` | オプトインLP |
| `video_funnel_ep1〜ep5` | 動画ファネル 1〜5話 |
| `sales_lp` | 販売LP |

骨子生成ロジックは `outline.py` の `_funnel_category()` で `optin` / `video_funnel` / `sales_lp` の3カテゴリに振り分けられる。

## データフロー

```
台本(.docx) + funnel_config.yaml
    ↓ outline.get_outline()
骨子（セクション一覧）  ← キャッシュ: outlines/*_骨子.md
    ↓ generator.generate_page()
各セクション: コピー + 画像指示書
    ↓ html_builder.markdown_to_html()
output/*.html
```

## 重要な設計ルール

- **funnel_config.yaml が固有名詞・数字の正規情報源**。台本はストーリーと言葉づかいの参照源。数字や商品名は必ず YAML から取得する。
- 骨子は `outlines/` にキャッシュされ、同じ台本なら再生成しない（`get_outline()` が判定）。
- 参考LPは `references/` に `{funnel_type}_ref.txt` 形式で保存。`load_references_for_generation()` で生成時に注入される。
- `run_optin.py` の `verify_config()` が必須フィールドを検証し、不足があればユーザーに入力を促す。

## よく修正する箇所

- **新しいファネル種別を追加**: `app.py` の `FUNNEL_LABELS`、`outline.py` の `_funnel_category()` と専用プロンプト関数、`app.py` の `CRITICAL_FIELDS_BY_TYPE`
- **セクション表示名の変更**: `generator.py` の `SECTION_NAMES_JA`
- **LP デザイン変更**: `html_builder.py` の `_render_section()` / `_render_lines()`
- **骨子プロンプト変更**: `outline.py` の `_prompt_optin()` / `_prompt_video_funnel()` / `_prompt_sales_lp()`

## Claude API 使用箇所

- `outline.py`: 骨子生成（`claude-opus-4-5` 相当、長文生成）
- `generator.py`: セクションごとのコピー・画像指示書生成
- `reference_loader.py`: 参考LPのコピー抽出・外見分析
- `run_optin.py`: YAMLが未作成の場合に台本から自動抽出

モデルIDを変更する場合は上記4ファイルを横断して確認すること。
