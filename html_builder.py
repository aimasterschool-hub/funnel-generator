"""
html_builder.py - LP プレビュー用HTML生成モジュール
"""

import re
from pathlib import Path

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: #555;
      font-family: 'Hiragino Kaku Gothic ProN', 'Hiragino Sans', 'Noto Sans JP', Arial, sans-serif;
    }}
    .lp-wrap {{
      max-width: 1040px;
      margin: 0 auto;
      background: #111;
      box-shadow: 0 0 40px rgba(0,0,0,0.6);
    }}

    /* ── セクション共通 ── */
    .sec {{ width: 100%; padding: 56px 48px; position: relative; }}
    .sec-dark   {{ background: #0d0d1a; color: #fff; }}
    .sec-black  {{ background: #111; color: #eee; }}
    .sec-navy   {{ background: #0b1628; color: #eee; }}
    .sec-green  {{ background: #0d1f0d; color: #fff; }}
    .sec-white  {{ background: #fff; color: #111; }}
    .sec-cream  {{ background: #faf7f2; color: #222; }}
    .sec-gray   {{ background: #f2f2f2; color: #333; }}
    .sec-footer {{ background: #1a1a1a; color: #777; font-size: 0.78rem; line-height: 1.9; padding: 40px 48px; }}
    .sec-footer-bar {{
      background: #1a1a1a; padding: 20px 48px;
      display: flex; justify-content: center; gap: 48px;
      border-top: 1px solid #2a2a2a;
    }}
    .footer-link {{
      color: #555; font-size: 0.75rem; text-decoration: underline;
      text-underline-offset: 3px; cursor: pointer;
    }}
    .footer-link:hover {{ color: #999; }}

    /* ── テキスト要素 ── */
    .el-banner {{
      text-align: center; font-size: 0.85rem; font-weight: 700;
      letter-spacing: 0.12em; color: #f0c040; margin-bottom: 10px;
    }}
    .el-headline {{
      text-align: center; font-size: 2.4rem; font-weight: 900;
      line-height: 1.45; margin: 14px 0; letter-spacing: -0.01em;
    }}
    .el-headline.dark {{ color: #fff; text-shadow: 0 2px 12px rgba(0,0,0,0.5); }}
    .el-headline.light {{ color: #111; }}

    .el-sub {{
      text-align: center; font-size: 1.25rem; font-weight: 700;
      line-height: 1.6; margin: 14px 0; opacity: 0.9;
    }}
    .el-body {{
      font-size: 0.97rem; line-height: 2; max-width: 760px;
      margin: 18px auto; opacity: 0.9;
    }}
    .el-number {{
      text-align: center; font-size: 3rem; font-weight: 900;
      color: #f0c040; margin: 20px 0; letter-spacing: -0.02em;
    }}
    .el-profile {{
      font-size: 0.93rem; line-height: 2; max-width: 720px; margin: 18px auto;
      padding: 20px 24px;
      border-left: 4px solid #f0c040;
      background: rgba(255,255,255,0.04);
      border-radius: 0 8px 8px 0;
    }}

    /* ── リスト ── */
    .el-bullets {{ max-width: 720px; margin: 18px auto; list-style: none; }}
    .el-bullets li {{
      padding: 10px 0 10px 32px; position: relative;
      border-bottom: 1px solid rgba(200,200,200,0.12);
      font-size: 0.95rem; line-height: 1.7;
    }}
    .el-bullets li::before {{
      content: "▶"; position: absolute; left: 0;
      color: #f0c040; font-size: 0.75rem; top: 13px;
    }}
    .el-steps {{ max-width: 720px; margin: 18px auto; list-style: none; counter-reset: st; }}
    .el-steps li {{
      counter-increment: st;
      padding: 14px 0 14px 60px; position: relative;
      border-bottom: 1px solid rgba(200,200,200,0.12);
      font-size: 0.95rem; line-height: 1.7;
    }}
    .el-steps li::before {{
      content: counter(st);
      position: absolute; left: 0; top: 10px;
      width: 36px; height: 36px; border-radius: 50%;
      background: #f0c040; color: #111;
      font-weight: 900; font-size: 1rem;
      display: flex; align-items: center; justify-content: center;
    }}

    /* ── CTAボタン ── */
    .el-btn {{
      display: block; max-width: 600px; margin: 28px auto 8px;
      padding: 22px 40px; text-align: center;
      background: linear-gradient(180deg, #ff3a28 0%, #c01800 100%);
      color: #fff; font-size: 1.25rem; font-weight: 900;
      border-radius: 6px; letter-spacing: 0.04em; line-height: 1.5;
      box-shadow: 0 8px 0 #8b1000, 0 10px 24px rgba(180,0,0,0.35);
      cursor: pointer;
    }}
    .el-btn::after {{
      content: " ›"; font-size: 1.4rem;
    }}

    /* ── 画像プレースホルダー ── */
    .img-ph {{
      width: 100%; position: relative; overflow: hidden;
      display: flex; align-items: center; justify-content: center;
      margin-bottom: 0;
    }}
    .img-ph-bg {{
      position: absolute; inset: 0;
      background: linear-gradient(135deg, #1a1a3e 0%, #2a2050 40%, #1a0a2a 100%);
    }}
    .img-ph-bg.light {{
      background: linear-gradient(135deg, #c8c8d8 0%, #b0b0c8 100%);
    }}
    .img-ph-content {{
      position: relative; z-index: 1;
      text-align: center; padding: 40px 60px; width: 100%;
    }}
    .img-ph-copy {{
      font-size: 2rem; font-weight: 900; color: #fff;
      line-height: 1.7; white-space: pre-line;
      text-shadow: 0 3px 16px rgba(0,0,0,0.8);
      margin-bottom: 20px;
    }}
    .img-ph-label {{
      display: inline-block;
      background: rgba(0,0,0,0.45); color: rgba(255,255,255,0.65);
      font-size: 0.72rem; padding: 4px 14px; border-radius: 20px;
      letter-spacing: 0.08em;
    }}

    /* ── 画像指示書（折りたたみ） ── */
    details.brief-details {{ margin: 0; }}
    details.brief-details > summary {{
      background: #222; color: #aaa; font-size: 0.72rem;
      padding: 6px 16px; cursor: pointer; text-align: right;
      user-select: none; list-style: none; display: block;
    }}
    details.brief-details > summary::-webkit-details-marker {{ display: none; }}
    details.brief-details > summary:hover {{ background: #333; }}
    /* コンテンツの表示・非表示をCSSで明示制御 */
    details.brief-details > .brief-box {{ display: none; }}
    details.brief-details[open] > .brief-box {{ display: block; }}
    .brief-box {{
      background: #1a1a1a; border-top: 1px solid #333;
      padding: 16px 20px; font-size: 0.78rem; color: #bbb;
    }}
    .brief-box table {{ width: 100%; border-collapse: collapse; }}
    .brief-box td {{
      padding: 5px 10px; border-bottom: 1px solid #2a2a2a;
      vertical-align: top;
    }}
    .brief-box td:first-child {{
      color: #f0c040; font-weight: 700; width: 130px; white-space: nowrap;
    }}
    .brief-val {{
      outline: none; padding: 3px 6px; border-radius: 4px;
      transition: background 0.15s; min-width: 200px; white-space: pre-wrap;
    }}
    .brief-val:hover {{ background: rgba(255,255,255,0.05); cursor: text; }}
    .brief-val:focus {{ background: rgba(108,92,231,0.12); outline: 1px solid rgba(108,92,231,0.4); }}
    .brief-toolbar {{
      display: flex; justify-content: flex-end; margin-bottom: 10px;
    }}
    .brief-copy-btn {{
      background: #1a1a2e; border: 1px solid #3a3a6a; color: #a29bfe;
      font-size: 0.7rem; padding: 4px 12px; border-radius: 4px; cursor: pointer;
    }}
    .brief-copy-btn:hover {{ background: #2a2060; border-color: #6c5ce7; }}

    /* ── モード切り替えバー ── */
    .mode-bar {{
      position: sticky; top: 0; z-index: 999;
      background: #0a0a0a; border-bottom: 1px solid #2a2a2a;
      display: flex; align-items: center; justify-content: space-between;
      padding: 8px 20px; gap: 12px;
    }}
    .mode-bar-title {{
      font-size: 0.72rem; color: #555; letter-spacing: 0.1em;
    }}
    .mode-toggle-btn {{
      display: flex; border: 1px solid #333; border-radius: 6px; overflow: hidden; cursor: pointer;
    }}
    .mode-toggle-btn span {{
      padding: 5px 14px; font-size: 0.72rem; font-weight: 700;
      letter-spacing: 0.08em; transition: background 0.15s, color 0.15s;
      user-select: none;
    }}
    .mode-toggle-btn .btn-brief {{
      background: #f0c040; color: #111;
    }}
    .mode-toggle-btn .btn-lp {{
      background: transparent; color: #555;
    }}
    body.lp-mode .mode-toggle-btn .btn-brief {{
      background: transparent; color: #555;
    }}
    body.lp-mode .mode-toggle-btn .btn-lp {{
      background: #6c5ce7; color: #fff;
    }}

    /* ── 指示書モード専用要素 ── */
    .sec-label-bar {{
      margin: 0 -48px 28px;
      padding: 10px 48px;
      background: #1a1a1a;
      border-top: 3px solid #f0c040;
      border-bottom: 1px solid #2a2a2a;
      display: flex; align-items: center; gap: 14px;
    }}
    .sec-label-num {{
      font-size: 0.7rem; font-weight: 900; color: #111;
      background: #f0c040; padding: 2px 9px; border-radius: 4px;
      letter-spacing: 0.05em; white-space: nowrap;
    }}
    .sec-label-name {{
      font-size: 1rem; font-weight: 900; color: #f0c040;
      letter-spacing: 0.08em;
    }}
    .sec-label-role {{
      font-size: 0.7rem; color: #666; margin-left: auto;
      text-align: right; line-height: 1.5; max-width: 360px;
    }}

    /* ── LPモード：指示書要素を非表示 ── */
    body.lp-mode .sec-label-bar {{ display: none; }}
    body.lp-mode details.brief-details {{ display: none; }}
    body.lp-mode .sec {{ padding-top: 56px; }}

    .divider {{ height: 6px; background: linear-gradient(90deg, transparent, #2a2a2a 20%, #2a2a2a 80%, transparent); margin: 0; }}
    body.lp-mode .divider {{ height: 0; }}

    /* ── 定型文ボックス ── */
    .el-fixed-text {{
      max-width: 760px; margin: 18px auto; padding: 20px 24px;
      background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1);
      border-radius: 8px; font-size: 0.82rem; line-height: 2; color: #888;
      text-align: left;
    }}
    .el-fixed-text p {{ margin: 0 0 10px 0; }}
    .el-fixed-text p:last-child {{ margin-bottom: 0; }}
  </style>
  <script>
    document.addEventListener('DOMContentLoaded', function() {{
      // ── モード切り替え ──
      var toggleBtn = document.getElementById('modeToggle');
      if (toggleBtn) {{
        toggleBtn.addEventListener('click', function() {{
          document.body.classList.toggle('lp-mode');
        }});
      }}

      // ── 画像指示書コピー ──
      document.querySelectorAll('.brief-copy-btn').forEach(function(btn) {{
        btn.addEventListener('click', function() {{
          var box = btn.closest('.brief-box');
          var rows = box.querySelectorAll('table tr');
          var lines = ['【画像指示書】'];
          rows.forEach(function(row) {{
            var cells = row.querySelectorAll('td');
            if (cells.length >= 2) {{
              var key = cells[0].textContent.trim();
              var val = cells[1].textContent.trim();
              if (val) lines.push(key + ': ' + val);
            }}
          }});
          var text = lines.join('\\n');
          var ta = document.createElement('textarea');
          ta.value = text;
          ta.style.position = 'fixed';
          ta.style.opacity = '0';
          document.body.appendChild(ta);
          ta.select();
          try {{ document.execCommand('copy'); }} catch(e) {{}}
          document.body.removeChild(ta);
          var orig = btn.textContent;
          btn.textContent = '✓ コピーしました';
          setTimeout(function() {{ btn.textContent = orig; }}, 2000);
        }});
      }});
    }});
  </script>
</head>
<body>
  <div class="mode-bar">
    <span class="mode-bar-title">📄 {title}</span>
    <div class="mode-toggle-btn" id="modeToggle" title="表示モードを切り替え">
      <span class="btn-brief">指示書モード</span>
      <span class="btn-lp">LPプレビュー</span>
    </div>
  </div>
  <div class="lp-wrap">
{body}
  </div>
</body>
</html>"""

# セクション名 → CSSクラス
SECTION_CLASS = {
    "ファーストビュー":               "sec-dark",
    "特典＋登録ボタン（上部）":       "sec-green",
    "特典＋登録ボタン（下部）":       "sec-green",
    "登録の流れ（上部）":             "sec-gray",
    "登録の流れ（下部）":             "sec-gray",
    "問題提起・共感":                 "sec-black",
    "エビデンス":                     "sec-navy",
    "利用者の声":                     "sec-cream",
    "喜びの声":                       "sec-cream",
    "販売者紹介":                     "sec-white",
    "システム詳細":                   "sec-navy",
    "YouTube動画":                    "sec-black",
    "質問投げかけ":                   "sec-dark",
    "質問回答ボタン（上部）":         "sec-green",
    "質問回答ボタン（下部）":         "sec-green",
    "プレゼント内容（上部）":         "sec-green",
    "プレゼント内容（下部）":         "sec-green",
    "商品概要":                       "sec-navy",
    # optin/short
    "登録ボタン（上部）":             "sec-green",
    "登録ボタン（中部）":             "sec-green",
    "登録ボタン（下部）":             "sec-green",
    "特典詳細":                       "sec-navy",
    "受け取り方法":                   "sec-gray",
    # 動画ファネル共通
    "質問投げかけ":                   "sec-dark",
    "自己紹介":                       "sec-white",
    "特典オファー":                   "sec-green",
    # 未マップセクション向け汎用
    "登録ボタン①（上部）":           "sec-green",
    "登録ボタン②（中部）":           "sec-green",
    "特典紹介":                       "sec-navy",
    "実績証明":                       "sec-navy",
    "実績証明（続き）":               "sec-navy",
    "実績まとめ":                     "sec-navy",
    "お客様の声":                     "sec-cream",
    "販売者プロフィール":             "sec-white",
    "優位性・仕組み":                 "sec-navy",
    "差別化ポイント":                 "sec-white",
    "特典再提示":                     "sec-green",
    "クロージング":                   "sec-green",
    "解決への橋渡し":                 "sec-black",
    "フッター":                       "sec-footer",
    "プライバシーポリシー":           "sec-footer",
    "特定商取引法に基づく表記":       "sec-footer",
    # 販売LP
    "先着枠・数量提示":               "sec-dark",
    "チェックアウトブロック①（上部）": "sec-white",
    "チェックアウトブロック②（中部）": "sec-white",
    "チェックアウトブロック③（下部）": "sec-white",
    "販売者メッセージ":               "sec-navy",
    "商品のエビデンス":               "sec-navy",
}

# セクションが暗い背景かどうか
DARK_SECTIONS = {
    "ファーストビュー", "特典＋登録ボタン（上部）", "特典＋登録ボタン（下部）",
    "問題提起・共感", "エビデンス", "システム詳細",
    "YouTube動画", "質問投げかけ", "商品概要",
    "先着枠・数量提示", "販売者メッセージ", "商品のエビデンス",
    "登録ボタン（上部）", "登録ボタン（中部）", "登録ボタン（下部）",
    "特典詳細", "特典紹介", "特典再提示", "特典オファー",
    "実績証明", "実績証明（続き）", "実績まとめ",
    "解決への橋渡し", "クロージング",
    "登録ボタン①（上部）", "登録ボタン②（中部）",
}

# オプションセクション（表示はするがバッジで「オプション」と示す）
OPTIONAL_SECTIONS = {
    "プレゼント内容（上部）", "プレゼント内容（下部）",
}


FOOTER_LINK_SECTIONS = {"プライバシーポリシー", "特定商取引法に基づく表記"}


def markdown_to_html(markdown_text: str, title: str, out_dir: str = "output") -> str:
    lines = markdown_text.split("\n")
    sections = _split_sections(lines)
    parts = []
    footer_names = []
    img_dir = Path(out_dir) / "images"
    img_counter = [0]

    for sec in sections:
        if sec["name"] in FOOTER_LINK_SECTIONS:
            footer_names.append(sec["name"])
        else:
            parts.append(_render_section(sec, img_dir, img_counter))

    # フッターリンクバー（横並び）
    if footer_names:
        links = "".join(
            f'<a class="footer-link" href="#">{_esc(n)}</a>'
            for n in footer_names
        )
        parts.append(f'    <div class="sec-footer-bar">{links}</div>')

    return HTML_TEMPLATE.format(title=_esc(title), body="\n".join(parts))


def _split_sections(lines):
    sections, cur = [], {"name": "", "role": "", "number": 0, "lines": []}
    sec_count = 0
    for line in lines:
        if line.startswith("## "):
            if cur["name"]:
                sections.append(cur)
            sec_count += 1
            cur = {"name": line[3:].strip(), "role": "", "number": sec_count, "lines": []}
        elif line.startswith("> 役割:"):
            cur["role"] = line[6:].strip()
        elif not line.startswith("# "):
            cur["lines"].append(line)
    if cur["name"]:
        sections.append(cur)
    return sections


def _render_section(sec, img_dir=None, img_counter=None):
    name   = sec["name"]
    role   = sec.get("role", "")
    number = sec.get("number", 0)
    cls    = SECTION_CLASS.get(name, "sec-white")
    is_dark = name in DARK_SECTIONS
    hl_cls  = "dark" if is_dark else "light"

    inner = _render_lines(sec["lines"], is_dark, hl_cls, name, img_dir, img_counter)

    if cls == "sec-footer":
        return (
            f'    <div class="{cls}">\n'
            f'      <p style="font-weight:700;margin-bottom:8px;">{_esc(name)}</p>\n'
            f'{inner}\n'
            f'    </div>'
        )

    optional_tag = ""
    if name in OPTIONAL_SECTIONS:
        optional_tag = '<span style="font-size:0.65rem;color:#888;border:1px solid #555;padding:1px 8px;border-radius:10px;margin-left:6px;">オプション</span>'

    num_label = f'SEC {number}' if number else 'SEC'
    role_html = f'<div class="sec-label-role">{_esc(role)}</div>' if role else ''

    label_bar = (
        f'      <div class="sec-label-bar">'
        f'<span class="sec-label-num">{num_label}</span>'
        f'<span class="sec-label-name">{_esc(name)}</span>{optional_tag}'
        f'{role_html}'
        f'</div>\n'
    )

    return (
        f'    <div class="sec {cls}">\n'
        f'{label_bar}'
        f'{inner}\n'
        f'    </div>\n'
        f'    <div class="divider"></div>'
    )


def _render_lines(lines, is_dark=True, hl_cls="dark", section_name="", img_dir=None, img_counter=None):
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # 画像ブロック
        if line.startswith("### 画像ブロック:"):
            block = [line]
            i += 1
            while i < len(lines) and not lines[i].startswith("###") and lines[i].strip() != "---":
                block.append(lines[i])
                i += 1
            out.append(_render_img(block, section_name, img_dir, img_counter))
            continue

        # キャッチコピーブロック → スキップ（画像指示書側で表示するため不要）
        if "【画像上のキャッチコピー】" in line:
            i += 1
            while i < len(lines) and not lines[i].startswith("#") and lines[i].strip() != "---":
                i += 1
            continue

        # 役割説明 → スキップ
        if line.startswith("> 役割:"):
            i += 1
            continue

        # h3 要素 → コンテンツ収集して種類別レンダリング
        if line.startswith("### "):
            kind = re.sub(r"[\[\]]", "", line[4:]).strip()
            i += 1
            content = []
            if kind == "定型文":
                # 空行を含めて次の ### または --- まで収集
                while i < len(lines) and not lines[i].startswith("#") and lines[i].strip() != "---":
                    content.append(lines[i])
                    i += 1
            else:
                while i < len(lines) and lines[i].strip() and not lines[i].startswith("#") and lines[i].strip() != "---":
                    content.append(lines[i])
                    i += 1
            out.append(_render_el(kind, content, hl_cls))
            continue

        if line.strip() in ("---", ""):
            i += 1
            continue

        # 普通のテキスト
        if line.strip():
            out.append(f'      <p class="el-body" style="text-align:center">{_inline(line)}</p>')
        i += 1

    return "\n".join(out)


def _render_el(kind, content_lines, hl_cls):
    # コンテンツ不要な特殊 kind は先にハンドル（空チェックより前）
    if kind in ("動画埋め込み", "video_embed", "YouTube埋め込み"):
        return (
            '      <div style="margin:0 -48px;width:calc(100% + 96px);background:#000;'
            'aspect-ratio:16/9;display:flex;align-items:center;justify-content:center;">'
            '<div style="text-align:center;color:#555;">'
            '<div style="font-size:2.5rem;margin-bottom:12px;">▶</div>'
            '<div style="font-size:0.85rem;letter-spacing:0.1em;">YouTube 動画エリア</div>'
            '</div></div>'
        )

    if kind == "定型文":
        paragraphs, current = [], []
        for l in content_lines:
            if l.strip():
                current.append(l.strip())
            else:
                if current:
                    paragraphs.append(current)
                    current = []
        if current:
            paragraphs.append(current)
        parts = []
        for para in paragraphs:
            para_html = "<br>".join(_esc(l) for l in para)
            parts.append(f"<p>{para_html}</p>")
        inner = "\n        ".join(parts)
        return f'      <div class="el-fixed-text">\n        {inner}\n      </div>'

    text = "\n".join(content_lines).strip()
    if not text:
        return ""

    # 箇条書き検出
    is_bullets = all(re.match(r"^[-・▶]", l.strip()) or not l.strip() for l in content_lines if l.strip())
    is_steps   = all(re.match(r"^\d+\.", l.strip()) or not l.strip() for l in content_lines if l.strip())

    if kind in ("メインコピー",):
        return f'      <div class="el-headline {hl_cls}">{_inline(text, br=True)}</div>'
    if kind == "バナーテキスト":
        return f'      <div class="el-banner">{_inline(text)}</div>'
    if kind == "サブコピー":
        return f'      <div class="el-sub">{_inline(text, br=True)}</div>'
    if kind == "ボタン":
        return f'      <div class="el-btn">{_inline(text)}</div>'
    if kind == "数字ハイライト":
        return f'      <div class="el-number">{_inline(text)}</div>'
    if kind == "プロフィール文":
        return f'      <div class="el-profile">{_inline(text, br=True)}</div>'

    if kind == "箇条書き" or is_bullets:
        items = [re.sub(r"^[-・▶]\s*", "", l).strip() for l in content_lines if l.strip()]
        lis = "\n".join(f'        <li>{_inline(it)}</li>' for it in items if it)
        return f'      <ul class="el-bullets">\n{lis}\n      </ul>'

    if kind == "ステップリスト" or is_steps:
        items = [re.sub(r"^\d+\.\s*", "", l).strip() for l in content_lines if l.strip()]
        lis = "\n".join(f'        <li>{_inline(it)}</li>' for it in items if it)
        return f'      <ol class="el-steps">\n{lis}\n      </ol>'

    # 本文デフォルト
    return f'      <p class="el-body">{_inline(text, br=True)}</p>'


def _render_img(block_lines, section_name="", img_dir=None, img_counter=None):
    title = block_lines[0].replace("### 画像ブロック:", "").strip()
    fields = {}
    current_key = None
    for line in block_lines[1:]:
        m = re.match(r"^- \*\*(.+?)\*\*:\s*(.*)$", line)
        if m:
            current_key = m.group(1)
            fields[current_key] = m.group(2).strip()
        elif current_key and line.strip() and not line.startswith("-"):
            # 前フィールドの続き行（多行コピーなど）
            fields[current_key] = fields[current_key] + "\n" + line.strip()

    size = fields.get("サイズ", "幅1040px")
    kind = fields.get("種別", "画像")
    copy = fields.get("画像内テキスト（コピー）", "")
    if copy in ("なし", "null", ""):
        copy = ""

    rows = "".join(
        f'<tr><td>{_esc(k)}</td>'
        f'<td><div class="brief-val" contenteditable="true">{_esc(v)}</div></td></tr>'
        for k, v in fields.items()
        if v and v not in ("なし", "null")
    )

    # 画像プレースホルダー
    placeholder = (
        f'<div style="'
        f'background:#1e1e2e;border:2px dashed #3a3a5a;'
        f'display:flex;align-items:center;justify-content:center;'
        f'min-height:180px;width:100%;'
        f'">'
        f'<div style="text-align:center;color:#555;">'
        f'<div style="font-size:2rem;margin-bottom:8px;">🖼</div>'
        f'<div style="font-size:0.8rem;letter-spacing:0.1em;">ここに画像</div>'
        f'<div style="font-size:0.72rem;margin-top:4px;color:#444;">{_esc(size)} ／ {_esc(kind)}</div>'
        f'</div></div>'
    )

    # 画像内テキスト（コピー）＋サイズを画像の下にテキストで表示
    copy_block = (
        f'<div style="background:#12122a;border-left:3px solid #f0c040;padding:16px 20px;margin-top:0;">'
    )
    if copy:
        copy_block += (
            f'<div style="font-size:0.7rem;color:#f0c040;font-weight:700;'
            f'letter-spacing:0.1em;margin-bottom:8px;">画像に掲載するテキスト</div>'
            f'<div style="font-size:1.1rem;font-weight:700;color:#fff;line-height:1.8;'
            f'white-space:pre-line;margin-bottom:12px;">{_esc(copy)}</div>'
        )
    copy_block += (
        f'<div style="font-size:0.75rem;color:#888;">'
        f'📐 {_esc(size)}</div>'
        f'</div>'
    )

    return (
        f'      <div style="margin: 0 -48px; width: calc(100% + 96px);">\n'
        f'        {placeholder}\n'
        f'        {copy_block}\n'
        f'        <details class="brief-details">\n'
        f'          <summary>▼ 画像指示書を確認する</summary>\n'
        f'          <div class="brief-box">'
        f'<div class="brief-toolbar">'
        f'<button class="brief-copy-btn">📋 指示書をコピー</button>'
        f'</div>'
        f'<table>{rows}</table></div>\n'
        f'        </details>\n'
        f'      </div>'
    )


def _esc(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _inline(text, br=False):
    text = _esc(text)
    if br:
        text = text.replace("\n", "<br>")
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    return text
