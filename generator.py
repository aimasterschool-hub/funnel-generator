"""
generator.py - テキスト・画像指示書生成モジュール
ページ骨子と台本をもとに各セクションのコンテンツをClaude APIで生成する
"""

import json
from pathlib import Path
import anthropic

client = anthropic.Anthropic()

SECTION_NAMES_JA = {
    "hero":                    "ファーストビュー",
    "header":                  "ファーストビュー",
    "cta_primary_first":       "登録ボタン①（上部）",
    "cta_primary_1":           "登録ボタン①（上部）",
    "cta_primary":             "登録ボタン①（上部）",
    "incentive_detail":        "特典紹介",
    "gift_offer":              "特典紹介",
    "lead_magnet":             "特典紹介",
    "instruction_steps":       "受け取り方法",
    "registration_steps":      "受け取り方法",
    "cta_primary_second":      "登録ボタン②（中部）",
    "cta_primary_2":           "登録ボタン②（中部）",
    "cta_secondary":           "登録ボタン②（中部）",
    "pain_point_agitation":    "問題提起・共感",
    "problem_agitation":       "問題提起・共感",
    "solution_bridge":         "解決への橋渡し",
    "proof_results":           "実績証明",
    "proof_results_main":      "実績証明",
    "proof_results_additional":"実績証明（続き）",
    "proof_summary":           "実績まとめ",
    "total_results_highlight": "実績まとめ",
    "testimonial_stories":     "お客様の声",
    "social_proof_users":      "お客様の声",
    "author_profile":          "販売者プロフィール",
    "developer_profile":       "販売者プロフィール",
    "superiority_mechanism":   "優位性・仕組み",
    "system_superiority":      "優位性・仕組み",
    "feature_explanation":     "差別化ポイント",
    "differentiation":         "差別化ポイント",
    "gift_recap":              "特典再提示",
    "cta_final":               "クロージング",
    "cta_final_comprehensive": "クロージング",
    "footer":                  "フッター",
    # Word doc derived names
    "free_gift_cta_top":       "特典＋登録ボタン（上部）",
    "free_gift_cta_bottom":    "特典＋登録ボタン（下部）",
    "registration_flow":       "登録の流れ（上部）",
    "registration_flow_bottom":"登録の流れ（下部）",
    "evidence":                "エビデンス",
    "testimonials":            "利用者の声",
    "profile_introduction":    "販売者紹介",
    "system_detail":           "システム詳細",
    "privacy_policy":          "プライバシーポリシー",
    "specified_commercial_transaction": "特定商取引法に基づく表記",
    # 動画ファネル
    "video_embed":             "YouTube動画",
    "question_hook":           "質問投げかけ",
    "question_cta_top":        "質問回答ボタン（上部）",
    "question_cta_bottom":     "質問回答ボタン（下部）",
    "gift_top":                "プレゼント内容（上部）",
    "gift_bottom":             "プレゼント内容（下部）",
    # 販売LP
    "scarcity_notice":         "先着枠・数量提示",
    "checkout_top":            "チェックアウトブロック①（上部）",
    "checkout_middle":         "チェックアウトブロック②（中部）",
    "checkout_bottom":         "チェックアウトブロック③（下部）",
    "seller_message":          "販売者メッセージ",
    "evidence_sales":          "商品のエビデンス",
    # optin/short
    "cta_top":                 "登録ボタン（上部）",
    "cta_middle":              "登録ボタン（中部）",
    "cta_bottom":              "登録ボタン（下部）",
    "gift_detail":             "特典詳細",
    "how_to_receive":          "受け取り方法",
    # 動画ファネル共通
    "question":                "質問投げかけ",
    "self_introduction":       "自己紹介",
    "bonus_offer":             "特典オファー",
    "product_overview":        "商品概要",
}

# テキスト生成をスキップしてリンクのみ表示するセクション
LINK_ONLY_SECTIONS = {
    "プライバシーポリシー",
    "特定商取引法に基づく表記",
}

# structure.json に section_image フラグがなくても自動でバナー画像指示書を付与するセクション
AUTO_SECTION_IMAGE = {
    "特典＋登録ボタン（上部）", "特典＋登録ボタン（下部）",
    "登録ボタン（上部）", "登録ボタン（中部）", "登録ボタン（下部）",
    "登録ボタン①（上部）", "登録ボタン②（中部）",
    "特典詳細", "特典紹介", "特典再提示", "特典オファー",
    "クロージング",
    "質問回答ボタン（上部）", "質問回答ボタン（下部）",
    "プレゼント内容（上部）", "プレゼント内容（下部）",
    "チェックアウトブロック①（上部）", "チェックアウトブロック②（中部）", "チェックアウトブロック③（下部）",
}

LENGTH_GUIDE = {
    "long":  "各要素200〜400文字を目安に、読み応えのある文章で書いてください。",
    "short": "各要素50〜150文字を目安に、簡潔に要点だけ書いてください。",
}

# シンプルなセクションはHaikuで生成（コスト削減）
HAIKU_SECTIONS = {
    "登録の流れ（上部）",
    "登録の流れ（下部）",
    "プライバシーポリシー",
    "特定商取引法に基づく表記",
}

MODEL_SONNET = "claude-sonnet-4-6"
MODEL_HAIKU  = "claude-haiku-4-5-20251001"


KIND_NAMES_JA = {
    "headline":        "メインコピー",
    "sub_headline":    "サブコピー",
    "banner_text":     "バナーテキスト",
    "body_text":       "本文",
    "cta_button":      "ボタン",
    "bullet_list":     "箇条書き",
    "step_list":       "ステップリスト",
    "number_highlight":"数字ハイライト",
    "profile_text":    "プロフィール文",
    "image":           "画像",
}


def _section_display_name(name: str) -> str:
    return SECTION_NAMES_JA.get(name, name)


def _kind_display_name(kind: str) -> str:
    return KIND_NAMES_JA.get(kind, kind)


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

IMAGE_BRIEF_TEMPLATE = """### 画像ブロック: {purpose}

- **種別**: {kind}
- **サイズ**: {size}
- **背景・雰囲気**: {background}
- **人物・被写体**: {subject}
- **画像内テキスト（コピー）**: {copy_text}
- **フォント指示**: {font_spec}
- **補足**: {notes}
"""


def generate_page(structure: dict, script: str, page_type: str, length: str = "long") -> "tuple[str, list]":
    """
    1ページ分のMarkdownコンテンツ（テキスト＋画像指示書）を生成して返す。
    各セクションを個別のAPIコールで処理する。
    """
    page_label = structure.get("page_label", page_type)
    sections = structure.get("sections", [])

    lines = [f"# {page_label}\n"]
    all_image_briefs = []

    for section in sections:
        section_md, image_briefs = _generate_section(section, script, page_label, length)
        lines.append(section_md)
        all_image_briefs.extend(image_briefs)

    return "\n".join(lines), all_image_briefs


def _generate_section(section: dict, script: str, page_label: str, length: str = "long") -> "tuple[str, list]":
    """
    1セクション分のMarkdownと画像指示書リストを生成して返す。
    elements を定義順に処理し、fixed_content / video_embed / image / AI text を適切に扱う。
    """
    section_name = section.get("name", "セクション")
    role = section.get("role", "")
    elements = section.get("elements", [])
    display_name = _section_display_name(section_name)

    # 旧形式との互換性：elements がなければ text_blocks/image_blocks から変換
    if not elements:
        for tb in section.get("text_blocks", []):
            elements.append({"kind": "body_text", "desc": tb, "size": None})
        for ib in section.get("image_blocks", []):
            elements.append({
                "kind": "image",
                "desc": ib.get("notes", ib.get("purpose", "")),
                "size": ib.get("suggested_size"),
                "purpose": ib.get("purpose", ""),
            })

    # リンクのみセクション → テキスト生成スキップ（API呼び出しなし）
    if display_name in LINK_ONLY_SECTIONS:
        return f"## {display_name}\n\n---\n", []

    lines = [f"## {display_name}\n", f"> 役割: {role}\n"]
    image_briefs = []

    # ファーストビュー（画像のみセクション）はキャッチコピーを先に生成
    is_hero = any(k in section_name or k in display_name
                  for k in ["hero", "header", "ファーストビュー", "ヘッド"])
    has_ai_text = any(
        e.get("kind") not in ("image", "video_embed") and not e.get("fixed_content")
        for e in elements
    )
    has_images = any(e.get("kind") == "image" for e in elements)
    pre_copy = None
    if not has_ai_text and has_images and is_hero:
        pre_copy = _generate_catchcopy(display_name, role, script, page_label)
        lines.append(f"**【画像上のキャッチコピー】**\n\n{pre_copy}\n")

    # 要素を定義順に処理
    i = 0
    while i < len(elements):
        elem = elements[i]

        # fixed_content → verbatim 出力（API 呼び出しなし）
        if elem.get("fixed_content"):
            lines.append(f"### [定型文]\n{elem['fixed_content']}\n")
            i += 1
            continue

        # 動画埋め込み → プレースホルダーマーカーのみ出力
        if elem.get("kind") == "video_embed":
            lines.append("### [動画埋め込み]\n")
            i += 1
            continue

        # 画像要素 → 画像指示書を生成
        if elem.get("kind") == "image":
            img_block = {
                "purpose": elem.get("purpose") or elem.get("desc", ""),
                "suggested_size": elem.get("size") or "",
                "notes": elem.get("desc", ""),
            }
            brief_md, brief_data = _generate_image_brief(
                img_block, display_name, script, page_label,
                pre_copy=pre_copy if not has_ai_text else None,
            )
            lines.append(brief_md)
            image_briefs.append(brief_data)
            i += 1
            continue

        # AI テキスト要素：連続するものをまとめて 1 回の API 呼び出し
        batch = []
        while i < len(elements) and elements[i].get("kind") not in ("image", "video_embed") and not elements[i].get("fixed_content"):
            batch.append(elements[i])
            i += 1

        if batch:
            model = MODEL_HAIKU if display_name in HAIKU_SECTIONS else MODEL_SONNET
            text_content = _generate_text_content(
                display_name, role, batch, script, page_label, length, model
            )
            lines.append(text_content)

    # セクション全体を1枚の画像にする場合の指示書
    # structure.json の section_image フラグ、または AUTO_SECTION_IMAGE に含まれるセクションは自動生成
    if section.get("section_image") or display_name in AUTO_SECTION_IMAGE:
        visual_elems = [
            e for e in elements
            if e.get("kind") not in ("video_embed",) and not e.get("fixed_content")
        ]
        if visual_elems:
            elem_desc = "\n".join(
                f"- [{e.get('kind','')}] {e.get('desc','')}"
                for e in visual_elems
            )
            section_img_block = {
                "purpose": f"{display_name}セクション全体をひとつのバナー画像として制作する場合の指示書",
                "suggested_size": section.get("section_image_size", ""),
                "notes": (
                    f"役割: {role}\n\n"
                    f"画像内に含めるコンテンツ要素:\n{elem_desc}\n\n"
                    "※ テキスト量に応じて高さを調整すること（目安: 600〜1200px）"
                ),
            }
            brief_md, brief_data = _generate_image_brief(
                section_img_block, display_name, script, page_label
            )
            lines.append(brief_md)
            image_briefs.append(brief_data)

    lines.append("\n---\n")
    return "\n".join(lines), image_briefs


def _infer_kind(purpose: str) -> str:
    """purposeテキストから画像種別を推定する"""
    p = purpose
    if any(k in p for k in ["ヒーロー", "ファーストビュー", "バナー", "メインビジュアル"]):
        return "ヒーローバナー"
    if any(k in p for k in ["人物", "プロフィール", "顔", "写真"]):
        return "人物写真"
    if any(k in p for k in ["実績", "スクリーンショット", "エビデンス", "グラフ"]):
        return "実績・証拠画像"
    if any(k in p for k in ["図解", "説明", "システム", "仕組み"]):
        return "説明図解"
    if any(k in p for k in ["商品", "ツール", "アイコン"]):
        return "商品イメージ"
    return "画像"


def _generate_catchcopy(
    section_name: str, role: str, script: str, page_label: str
) -> str:
    """ファーストビュー画像に重ねるキャッチコピーを生成"""
    system = [
        {
            "type": "text",
            "text": f"【情報源（販売者・商品情報）】\n{script}",
            "cache_control": {"type": "ephemeral"},
        }
    ]
    user_prompt = (
        f"「{page_label}」のファーストビュー画像に重ねる3〜4行のキャッチコピーを作成してください。\n\n"
        f"【セクションの役割】{role}\n\n"
        "【ルール】\n"
        "- 1行目: 情報源にある最も強い数字・実績（例: 元手1万円で毎月60万円）\n"
        "- 2行目: 誰が・何が・差別化要素\n"
        "- 3行目: 提供・行動喚起（例: 今だけ無償提供）\n"
        "- 各行15〜25文字以内\n"
        "- 情報源に登場する数字・固有名詞のみ使うこと\n"
        "- 説明・前置き不要。キャッチコピーのみ出力"
    )
    response = client.messages.create(
        model=MODEL_SONNET,
        max_tokens=200,
        system=system,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return response.content[0].text.strip()


def _generate_text_content(
    section_name: str,
    role: str,
    text_elements: list,
    script: str,
    page_label: str,
    length: str = "long",
    model: str = MODEL_SONNET,
) -> str:
    """セクションのテキストコンテンツをClaude APIで生成（プロンプトキャッシュ対応）"""
    elements_desc = "\n".join(
        "{}. [{}] {} {}".format(
            i + 1,
            _kind_display_name(e.get("kind", "text")),
            e.get("desc", ""),
            "（上限{}文字）".format(e["char_limit"]) if e.get("char_limit") else "",
        )
        for i, e in enumerate(text_elements)
    )

    # 情報源をsystem promptに置いてキャッシュ（5分間有効）
    system = [
        {
            "type": "text",
            "text": (
                "あなたは日本語のセールスコピーライターです。\n\n"
                "【厳守ルール】\n"
                "- テキストはすべて以下の情報源の内容・登場人物・数字・商品名に基づいて生成すること\n"
                "- 情報源に登場しない固有名詞・数字・人物名は絶対に使わないこと\n"
                "- 各要素に「上限○文字」と書かれている場合は必ずその文字数以内に収めること\n"
                "- LPは読まれるものではなく「見られるもの」。短く・強く・一瞬で伝わる文章にすること\n\n"
                f"【情報源（販売者情報・商品情報・台本）】\n{script}"
            ),
            "cache_control": {"type": "ephemeral"},
        }
    ]

    user_prompt = (
        f"「{page_label}」の「{section_name}」セクションのテキストを作成してください。\n\n"
        f"【セクションの役割】\n{role}\n\n"
        f"【レイアウト要素（この順番で書く。文字数上限を厳守すること）】\n{elements_desc}\n\n"
        "【出力形式】\n"
        "- Markdownで出力してください\n"
        "- 各要素を見出し（###）で区切ってください\n"
        "- 余分な説明・前置き・コメントは不要です。コンテンツのみ出力してください"
    )

    response = client.messages.create(
        model=model,
        max_tokens=2000,
        system=system,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return response.content[0].text.strip() + "\n"


def _generate_image_brief(
    img_block: dict, section_name: str, script: str, page_label: str,
    pre_copy: "str | None" = None
) -> tuple[str, dict]:
    """画像指示書をClaude APIで生成し、MarkdownとdictのペアとしてReturn"""
    purpose = img_block.get("purpose", "画像")
    notes = img_block.get("notes", "")
    suggested_size = img_block.get("suggested_size", "")

    is_hero = any(k in section_name for k in ["ファーストビュー", "ヒーロー", "ヘッド", "hero", "header"])
    is_large_page = any(k in page_label for k in ["動画", "販売LP"])
    if suggested_size:
        size_hint = f"幅1040px固定・高さ {suggested_size.replace('1040x', '')}（指定サイズ: {suggested_size}）。AI画像生成ツールへの入稿を想定しているため、アスペクト比も明記すること"
    elif is_hero:
        size_hint = "幅1040px固定・高さ900〜1200px（ファーストビュー指定サイズ）。AI画像生成ツールへの入稿を想定しているため、アスペクト比も明記すること"
    elif is_large_page:
        size_hint = "幅1040px固定・高さ800〜1200pxの範囲でセクション用途に応じて決定。AI画像生成ツールへの入稿を想定しているため、アスペクト比も明記すること"
    else:
        size_hint = "幅1040px固定・高さはセクション用途に合わせて調整（目安: 人物写真=640px、エビデンス=800px）。AI画像生成ツールへの入稿を想定しているため、アスペクト比も明記すること"

    if pre_copy:
        copy_instruction = f"\n【確定コピー】以下のキャッチコピーをcopy_textにそのまま使用してください：\n{pre_copy}"
        copy_field = "← 上記【確定コピー】をそのまま入れること"
    else:
        copy_instruction = ""
        copy_field = "画像内に重ねるテキストコピー。画像上にテキストが一切不要な場合のみ null"

    system = [
        {
            "type": "text",
            "text": f"【台本・情報源（参照用）】\n{script[:4000]}",
            "cache_control": {"type": "ephemeral"},
        }
    ]
    user_prompt = (
        f"あなたはWebデザイナー兼コピーライターです。"
        f"以下の情報をもとに、AI画像生成ツール（Midjourney等）への入稿用画像制作指示書をJSONで作成してください。{copy_instruction}\n\n"
        f"【ページ種別】{page_label}\n"
        f"【セクション】{section_name}\n"
        f"【画像の用途】{purpose}\n"
        f"【サイズ仕様】{size_hint}\n"
        f"【補足情報】{notes}\n\n"
        "以下のフィールドをすべて含むJSONのみ出力してください。\n"
        "{{\n"
        '  "purpose": "画像の用途",\n'
        '  "kind": "種別（例: ヒーロービジュアル / 人物写真 / 商品イメージ / 説明図解 など）",\n'
        '  "size": "サイズ（幅は必ず1040px固定。高さと比率を明記。例: 1040×900px（約16:14））",\n'
        '  "background": "背景・全体の雰囲気・色調の詳細説明",\n'
        '  "subject": "人物や被写体の詳細説明（不要なら null）",\n'
        f'  "copy_text": "{copy_field}",\n'
        '  "font_spec": "フォント指示（copy_textがある場合は必須）",\n'
        '  "notes": "AI画像生成プロンプトに役立つ追加情報（スタイル・雰囲気・禁止事項など）"\n'
        "}}"
    )

    response = client.messages.create(
        model=MODEL_SONNET,
        max_tokens=1000,
        system=system,
        messages=[{"role": "user", "content": user_prompt}],
    )

    text = response.content[0].text.strip()
    try:
        brief_data = _extract_json(text)
    except (ValueError, json.JSONDecodeError):
        brief_data = {
            "purpose": purpose,
            "kind": _infer_kind(purpose),
            "size": "",
            "background": notes,
            "subject": None,
            "copy_text": pre_copy,
            "font_spec": None,
            "notes": "",
        }

    # サイズを確定値に強制上書き（is_heroが最優先）
    if is_hero:
        brief_data["size"] = "幅1040px × 高さ900〜1200px（ファーストビュー）"
    elif suggested_size:
        height = suggested_size.split("x", 1)[1] if "x" in suggested_size else suggested_size
        brief_data["size"] = f"幅1040px × 高さ {height}（指定サイズ）"
    elif is_large_page and not brief_data.get("size"):
        brief_data["size"] = "幅1040px × 高さ800〜1200px"

    brief_md = IMAGE_BRIEF_TEMPLATE.format(
        purpose=brief_data.get("purpose", purpose),
        kind=brief_data.get("kind", ""),
        size=brief_data.get("size", "1040xauto"),
        background=brief_data.get("background", ""),
        subject=brief_data.get("subject") or "なし",
        copy_text=brief_data.get("copy_text") or "なし",
        font_spec=brief_data.get("font_spec") or "なし",
        notes=brief_data.get("notes", ""),
    )

    # セクション情報をデータにも付与（all_image_briefs.md 用）
    brief_data["_page"] = ""  # main.py側でセット
    brief_data["_section"] = section_name

    return brief_md, brief_data


def build_all_image_briefs(all_briefs: list[dict]) -> str:
    """全ページの画像指示書をまとめたMarkdownを生成"""
    lines = ["# 画像指示書まとめ（全ページ）\n"]
    current_page = None

    for brief in all_briefs:
        page = brief.get("_page", "")
        if page != current_page:
            lines.append(f"\n## {page}\n")
            current_page = page

        lines.append(
            IMAGE_BRIEF_TEMPLATE.format(
                purpose=brief.get("purpose", ""),
                kind=brief.get("kind", ""),
                size=brief.get("size", ""),
                background=brief.get("background", ""),
                subject=brief.get("subject") or "なし",
                copy_text=brief.get("copy_text") or "なし",
                font_spec=brief.get("font_spec") or "なし",
                notes=brief.get("notes", ""),
            )
        )

    return "\n".join(lines)
