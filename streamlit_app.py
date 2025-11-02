import streamlit as st
import requests

# 看護管理者向け 経営理論チャットボット
st.set_page_config(page_title="看護管理者のための経営理論チャットボット", page_icon="🩺")
st.title("🩺 看護管理者向け 経営理論チャットボット")
st.write("看護管理（看護管理者・師長・主任など）を対象に、経営理論をわかりやすく、実務に使える形で説明します。事例や具体的な実践アドバイスを含めます。")

# APIキー取得
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    st.warning(".streamlit/secrets.toml に GEMINI_API_KEY を設定してください（Streamlit Cloud を使用する場合）。ローカル実行時は環境変数等でキーを設定してください。")

# サイドバー設定
with st.sidebar:
    st.header("設定")
    model_name = st.selectbox("モデルを選択", ["gemini-2.5-flash", "gemini-2.5-pro"], index=0)
    explanation_level = st.selectbox("説明レベル", ["かんたん（新人・現場向け）", "標準（管理者向け）", "詳しい（研究・教育向け）"], index=1)
    include_examples = st.checkbox("具体的な現場事例を含める", value=True)
    include_steps = st.checkbox("実行手順（ステップ）を含める", value=True)
    include_tools = st.checkbox("使えるツール・テンプレートを示す", value=True)

# テンプレートトピック（看護管理に関連した経営理論トピック）
st.subheader("トピックを選ぶ（または自由に質問してください）")
topic = st.selectbox("よくあるトピック", [
    "選んでください",
    "スタッフ配置（人員計画・シフト最適化）",
    "コスト管理と予算編成",
    "品質管理（CQI/PDCA・看護の安全）",
    "リーダーシップとモチベーション",
    "組織文化と風土改革",
    "戦略的計画（病棟・部門レベル）",
    "業務改善とプロセス設計（看護動線など）",
    "意思決定とデータ活用（KPI設定・可視化）",
    "危機管理・BCP（感染対策等）"
])

preset_question = ""
if topic != "選んでください":
    preset_question = st.text_area("テンプレート質問（編集可）", value=f"{topic}について、看護管理者向けに{explanation_level}の説明と実践アドバイスを教えてください。", height=80)
else:
    preset_question = st.text_area("質問を入力してください（自由入力）", value="看護管理に関する質問を入力してください。例：病棟のスタッフ不足をどう戦略的に解決するか？", height=80)

# 追加オプション
st.markdown("---")
with st.expander("追加オプション（詳細）", expanded=False):
    st.write("出力フォーマットや長さの微調整")
    max_tokens = st.slider("応答の最大トークン（目安）", min_value=100, max_value=2048, value=600)
    temperature = st.slider("創造性（temperature）", min_value=0.0, max_value=1.0, value=0.4, step=0.1)

# チャット履歴の管理
if "messages" not in st.session_state:
    st.session_state.messages = []

# 表示しているメッセージをレンダリング
for msg in st.session_state.messages:
    role = msg.get("role", "user")
    with st.chat_message(role):
        st.markdown(msg.get("content", ""))

# ユーザー入力
user_input = st.chat_input("質問を入力して Enter を押してください（テンプレートを編集して使えます）")
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    # 表示
    with st.chat_message("user"):
        st.markdown(user_input)

    # システムプロンプトを準備（看護管理者向け）
    system_prompt = (
        "あなたは看護管理と経営理論に詳しい専門家です。受け手は看護管理者（師長・主任・看護部門の管理職）で、実務にすぐ使える具体的な助言を求めています。回答は日本語で、以下の点を守ってください：\n"
        "- 看護現場の制約（人員不足、交代制勤務、法的・倫理的配慮）を踏まえること。\n"
        "- 具体例や簡単なチェックリスト、実行ステップを含めること（要望があればテンプレートとして示す）。\n"
        "- KPIや評価指標の具体例を示すこと。\n"
        "- できるだけ短い見出しと箇条書きで読みやすくまとめること。\n"
        "- エビデンスが必要な場合はその旨を明示し、参考にする文献タイプ（ガイドライン、レビュー）を示す。"
    )

    # メッセージをAPI用に整形
    contents = []
    contents.append({"role": "system", "parts": [{"text": system_prompt}]})

    # コンテキスト（最近の会話）を付与
    for m in st.session_state.messages:
        role = m["role"]
        api_role = "user" if role == "user" else "assistant"
        contents.append({"role": api_role, "parts": [{"text": m["content"]}]})

    # 追加ヒント（出力スタイル）
    style_hint = f"説明レベル: {explanation_level}. 具体例: {'含める' if include_examples else '含めない'}. 実行手順: {'含める' if include_steps else '含めない'}. テンプレート: {'提示' if include_tools else '提示しない'}."
    contents.append({"role": "user", "parts": [{"text": style_hint}]})

    # API呼び出し
    api_url = f"https://generativelanguage.googleapis.com/v1/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": contents,
        "generationConfig": {
            "temperature": temperature,
            "topP": 0.9,
            "maxOutputTokens": max_tokens
        }
    }

    # 送信とレスポンス表示
    with st.chat_message("assistant"):
        with st.spinner("応答を生成中..."):
            if not GEMINI_API_KEY:
                reply_text = "エラー: GEMINI_API_KEY が設定されていません。環境変数または .streamlit/secrets.toml を確認してください。"
            else:
                try:
                    resp = requests.post(api_url, headers=headers, json=data, timeout=60)
                    resp.raise_for_status()
                    rj = resp.json()
                    if "candidates" in rj and rj["candidates"] and "content" in rj["candidates"][0] and "parts" in rj["candidates"][0]["content"]:
                        reply_text = rj["candidates"][0]["content"]["parts"][0]["text"]
                    else:
                        reply_text = f"エラー: 予期しないAPI応答形式です。{rj}"
                except requests.exceptions.RequestException as e:
                    reply_text = f"APIリクエストエラー: {e}"

            st.markdown(reply_text)
            st.session_state.messages.append({"role": "assistant", "content": reply_text})

# ボタンでテンプレート質問を送信
st.markdown("---")
col1, col2 = st.columns(2)
with col1:
    if st.button("スタッフ配置のテンプレートを挿入"):
        template = (
            "病棟でのスタッフ不足に対処するための戦略（短期・中期・長期）を、看護管理者向けに実行可能な手順で教えてください。"
        )
        st.session_state.messages.append({"role": "user", "content": template})
        st.experimental_rerun()
with col2:
    if st.button("品質管理（PDCA）のテンプレートを挿入"):
        template = (
            "看護の質向上のためのPDCAサイクルの回し方を、指標（KPI）と実行チェックリスト付きで教えてください。"
        )
        st.session_state.messages.append({"role": "user", "content": template})
        st.experimental_rerun()

# フッター
st.caption("このアプリは看護管理者向けの説明を支援するためのツールです。実際の運用や法的判断は医療機関の規定や専門家の助言に従ってください。")

# End of file
