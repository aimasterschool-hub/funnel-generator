"""
reference_loader.py - 参考ファネルからコピースタイルを抽出するモジュール
"""

import base64
import anthropic
from pathlib import Path
from bs4 import BeautifulSoup

REFERENCES_DIR = Path("references")
SELLER_PHOTOS_DIR = Path("seller_photos")


def extract_copy_from_html(html: str) -> str:
    """HTMLのLPコピー要素だけを抽出して平文化する"""
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(["script", "style", "details", "head"]):
        tag.decompose()

    copy_classes = [
        "el-banner", "el-headline", "el-sub", "el-number",
        "el-body", "el-bullets", "el-steps", "el-btn",
    ]

    lines = []
    for el in soup.find_all(
        class_=lambda c: c and any(cls in c.split() for cls in copy_classes)
    ):
        text = el.get_text(separator="\n").strip()
        if text and len(text) > 3:
            lines.append(text)

    return "\n\n".join(lines)


def extract_copy_from_image(image_bytes: bytes, media_type: str) -> str:
    """画像（スクショ等）からLPコピーテキストをClaude Visionで1回だけ抽出する"""
    client = anthropic.Anthropic()
    image_data = base64.standard_b64encode(image_bytes).decode("utf-8")
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4000,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": media_type, "data": image_data},
                },
                {
                    "type": "text",
                    "text": (
                        "このLPページのスクリーンショットから、すべてのコピーテキスト（キャッチコピー、本文、"
                        "ボタンテキスト、特典名、価格、注意書きなど）を抽出してください。\n"
                        "・画像・装飾・色・レイアウトの説明は不要です\n"
                        "・テキストのみをページ上から下の順番でそのまま出力してください\n"
                        "・セクションの区切りには空行を入れてください"
                    ),
                },
            ],
        }],
    )
    return response.content[0].text


def extract_appearance_from_image(image_bytes: bytes, media_type: str) -> str:
    """販売者の写真から外見・雰囲気の説明文をClaude Visionで生成する（API呼び出し）"""
    client = anthropic.Anthropic()
    image_data = base64.standard_b64encode(image_bytes).decode("utf-8")
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": media_type, "data": image_data},
                },
                {
                    "type": "text",
                    "text": (
                        "この人物写真から、LPの画像生成指示に使える外見・雰囲気の説明を20〜40文字で生成してください。\n"
                        "・年代、性別、髪型・髪色、服装の雰囲気、表情・印象を含めてください\n"
                        "・例: 30代女性、黒髪ショート、清潔感のあるスーツ、知的で明るい笑顔\n"
                        "・説明文のみを出力してください（前置き・後書き不要）"
                    ),
                },
            ],
        }],
    )
    return response.content[0].text.strip()


def get_or_extract_appearance(image_bytes: bytes, media_type: str, filename: str) -> tuple[str, bool]:
    """キャッシュがあれば返し、なければAPIで分析してキャッシュ保存する。
    戻り値: (外見説明文, キャッシュ使用フラグ)"""
    SELLER_PHOTOS_DIR.mkdir(exist_ok=True)
    cache_key = Path(filename).stem
    cache_path = SELLER_PHOTOS_DIR / f"{cache_key}.txt"
    if cache_path.exists():
        return cache_path.read_text(encoding="utf-8").strip(), True
    appearance = extract_appearance_from_image(image_bytes, media_type)
    cache_path.write_text(appearance, encoding="utf-8")
    return appearance, False


def save_reference(funnel_type: str, raw_content: str, is_html: bool, suffix: str = "") -> None:
    """参考ファネルのコピーテキストをreferences/に保存する"""
    REFERENCES_DIR.mkdir(exist_ok=True)
    name = f"{funnel_type}_{suffix}_ref.txt" if suffix else f"{funnel_type}_ref.txt"
    path = REFERENCES_DIR / name
    text = extract_copy_from_html(raw_content) if is_html else raw_content
    path.write_text(text, encoding="utf-8")


def load_reference(funnel_type: str) -> "str | None":
    """保存済み参考コピーを読み込む（単体）"""
    path = REFERENCES_DIR / f"{funnel_type}_ref.txt"
    return path.read_text(encoding="utf-8") if path.exists() else None


def load_references_for_generation(funnel_type: str) -> str:
    """生成に使う参考コピーをすべてロードして結合する。
    video_funnel_* 系は全エピソードの参考を統合して学習に使う。"""
    # video_funnel 系は全エピソードを統合して学習
    if funnel_type.startswith("video_funnel"):
        paths = sorted(REFERENCES_DIR.glob("video_funnel_*_ref.txt"))
    else:
        # その他は同一ファネル種別のファイルをすべて読む（例: sales_lp_ref.txt + sales_lp_autoedc_ref.txt）
        paths = sorted(REFERENCES_DIR.glob(f"{funnel_type}*_ref.txt"))

    parts = []
    for path in paths:
        if path.exists():
            ep_label = path.stem.replace("_ref", "")
            text = path.read_text(encoding="utf-8")
            parts.append(f"【参考例: {ep_label}】\n{text}")

    return "\n\n---\n\n".join(parts)
