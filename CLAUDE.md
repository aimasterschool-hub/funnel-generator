# funnel-generator — Claude Code 作業ガイド

<!-- ★共通の入口 ここから（機械で配っています／youtube-tool: tools/dryrun/repo_entry_sync.js） -->

## ★コードを触る前に読むもの（全プロジェクト共通）

★**バグの型の正本はここ1か所です**（★写してはいけません。★読んでください）:

- `~/projects/defect_types_master_v1.md`（★型 93件・T-A〜T-CN）
- GitHub: https://github.com/aimasterschool-hub/projects-docs/blob/main/defect_types_master_v1.md
- ★実例と「直した形」の詳細: `~/projects/youtube-tool/docs/defect_map.md` の §3

★**型番号で呼び合います**（Director の記憶・Codex・Claude Code で同じ番号）。

### ★共通の規約（詳しくは正本の末尾）

- ★**規約A** 同じ処理が複数箇所にあるなら、★**先に全箇所を数えてから**直す
- ★**規約B** 数える機能には★**陽性対照**を対にする（★0件は安全を意味しない）
- ★**規約C** ★「測れなかった」と「異常だった」を★同じ値で返さない
- ★**規約D** 数字には札を付ける（【一次】【実測】【計算】【推定】【未測】＋【範囲】）
- ★**規約E** 切り替えるもの（鍵・URL・設定）は★使う直前に読む
- ★**規約F** 検査IDは★一意にする

### ★新しい型を見つけたら

1. `youtube-tool/docs/defect_map.md` の §3 に節を足す（どこ・症状・実測・直した形・見張り）
2. 同じファイルの §5 に型を1行足す（★なぜダメか／どう直すか）
3. `node tools/dryrun/types_master_sync.js --write`（★正本の1枚に配る）
4. `node tools/dryrun/repo_entry_sync.js --write`（★全リポの入口を更新）

<!-- ★共通の入口 ここまで -->

最終更新：2026-07-06

## 0. セッション開始時の前提（自動読込・ユーザー明示不要）

- **グローバル設定**：`~/.claude/CLAUDE.md`（開発規約・ブループリント・secrets・自発リマインド §7.1）
- **セッション状態**：本ディレクトリの `HANDOFF.md`（毎セッション終了時に更新→push）
- **改善バックログ**：`~/projects/improvement_backlog_v1.md` の **§1（横断）** と **§2.2（funnel-generator 個別 F01〜F24）**、**§5.3 Phase 4 移行前必須** を必要に応じ参照

## 0.1 このプロジェクトの位置づけ

マスターブループリント（`~/projects/master_system_blueprint_v*.md` 最新版）**ライン2：投資商品・ローンチ制作**の中核。台本 docx→optin LP／VSL／販売LP を Claude API で自動生成する Streamlit アプリ。**product_launch_generator の後工程**（ローンチ台本→本ツールでファネル各ページ化）。

## 0.2 このプロジェクト固有の注意（監査バックログ抜粋）

- 🔴 過去に `.git/config` にトークン直書き事故 → SSH 化済み。トークン系は**絶対に .git/config に書かない**（規約 §4）
- 🔴 `references/` `saved_scripts/` `seller_photos/` `samples/**/*.PNG` は著作物由来・顧客データを含みうる → `.gitignore` で追跡防止済み（F01/F03/D2 対応・2026-07-06）
- 🟡 モデルID が 8ファイルに散在（F02）→ 変更時は必ず全 grep：`grep -RIEn 'claude-(sonnet|haiku|opus)-' --include='*.py'`
- 🟡 エントリポイント4本（`main.py` は旧シグネチャで壊れかけ・`generate.py`／`run_optin.py`／`app.py`）→ どれが「今使う」入口かは HANDOFF §運用方針で確認（実装は F07 未対応）
- 🟡 Anthropic クライアント6ファイルで個別初期化（F06 未対応。**SDK バージョンアップ時は全ファイル修正が必要**）
- 🟡 `FUNNEL_PASS` の明示 fail-closed 化（C3）は Streamlit Cloud secrets 設定確認待ちで**保留中**

---

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
