"""
image_preview.py - LP プレビュー用の簡易画像生成モジュール
Pillowでグラデーション背景＋日本語テキストの画像を生成する
"""

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

FONT_BOLD   = "/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc"
FONT_MEDIUM = "/System/Library/Fonts/ヒラギノ角ゴシック W4.ttc"

# セクション種別ごとの配色 (bg_top, bg_bottom, text_color, accent_color)
SECTION_COLORS = {
    "hero":    ((13, 13, 30),   (30, 10, 50),   (255,255,255), (240,192, 64)),
    "cta":     ((13, 31, 13),   (10, 45, 20),   (255,255,255), (240,192, 64)),
    "steps":   ((240,240,240),  (225,225,225),  ( 30, 30, 30), ( 30, 30,220)),
    "problem": (( 17, 17, 17),  ( 30, 10, 10),  (238,238,238), (240, 80, 64)),
    "proof":   (( 11, 22, 40),  ( 20, 40, 70),  (238,238,238), (240,192, 64)),
    "profile": ((255,255,255),  (240,240,248),  ( 30, 30, 30), (240,192, 64)),
    "default": (( 20, 20, 40),  ( 40, 20, 60),  (255,255,255), (240,192, 64)),
}

SECTION_NAME_MAP = {
    "ファーストビュー":         "hero",
    "特典＋登録ボタン（上部）": "cta",
    "特典＋登録ボタン（下部）": "cta",
    "登録の流れ（上部）":       "steps",
    "登録の流れ（下部）":       "steps",
    "問題提起・共感":           "problem",
    "エビデンス":               "proof",
    "利用者の声":               "profile",
    "販売者紹介":               "profile",
    "システム詳細":             "proof",
}


def _make_gradient(w: int, h: int, c1: tuple, c2: tuple) -> Image.Image:
    """縦方向グラデーション画像を生成"""
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    for i, (a, b) in enumerate(zip(c1, c2)):
        arr[:, :, i] = np.linspace(a, b, h, dtype=np.uint8).reshape(h, 1)
    return Image.fromarray(arr, "RGB")


def _load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.ImageDraw) -> list:
    """テキストを max_width に収まるよう折り返す（日本語対応）"""
    lines = []
    for paragraph in text.split("\n"):
        line = ""
        for char in paragraph:
            test = line + char
            w = draw.textlength(test, font=font)
            if w > max_width and line:
                lines.append(line)
                line = char
            else:
                line = test
        if line:
            lines.append(line)
    return lines


def generate_image(
    section_name: str,
    copy_text: str,
    kind: str,
    size_str: str,
    out_path: Path,
) -> Path:
    """
    プレビュー画像を生成して out_path に保存し、パスを返す。
    """
    # サイズ解析
    w, h = 1040, 480
    import re
    m = re.search(r"高さ\s*(\d+)", size_str)
    if m:
        h = min(int(m.group(1)), 700)
    else:
        m2 = re.search(r"(\d+)[xX×]\s*(\d+)", size_str)
        if m2:
            h = min(int(m2.group(2)), 700)

    # カラースキーム
    style_key = SECTION_NAME_MAP.get(section_name, "default")
    c_top, c_bot, c_text, c_accent = SECTION_COLORS[style_key]

    img = _make_gradient(w, h, c_top, c_bot)
    draw = ImageDraw.Draw(img)

    # コピーテキスト描画
    if copy_text and copy_text not in ("なし", "null"):
        font_size = max(36, min(64, w // len(copy_text.split("\n")[0]) + 10)) if copy_text else 40
        font_size = min(font_size, 56)
        font = _load_font(FONT_BOLD, font_size)

        padding = 80
        lines = _wrap_text(copy_text, font, w - padding * 2, draw)

        # テキスト全体の高さ計算
        line_h = font_size + 12
        total_h = line_h * len(lines)
        y = (h - total_h) // 2 - 20

        for line in lines:
            tw = draw.textlength(line, font=font)
            x = (w - tw) // 2
            # 影
            draw.text((x + 3, y + 3), line, font=font, fill=(0, 0, 0, 160))
            draw.text((x, y), line, font=font, fill=c_text)
            y += line_h
    else:
        # コピーなし → 種別テキストだけ薄く表示
        font = _load_font(FONT_MEDIUM, 28)
        label = f"[ {kind} ]"
        tw = draw.textlength(label, font=font)
        draw.text(((w - tw) // 2, h // 2 - 20), label, font=font,
                  fill=tuple(min(c + 80, 255) for c in c_top))

    # 下部に種別ラベル
    label_font = _load_font(FONT_MEDIUM, 20)
    label_text = f"📐 {size_str}  ／  {kind}"
    # 半透明バー
    bar_h = 36
    bar = Image.new("RGBA", (w, bar_h), (0, 0, 0, 120))
    img.paste(Image.fromarray(np.array(bar)[:, :, :3]), (0, h - bar_h))
    lw = draw.textlength(label_text, font=label_font)
    draw.text(((w - lw) // 2, h - bar_h + 8), label_text, font=label_font,
              fill=(200, 200, 200))

    # アクセントライン（上部）
    draw.rectangle([0, 0, w, 4], fill=c_accent)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG")
    return out_path
