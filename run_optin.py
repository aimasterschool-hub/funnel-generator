"""
run_optin.py - オプトインLP専用生成スクリプト

使い方:
  python3 run_optin.py --script scripts/AutoEdge1話.docx
  python3 run_optin.py  # デフォルトパスで実行

設定YAML自動検出:
  scripts/AutoEdge1話.docx があれば scripts/AutoEdge1話.yaml を自動読み込み。
  YAMLが存在しない場合は台本から自動抽出して生成・保存する。
  --config で明示的に指定した場合はそちらを優先する。
"""

import argparse
import sys
import yaml
import anthropic
from pathlib import Path
from typing import Optional
from docx import Document

from analyzer import analyze_sample_multi_images
from generator import generate_page
from html_builder import markdown_to_html

client = anthropic.Anthropic()


def load_script_docx(path: Path) -> str:
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def load_script(path_str: str) -> str:
    p = Path(path_str)
    if not p.exists():
        print(f"[ERROR] 台本ファイルが見つかりません: {path_str}", file=sys.stderr)
        sys.exit(1)
    if p.suffix.lower() == ".docx":
        return load_script_docx(p)
    return p.read_text(encoding="utf-8", errors="ignore")


def resolve_config_path(script_path: str, explicit_config: Optional[str]) -> Path:
    """設定YAMLのパスを解決する。明示指定 > 台本同名 > なし の優先順位。"""
    if explicit_config:
        return Path(explicit_config)
    # 台本と同じディレクトリ・同じ名前の .yaml
    p = Path(script_path)
    return p.parent / (p.stem + ".yaml")


def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        return {}
    with config_path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def extract_config_from_script(script: str, save_path: Path) -> dict:
    """台本テキストからClaude APIで情報を抽出し、YAMLとして保存して返す。"""
    print(f"    YAMLを自動生成中（Claude APIで台本を解析）...")

    prompt = f"""以下は日本語のセールスファネル台本です。
この台本を分析して、ファネル設定情報を抽出してください。
抽出できない項目は null にしてください。

出力は以下のYAML形式で。説明文・コードブロック記号は不要、YAMLのみ出力してください。

seller:
  name:          # 販売者の名前
  age:           # 年齢（数値）
  education:     # 学歴
  career_before: # 前職・経歴
  personality:   # 性格・信条（複数行可）
  turning_point: # 転機・挫折エピソード（複数行可）
  recovery:      # 這い上がりの過程（複数行可）
  insight:       # 発見した手法・気づきの本質（複数行可）
  mission:       # ミッション・使命（複数行可）
  collaborator:
    name:        # 共同開発者名（いれば）
    background:  # 共同開発者の経歴
    role:        # 共同開発者の役割

product:
  name:              # 商品名（正式名称）
  name_short:        # 商品名（略称）
  concept:           # 商品コンセプト（複数行可）
  mechanism:         # 仕組み・手法の説明（複数行可）
  price_original:    # 通常価格
  price_now:         # 現在の提供価格
  condition_for_free: # 無料提供の条件（複数行可）
  caution:           # 注意事項（複数行可）
  users:             # ユーザー数・実績規模
  series:            # シリーズ・話数構成

results:
  headline:      # 実績の一言キャッチ
  target_monthly: # 目標月収
  seed_money:    # 必要元手
  evidence:
    - type:      # 取引種別
      detail:    # 詳細（元手・回数・利益）
  monthly_track_record:
    - period:    # 期間
      type:      # 取引種別
      amount:    # 金額

target_audience:
  description:   # ターゲット読者の説明
  pain_points:   # 悩み・ペインポイントのリスト
    -
  economic_context: # 経済的背景（複数行可）

cta:
  primary_button:  # ボタンテキスト
  question:        # 登録前の質問文
  urgency:         # 緊急性・希少性の訴求

--- 台本 ---
{script}
---"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )

    yaml_text = response.content[0].text.strip()
    # コードブロックが含まれている場合は除去
    if yaml_text.startswith("```"):
        lines = yaml_text.splitlines()
        yaml_text = "\n".join(
            line for line in lines
            if not line.startswith("```")
        )

    config = yaml.safe_load(yaml_text) or {}

    save_path.write_text(yaml_text, encoding="utf-8")
    print(f"    設定YAMLを保存しました: {save_path}")
    return config


VERIFY_FIELDS = [
    # (YAMLのキーパス,          質問文,                              例)
    (["seller", "gender"],     "販売者の性別",                       "女性 / 男性"),
    (["seller", "name"],       "販売者の名前",                       "例: かとう"),
    (["seller", "appearance"], "販売者の外見・雰囲気（画像生成に使用）", "例: 30代女性、黒髪ショート、知的な雰囲気"),
    (["product", "name"],      "商品名（正式名称）",                  "例: Sign Edge"),
]


def _analyze_appearance_from_photo(photo_path: str) -> str:
    """写真ファイルをVision APIで分析して外見・雰囲気の説明文を返す"""
    import base64
    p = Path(photo_path)
    if not p.exists():
        print(f"  [エラー] ファイルが見つかりません: {photo_path}")
        return ""
    ext = p.suffix.lower()
    media_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                 ".png": "image/png", ".webp": "image/webp"}
    media_type = media_map.get(ext, "image/jpeg")
    data = base64.standard_b64encode(p.read_bytes()).decode("utf-8")

    print("  写真を分析中...")
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": data}},
                {"type": "text", "text": (
                    "この写真に写っている人物の外見・雰囲気を、LP画像制作の指示書に使えるよう日本語で説明してください。"
                    "年代・髪型・髪色・体型・服装・表情・全体の雰囲気を簡潔に1〜2文で記述してください。"
                    "説明文のみ出力してください。"
                )},
            ],
        }],
    )
    return response.content[0].text.strip()


def _ask_appearance() -> str:
    """販売者の外見を写真分析か手動入力で取得する"""
    print("\n  販売者の外見・雰囲気の設定方法を選んでください:")
    print("    1: 写真ファイルを指定して自動分析（Claude Vision）")
    print("    2: テキストで手動入力")
    print("    Enter: スキップ")
    try:
        choice = input("  選択 > ").strip()
    except EOFError:
        return ""

    if choice == "1":
        try:
            path = input("  写真ファイルのパスを入力してください > ").strip()
        except EOFError:
            return ""
        return _analyze_appearance_from_photo(path)
    elif choice == "2":
        try:
            return input("  外見・雰囲気を入力してください（例: 30代女性、黒髪ショート、知的な雰囲気）> ").strip()
        except EOFError:
            return ""
    return ""


def verify_config(config: dict, config_path: Path) -> dict:
    """未設定の必須項目をユーザーに確認して補完し、YAMLに保存する"""
    missing = []
    for keys, label, example in VERIFY_FIELDS:
        obj = config
        for k in keys[:-1]:
            if not isinstance(obj.get(k), dict):
                obj[k] = {}
            obj = obj[k]
        if not obj.get(keys[-1]):
            missing.append((obj, keys[-1], label, example))

    if not missing:
        return config

    import sys
    if not sys.stdin.isatty():
        # 非対話環境（バックグラウンド実行など）はスキップ
        fields = ", ".join(label for _, _, label, _ in missing)
        print(f"\n[スキップ] 未設定項目あり（{fields}）。対話ターミナルで実行すると入力できます。\n")
        return config

    print("\n[確認] 以下の項目が未設定です。入力してください（Enterでスキップ）:")
    updated = False
    for obj, key, label, example in missing:
        if key == "appearance":
            val = _ask_appearance()
        else:
            try:
                val = input(f"  {label}（{example}）> ").strip()
            except EOFError:
                val = ""
        if val:
            obj[key] = val
            updated = True

    if updated:
        # YAMLに書き戻す（ruamel使わず safe_dump で上書き）
        import yaml as _yaml
        with config_path.open("w", encoding="utf-8") as f:
            _yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        print(f"    設定を更新しました: {config_path}\n")

    return config


def config_to_text(config: dict) -> str:
    """YAMLの設定情報を自然言語テキストに変換してプロンプトに埋め込む"""
    if not config:
        return ""

    lines = ["=== ファネル設定情報（必ずこの情報を使うこと）===\n"]

    seller = config.get("seller", {}) or {}
    if seller:
        lines.append("【販売者プロフィール】")
        if seller.get("name"):
            lines.append(f"名前: {seller['name']}")
        if seller.get("gender"):
            lines.append(f"性別: {seller['gender']}")
        if seller.get("age"):
            lines.append(f"年齢: {seller['age']}歳")
        if seller.get("appearance"):
            lines.append(f"外見・雰囲気: {seller['appearance']}")
        if seller.get("education"):
            lines.append(f"最終学歴: {seller['education']}")
        if seller.get("career_before"):
            lines.append(f"前職: {seller['career_before']}")
        if seller.get("personality"):
            lines.append(f"性格・信条:\n{str(seller['personality']).strip()}")
        if seller.get("turning_point"):
            lines.append(f"転機・挫折:\n{str(seller['turning_point']).strip()}")
        if seller.get("recovery"):
            lines.append(f"這い上がりの過程:\n{str(seller['recovery']).strip()}")
        if seller.get("insight"):
            lines.append(f"発見した手法の本質:\n{str(seller['insight']).strip()}")
        if seller.get("mission"):
            lines.append(f"ミッション・使命:\n{str(seller['mission']).strip()}")
        collab = seller.get("collaborator") or {}
        if collab and collab.get("name"):
            lines.append(f"共同開発者: {collab['name']} （{collab.get('background', '')}）")
            lines.append(f"役割: {collab.get('role', '')}")
        lines.append("")

    product = config.get("product", {}) or {}
    if product:
        lines.append("【商品情報】")
        if product.get("name"):
            lines.append(f"商品名: {product['name']}")
        if product.get("concept"):
            lines.append(f"コンセプト:\n{str(product['concept']).strip()}")
        if product.get("mechanism"):
            lines.append(f"仕組み:\n{str(product['mechanism']).strip()}")
        if product.get("price_original"):
            lines.append(f"通常価格: {product['price_original']}")
        if product.get("price_now"):
            lines.append(f"提供価格: {product['price_now']}")
        if product.get("condition_for_free"):
            lines.append(f"無料提供の条件:\n{str(product['condition_for_free']).strip()}")
        if product.get("caution"):
            lines.append(f"注意事項:\n{str(product['caution']).strip()}")
        if product.get("users"):
            lines.append(f"ユーザー数: {product['users']}")
        if product.get("series"):
            lines.append(f"シリーズ構成: {product['series']}")
        lines.append("")

    results = config.get("results", {}) or {}
    if results:
        lines.append("【実績データ】")
        if results.get("headline"):
            lines.append(f"キャッチ: {results['headline']}")
        if results.get("target_monthly"):
            lines.append(f"目標月収: {results['target_monthly']}")
        if results.get("seed_money"):
            lines.append(f"必要元手: {results['seed_money']}")
        for ev in results.get("evidence") or []:
            lines.append(f"・{ev.get('type', '')}: {ev.get('detail', '')}")
        records = results.get("monthly_track_record") or []
        if records:
            lines.append("月次実績:")
            for rec in records:
                lines.append(f"・{rec.get('period', '')} {rec.get('type', '')} {rec.get('amount', '')}")
        lines.append("")

    audience = config.get("target_audience", {}) or {}
    if audience:
        lines.append("【ターゲット読者】")
        if audience.get("description"):
            lines.append(f"対象: {audience['description']}")
        for pain in audience.get("pain_points") or []:
            if pain:
                lines.append(f"・{pain}")
        if audience.get("economic_context"):
            lines.append(f"経済的背景:\n{str(audience['economic_context']).strip()}")
        lines.append("")

    cta = config.get("cta", {}) or {}
    if cta:
        lines.append("【CTA情報】")
        if cta.get("primary_button"):
            lines.append(f"ボタンテキスト: {cta['primary_button']}")
        if cta.get("question"):
            lines.append(f"質問文: {cta['question']}")
        if cta.get("urgency"):
            lines.append(f"緊急性: {cta['urgency']}")

    lines.append("\n=== 設定情報ここまで ===")
    return "\n".join(lines)


def parse_args():
    parser = argparse.ArgumentParser(description="オプトインLPをサンプル画像と台本から生成する")
    parser.add_argument(
        "--images",
        nargs="+",
        default=sorted(str(p) for p in Path("samples").glob("IMG_*.PNG")),
        help="サンプル画像ファイル（複数指定可）",
    )
    parser.add_argument(
        "--script",
        default="scripts/AutoEdge1話.docx",
        help="台本ファイル (.txt または .docx)",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="設定YAMLファイル（省略時は台本と同名のYAMLを自動検出）",
    )
    parser.add_argument("--html", action="store_true", help="HTMLファイルも出力する")
    parser.add_argument("--output", default="output", help="出力ディレクトリ")
    return parser.parse_args()


def main():
    args = parse_args()

    print("=== オプトインLP 生成 ===\n")

    # 台本読み込み
    print(f"[1] 台本を読み込み中: {args.script}")
    script = load_script(args.script)
    print(f"    {len(script)} 文字\n")

    # 設定YAML解決（自動検出 or 明示指定）
    config_path = resolve_config_path(args.script, args.config)
    print(f"[2] 設定YAMLを確認中: {config_path}")
    if config_path.exists():
        config = load_config(config_path)
        print(f"    既存YAMLを読み込みました\n")
    else:
        print(f"    YAMLが見つかりません。台本から自動生成します...")
        config = extract_config_from_script(script, config_path)
        print()

    config_text = config_to_text(config)

    # サンプル画像解析
    print(f"[3] サンプル画像を解析中 ({len(args.images)} 枚)...")
    for img in args.images:
        print(f"    {img}")
    structure = analyze_sample_multi_images(args.images, "optin")
    sections = structure.get("sections", [])
    print(f"    {len(sections)} セクションを検出\n")

    # コンテンツ生成（設定情報＋台本を渡す）
    combined_source = config_text + "\n\n" + script if config_text else script
    print(f"[4] コンテンツを生成中 ({len(sections)} セクション)...")
    md_content, image_briefs = generate_page(structure, combined_source, "optin")

    # 出力
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 出力ファイル名を台本名から生成
    stem = Path(args.script).stem
    md_path = out_dir / f"{stem}_optin_lp.md"
    md_path.write_text(md_content, encoding="utf-8")
    print(f"\n[完了] {md_path}")

    if args.html:
        html_path = out_dir / f"{stem}_optin_lp.html"
        html_content = markdown_to_html(md_content, "オプトインLP")
        html_path.write_text(html_content, encoding="utf-8")
        print(f"[完了] {html_path}")

    print(f"\n画像指示書: {len(image_briefs)} 件生成")


if __name__ == "__main__":
    main()
