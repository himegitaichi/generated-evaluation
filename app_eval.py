import streamlit as st
import os
import random
import csv
import datetime
from PIL import Image
import pandas as pd  # 読み込み用に追加

# ==========================================
# 1. 設定 & データ定義 (変更なし)
# ==========================================
IMAGE_DIR = "images"
RESULTS_DIR = "results_eval"
os.makedirs(RESULTS_DIR, exist_ok=True)

REGION_MAP = {
    "saga": "佐賀",
    "miyazaki": "宮崎",
    "osaka": "大阪",
    "nara": "奈良",
    "shiga": "滋賀",
    "saitama": "埼玉",
}

# (中略: METRICS, LIKERT_SCALE はそのまま)
METRICS = {
    "authenticity": "1. 地域の真正性（その地域らしい雰囲気があるか？）",
    "fidelity": "2. 特徴の再現度（配布資料の特徴を捉えているか？）",
    "naturalness": "3. 構造の自然さ（建物として破綻していないか？）",
    "harmony": "4. 景観調和性（歴史的町並みに馴染むか？）",
}

LIKERT_SCALE = {
    "5. 非常にそう思う": 5,
    "4. ややそう思う": 4,
    "3. どちらともいえない": 3,
    "2. あまりそう思わない": 2,
    "1. 全くそう思わない": 1,
}

# ==========================================
# 2. 関数定義 (ここを修正)
# ==========================================


# ★ 追加: 完了済みの画像を取得する関数
def get_done_images(user_name):
    csv_path = os.path.join(RESULTS_DIR, f"eval_{user_name}.csv")
    if not os.path.exists(csv_path):
        return []
    try:
        df = pd.read_csv(csv_path)
        # 'image_file' 列にあるファイル名のリストを返す
        if "image_file" in df.columns:
            return df["image_file"].tolist()
        return []
    except:
        return []


# ★ 修正: ユーザー名を受け取り、未回答の画像だけをロードする
def load_image_list(user_name):
    image_files = []

    # フォルダ順に取得
    for region_code in REGION_MAP.keys():
        region_dir = os.path.join(IMAGE_DIR, region_code)
        if os.path.exists(region_dir):
            files = sorted(
                [f for f in os.listdir(region_dir) if f.endswith((".png", ".jpg"))]
            )
            for f in files:
                image_files.append(os.path.join(region_code, f))

    # ソート (順序固定)
    def sort_key(filepath):
        return os.path.basename(filepath)

    image_files.sort(key=sort_key)

    # ★ 済み画像を除外する処理
    done_files = get_done_images(user_name)  # ファイル名のリスト

    remaining_files = []
    for filepath in image_files:
        filename = os.path.basename(filepath)
        if filename not in done_files:
            remaining_files.append(filepath)

    return remaining_files, len(image_files)  # 残りリストと、全枚数を返す


# ==========================================
# 3. アプリケーション本体 (ここも修正)
# ==========================================

# ユーザー名入力
if "user_name" not in st.session_state or st.session_state["user_name"] == "":
    st.title("🏛️ 建築デザイン評価実験")
    st.info("分類実験のご協力ありがとうございました。続いて「評価」をお願いします。")

    name = st.text_input(
        "お名前（またはID）を入力してEnterを押してください", key="input_name"
    )
    if name:
        st.session_state["user_name"] = name
        st.rerun()

# 評価画面
else:
    user_name = st.session_state["user_name"]

    # ★ 毎回リストを更新して、終わったものを除外する
    target_images, total_count = load_image_list(user_name)
    done_count = total_count - len(target_images)

    # 全部終わっている場合
    if not target_images:
        st.balloons()
        st.success(f"全ての画像（{total_count}枚）の評価が完了しています！")
        st.info("データは保存されています。ブラウザを閉じて終了してください。")
        st.stop()  # 処理を止める

    # 現在の画像（リストの先頭を表示すればよい）
    current_filepath = target_images[0]
    filename = os.path.basename(current_filepath)

    # 情報解析
    try:
        parts = filename.split("_")
        true_region_code = parts[0]
        prompt_type = parts[1]
    except:
        true_region_code = "unknown"
        prompt_type = "unknown"

    true_region_name = REGION_MAP.get(true_region_code, "不明")

    # 進捗表示
    st.progress(done_count / total_count)
    st.caption(f"進捗: {done_count + 1} / {total_count} 枚目 （完了: {done_count}枚）")

    # 画像表示レイアウト
    col1, col2 = st.columns([1.5, 1])
    with col1:
        img_full_path = os.path.join(IMAGE_DIR, current_filepath)
        try:
            image = Image.open(img_full_path)
            st.image(image, use_container_width=True)
        except:
            st.error(f"画像読み込みエラー: {img_full_path}")

    with col2:
        st.subheader(f"正解設定: 【 {true_region_name} 】")
        st.info(
            f"お手元の資料の **「{true_region_name}」** のページを参照して評価してください。"
        )

    st.markdown("---")

    # フォーム
    # keyにfilenameを含めることで、画像が変わるたびにフォームをリセット
    with st.form(key=f"form_{filename}"):
        st.write("### 評価")
        input_scores = {}
        for key, question in METRICS.items():
            st.markdown(f"**{question}**")
            label = st.radio(
                f"{key}_radio",
                list(LIKERT_SCALE.keys()),
                index=2,
                horizontal=True,
                label_visibility="collapsed",
            )
            input_scores[key] = LIKERT_SCALE[label]
            st.write("")

        submit = st.form_submit_button("評価を保存して次へ", type="primary")

        if submit:
            # データの作成
            record = {
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "user": user_name,
                "image_file": filename,
                "region": true_region_code,
                "prompt_type": prompt_type,
                "authenticity": input_scores["authenticity"],
                "fidelity": input_scores["fidelity"],
                "naturalness": input_scores["naturalness"],
                "harmony": input_scores["harmony"],
            }

            # ★ ここで即時保存 (Appendモード)
            csv_path = os.path.join(RESULTS_DIR, f"eval_{user_name}.csv")
            file_exists = os.path.exists(csv_path)

            try:
                with open(csv_path, "a", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=record.keys())
                    # 初回のみヘッダーを書く
                    if not file_exists:
                        writer.writeheader()
                    writer.writerow(record)

                st.success("保存しました！")
                st.rerun()  # リロードして次の画像へ（リストから今の画像が消える）

            except Exception as e:
                st.error(f"保存エラー: {e}")

# --- 管理者メニュー (変更なし) ---
with st.sidebar:
    st.markdown("---")
    st.write(f"Login: {st.session_state.get('user_name', 'Guest')}")
    if st.checkbox("結果ファイルを表示"):
        if os.path.exists(RESULTS_DIR):
            files = os.listdir(RESULTS_DIR)
            for f in files:
                path = os.path.join(RESULTS_DIR, f)
                with open(path, "rb") as file:
                    st.download_button(f"📥 {f}", file, file_name=f)
