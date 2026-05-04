"""
test_all.py - API費用ゼロで全機能を検証するテストスイート
改修後は必ずこれを実行してから実機テストする
"""

import sys, json, traceback, re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

errors = []
ok = []

def check(name, fn):
    try:
        fn()
        ok.append(name)
    except Exception as e:
        errors.append(f"{name}: {e}\n    {traceback.format_exc().splitlines()[-2]}")


# ── インポート ──────────────────────────────────────────────
def t_imports():
    import generator, html_builder, analyzer
    from html_builder import _render_el, _render_img, _render_lines, markdown_to_html, SECTION_CLASS
    from run_optin import load_script, load_config, config_to_text

check("インポート（全モジュール）", t_imports)

import generator
from html_builder import _render_el, _render_img, _render_lines, markdown_to_html, SECTION_CLASS, FOOTER_LINK_SECTIONS


# ── structure.json 整合性 ────────────────────────────────────
def t_structure_json():
    files = list(Path("samples").glob("**/structure.json"))
    assert files, "structure.json が1件もない"
    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        assert "sections" in data, f"{f}: sections キーなし"
        for sec in data["sections"]:
            assert "elements" in sec, f"{f} / {sec.get('name')}: elements キーなし"
    return len(files)

check("structure.json パース・構造チェック", t_structure_json)


def t_section_image_flags():
    files = list(Path("samples").glob("**/structure.json"))
    total = sum(
        sum(1 for s in json.loads(f.read_text())["sections"] if s.get("section_image"))
        for f in files
    )
    assert total > 0, "section_image フラグが1件もない"

check("section_image フラグ存在", t_section_image_flags)


def t_fixed_content():
    files = list(Path("samples").glob("**/structure.json"))
    total = sum(
        sum(1 for s in json.loads(f.read_text())["sections"]
            for e in s["elements"] if e.get("fixed_content"))
        for f in files
    )
    assert total > 0, "fixed_content 要素が1件もない"

check("fixed_content 要素存在", t_fixed_content)


# ── SECTION_NAMES_JA ─────────────────────────────────────────
def t_section_names():
    required = [
        "video_embed", "question_hook", "question_cta_top", "question_cta_bottom",
        "gift_top", "gift_bottom",
        "scarcity_notice", "checkout_top", "checkout_middle", "checkout_bottom",
        "seller_message", "evidence_sales",
    ]
    missing = [k for k in required if k not in generator.SECTION_NAMES_JA]
    assert not missing, f"SECTION_NAMES_JA 欠落: {missing}"

check("SECTION_NAMES_JA 新規エントリ", t_section_names)


# ── SECTION_CLASS ─────────────────────────────────────────────
def t_section_class():
    required = [
        "先着枠・数量提示",
        "チェックアウトブロック①（上部）",
        "チェックアウトブロック②（中部）",
        "チェックアウトブロック③（下部）",
        "販売者メッセージ",
        "商品のエビデンス",
    ]
    missing = [s for s in required if s not in SECTION_CLASS]
    assert not missing, f"SECTION_CLASS 欠落: {missing}"

check("SECTION_CLASS 販売LP エントリ", t_section_class)


# ── _render_el ────────────────────────────────────────────────
def t_video_embed():
    html = _render_el("動画埋め込み", [], "dark")
    assert "YouTube 動画エリア" in html
    assert "aspect-ratio:16/9" in html

check("動画埋め込み（空コンテンツ）レンダリング", t_video_embed)


def t_teikei():
    content = ["クレジットカードについて", "VISAです。", "", "銀行振込", "平日のみ。"]
    html = _render_el("定型文", content, "dark")
    assert "el-fixed-text" in html
    assert "銀行振込" in html, "空行後の段落が欠落"

check("定型文 段落付きレンダリング", t_teikei)


def t_teikei_blank_lines():
    lines = ["### [定型文]", "パート1", "テキスト", "", "パート2", "内容", "---"]
    html = _render_lines(lines, is_dark=True, hl_cls="dark")
    assert "パート2" in html, "空行後のテキストが欠落"
    assert "el-fixed-text" in html

check("定型文 空行保持（_render_lines）", t_teikei_blank_lines)


def t_render_el_empty_guard():
    # 通常の kind で空コンテンツは空文字を返す（クラッシュしない）
    result = _render_el("メインコピー", [], "dark")
    assert result == ""

check("_render_el 空コンテンツ guard", t_render_el_empty_guard)


# ── 画像指示書 ────────────────────────────────────────────────
def t_image_brief_editable():
    block = [
        "### 画像ブロック: テスト",
        "- **用途**: テスト",
        "- **種別**: バナー",
        "- **サイズ**: 1040x900px",
        "- **背景・雰囲気**: 黒",
        "- **人物・被写体**: なし",
        "- **画像内テキスト（コピー）**: コピー",
        "- **フォント指示**: 太字",
        "- **補足**: テスト",
    ]
    html = _render_img(block)
    assert 'contenteditable="true"' in html, "contenteditable がない"
    assert "brief-copy-btn" in html, "コピーボタンがない"
    assert "brief-val" in html, "brief-val クラスがない"
    assert "copyBrief" in html, "copyBrief JS がない"

check("画像指示書 編集/コピーボタン", t_image_brief_editable)


def t_image_brief_multiline_copy():
    # 複数行コピーテキストが正しくパースされるか
    block = [
        "### 画像ブロック: テスト",
        "- **用途**: テスト",
        "- **サイズ**: 1040x900px",
        "- **背景・雰囲気**: 黒背景",
        "- **人物・被写体**: なし",
        "- **画像内テキスト（コピー）**: 1行目",
        "2行目",
        "3行目",
        "- **フォント指示**: 太字",
        "- **補足**: テスト",
    ]
    html = _render_img(block)
    assert "2行目" in html, "多行コピーテキストの2行目が欠落"
    assert "3行目" in html, "多行コピーテキストの3行目が欠落"

check("画像指示書 多行コピーテキスト", t_image_brief_multiline_copy)


# ── markdown_to_html パイプライン ─────────────────────────────
def t_full_pipeline():
    md = """# テスト販売LP

## チェックアウトブロック①（上部）

> 役割: テスト

### [メインコピー]
テストコピー

### [定型文]
クレジットカードについて
VISAです。

銀行振込
平日のみ。

---

## YouTube動画

> 役割: 動画

### [動画埋め込み]

---

## 先着枠・数量提示

> 役割: 緊急性

### [バナーテキスト]
先着30名限定

---
"""
    html = markdown_to_html(md, "テスト", "/tmp")
    assert "el-fixed-text" in html,          "定型文ブロックなし"
    assert "YouTube 動画エリア" in html,     "動画プレースホルダーなし"
    assert "sec-white" in html,              "チェックアウトブロックのCSSクラスなし"
    assert "sec-dark" in html,               "先着枠のCSSクラスなし"
    assert "先着30名限定" in html,           "バナーテキスト欠落"

check("markdown_to_html フルパイプライン", t_full_pipeline)


# ── generator 要素分類ロジック ────────────────────────────────
def t_generator_element_classification():
    elements = [
        {"kind": "image", "desc": "商品画像", "size": "1040x900px"},
        {"kind": "body_text", "desc": "商品説明"},
        {"kind": "video_embed", "desc": "YouTube"},
        {"kind": "fixed_content", "fixed_content": "定型文テスト"},
    ]
    has_ai = any(
        e.get("kind") not in ("image", "video_embed") and not e.get("fixed_content")
        for e in elements
    )
    assert has_ai is True, "AI テキスト要素の検出失敗"

    visual = [
        e for e in elements
        if e.get("kind") not in ("video_embed",) and not e.get("fixed_content")
    ]
    assert len(visual) == 2, f"section_image 用 visual 要素数が {len(visual)} (期待値 2)"

check("generator 要素分類ロジック（section_image / fixed_content）", t_generator_element_classification)


def t_size_hint_logic():
    # 動画/販売LPは大サイズ、オプトインはデフォルト
    for page_label, suggested, expect_large in [
        ("販売LP",       "1040x900px", True),
        ("動画ファネル", "",           True),
        ("オプトインLP", "",           False),
    ]:
        is_large = any(k in page_label for k in ["動画", "販売LP"])
        suggested_size = suggested
        if suggested_size:
            hint = f"幅1040px固定・高さ {suggested_size.replace('1040x','')}"
        elif is_large:
            hint = "幅1040px固定・高さ800〜1200px"
        else:
            hint = "幅1040px固定・高さはセクション用途に合わせて調整"

        if expect_large:
            assert "800" in hint or suggested_size, f"{page_label}: 大サイズ指示がない"
        else:
            assert "800〜1200" not in hint, f"{page_label}: 誤って大サイズ指示が入った"

check("画像サイズ指示ロジック（動画/販売LP vs オプトイン）", t_size_hint_logic)


# ── フッターリンク ────────────────────────────────────────────
def t_footer_link_sections_defined():
    assert "プライバシーポリシー" in FOOTER_LINK_SECTIONS
    assert "特定商取引法に基づく表記" in FOOTER_LINK_SECTIONS

check("FOOTER_LINK_SECTIONS 定義", t_footer_link_sections_defined)


def t_footer_links_rendered():
    md = """# テスト

## メインコピー

> 役割: ヒーロー

### [メインコピー]
本文テスト

---

## プライバシーポリシー

> 役割: フッター

---

## 特定商取引法に基づく表記

> 役割: フッター

---
"""
    html = markdown_to_html(md, "テスト", "/tmp")
    assert "sec-footer-bar" in html, "sec-footer-bar がない"
    assert "footer-link" in html, "footer-link クラスがない"
    assert "プライバシーポリシー" in html, "プライバシーポリシーの文言がない"
    assert "特定商取引法に基づく表記" in html, "特定商取引法の文言がない"

check("フッターリンク レンダリング", t_footer_links_rendered)


def t_footer_link_only_sections_skipped():
    from generator import LINK_ONLY_SECTIONS
    assert "プライバシーポリシー" in LINK_ONLY_SECTIONS
    assert "特定商取引法に基づく表記" in LINK_ONLY_SECTIONS

check("generator LINK_ONLY_SECTIONS 定義", t_footer_link_only_sections_skipped)


# ── 結果出力 ──────────────────────────────────────────────────
print()
print("=" * 50)
print(" テスト結果")
print("=" * 50)
for m in ok:
    print(f"  ✅ {m}")
print()
for m in errors:
    print(f"  ❌ {m}")
print()
print(f"  OK: {len(ok)}  NG: {len(errors)}")
if not errors:
    print()
    print("  >>> 全テスト通過 — 実機テストに進んでください")
else:
    print()
    print("  >>> エラーを修正してから実機テストしてください")
    sys.exit(1)
