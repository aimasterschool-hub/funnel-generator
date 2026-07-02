# HANDOFF — funnel-generator
最終更新：2026-07-03

## プロジェクト位置づけ
マスターブループリント v1.1「ライン2：投資商品・ローンチ制作」の中核。
台本docx→optin LP／VSL／販売LP を Claude API で自動生成する Streamlit アプリ。
将来Next.js+Clerk+Supabase+Vercel化構想あり（Phase 4で再検討）。

## 今回完了したこと（2026-07-03 規約適用セッション）
- `dev_standards_kit.md` を本プロジェクトに適用
- `.git/config` トークン直書き事故（過去）→ SSH認証に切替済みを確認
  - origin URL: `git@github.com:aimasterschool-hub/funnel-generator.git`
  - `ssh -T git@github.com` 疎通OK（aimasterschool-hub として認証）
  - `git ls-remote origin HEAD` 成功
- 履歴・作業ツリー全域を `ghp_/gho_/github_pat_/x-access-token` パターンで grep → 残骸ゼロ確認
- `.gitignore` 内容確認：`.env` `.claude/settings.local.json` `.venv/` `__pycache__/` `jobs/` `outlines/` `output/` `.DS_Store` 収録済み → 規約準拠
- 直近コミット「ハードコードされたデフォルトパスワードを削除（fail-closed 化）」で `FUNNEL_PASS` 未設定時に落ちる設計に変更済み
- ローカル/originは同期済み（`origin/main..HEAD` 差分なし）

## 現状の到達点
### 機能
- Streamlit UIから台本(.docx)+funnel_config.yaml投入→骨子キャッシュ→セクション別コピー＋画像指示書生成：**済**
- ファネル種別：optin / video_funnel_ep1〜ep5 / sales_lp：**済**
- 参考ファネル複数同時アップ／保存＆再利用／カラーテーマ選択：**済**
- CLIエントリ（`run_optin.py`）：**済**

### インフラ
- GitHub保全：**済**（aimasterschool-hub/funnel-generator, SSH）
- secrets：**済**（.env / Streamlit Secrets 両対応、`ANTHROPIC_API_KEY` `FUNNEL_PASS`）
- HANDOFF/CLAUDE.md：**済**（本ファイル＋既存CLAUDE.md）
- 設計メモ：**未**（v1のCLAUDE.mdが設計メモの代役だが、`funnel-generator_design_memo.md` としては未整備）

## 次回やること（優先順）
1. Phase 2「ライン2の接続テスト」：商品マスター→ローンチ台本gen→funnel-generatorの一気通貫（ブループリント §5 Phase 2-8）
2. `funnel_config.yaml` の項目を **商品マスター**（Phase 2で整備）から自動生成する機構
3. 生成物の出口を **コンプラチェッカー v2.2** に接続（`compliance_checklist_v2.md §6` の出口プロンプト適用）
4. VSL用プロンプトを `~/projects/prompts/prompt_library_v0.md` に移植（Phase 2）
5. 必要に応じ `funnel-generator_design_memo.md` を規約キット §3 雛形で新規作成

## ハマりポイント・注意（次回の自分への警告）
- **secretsは絶対に `.git/config` に書かない**。SSHで統一。過去にトークン直書き事故あり
- `FUNNEL_PASS` は fail-closed 設計：未設定だとアプリが起動しない仕様（安全側）
- `outlines/` `output/` `jobs/` はgit管理外（生成物）。共有したい場合はサンプルを別途コミット
- `references/` 内の参考ファネル（HTML抽出済みコピー）は著作物由来 → 外部公開しない
- モデルID変更時は `outline.py` `generator.py` `reference_loader.py` `run_optin.py` の4ファイル横断

## 将来メモ
- Next.js+Clerk+Supabase+Vercel移行構想（Phase 4）
- 商品マスターDB化（Supabase）と連動
- 生成物へのコンプラチェッカー自動接続（出口プロンプトをジョブ末尾に組み込み）

## クラウド資産・外部リンク
- GitHubリポ：`git@github.com:aimasterschool-hub/funnel-generator.git`
- 参照文書：`~/projects/master_system_blueprint_v1.1.md`（ライン2）／`~/projects/compliance_checklist_v2.md`（出口チェック）／`~/projects/prompts/prompt_library_v0.md`（プロンプト骨格）
