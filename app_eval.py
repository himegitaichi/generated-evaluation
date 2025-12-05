import streamlit as st
import os
import random
import csv
import datetime
from PIL import Image

# ==========================================
# 1. 設定 & データ定義
# ==========================================
IMAGE_DIR = "images"
RESULTS_DIR = "results_eval"  # 評価用の保存フォルダ
os.makedirs(RESULTS_DIR, exist_ok=True)

# ファイル名のコードと表示名の対応
REGION_MAP = {
    "saga": "佐賀",
    "miyazaki": "宮崎",
    "osaka": "大阪",
    "nara": "奈良",
    "shiga": "滋賀",
    "saitama": "埼玉",
}

# ★ カンニングシート（スタイルガイド）の内容
# 被験者が「特徴の再現度」を評価する際の基準になります。
REGION_FEATURES = {
    "saga": """
    **【佐賀（鹿島・塩田津・有田）の特徴】**
    * **屋根:** 入母屋造（いりもや）、茅葺き（かやぶき）
    * **壁:** 白漆喰、なまこ壁（白の網目模様）
    * **窓・扉:** 鉄扉（てつとびら/防火用の鉄窓）
    """,
    "miyazaki": """
    **【宮崎（日向市美々津）の特徴】**
    * **構え:** 妻入り（屋根の三角面が正面）、切妻造（きりづま）
    * **1階:** 千本格子（非常に目の細かい格子）、庇（ひさし）がある
    * **2階:** 白壁、手すりがあることが多い
    """,
    "osaka": """
    **【大阪（富田林）の特徴】**
    * **屋根:** 本瓦葺き（重厚な瓦）、煙出し（屋根の上の小屋根）
    * **壁:** 焼杉・杉板張り（黒っぽい板壁）と白漆喰のコントラスト
    * **窓:** 虫籠窓（むしこまど/全体を漆喰で塗り固めた丸い格子窓）
    """,
    "nara": """
    **【奈良（今井町）の特徴】**
    * **屋根:** 本瓦葺き、煙出し（越屋根）
    * **構造:** つし二階（天井が低く、窓が小さい2階）
    * **壁:** 白漆喰の壁がメイン
    * **窓:** 虫籠窓、出格子
    """,
    "shiga": """
    **【滋賀（近江八幡・彦根）の特徴】**
    * **壁:** ベンガラ壁（赤茶色）、大壁造（柱が見えない）
    * **構造:** うだつ（屋根の上に突き出た防火壁）
    * **その他:** 格子戸、見越しの松
    """,
    "saitama": """
    **【埼玉（川越）の特徴】**
    * **様式:** 蔵造り（重厚な耐火建築）
    * **壁:** 黒漆喰（黒く磨き上げられた壁）
    * **屋根:** 大きな鬼瓦、重厚な瓦屋根
    * **扉:** 観音開き（分厚い扉）
    """,
}

# 評価項目リスト
METRICS = {
    "authenticity": "1. 地域の真正性（その地域らしい雰囲気があるか？）",
    "fidelity": "2. 特徴の再現度（カンニングシートの特徴を捉えているか？）",
    "naturalness": "3. 構造の自然さ（建物として破綻していないか？）",
    "harmony": "4. 景観調和性（歴史的町並みに馴染むか？）",
}

# リッカート尺度の定義（表示ラベル -> 保存する数値）
LIKERT_SCALE = {
    "5. 非常にそう思う": 5,
    "4. ややそう思う": 4,
    "3. どちらともいえない": 3,
    "2. あまりそう思わない": 2,
    "1. 全くそう思わない": 1,
}

# ==========================================
# 2. セッションの初期化
# ==========================================
if "images" not in st.session_state:
    if os.path.exists(IMAGE_DIR):
        # 画像ファイルを取得してシャッフル
        all_images = [
            f
            for f in os.listdir(IMAGE_DIR)
            if f.lower().endswith((".png", ".jpg", ".jpeg"))
        ]
        random.shuffle(all_images)
    else:
        st.error("画像フォルダが見つかりません。")
        all_images = []

    st.session_state["images"] = all_images
    st.session_state["current_index"] = 0
    st.session_state["results"] = []
    st.session_state["user_name"] = ""
    st.session_state["started"] = False
    st.session_state["finished"] = False

# ==========================================
# 3. 画面構築
# ==========================================

# --- 画面A: スタート画面 ---
if not st.session_state["started"]:
    st.title("🏛️ 建築デザイン評価実験（フェーズ2）")
    st.info("分類実験のご協力ありがとうございました。続いて「評価」をお願いします。")
    st.markdown(
        """
    **【手順】**
    1. 生成された画像と、その画像の **「正解の地域（設定）」** を表示します。
    2. 同時に表示される **「地域の特徴（カンニングシート）」** を参考にしてください。
    3. その画像が地域の特徴を捉えているかなど、**4つの項目** を評価してください。
    """
    )

    name_input = st.text_input(
        "お名前（またはID）を入力してください", placeholder="例: yamada"
    )

    if st.button("評価を開始する", type="primary"):
        if name_input:
            st.session_state["user_name"] = name_input
            st.session_state["started"] = True
            st.rerun()
        else:
            st.warning("名前を入力してください。")

# --- 画面C: 終了画面 ---
elif st.session_state["finished"]:
    st.balloons()
    st.success(
        f"お疲れ様でした！ 全{len(st.session_state['results'])}枚の評価が完了しました。"
    )
    st.warning(
        "この画面のままブラウザを閉じて終了してください。（データは管理者に送信されました）"
    )

# --- 画面B: 評価メイン画面 ---
else:
    # 現在の画像情報
    current_idx = st.session_state["current_index"]
    total_images = len(st.session_state["images"])
    filename = st.session_state["images"][current_idx]

    # ファイル名解析 (例: saga_simple_001.png)
    try:
        parts = filename.split("_")
        true_region_code = parts[0]  # saga
        prompt_type = parts[1]  # simple
    except:
        true_region_code = "unknown"
        prompt_type = "unknown"

    true_region_name = REGION_MAP.get(true_region_code, "不明")
    feature_text = REGION_FEATURES.get(true_region_code, "特徴データがありません")

    # 進捗バー
    st.progress((current_idx + 1) / total_images)
    st.caption(f"画像: {current_idx + 1} / {total_images}")

    # --- レイアウト: 画像と正解情報を並べる ---
    col_img, col_info = st.columns([1.2, 1])

    with col_img:
        img_path = os.path.join(IMAGE_DIR, filename)
        try:
            image = Image.open(img_path)
            st.image(image, use_container_width=True)
        except:
            st.error(f"画像エラー: {filename}")

    with col_info:
        st.subheader(f"正解設定: {true_region_name}")
        st.info("この画像は、上記の地域として生成されました。")

        with st.expander("📖 この地域の特徴（カンニングシート）", expanded=True):
            st.markdown(feature_text)

    st.markdown("---")

    # --- 評価フォーム ---
    with st.form(key=f"form_{current_idx}"):
        st.write("### 評価アンケート")
        st.write("以下の4項目について、あなたの感覚に最も近いものを選んでください。")

        input_scores = {}

        # 4項目のラジオボタンを生成
        for key, question in METRICS.items():
            st.markdown(f"**{question}**")
            selected_label = st.radio(
                f"{key}_label",  # label_visibility="collapsed"にするためのダミー
                options=list(LIKERT_SCALE.keys()),
                index=2,  # デフォルト: 3. どちらともいえない
                horizontal=True,
                label_visibility="collapsed",
                key=f"{key}_{current_idx}",  # ユニークキー
            )
            input_scores[key] = LIKERT_SCALE[selected_label]  # 数値(1-5)に変換して保持
            st.write("")  # 余白

        submit_btn = st.form_submit_button("次の画像へ", type="primary")

        if submit_btn:
            # データの記録
            record = {
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "user": st.session_state["user_name"],
                "image_file": filename,
                "region": true_region_code,
                "prompt_type": prompt_type,
                "authenticity": input_scores["authenticity"],
                "fidelity": input_scores["fidelity"],
                "naturalness": input_scores["naturalness"],
                "harmony": input_scores["harmony"],
            }
            st.session_state["results"].append(record)

            # 次へ進む or 終了
            if current_idx + 1 < total_images:
                st.session_state["current_index"] += 1
                st.rerun()
            else:
                # CSV保存処理
                csv_filename = f"eval_{st.session_state['user_name']}.csv"
                csv_path = os.path.join(RESULTS_DIR, csv_filename)

                if st.session_state["results"]:
                    fieldnames = record.keys()
                    with open(csv_path, "w", newline="", encoding="utf-8") as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(st.session_state["results"])

                st.session_state["finished"] = True
                st.rerun()

# ==========================================
# 4. 管理者メニュー (CSVダウンロード)
# ==========================================
with st.sidebar:
    st.markdown("---")
    st.write("🔧 管理者メニュー")
    if st.checkbox("結果ファイルを表示"):
        if os.path.exists(RESULTS_DIR):
            files = os.listdir(RESULTS_DIR)
            if not files:
                st.caption("まだデータはありません")
            for f in files:
                path = os.path.join(RESULTS_DIR, f)
                with open(path, "rb") as file:
                    st.download_button(
                        label=f"📥 Download {f}",
                        data=file,
                        file_name=f,
                        mime="text/csv",
                    )
