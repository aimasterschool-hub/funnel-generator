"""
generate.py - ファネル自動生成ツール（メインエントリー）

使い方:
  python3 generate.py --script scripts/AutoEdge1話.docx
  python3 generate.py  # デフォルト台本で実行
"""

import argparse
import sys
import yaml
import anthropic
from pathlib import Path
from typing import Optional
from docx import Document

from analyzer import get_sample_structure
from generator import generate_page
from html_builder import markdown_to_html
from outline import get_outline
from run_optin import load_script, resolve_config_path, load_config, \
                      config_to_text, extract_config_from_script, verify_config

client = anthropic.Anthropic()

FUNNEL_TYPES = {
    "1": ("optin",        "オプトインLP"),
    "2": ("video_funnel", "動画ファネル"),
    "3": ("sales_lp",     "販売LP"),
}

LENGTHS = {
    "1": ("long",  "ロング"),
    "2": ("short", "ショート"),
}

OUTPUT_STEMS = {
    "optin":        "optin_lp",
    "video_funnel": "video_funnel",
    "sales_lp":     "sales_lp",
}


def ask_funnel_type() -> tuple[str, str]:
    print("どのファネルを作りますか？")
    for key, (_, label) in FUNNEL_TYPES.items():
        print(f"  {key}: {label}")
    while True:
        choice = input("番号を入力 > ").strip()
        if choice in FUNNEL_TYPES:
            page_type, label = FUNNEL_TYPES[choice]
            print(f"  → {label}\n")
            return page_type, label
        print("  1〜3 で入力してください")


def ask_length() -> tuple[str, str]:
    print("ロング / ショート どちらですか？")
    for key, (_, label) in LENGTHS.items():
        print(f"  {key}: {label}")
    while True:
        choice = input("番号を入力 > ").strip()
        if choice in LENGTHS:
            length, label = LENGTHS[choice]
            print(f"  → {label}\n")
            return length, label
        print("  1〜2 で入力してください")


def parse_args():
    parser = argparse.ArgumentParser(description="ファネルを台本から自動生成する")
    parser.add_argument(
        "--script",
        default="scripts/AutoEdge1話.docx",
        help="台本ファイル (.txt または .docx)",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="設定YAMLファイル（省略時は台本と同名を自動検出）",
    )
    parser.add_argument(
        "--type",
        choices=["optin", "video_funnel", "sales_lp"],
        default=None,
        help="ファネル種類（省略時は対話選択）",
    )
    parser.add_argument(
        "--length",
        choices=["long", "short"],
        default=None,
        help="ロング/ショート（省略時は対話選択）",
    )
    parser.add_argument("--html", action="store_true", help="HTMLファイルも出力する")
    parser.add_argument("--output", default="output", help="出力ディレクトリ")
    return parser.parse_args()


def main():
    args = parse_args()

    print("=" * 50)
    print("  ファネル自動生成ツール")
    print("=" * 50 + "\n")

    # ① ファネル種類・長さを選択（引数指定があればスキップ）
    if args.type:
        page_type = args.type
        type_label = FUNNEL_TYPES[[k for k, v in FUNNEL_TYPES.items() if v[0] == args.type][0]][1]
    else:
        page_type, type_label = ask_funnel_type()

    if args.length:
        length = args.length
        length_label = LENGTHS[[k for k, v in LENGTHS.items() if v[0] == args.length][0]][1]
    else:
        length, length_label = ask_length()

    # ② 台本読み込み
    print(f"[1] 台本を読み込み中: {args.script}")
    script = load_script(args.script)
    print(f"    {len(script)} 文字\n")

    # ③ 設定YAML（販売者・商品情報）
    config_path = resolve_config_path(args.script, args.config)
    print(f"[2] 設定YAMLを確認中: {config_path}")
    if config_path.exists():
        config = load_config(config_path)
        print(f"    既存YAMLを読み込みました")
    else:
        print(f"    YAMLが見つかりません。台本から自動生成します...")
        config = extract_config_from_script(script, config_path)
    config = verify_config(config, config_path)
    config_text = config_to_text(config)

    # ④ 台本骨子（生成コスト削減のためキャッシュ利用）
    print(f"[3] 台本骨子を確認中...")
    outline, from_cache = get_outline(script, args.script)
    if from_cache:
        print(f"    既存の骨子を再利用しました: {args.script.replace('.docx','').replace('.txt','')}_骨子.md\n")
    else:
        print(f"    骨子を新規生成・保存しました\n")

    # ⑤ サンプル構造読み込み（キャッシュあれば無料）
    print(f"[4] サンプル構造を読み込み中 ({type_label} / {length_label})...")
    try:
        structure = get_sample_structure(page_type, length)
        sections = structure.get("sections", [])
        cached = (Path(f"samples/{page_type}/{length}/structure.json")).exists()
        status = "キャッシュから読み込み" if cached else "新規解析・保存"
        print(f"    {len(sections)} セクション検出（{status}）\n")
    except FileNotFoundError as e:
        print(f"    [ERROR] {e}", file=sys.stderr)
        print(f"    samples/{page_type}/{length}/ にサンプルファイルを追加してください。", file=sys.stderr)
        sys.exit(1)

    # ⑥ コンテンツ生成（骨子＋設定情報を使用）
    combined_source = "\n\n".join(filter(None, [config_text, outline]))
    print(f"[5] コンテンツを生成中 ({len(sections)} セクション)...")
    md_content, image_briefs = generate_page(structure, combined_source, page_type, length)

    # ⑦ 出力
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    script_stem = Path(args.script).stem
    out_stem = f"{script_stem}_{OUTPUT_STEMS[page_type]}_{length}"

    md_path = out_dir / f"{out_stem}.md"
    md_path.write_text(md_content, encoding="utf-8")
    print(f"\n[完了] {md_path}")

    if args.html:
        html_path = out_dir / f"{out_stem}.html"
        html_content = markdown_to_html(md_content, f"{type_label}（{length_label}）", str(out_dir))
        html_path.write_text(html_content, encoding="utf-8")
        print(f"[完了] {html_path}")

    print(f"\n画像指示書: {len(image_briefs)} 件生成")
    print(f"\n{'=' * 50}")


if __name__ == "__main__":
    main()
