"""
main.py - ファネル自動生成ツール エントリーポイント

使い方:
  python main.py \\
    --optin  samples/optin.html \\
    --vsl    samples/vsl.png \\
    --sales  samples/sales.html \\
    --script scripts/script.txt \\
    [--html]
"""

import argparse
import sys
from pathlib import Path

from analyzer import analyze_sample
from generator import generate_page, build_all_image_briefs
from html_builder import markdown_to_html

PAGE_CONFIGS = [
    ("optin", "オプトインLP", "optin_lp"),
    ("vsl", "VSLファネル", "vsl_funnel"),
    ("sales", "販売LP", "sales_lp"),
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="台本からオプトインLP・VSLファネル・販売LPを自動生成するツール"
    )
    parser.add_argument("--optin", required=True, help="オプトインLPのサンプルファイル (.html/.png/.jpg)")
    parser.add_argument("--vsl", required=True, help="VSLファネルのサンプルファイル (.html/.png/.jpg)")
    parser.add_argument("--sales", required=True, help="販売LPのサンプルファイル (.html/.png/.jpg)")
    parser.add_argument("--script", required=True, help="台本テキストファイル (.txt)")
    parser.add_argument("--html", action="store_true", help="HTMLファイルも出力する")
    parser.add_argument("--output", default="output", help="出力ディレクトリ (デフォルト: output)")
    return parser.parse_args()


def load_script(path: str) -> str:
    p = Path(path)
    if not p.exists():
        print(f"[ERROR] 台本ファイルが見つかりません: {path}", file=sys.stderr)
        sys.exit(1)
    return p.read_text(encoding="utf-8", errors="ignore")


def ensure_output_dir(output_dir: str) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    return out


def main():
    args = parse_args()
    sample_map = {"optin": args.optin, "vsl": args.vsl, "sales": args.sales}

    print("=== ファネル自動生成ツール ===\n")

    # 台本を読み込む
    print(f"[1/3] 台本を読み込み中: {args.script}")
    script = load_script(args.script)
    print(f"      台本: {len(script)} 文字\n")

    out_dir = ensure_output_dir(args.output)
    all_image_briefs = []

    for page_key, page_label, file_stem in PAGE_CONFIGS:
        sample_file = sample_map[page_key]
        print(f"[処理] {page_label} ({sample_file})")

        # ステップ1: サンプル解析
        print(f"  → サンプル解析中...")
        try:
            structure = analyze_sample(sample_file, page_key)
        except FileNotFoundError as e:
            print(f"  [ERROR] {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"  [ERROR] サンプル解析に失敗しました: {e}", file=sys.stderr)
            sys.exit(1)

        sections = structure.get("sections", [])
        print(f"  → {len(sections)} セクションを検出")

        # ステップ2: テキスト・画像指示書生成
        print(f"  → コンテンツ生成中（{len(sections)} セクション）...")
        try:
            md_content, image_briefs = generate_page(structure, script, page_key)
        except Exception as e:
            print(f"  [ERROR] コンテンツ生成に失敗しました: {e}", file=sys.stderr)
            sys.exit(1)

        # 画像指示書にページラベルを付与
        for brief in image_briefs:
            brief["_page"] = page_label
        all_image_briefs.extend(image_briefs)

        # Markdown出力
        md_path = out_dir / f"{file_stem}.md"
        md_path.write_text(md_content, encoding="utf-8")
        print(f"  → 出力: {md_path}")

        # HTML出力（オプション）
        if args.html:
            html_content = markdown_to_html(md_content, page_label)
            html_path = out_dir / f"{file_stem}.html"
            html_path.write_text(html_content, encoding="utf-8")
            print(f"  → 出力: {html_path}")

        print()

    # 画像指示書まとめ
    print("[2/3] 画像指示書まとめを生成中...")
    briefs_md = build_all_image_briefs(all_image_briefs)
    briefs_path = out_dir / "all_image_briefs.md"
    briefs_path.write_text(briefs_md, encoding="utf-8")
    print(f"  → 出力: {briefs_path}\n")

    print("[3/3] 完了!")
    print(f"\n生成ファイル一覧 ({out_dir}/):")
    for f in sorted(out_dir.iterdir()):
        size_kb = f.stat().st_size / 1024
        print(f"  {f.name} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
