"""一時解析スクリプト: オプトインLPの構成を把握する"""

import base64
import glob
from pathlib import Path
from docx import Document
import anthropic

client = anthropic.Anthropic()

SAMPLES_DIR = Path("samples")

# docx読み込み
docx_path = SAMPLES_DIR / "ゼノオプトLPlong.docx"
doc = Document(docx_path)
docx_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
print(f"[docx] {len(docx_text)} 文字を抽出\n")

# 画像8枚を番号順に読み込む
image_files = sorted(SAMPLES_DIR.glob("IMG_*.PNG"))
print(f"[画像] {len(image_files)} 枚を読み込みます:")
for f in image_files:
    print(f"  {f.name}")
print()

# プロンプト構築
content = []

# 画像を順番に追加
for img_path in image_files:
    data = base64.standard_b64encode(img_path.read_bytes()).decode("utf-8")
    content.append({
        "type": "image",
        "source": {"type": "base64", "media_type": "image/png", "data": data},
    })

# テキストプロンプト
content.append({
    "type": "text",
    "text": f"""上の画像はオプトインLPを上から下にスクロールしながら撮影したスクリーンショット8枚です（IMG_2985〜2992の順番）。
これらを1つの縦長ページとして見てください。

また、以下はこのページの構成ドキュメント（Word）の内容です：

--- 構成ドキュメント ---
{docx_text[:5000]}
---

画像と構成ドキュメントの両方を参照して、このオプトインLPのページ構成を上から順番に日本語で詳しく説明してください。

以下の形式で出力してください：

## セクション一覧

### セクション1: [セクション名]
- **役割**:
- **テキスト内容**: （実際に書かれている文言や要素）
- **画像・ビジュアル要素**: （画像、アイコン、動画など）
- **その他**: （フォーム、ボタン、装飾など）

### セクション2: [セクション名]
...（以下同様）

最後に全体の構成の特徴・ポイントを2〜3文でまとめてください。"""
})

print("[API] Claude Vision APIに送信中...\n")
response = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=4000,
    messages=[{"role": "user", "content": content}],
)

result = response.content[0].text
print("=" * 60)
print(result)
print("=" * 60)

# 結果をファイルにも保存
out = Path("output/optin_structure_analysis.md")
out.parent.mkdir(exist_ok=True)
out.write_text(f"# オプトインLP 構成解析\n\n{result}\n", encoding="utf-8")
print(f"\n[保存] {out}")
