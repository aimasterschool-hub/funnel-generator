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
CRITICAL_FIELDS_LIST = [
    (["seller", "name"],       "販売者の名前",                          "例: 加藤かおる"),
    (["seller", "gender"],     "販売者の性別",                          "女性 または 男性"),
    (["product", "name"],      "商品名（正式名称）",                     "例: Sign Edge"),
    (["results", "headline"],  "実績の一言キャッチ（LPコピーに使用）",   "例: 元手1万円で月60万円"),
    (["seller", "appearance"], "販売者の外見・雰囲気（画像指示に使用）", "例: 30代女性、黒髪ショート、知的な雰囲気"),
]

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


def check_missing_fields(config: dict) -> list:
    missing = []
    for keys, label, example in CRITICAL_FIELDS_LIST:
        obj = config
        for k in keys[:-1]:
            obj = (obj or {}).get(k) or {}
        val = (obj or {}).get(keys[-1])
        if _is_missing(val):
            missing.append({"id": "__".join(keys), "label": label, "example": example, "keys": keys})
    return missing


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
    "step":         "input",
    "script_text":  "",
    "script_name":  "",
    "config":       {},
    "missing_fields": [],
    "funnel_type":  "optin",
    "length":       "long",
    "md_content":   "",
    "html_content": "",
    "tmp_dir":      None,
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

# ── ステップ1: 台本アップロード ────────────────────────────────────────
if st.session_state.step == "input":
    st.title("📄 ファネル生成ツール")

    with st.form("input_form"):
        st.subheader("台本をアップロードして生成する")
        uploaded = st.file_uploader("台本ファイル（.docx または .txt）", type=["docx", "txt"])

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

        submitted = st.form_submit_button("生成開始 →", type="primary", use_container_width=True)

    if submitted and not uploaded:
        st.error("台本ファイルをアップロードしてください")

    if submitted and uploaded:
        tmp_dir = tempfile.mkdtemp()
        script_path = Path(tmp_dir) / uploaded.name
        script_path.write_bytes(uploaded.getvalue())

        with st.spinner("台本から設定情報を抽出中...（30秒〜1分かかります）"):
            script_text = load_script(str(script_path))
            config_path = Path(tmp_dir) / (script_path.stem + ".yaml")
            config = extract_config_from_script(script_text, config_path)

        missing = check_missing_fields(config)
        next_step = "missing" if missing else "generating"

        st.session_state.update({
            "step":          next_step,
            "script_text":   script_text,
            "script_name":   uploaded.name,
            "config":        config,
            "missing_fields": missing,
            "funnel_type":   funnel_type,
            "length":        length,
            "tmp_dir":       tmp_dir,
        })
        st.rerun()

# ── ステップ2: 不足フィールド入力 ─────────────────────────────────────
elif st.session_state.step == "missing":
    st.title("📄 追加情報の入力")
    st.info("台本から自動抽出できなかった項目を入力してください（Enterでスキップも可能です）")

    with st.form("missing_form"):
        values = {}
        for field in st.session_state.missing_fields:
            values[field["id"]] = st.text_input(
                field["label"],
                placeholder=field["example"],
                key=f"field_{field['id']}",
            )

        col1, col2 = st.columns(2)
        with col1:
            confirmed = st.form_submit_button("この内容で生成する →", type="primary", use_container_width=True)
        with col2:
            skipped = st.form_submit_button("スキップして生成する", use_container_width=True)

    if confirmed:
        config = apply_missing_values(st.session_state.config, values)
        st.session_state.config = config
        st.session_state.step = "generating"
        st.rerun()
    elif skipped:
        st.session_state.step = "generating"
        st.rerun()

# ── ステップ3: 生成 ────────────────────────────────────────────────────
elif st.session_state.step == "generating":
    st.title("📄 生成中...")

    config      = st.session_state.config
    script_text = st.session_state.script_text
    script_name = st.session_state.script_name
    funnel_type = st.session_state.funnel_type
    length      = st.session_state.length
    tmp_dir     = st.session_state.tmp_dir or "."

    try:
        with st.status("コンテンツを生成中...", expanded=True) as status:
            st.write("台本骨子を生成中...")
            outline, cached = get_outline(script_text, script_name)
            st.write(f"✅ 骨子{'（キャッシュ）' if cached else 'を生成しました'}")

            st.write("サンプル構造を読み込み中...")
            structure = get_sample_structure(funnel_type, length)
            n_sections = len(structure.get("sections", []))
            st.write(f"✅ {n_sections} セクション構成")

            st.write(f"各セクションのコンテンツを生成中（{n_sections} 回 API 呼び出し）...")
            config_text = config_to_text(config)
            combined    = "\n\n".join(filter(None, [config_text, outline]))
            md_content, _ = generate_page(structure, combined, funnel_type, length)
            st.write("✅ Markdown 生成完了")

            st.write("HTML を生成中...")
            type_label   = FUNNEL_LABELS.get(funnel_type, funnel_type)
            length_label = LENGTH_LABELS.get(length, length)
            html_content = markdown_to_html(md_content, f"{type_label}（{length_label}）", tmp_dir)
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
    st.title("✅ 生成完了")

    stem        = Path(st.session_state.script_name).stem
    ts          = datetime.now().strftime("%Y%m%d_%H%M")
    funnel_type = st.session_state.funnel_type
    length      = st.session_state.length
    fname       = f"{ts}_{stem}_{funnel_type}_{length}"

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "📥 Markdown をダウンロード (.txt)",
            data=st.session_state.md_content.encode("utf-8"),
            file_name=f"{fname}.txt",
            mime="text/plain",
            use_container_width=True,
        )
    with col2:
        st.download_button(
            "📥 HTML をダウンロード (.html)",
            data=st.session_state.html_content.encode("utf-8"),
            file_name=f"{fname}.html",
            mime="text/html",
            use_container_width=True,
        )

    st.subheader("プレビュー")
    components.html(st.session_state.html_content, height=900, scrolling=True)
