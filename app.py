import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import date

# -----------------------
# 1. 기본 설정
# -----------------------

st.set_page_config(
    page_title="MoodLog",
    page_icon="🌱",
    layout="wide"
)

st.title("🌱 MoodLog")
st.caption("나의 하루를 기록하고 감정의 변화를 살펴보세요.")

# -----------------------
# 2. 감정 사전
# -----------------------

emotion_dict = {
    "긍정": [
        "행복", "즐겁", "신나", "좋았",
        "뿌듯", "기쁘", "설레", "감사",
        "만족", "재밌", "최고"
    ],

    "부정": [
        "우울", "슬프", "속상", "외롭",
        "짜증", "화났", "힘들", "불안",
        "걱정", "실망", "괴롭"
    ]
}

# -----------------------
# 3. 감정 분석
# -----------------------

def analyze_emotion(text):

    positive = [
        w for w in emotion_dict["긍정"]
        if w in text
    ]

    negative = [
        w for w in emotion_dict["부정"]
        if w in text
    ]

    score = len(positive) - len(negative)

    if score > 0:
        emotion = "긍정"
    elif score < 0:
        emotion = "부정"
    else:
        emotion = "중립"

    return emotion, score, positive, negative

# -----------------------
# 4. 데이터베이스
# -----------------------

conn = sqlite3.connect("moodlog.db")

conn.execute("""
CREATE TABLE IF NOT EXISTS diaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    diary_date TEXT,
    content TEXT,
    emotion TEXT,
    score INTEGER
)
""")

conn.commit()

# -----------------------
# 5. 메뉴
# -----------------------

menu = st.sidebar.radio(
    "메뉴",
    ["✏️ 일기 작성", "📊 감정 분석", "📅 기록 확인"]
)

# -----------------------
# 6. 일기 작성
# -----------------------

if menu == "✏️ 일기 작성":

    st.header("오늘의 일기")

    diary_date = st.date_input(
        "날짜 선택",
        value=date.today()
    )

    content = st.text_area(
        "오늘 하루는 어땠나요?",
        height=200,
        placeholder="오늘 있었던 일을 자유롭게 작성해 보세요."
    )

    if st.button("일기 저장 및 감정 분석"):

        if content.strip():

            emotion, score, pos, neg = analyze_emotion(content)

            conn.execute(
                """
                INSERT INTO diaries
                (diary_date, content, emotion, score)
                VALUES (?, ?, ?, ?)
                """,
                (
                    str(diary_date),
                    content,
                    emotion,
                    score
                )
            )

            conn.commit()

            st.success("일기가 저장되었습니다!")

            st.subheader("감정 분석 결과")

            st.metric("감정 분류", emotion)
            st.metric("감정 점수", score)

            st.write("긍정 단어:", pos)
            st.write("부정 단어:", neg)

        else:
            st.warning("일기를 먼저 작성해 주세요.")

# -----------------------
# 7. 감정 분석 대시보드
# -----------------------

elif menu == "📊 감정 분석":

    st.header("📊 나의 감정 통계")

    df = pd.read_sql_query(
        "SELECT * FROM diaries ORDER BY diary_date",
        conn
    )

    if not df.empty:

        col1, col2, col3 = st.columns(3)

        col1.metric("총 일기 수", len(df))

        col2.metric(
            "긍정 일기",
            int((df["emotion"] == "긍정").sum())
        )

        col3.metric(
            "부정 일기",
            int((df["emotion"] == "부정").sum())
        )

        st.subheader("감정 변화 그래프")

        fig = px.line(
            df,
            x="diary_date",
            y="score",
            markers=True,
            title="날짜별 감정 점수 변화"
        )

        fig.update_layout(
            xaxis_title="날짜",
            yaxis_title="감정 점수"
        )

        st.plotly_chart(fig, use_container_width=True)

        st.subheader("감정 분포")

        emotion_count = df["emotion"].value_counts()

        fig2 = px.pie(
            values=emotion_count.values,
            names=emotion_count.index,
            title="전체 감정 비율"
        )

        st.plotly_chart(fig2, use_container_width=True)

    else:
        st.info("아직 저장된 일기가 없습니다.")

# -----------------------
# 8. 과거 일기 확인
# -----------------------

elif menu == "📅 기록 확인":

    st.header("📅 지난 일기")

    df = pd.read_sql_query(
        "SELECT * FROM diaries ORDER BY diary_date DESC",
        conn
    )

    if not df.empty:

        for _, row in df.iterrows():

            with st.expander(
                f"{row['diary_date']} | {row['emotion']}"
            ):

                st.write(row["content"])

                st.write(
                    f"감정 점수: {row['score']}"
                )

                if st.button(
                    "이 일기 삭제",
                    key=f"delete_{row['id']}"
                ):

                    conn.execute(
                        "DELETE FROM diaries WHERE id = ?",
                        (int(row["id"]),)
                    )

                    conn.commit()

                    st.rerun()

    else:
        st.info("작성한 일기가 없습니다.")

conn.close()
