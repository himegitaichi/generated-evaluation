import streamlit as st
import os
import random
import csv
import datetime
from PIL import Image

# ==========================================
# 1. 設定
# ==========================================
IMAGE_DIR = "images"
RESULTS_DIR = "results_eval"
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

# 評価項目リスト
METRICS = {
    "authenticity": "1. 地域の真正性（その地域らしい雰囲気があるか？）",
    "fidelity": "2. 特徴の再現度（配布資料の特徴を捉えているか？）",
    "naturalness": "3. 構造の自然さ（建物として破綻していないか？）",
    "harmony": "4. 景観調和性（歴史的町並みに馴染むか？）",
}

# リッカート尺度の定義
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
        all_images = [
            f
            for f in os.listdir(IMAGE_DIR)
            if f.lower().endswith((".png", ".jpg", ".jpeg"))
        ]

        # ▼▼▼ 修正ここから ▼▼▼

        # 1. 表示したい順序を定義（ここに書いた順に表示されます）
        #    REGION_MAPのキーと一致させてください
        REGION_ORDER = [
            "saga",  # 佐賀
            "miyazaki",  # 宮崎
            "osaka",  # 大阪
            "nara",  # 奈良
            "shiga",  # 滋賀
            "saitama",  # 埼玉
        ]

        # 2. 並び替え用の関数を定義
        def sort_key(filename):
            # ファイル名から "saga" などを取り出す
            try:
                code = filename.split("_")[0]
            except:
                code = ""

            # リストの何番目にあるかを探す（リストにないものは一番後ろへ）
            if code in REGION_ORDER:
                return (REGION_ORDER.index(code), filename)
            else:
                return (len(REGION_ORDER), filename)

        # 3. 定義した順序で並び替え実行
        all_images.sort(key=sort_key)

        # ▲▲▲ 修正ここまで ▲▲▲

    else:
        st.error("画像フォルダが見つかりません。")
        all_images = []

    st.session_state["images"] = all_images
    # 以下、変更なし
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
    1. お手元の **「参考資料（カンニングシート）」** をご用意ください。
    2. 画面に表示される画像が **「どこの地域の設定か」** をお伝えします。
    3. 資料と照らし合わせながら、**4つの項目** を評価してください。
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

    # ファイル名解析
    try:
        parts = filename.split("_")
        true_region_code = parts[0]  # saga
        prompt_type = parts[1]  # simple
    except:
        true_region_code = "unknown"
        prompt_type = "unknown"

    true_region_name = REGION_MAP.get(true_region_code, "不明")

    # 進捗バー
    st.progress((current_idx + 1) / total_images)
    st.caption(f"画像: {current_idx + 1} / {total_images}")

    # --- レイアウト: 画像と正解情報をシンプルに表示 ---
    st.subheader(f"正解設定: 【 {true_region_name} 】")
    st.info(f"お手元の資料の **「{true_region_name}」** のページをご覧ください。")

    img_path = os.path.join(IMAGE_DIR, filename)
    try:
        image = Image.open(img_path)
        # 画像を大きく表示するために use_container_width=True
        st.image(image, use_container_width=True)
    except:
        st.error(f"画像エラー: {filename}")

    st.markdown("---")

    # --- 評価フォーム ---
    with st.form(key=f"form_{current_idx}"):
        st.write("### 評価アンケート")

        input_scores = {}

        for key, question in METRICS.items():
            st.markdown(f"**{question}**")
            selected_label = st.radio(
                f"{key}_label",
                options=list(LIKERT_SCALE.keys()),
                index=2,  # デフォルト: 3. どちらともいえない
                horizontal=True,
                label_visibility="collapsed",
                key=f"{key}_{current_idx}",
            )
            input_scores[key] = LIKERT_SCALE[selected_label]
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

# --- 管理者メニュー ---
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
