import streamlit as st
import requests

# タイトルと説明の表示
st.title("💬 Gemini チャットボット（経営理論モード対応）")
st.write("このチャットボットは Google の Gemini API を利用して応答を生成します。経営理論について「わかりやすく」説明するためのモードを追加しました。")

# Streamlit Community CloudのSecretsからAPIキーを取得
# .streamlit/secrets.toml に GEMINI_API_KEY = "YOUR_API_KEY" を設定してください
gemini_api_key = st.secrets.get("GEMINI_API_KEY")

if not gemini_api_key:
    st.info("Streamlit Community CloudのSecretsに `GEMINI_API_KEY` を設定してください。", icon="🗝️")
else:
    # ユーザーがモデルを選択できるようにする（正しいモデル名表記を使用）
    model_name = st.selectbox(
        "使用する Gemini モデルを選択",
        (
            "gemini-2.5-flash",
            "gemini-2.5-pro"
        )
    )
    st.write(f"現在のモデル: **{model_name}**")  # 選択中のモデルを表示

    # 経営理論に特化して「やさしく」回答するモード
    management_mode = st.checkbox("経営理論に特化してやさしく説明する", value=True)

    # 説明レベル（出力の詳細さ）
    explanation_level = st.selectbox(
        "説明レベル",
        ("かんたん（初心者向け）", "標準（大学生・実務入門）", "詳しい（専門家向け）")
    )

    # 説明レベルに応じた generationConfig のパラメータ調整
    if explanation_level == "かんたん（初心者向け）":
        temp = 0.2
        max_tokens = 300
        style_hint = "短く、平易な日本語で、例え話や箇条書きを使って説明してください。専門用語を使う場合は必ず注釈をつけてください。"
    elif explanation_level == "標準（大学生・実務入門）":
        temp = 0.5
        max_tokens = 512
        style_hint = "読みやすい日本語で、重要な概念を定義し、実務的な例と簡単な図解（テキストによる）を使って説明してください。"
    else:
        temp = 0.7
        max_tokens = 1024
        style_hint = "専門的な用語を許容し、理論の背景・代表的な論者・批判点・実務への応用を含めて詳しく説明してください。"

    if "messages" not in st.session_state:
        # 初期のメッセージリストをセッションステートに作成
        st.session_state.messages = []

    # 既存のチャットメッセージを表示
    for message in st.session_state.messages:
        # roleに応じて日本語で表示
        display_role = "ユーザー" if message["role"] == "user" else "アシスタント"
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # ユーザーがメッセージを入力するためのチャット入力フィールド
    if prompt := st.chat_input("ここにメッセージを入力"):
        # ユーザーのプロンプトを保存・表示
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Gemini API用にメッセージ形式を準備（ロールを "user"/"assistant"/"system" に変換）
        gemini_messages = []

        # 経営理論モードが有効な場合、最初に system メッセージで振る舞いを指定
        if management_mode:
            system_instruction = (
                "あなたは経営理論の専門家で、受け手にとって分かりやすく説明する能力があります。"
                "依頼があれば、次の点を常に守ってください：\n"
                f"- 回答は日本語で書くこと。\n"
                f"- {style_hint}\n"
                "- 必要に応じて簡単な箇条書き・番号付きリスト・例え話を用いること。\n"
                "- 初心者向けの用語説明（定義）を含めること。\n"
                "- 質問で事例や業界が指定されている場合は、その文脈に合わせて説明すること。"
            )
            gemini_messages.append({
                "role": "system",
                "parts": [{"text": system_instruction}]
            })

        # 既存の会話を API に渡す
        for m in st.session_state.messages:
            # StreamlitのロールをAPIのロールにマッピング
            if m["role"] == "user":
                api_role = "user"
            elif m["role"] == "assistant":
                api_role = "assistant"
            else:
                api_role = "user"
            gemini_messages.append(
                {
                    "role": api_role,
                    "parts": [{"text": m["content"]}]
                }
            )

        # Gemini API endpoint
        api_url = f"https://generativelanguage.googleapis.com/v1/models/{model_name}:generateContent?key={gemini_api_key}"

        headers = {"Content-Type": "application/json"}
        data = {
            "contents": gemini_messages,
            "generationConfig": {
                "temperature": temp,
                "topP": 0.8,
                "maxOutputTokens": max_tokens
            }
        }

        try:
            # アシスタントの応答をチャットメッセージコンテナ内に表示
            with st.chat_message("assistant"):
                with st.spinner(f"{model_name} が応答を生成中..."):
                    response = requests.post(api_url, headers=headers, json=data, timeout=60)
                    response.raise_for_status()  # HTTPエラーがあれば例外を発生

                    result = response.json()

                    # APIからのレスポンス構造のチェックと応答の取得
                    if "candidates" in result and result["candidates"] and \
                       "content" in result["candidates"][0] and \
                       "parts" in result["candidates"][0]["content"] and \
                       result["candidates"][0]["content"]["parts"]:

                        gemini_reply = result["candidates"][0]["content"]["parts"][0]["text"]
                    else:
                        # 予期しないレスポンス形式の場合
                        gemini_reply = f"エラー: 予期しないAPI応答形式です。{result}"

                    st.markdown(gemini_reply)

            # アシスタントの応答をセッションステートに保存
            st.session_state.messages.append({"role": "assistant", "content": gemini_reply})

        except requests.exceptions.RequestException as e:
            error_message = f"APIリクエストエラーが発生しました: {e}"
            st.error(error_message)
            st.session_state.messages.append({"role": "assistant", "content": error_message})
        except Exception as e:
            error_message = f"予期せぬエラーが発生しました: {e}"
            st.error(error_message)
            st.session_state.messages.append({"role": "assistant", "content": error_message})
