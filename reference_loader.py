"""
reference_loader.py - 参考ファネルからコピースタイルを抽出するモジュール
"""

from pathlib import Path
from bs4 import BeautifulSoup

REFERENCES_DIR = Path("references")


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


def save_reference(funnel_type: str, raw_content: str, is_html: bool) -> None:
    """参考ファネルのコピーテキストをreferences/に保存する"""
    REFERENCES_DIR.mkdir(exist_ok=True)
    path = REFERENCES_DIR / f"{funnel_type}_ref.txt"
    text = extract_copy_from_html(raw_content) if is_html else raw_content
    path.write_text(text, encoding="utf-8")


def load_reference(funnel_type: str) -> "str | None":
    """保存済み参考コピーを読み込む"""
    path = REFERENCES_DIR / f"{funnel_type}_ref.txt"
    return path.read_text(encoding="utf-8") if path.exists() else None
