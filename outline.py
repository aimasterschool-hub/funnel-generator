"""
outline.py - 台本から骨子を生成・キャッシュするモジュール

台本（動画ナレーション用）からLP生成に最適化された骨子を作成する。
骨子はscriptsフォルダに台本と同名の _骨子.md として保存・再利用する。
"""

from pathlib import Path
from typing import Optional
import anthropic

client = anthropic.Anthropic()


OUTLINES_DIR = Path("outlines")


def resolve_outline_path(script_path: str) -> Path:
    """共有outlines/ディレクトリにファイル名ベースで保存（job_idに依存しない）"""
    stem = Path(script_path).stem
    OUTLINES_DIR.mkdir(exist_ok=True)
    return OUTLINES_DIR / (stem + "_骨子.md")


def load_outline(script_path: str) -> Optional[str]:
    # 共有キャッシュを優先、なければ旧形式（台本と同階層）も確認
    shared = resolve_outline_path(script_path)
    if shared.exists():
        return shared.read_text(encoding="utf-8")
    legacy = Path(script_path).parent / (Path(script_path).stem + "_骨子.md")
    if legacy.exists():
        return legacy.read_text(encoding="utf-8")
    return None


def generate_outline(script: str, script_path: str) -> str:
    """台本テキストからLP生成用の骨子を生成して保存・返す"""
    save_path = resolve_outline_path(script_path)

    prompt = f"""以下は動画セールスレター（VSL）の台本です。
この台本には、スライド指示・ト書き・演出メモ・タイムコードが混在しています。

これをLP（ランディングページ）のコピー生成に直接使える「骨子」に整理してください。

【骨子に含めること】
- 販売者のストーリー（挫折・這い上がり・発見・感情的なエピソード）
- 商品の特徴・仕組み・独自性
- 実績・証拠となる具体的な数字（金額・人数・期間など）
- ターゲットの悩みとペインポイント
- 無料提供の条件・CTA
- 各特典の名称・通常価格・内容・メリット（特典ごとに詳細に）
- 緊急性・限定性の根拠（人数・期間・条件）

【骨子から除くこと】
- スライド表記指示（「ここのスライド表記」等）
- ト書き・演出メモ（「背景画変えて」「エフェクトかけて」等）
- タイムコード（「1:10」「4:50あたり」等）
- 重複している修正バリエーション（「→」で始まる差し替え案は最新版のみ残す）

【出力形式】
Markdownで、以下のセクション構成で出力してください：

## 販売者プロフィール・ストーリー
（生い立ち・職歴・転機・感情的なエピソードを具体的に）

## ターゲットの悩み・恐怖・欲求
（最大の痛みポイント・恐怖・叶えたい欲求を感情的な言葉で）

## 商品概要・コンセプト
（商品名・どんなツールか・何ができるか・独自性）

## 独自の手法・仕組み
（なぜ稼げるのか・他と何が違うのか・ロジック）

## 実績・エビデンス
（具体的な数字・金額・期間・スクリーンショットの内容）

## 社会的証明・権威性
（ユーザー数・第三者の声・メディア掲載等）

## 特典・価格情報
（特典①〜の名称・通常価格・提供価格・具体的な内容・メリットを特典ごとに記載）

## 緊急性・限定性
（配布終了条件・人数制限・期間制限の具体的な根拠）

## キラーフレーズ集
（台本中の強いコピー候補。「強制チャージ」「逆転ロジック」など、そのままLPで使えるインパクトのある言葉・フレーズを20個以上列挙）

--- 台本 ---
{script}
---"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )

    outline = response.content[0].text.strip()
    save_path.write_text(outline, encoding="utf-8")
    return outline


def get_outline(script: str, script_path: str) -> "tuple[str, bool]":
    """
    骨子を取得する。既存なら読み込み、なければ生成して保存。
    Returns: (骨子テキスト, キャッシュから読んだか)
    """
    existing = load_outline(script_path)
    if existing:
        return existing, True
    outline = generate_outline(script, script_path)
    return outline, False
