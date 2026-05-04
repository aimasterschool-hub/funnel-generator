"""
analyzer.py - サンプルページの骨子解析モジュール
HTMLファイルまたはスクショ画像から、各セクションの構造を把握する
"""

import base64
import json
from pathlib import Path
from bs4 import BeautifulSoup
import anthropic

client = anthropic.Anthropic()


def _extract_json(text: str) -> dict:
    """括弧の深さを追跡して最初の完全なJSONオブジェクトを抽出する"""
    start = text.find("{")
    if start == -1:
        raise ValueError("JSONオブジェクトが見つかりません")
    depth = 0
    in_string = False
    escape_next = False
    for i, ch in enumerate(text[start:], start):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start:i + 1])
    raise ValueError("対応する閉じ括弧が見つかりません")

SAMPLE_DIRS = {
    ("optin",            "long"):  "samples/optin/long",
    ("optin",            "short"): "samples/optin/short",
    ("video_funnel_ep1", "long"):  "samples/video_funnel_ep1/long",
    ("video_funnel_ep1", "short"): "samples/video_funnel_ep1/short",
    ("video_funnel_ep2", "long"):  "samples/video_funnel_ep2/long",
    ("video_funnel_ep2", "short"): "samples/video_funnel_ep2/short",
    ("video_funnel_ep3", "long"):  "samples/video_funnel_ep3/long",
    ("video_funnel_ep3", "short"): "samples/video_funnel_ep3/short",
    ("video_funnel_ep4", "long"):  "samples/video_funnel_ep4/long",
    ("video_funnel_ep4", "short"): "samples/video_funnel_ep4/short",
    ("video_funnel_ep5", "long"):  "samples/video_funnel_ep5/long",
    ("video_funnel_ep5", "short"): "samples/video_funnel_ep5/short",
    ("sales_lp",         "long"):  "samples/sales_lp/long",
    ("sales_lp",         "short"): "samples/sales_lp/short",
}

PAGE_TYPES = {
    "optin": "オプトインLP（メールアドレス登録ページ）",
    "vsl": "VSLファネル（動画セールスレターページ）",
    "sales": "販売LP（商品購入ページ）",
}


def analyze_sample_multi_images(image_paths: list, page_type: str) -> dict:
    """
    複数のスクリーンショット画像を1ページとして解析してページ骨子を返す。
    """
    media_type_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    page_label = PAGE_TYPES.get(page_type, page_type)

    content = []
    for img_path in image_paths:
        p = Path(img_path)
        media_type = media_type_map.get(p.suffix.lower(), "image/png")
        data = base64.standard_b64encode(p.read_bytes()).decode("utf-8")
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": data},
        })

    content.append({
        "type": "text",
        "text": f"""上の画像は「{page_label}」を上から下にスクロールしながら撮影したスクリーンショットです。
これらを1つの縦長ページとして見て、セクション構造を上から順番に把握してください。
各セクションについて、以下を日本語で記述してください：
- セクション名（例: ヒーロー, 特典一覧, CTA など）
- テキストブロックの内容・役割
- 画像ブロックの内容・役割（存在する場合）
生のHTMLではなく、構造の説明文として出力してください。""",
    })

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        messages=[{"role": "user", "content": content}],
    )
    raw_summary = response.content[0].text
    return _call_structure_api(raw_summary, page_type, source="multi-image")


def analyze_sample(file_path: str, page_type: str) -> dict:
    """
    サンプルファイルを解析してページ骨子を返す。
    HTMLファイルとスクショ画像の両方に対応。
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"サンプルファイルが見つかりません: {file_path}")

    suffix = path.suffix.lower()
    if suffix in (".html", ".htm"):
        return _analyze_html(path, page_type)
    elif suffix in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
        return _analyze_image(path, page_type)
    else:
        raise ValueError(f"対応していないファイル形式です: {suffix}")


def _analyze_html(path: Path, page_type: str) -> dict:
    """HTMLファイルをBeautifulSoupで解析してセクション構造を抽出"""
    html = path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "html.parser")

    # スクリプト・スタイルを除去してテキストを抽出
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    # セクション候補タグを収集
    section_tags = soup.find_all(
        ["section", "div", "header", "footer", "main", "article"],
        recursive=False,
    )
    if not section_tags:
        section_tags = soup.find_all(["section", "div"], limit=20)

    # テキストと画像URLをまとめたサマリーを作成
    summary_lines = []
    for tag in section_tags[:30]:
        text = tag.get_text(separator=" ", strip=True)
        imgs = tag.find_all("img")
        img_info = [f"[画像: {img.get('alt', '無題')} src={img.get('src', '')[:60]}]" for img in imgs]
        if text or img_info:
            summary_lines.append(f"<block>{text[:300]} {' '.join(img_info)}</block>")

    raw_summary = "\n".join(summary_lines)

    # Claude APIでセクション骨子を構造化
    return _call_structure_api(raw_summary, page_type, source="HTML")


def _analyze_image(path: Path, page_type: str) -> dict:
    """スクショ画像をVision APIで解析してセクション構造を抽出"""
    image_data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")
    media_type_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    media_type = media_type_map.get(path.suffix.lower(), "image/png")

    page_label = PAGE_TYPES.get(page_type, page_type)
    prompt = f"""これは「{page_label}」のスクリーンショットです。
このページのセクション構造を上から順番に把握してください。
各セクションについて、以下を日本語で記述してください：
- セクション名（例: ヒーロー, 特典一覧, CTA など）
- テキストブロックの内容・役割
- 画像ブロックの内容・役割（存在する場合）
生のHTMLではなく、構造の説明文として出力してください。"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )
    raw_summary = response.content[0].text
    return _call_structure_api(raw_summary, page_type, source="image")


def _call_structure_api(raw_summary: str, page_type: str, source: str) -> dict:
    """
    生サマリーをClaude APIに渡してレイアウトテンプレートJSONを生成する。
    サンプルのテキスト内容は含めず、要素の種類・順序・役割のみを抽出する。
    """
    page_label = PAGE_TYPES.get(page_type, page_type)
    prompt = f"""以下は「{page_label}」のサンプルページ構造サマリーです（{source}から抽出）。

--- サマリー ---
{raw_summary}
---

【重要】これはレイアウトテンプレートの抽出です。
サンプルの具体的なテキスト内容・固有名詞・数字は一切含めないでください。
「どんな種類の要素が・どんな役割で・どの順番で並んでいるか」と「実際の文字量」を抽出してください。

このページを構成するセクションを上から順番に配列として、以下のJSON形式で出力してください。
必ずJSONのみを出力し、説明文は不要です。

{{
  "page_type": "{page_type}",
  "page_label": "{page_label}",
  "sections": [
    {{
      "id": "section_1",
      "name": "セクション名（英語スネークケース。例: hero, cta_primary, proof_results）",
      "type": "text | image | mixed",
      "role": "このセクションのマーケティング上の役割（サンプルの内容ではなく目的を記述）",
      "elements": [
        {{
          "kind": "要素の種類（headline / sub_headline / body_text / cta_button / image / step_list / bullet_list / banner_text / number_highlight / profile_text）",
          "desc": "この要素に入れるべきコンテンツの種類と役割（例：メイン実績数字、販売者の転機エピソード）。サンプルの文言は使わないこと",
          "char_limit": "サンプル画像を見て実際に表示されているテキストの文字数を推定した上限（整数）。画像要素はnull。例：キャッチコピー=20、ヘッドライン=40、本文=150、箇条書き1項目=50",
          "size": "画像の場合のサイズ（例: 1200x600px）。テキスト要素はnull"
        }}
      ]
    }}
  ]
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    try:
        return _extract_json(text)
    except (ValueError, json.JSONDecodeError) as e:
        raise ValueError(f"APIレスポンスからJSONを抽出できませんでした: {e}\n{text[:500]}")


def _analyze_docx_structure(docx_path: Path, page_type: str) -> dict:
    """
    構成ドキュメント（Word）からレイアウトテンプレートを抽出する。
    画像解析より正確にセクション構成を把握できる。
    """
    from docx import Document
    doc = Document(docx_path)
    docx_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    page_label = PAGE_TYPES.get(page_type, page_type)

    prompt = f"""以下は「{page_label}」の構成ドキュメント（Word）です。
このドキュメントにはページのセクション構成が記載されています。

【重要】これはレイアウトテンプレートの抽出です。
「どんな種類の要素が・どんな役割で・どの順番で並んでいるか」と「実際のLPに表示される文字数の上限」を抽出してください。
サンプルの具体的なテキスト内容・固有名詞は含めないでください。

--- 構成ドキュメント ---
{docx_text}
---

このページを構成するセクションを上から順番に配列として、以下のJSON形式で出力してください。
必ずJSONのみを出力し、説明文は不要です。

{{
  "page_type": "{page_type}",
  "page_label": "{page_label}",
  "sections": [
    {{
      "id": "section_1",
      "name": "セクション名（英語スネークケース）",
      "type": "text | image | mixed",
      "role": "このセクションのマーケティング上の役割",
      "elements": [
        {{
          "kind": "要素の種類（headline / sub_headline / body_text / cta_button / image / step_list / bullet_list / banner_text / number_highlight / profile_text）",
          "desc": "この要素に入れるべきコンテンツの種類と役割。サンプルの文言は使わないこと",
          "char_limit": "LPに実際に表示する文字数の上限（整数）。LPコピーは短く強くが原則。headline=20〜40、banner_text=15〜25、cta_button=20〜30、body_text=60〜150、bullet_list1項目=20〜40、profile_text=150〜300。画像はnull",
          "size": "画像の場合のサイズ（例: 1200x600px）。テキスト要素はnull"
        }}
      ]
    }}
  ]
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=6000,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    try:
        return _extract_json(text)
    except (ValueError, json.JSONDecodeError) as e:
        raise ValueError(f"Wordからの構造抽出に失敗: {e}\n{text[:500]}")


def get_sample_structure(page_type: str, length: str) -> dict:
    """
    サンプルフォルダの構成を解析してページ構造を返す。
    優先順位: キャッシュ > Word文書 > 画像 > HTML
    サンプルがない場合は同じファネル種類の別の長さにフォールバックする。
    """
    fallback_order = [length] + [l for l in ("long", "short") if l != length]
    sample_dir = None
    used_length = length
    for l in fallback_order:
        d = Path(SAMPLE_DIRS.get((page_type, l), ""))
        if d.exists() and (list(d.glob("*.docx")) or list(d.glob("*.png")) or
                           list(d.glob("*.PNG")) or list(d.glob("*.jpg")) or
                           (d / "structure.json").exists()):
            sample_dir = d
            used_length = l
            break
    if sample_dir is None:
        raise FileNotFoundError(f"サンプルファイルが見つかりません: samples/{page_type}/")
    if used_length != length:
        print(f"    [{length}] のサンプルがないため [{used_length}] で代替します")

    cache_path = sample_dir / "structure.json"

    # キャッシュがあれば返す
    if cache_path.exists():
        with cache_path.open(encoding="utf-8") as f:
            return json.load(f)

    # Word文書を優先（画像より正確にセクション構成を把握できる）
    docx_files = list(sample_dir.glob("*.docx"))
    image_files = sorted(sample_dir.glob("*.PNG")) + sorted(sample_dir.glob("*.png")) + \
                  sorted(sample_dir.glob("*.jpg")) + sorted(sample_dir.glob("*.jpeg"))
    html_files = list(sample_dir.glob("*.html")) + list(sample_dir.glob("*.htm"))

    if not docx_files and not image_files and not html_files:
        raise FileNotFoundError(f"サンプルファイルが見つかりません: {sample_dir}")

    if docx_files:
        print(f"    Wordドキュメントから構造を抽出中: {docx_files[0].name}")
        structure = _analyze_docx_structure(docx_files[0], page_type)
    elif image_files:
        structure = analyze_sample_multi_images([str(p) for p in image_files], page_type)
    else:
        structure = analyze_sample(str(html_files[0]), page_type)

    # length情報を付与してキャッシュ保存
    structure["length"] = length
    with cache_path.open("w", encoding="utf-8") as f:
        json.dump(structure, f, ensure_ascii=False, indent=2)

    return structure
