"""
app.py - ファネル生成ツール（Streamlit版）
"""

import os

# Streamlit CloudのSecretsをos.environに注入（他モジュールのAnthropicクライアント初期化前に実行）
try:
    import streamlit as st
    for _key in ("ANTHROPIC_API_KEY", "FUNNEL_PASS"):
        if _key in st.secrets and _key not in os.environ:
            os.environ[_key] = st.secrets[_key]
except Exception:
    pass

import tempfile
import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path
from datetime import datetime

from run_optin import load_script, load_config, config_to_text, extract_config_from_script
from outline import get_outline
from analyzer import get_sample_structure
from generator import generate_page
from html_builder import markdown_to_html
from reference_loader import extract_copy_from_html, extract_copy_from_image, get_or_extract_appearance, save_reference, load_reference, load_references_for_generation

# ── 定数 ──────────────────────────────────────────────────────────────
FUNNEL_LABELS = {
    "optin":             "オプトインLP",
    "video_funnel_ep1":  "動画ファネル 1話",
    "video_funnel_ep2":  "動画ファネル 2話",
    "video_funnel_ep3":  "動画ファネル 3話",
    "video_funnel_ep4":  "動画ファネル 4話",
    "video_funnel_ep5":  "動画ファネル 5話",
    "sales_lp":          "販売LP",
}
LENGTH_LABELS = {
    "long":  "ロング",
    "short": "ショート",
}
# 全ファネル共通の必須項目
CRITICAL_FIELDS_LIST = [
    (["seller", "name"],       "販売者の名前",                          "例: 加藤かおる"),
    (["seller", "gender"],     "販売者の性別",                          "女性 または 男性"),
    (["product", "name"],      "商品名（正式名称）",                     "例: Sign Edge"),
    (["results", "headline"],  "実績の一言キャッチ（LPコピーに使用）",   "例: 元手1万円で月60万円"),
    (["seller", "appearance"], "販売者の外見・雰囲気（画像指示に使用）", "例: 30代女性、黒髪ショート、知的な雰囲気"),
]

# ファネル種別ごとの追加必須項目
CRITICAL_FIELDS_BY_TYPE = {
    "sales_lp": [
        (["pricing", "regular_price"],  "通常価格",                             "例: 298,000円"),
        (["pricing", "special_price"],  "特別価格（割引後）",                   "例: 98,000円"),
        (["pricing", "limit"],          "限定枠数・締め切り",                   "例: 先着80枠"),
        (["pricing", "installment"],    "分割価格（あれば）",                   "例: 月々5,300円〜（最大24回）"),
        (["results", "top_result"],     "最高実績（期間・金額）",               "例: 半年で1,092万円"),
    ],
    "video_funnel_ep1": [
        (["product", "free_offer"],     "無料プレゼントの内容",                 "例: Sign Edge（通常30万円）を無償配布"),
        (["cta", "question"],           "動画後の質問文",                       "例: 1000万円稼げたら何に使いたいですか？"),
    ],
    "video_funnel_ep2": [
        (["product", "mechanism"],      "商品の仕組み・特徴（一言）",           "例: 97%の敗者ロジックを逆手に取る自動売買"),
        (["cta", "question"],           "動画後の質問文",                       "例: 月60万円入ってきたら生活はどう変わりますか？"),
    ],
    "video_funnel_ep3": [
        (["pricing", "regular_price"],  "通常価格",                             "例: 298,000円"),
        (["pricing", "special_price"],  "特別価格（割引後）",                   "例: 98,000円"),
        (["pricing", "limit"],          "限定枠数・締め切り",                   "例: 先着80枠・明日20時〜"),
        (["cta", "question"],           "動画後の質問文・行動促進テキスト",     "例: 先行受付はこちらから"),
    ],
    "optin": [
        (["product", "free_offer"],     "特典・情報の名称（無料プレゼントあり→特典名 / 情報公開型→登録で受け取れる情報・手法の名称）", "例（無料プレゼント）: FX攻略キーワード図解集 / 例（情報公開型）: 月60万円を叩き出した手法"),
        (["cta", "question"],           "オプトイン後の行動促進文",             "例: 今すぐ受け取る / 手法を受け取る"),
    ],
}

AUTH_PASS = os.environ.get("FUNNEL_PASS", "funnel2024")

# ── ページ設定 ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ファネル生成ツール",
    page_icon="📄",
    layout="wide",
)

# ── ヘルパー関数 ───────────────────────────────────────────────────────
def _is_missing(val) -> bool:
    if val is None:
        return True
    return str(val).strip().lower() in ("", "不明", "null", "none", "?", "-", "unknown")


def check_missing_fields(config: dict, funnel_type: str = "") -> list:
    fields = CRITICAL_FIELDS_LIST + CRITICAL_FIELDS_BY_TYPE.get(funnel_type, [])
    missing = []
    for keys, label, example in fields:
        obj = config
        for k in keys[:-1]:
            obj = (obj or {}).get(k) or {}
        val = (obj or {}).get(keys[-1])
        if _is_missing(val):
            missing.append({"id": "__".join(keys), "label": label, "example": example, "keys": keys})
    return missing


def build_step2_fields(config: dict, funnel_type: str) -> list:
    """Step2に表示するフィールド一覧を構築（抽出済みも含め全件表示）"""
    all_defs = CRITICAL_FIELDS_LIST + CRITICAL_FIELDS_BY_TYPE.get(funnel_type, [])
    fields = []
    for keys, label, example in all_defs:
        obj = config
        for k in keys[:-1]:
            obj = (obj or {}).get(k) or {}
        val = (obj or {}).get(keys[-1]) or ""
        current = "" if _is_missing(val) else str(val)
        fields.append({
            "id":         "__".join(keys),
            "label":      label,
            "example":    example,
            "keys":       keys,
            "value":      current,
            "is_missing": _is_missing(val),
        })
    return fields


def apply_missing_values(config: dict, values: dict) -> dict:
    for field_id, value in values.items():
        value = value.strip()
        if not value:
            continue
        parts = field_id.split("__")
        if len(parts) < 2:
            continue
        section, key = parts[0], parts[1]
        if not isinstance(config.get(section), dict):
            config[section] = {}
        config[section][key] = value
    return config


# ── 認証 ──────────────────────────────────────────────────────────────
def check_auth() -> bool:
    if st.session_state.get("authenticated"):
        return True
    st.title("📄 ファネル生成ツール")
    pwd = st.text_input("パスワード", type="password", key="pwd_input")
    if st.button("ログイン", type="primary"):
        if pwd == AUTH_PASS:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("パスワードが違います")
    return False


if not check_auth():
    st.stop()

# ── セッション初期化 ───────────────────────────────────────────────────
_defaults = {
    "step":            "input",
    "input_mode":      "script",
    "script_text":     "",
    "script_name":     "",
    "config":          {},
    "funnel_type":     "optin",
    "length":          "long",
    "use_opus":        False,
    "md_content":      "",
    "html_content":    "",
    "tmp_dir":         None,
    "style_reference": "",
}
for _k, _v in _defaults.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── サイドバー ─────────────────────────────────────────────────────────
with st.sidebar:
    st.header("ファネル生成ツール")
    if st.button("🔄 最初からやり直す"):
        for k in list(st.session_state.keys()):
            if k != "authenticated":
                del st.session_state[k]
        st.rerun()

# ── ステップ1: ファイルアップロード ───────────────────────────────────────
if st.session_state.step == "input":
    st.title("📄 ファネル生成ツール")

    # 入力形式の選択（フォーム外：変更で即リフレッシュ）
    input_mode = st.radio(
        "入力形式",
        ["script", "outline"],
        format_func=lambda x: {
            "script":  "📄 台本アップロード（AIが自動で骨子を生成）",
            "outline": "📋 骨子アップロード（骨子生成スキップ・精度UP・API費用削減）",
        }[x],
        horizontal=True,
        key="input_mode_radio",
    )

    THEMES = {
        "高級感（デフォルト）": {"color": "#f0c040", "desc": "黒 × ゴールド｜プレミアム・希少性を演出"},
        "プロフェッショナル":   {"color": "#a0b4c8", "desc": "黒 × シルバー｜知性・信頼感を演出"},
        "エネルギー":           {"color": "#ff4433", "desc": "黒 × レッド｜行動喚起・緊迫感を演出"},
        "ナチュラル":           {"color": "#6abf69", "desc": "黒 × グリーン｜安心感・健康・自然を演出"},
        "カスタム":             {"color": None,       "desc": "カラーピッカーで自由に指定"},
    }
    selected_theme = st.selectbox(
        "カラーテーマ",
        list(THEMES.keys()),
        format_func=lambda k: f"{k}　—　{THEMES[k]['desc']}",
        key="selected_theme",
    )
    if THEMES[selected_theme]["color"] is None:
        accent_color = st.color_picker("メインカラー", "#f0c040", key="custom_accent")
    else:
        accent_color = THEMES[selected_theme]["color"]

    with st.form("input_form"):
        if input_mode == "script":
            st.caption("台本（.docx / .txt）をアップロードしてください。AIが自動で骨子を生成してからLP生成します。")
            uploaded = st.file_uploader("台本ファイル（.docx または .txt）", type=["docx", "txt"])
        else:
            st.caption("台本を元に事前作成した骨子（.md / .txt / .docx）をアップロードしてください。骨子生成ステップをスキップします。")
            uploaded = st.file_uploader("骨子ファイル（.md / .txt / .docx）", type=["md", "txt", "docx"])

        col1, col2 = st.columns(2)
        with col1:
            funnel_type = st.selectbox(
                "ファネル種別",
                list(FUNNEL_LABELS.keys()),
                format_func=lambda x: FUNNEL_LABELS[x],
            )
        with col2:
            length = st.selectbox(
                "長さ",
                list(LENGTH_LABELS.keys()),
                format_func=lambda x: LENGTH_LABELS[x],
            )

        use_opus = st.checkbox(
            "🚀 高精度モード（Opus）— 文章生成のみOpus使用・API費用が約1.7倍になります",
            value=False,
        )

        ref_uploaded = st.file_uploader(
            "参考ファネル（任意・.html / .txt / 画像）— コピーのトーン・訴求強度の手本として使用。画像は初回のみ解析して保存します",
            type=["html", "htm", "txt", "png", "jpg", "jpeg", "webp"],
            accept_multiple_files=True,
        )

        seller_photo = st.file_uploader(
            "販売者の写真（任意・画像）— 外見・雰囲気を自動分析して画像指示に使用します",
            type=["png", "jpg", "jpeg", "webp"],
        )

        submitted = st.form_submit_button("生成開始 →", type="primary", use_container_width=True)

    if submitted and not uploaded:
        label = "台本" if input_mode == "script" else "骨子"
        st.error(f"{label}ファイルをアップロードしてください")

    if submitted and uploaded:
        tmp_dir = tempfile.mkdtemp()
        script_path = Path(tmp_dir) / uploaded.name
        script_path.write_bytes(uploaded.getvalue())

        # 参考ファネルの処理
        style_reference = ""
        if ref_uploaded:
            media_map = {".png": "image/png", ".jpg": "image/jpeg",
                         ".jpeg": "image/jpeg", ".webp": "image/webp"}
            with st.spinner("参考ファネルを解析中（初回のみ）..."):
                for f in ref_uploaded:
                    fname = f.name.lower()
                    is_image = fname.endswith((".png", ".jpg", ".jpeg", ".webp"))
                    is_html  = fname.endswith((".html", ".htm"))
                    if is_image:
                        ext = "." + fname.rsplit(".", 1)[-1]
                        media_type = media_map.get(ext, "image/png")
                        extracted = extract_copy_from_image(f.getvalue(), media_type)
                        save_reference(funnel_type, extracted, is_html=False)
                    else:
                        raw = f.getvalue().decode("utf-8")
                        save_reference(funnel_type, raw, is_html)
            # 保存後、同系列の全参考ファネルを統合して使う
            style_reference = load_references_for_generation(funnel_type) or ""
        else:
            style_reference = load_references_for_generation(funnel_type) or ""

        src_label = "台本" if input_mode == "script" else "骨子"
        with st.spinner(f"{src_label}から設定情報を抽出中...（30秒〜1分かかります）"):
            script_text = load_script(str(script_path))
            config_path = Path(tmp_dir) / (script_path.stem + ".yaml")
            config = extract_config_from_script(script_text, config_path)

        # 販売者写真がアップロードされていれば外見・雰囲気を自動分析してセット（キャッシュ優先）
        if seller_photo:
            fname_p = seller_photo.name.lower()
            media_map = {".png": "image/png", ".jpg": "image/jpeg",
                         ".jpeg": "image/jpeg", ".webp": "image/webp"}
            ext_p = "." + fname_p.rsplit(".", 1)[-1]
            media_type_p = media_map.get(ext_p, "image/jpeg")
            with st.spinner("販売者の写真を確認中..."):
                appearance, from_cache = get_or_extract_appearance(
                    seller_photo.getvalue(), media_type_p, seller_photo.name
                )
            if not isinstance(config.get("seller"), dict):
                config["seller"] = {}
            config["seller"]["appearance"] = appearance
            if from_cache:
                st.info(f"写真キャッシュを使用しました（API呼び出しなし）: {appearance}")
            else:
                st.success(f"写真を分析しました（キャッシュ保存済み）: {appearance}")

        st.session_state.update({
            "step":            "missing",
            "input_mode":      input_mode,
            "script_text":     script_text,
            "script_name":     uploaded.name,
            "config":          config,
            "funnel_type":     funnel_type,
            "length":          length,
            "use_opus":        use_opus,
            "tmp_dir":         tmp_dir,
            "style_reference": style_reference,
            "accent_color":    accent_color,
        })
        st.rerun()

# ── ステップ2: 生成情報の確認・入力 ────────────────────────────────────
elif st.session_state.step == "missing":
    funnel_type_s2 = st.session_state.funnel_type
    st.title(f"📄 生成情報の確認・入力（{FUNNEL_LABELS.get(funnel_type_s2, funnel_type_s2)}）")

    step2_fields = build_step2_fields(st.session_state.config, funnel_type_s2)
    missing_count = sum(1 for f in step2_fields if f["is_missing"])
    if missing_count > 0:
        st.warning(f"⚠️ {missing_count}件が未入力です。入力すると生成精度が上がります。抽出済みの項目も確認・修正できます。")
    else:
        st.success("✅ すべての情報が抽出済みです。内容を確認して生成してください。")

    # 販売者写真アップロード（フォームの外に配置）
    current_appearance = (st.session_state.config.get("seller") or {}).get("appearance", "")
    if not _is_missing(current_appearance):
        st.success(f"✅ 外見・雰囲気 設定済み: {current_appearance}")
        st.caption("変更する場合のみ写真をアップロードしてください")
    else:
        st.markdown("**販売者の写真（任意）**")
    appearance_photo = st.file_uploader(
        "写真をアップロードすると外見・雰囲気を自動分析します（キャッシュ保存で2回目以降はAPI費用なし）",
        type=["png", "jpg", "jpeg", "webp"],
        key="missing_seller_photo",
    )
    if appearance_photo:
        fname_p = appearance_photo.name.lower()
        media_map = {".png": "image/png", ".jpg": "image/jpeg",
                     ".jpeg": "image/jpeg", ".webp": "image/webp"}
        ext_p = "." + fname_p.rsplit(".", 1)[-1]
        media_type_p = media_map.get(ext_p, "image/jpeg")
        with st.spinner("販売者の写真を確認中..."):
            appearance, from_cache = get_or_extract_appearance(
                appearance_photo.getvalue(), media_type_p, appearance_photo.name
            )
        label = "キャッシュ使用（API費用なし）" if from_cache else "分析完了・キャッシュ保存済み"
        st.success(f"外見・雰囲気（{label}）: {appearance}")
        st.session_state["seller_appearance_from_photo"] = appearance
    else:
        st.session_state.pop("seller_appearance_from_photo", None)

    st.divider()

    with st.form("missing_form"):
        values = {}
        for field in step2_fields:
            if field["is_missing"]:
                label_text = f"⚠️ {field['label']}"
            else:
                label_text = f"✅ {field['label']}（抽出済み・修正可）"

            if field["id"] == "seller__appearance":
                label_text += "（写真をアップロードした場合は空欄でOK）"

            values[field["id"]] = st.text_input(
                label_text,
                value=field["value"],
                placeholder=field["example"],
                key=f"field_{field['id']}",
            )

        col1, col2 = st.columns(2)
        with col1:
            confirmed = st.form_submit_button("この内容で生成する →", type="primary", use_container_width=True)
        with col2:
            skipped = st.form_submit_button("確認せずに生成する", use_container_width=True)

    if confirmed or skipped:
        config = apply_missing_values(st.session_state.config, values) if confirmed else st.session_state.config
        if st.session_state.get("seller_appearance_from_photo"):
            if not isinstance(config.get("seller"), dict):
                config["seller"] = {}
            config["seller"]["appearance"] = st.session_state["seller_appearance_from_photo"]
        st.session_state.config = config
        st.session_state.step = "generating"
        st.rerun()

# ── ステップ3: 生成 ────────────────────────────────────────────────────
elif st.session_state.step == "generating":
    funnel_type = st.session_state.funnel_type
    length      = st.session_state.length
    use_opus    = st.session_state.get("use_opus", False)
    _gen_label  = f"{FUNNEL_LABELS.get(funnel_type, funnel_type)}（{LENGTH_LABELS.get(length, length)}）"
    _opus_label = "　🚀 高精度Opusモード" if use_opus else ""
    st.title(f"📄 生成中... {_gen_label}{_opus_label}")

    config      = st.session_state.config
    script_text = st.session_state.script_text
    script_name = st.session_state.script_name
    tmp_dir     = st.session_state.tmp_dir or "."

    input_mode = st.session_state.get("input_mode", "script")

    try:
        with st.status("コンテンツを生成中...", expanded=True) as status:
            if input_mode == "outline":
                outline = script_text
                st.write("✅ 骨子ファイルをそのまま使用（生成スキップ）")
            else:
                st.write("台本から骨子を生成中...")
                outline, cached = get_outline(script_text, script_name, funnel_type)
                st.write(f"✅ 骨子{'（キャッシュ）' if cached else 'を生成しました'}")

            st.write("サンプル構造を読み込み中...")
            structure = get_sample_structure(funnel_type, length)
            n_sections = len(structure.get("sections", []))
            st.write(f"✅ {n_sections} セクション構成")

            st.write(f"各セクションのコンテンツを生成中（{n_sections} 回 API 呼び出し）...")
            config_text     = config_to_text(config)
            combined        = "\n\n".join(filter(None, [config_text, outline]))
            style_reference = st.session_state.get("style_reference", "")
            if style_reference:
                st.write("📎 参考ファネルをスタイル参照として使用中")
            text_model = "claude-opus-4-7" if use_opus else "claude-sonnet-4-6"
            md_content, _ = generate_page(
                structure, combined, funnel_type, length,
                style_reference=style_reference,
                text_model=text_model,
            )
            st.write("✅ Markdown 生成完了")

            st.write("HTML を生成中...")
            type_label   = FUNNEL_LABELS.get(funnel_type, funnel_type)
            length_label = LENGTH_LABELS.get(length, length)
            accent_color = st.session_state.get("accent_color", "#f0c040")
            html_content = markdown_to_html(md_content, f"{type_label}（{length_label}）", tmp_dir, accent_color=accent_color)
            st.write("✅ HTML 生成完了")

            status.update(label="✅ 生成完了！", state="complete")

        st.session_state.update({
            "step":         "done",
            "md_content":   md_content,
            "html_content": html_content,
        })
        st.rerun()

    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
        st.exception(e)

# ── ステップ4: 結果表示 ────────────────────────────────────────────────
elif st.session_state.step == "done":
    stem        = Path(st.session_state.script_name).stem
    ts          = datetime.now().strftime("%Y%m%d_%H%M")
    funnel_type = st.session_state.funnel_type
    length      = st.session_state.length
    fname       = f"{ts}_{stem}_{funnel_type}_{length}"

    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.markdown("### ✅ 生成完了")
    with col2:
        st.download_button(
            "📥 Markdown (.txt)",
            data=st.session_state.md_content.encode("utf-8"),
            file_name=f"{fname}.txt",
            mime="text/plain",
            use_container_width=True,
        )
    with col3:
        st.download_button(
            "📥 HTML (.html)",
            data=st.session_state.html_content.encode("utf-8"),
            file_name=f"{fname}.html",
            mime="text/html",
            use_container_width=True,
        )

    components.html(st.session_state.html_content, height=1200, scrolling=True)
