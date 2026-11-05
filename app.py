import re
import calendar
from collections import Counter
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import streamlit as st

# =====================================================
# 1. 기본 설정 & 디자인
# =====================================================

st.set_page_config(page_title="MoodLog", page_icon="🌱", layout="wide")

COLORS = {"긍정": "#4CAF86", "중립": "#9AA5B1", "부정": "#EF6F6C"}
EMOJI = {"긍정": "😊", "중립": "😐", "부정": "😢"}
MOOD_FACE = {1: "😭 매우 나쁨", 2: "😟 나쁨", 3: "😐 보통", 4: "🙂 좋음", 5: "😄 매우 좋음"}
TAGS = ["학교", "친구", "가족", "공부", "동아리", "운동", "휴식", "고민", "취미"]

st.markdown("""
<style>
.block-container {padding-top: 2rem; max-width: 1100px;}
.hero {
    background: linear-gradient(135deg, #4CAF86 0%, #6C9BEF 100%);
    padding: 28px 32px; border-radius: 20px; color: white; margin-bottom: 24px;
}
.hero h1 {margin: 0; font-size: 2.2rem;}
.hero p {margin: 6px 0 0 0; opacity: 0.92;}
.card {
    background: white; border-radius: 16px; padding: 20px 22px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.07); border: 1px solid #eef1f4;
    margin-bottom: 14px;
}
.card .label {color: #7b8794; font-size: 0.85rem;}
.card .value {font-size: 1.9rem; font-weight: 700; color: #1f2933;}
.badge {
    display: inline-block; padding: 3px 12px; border-radius: 999px;
    color: white; font-size: 0.8rem; font-weight: 600; margin-right: 6px;
}
.tag {
    display: inline-block; padding: 2px 10px; border-radius: 999px;
    background: #eef2ff; color: #4c5fd5; font-size: 0.78rem; margin-right: 4px;
}
.msg {
    background: #f0faf5; border-left: 5px solid #4CAF86;
    padding: 16px 20px; border-radius: 10px; font-size: 1.02rem;
}
section[data-testid="stSidebar"] {background: #f7faf9;}
</style>
""", unsafe_allow_html=True)


def card(label, value, color="#1f2933"):
    st.markdown(
        f'<div class="card"><div class="label">{label}</div>'
        f'<div class="value" style="color:{color}">{value}</div></div>',
        unsafe_allow_html=True,
    )


def badge(emotion):
    return f'<span class="badge" style="background:{COLORS[emotion]}">{EMOJI[emotion]} {emotion}</span>'


def tag_html(tags):
    if not tags:
        return ""
    return "".join(f'<span class="tag">#{t}</span>' for t in tags.split(",") if t)


# =====================================================
# 2. 감정 사전 (단어: 강도)
# =====================================================

EMOTION_DICT = {
    "긍정": {
        "행복": 2, "즐겁": 2, "신나": 2, "좋았": 1, "좋아": 1, "뿌듯": 2,
        "기쁘": 2, "설레": 2, "감사": 1, "만족": 1, "재밌": 1, "최고": 3,
        "사랑": 2, "웃": 1, "편안": 1, "평화": 1, "성공": 2, "자랑": 1,
        "고마": 1, "상쾌": 1, "든든": 1, "대박": 2,
    },
    "부정": {
        "우울": 2, "슬프": 2, "속상": 2, "외롭": 2, "짜증": 2, "화났": 2,
        "화가": 2, "힘들": 2, "불안": 2, "걱정": 1, "실망": 2, "괴롭": 3,
        "지치": 1, "피곤": 1, "싫": 1, "무서": 2, "답답": 2, "눈물": 2,
        "스트레스": 2, "망했": 3, "최악": 3, "포기": 2,
    },
}

NEGATION_AFTER = ["지 않", "지않", "않았", "않아", "않은", "없었", "없어", "아니"]
NEGATION_BEFORE = ["안 ", "못 "]


def is_negated(text, idx, word):
    after = text[idx + len(word): idx + len(word) + 8]
    before = text[max(0, idx - 3): idx]
    return any(n in after for n in NEGATION_AFTER) or any(n in before for n in NEGATION_BEFORE)


def analyze_text(text):
    """글에서 감정 점수와 발견된 단어를 계산 (부정 표현이면 반대로 반영)"""
    score = 0
    pos_found, neg_found = [], []

    for polarity, words in EMOTION_DICT.items():
        sign = 1 if polarity == "긍정" else -1
        for word, weight in words.items():
            for m in re.finditer(word, text):
                negated = is_negated(text, m.start(), word)
                actual_sign = -sign if negated else sign
                score += actual_sign * weight
                label = f"안 {word}" if negated else word
                (pos_found if actual_sign > 0 else neg_found).append(label)

    return score, pos_found, neg_found


def analyze_emotion(text, mood):
    """글 점수 + 직접 고른 기분 → 종합 점수(-10~10)와 감정 분류"""
    text_score, pos, neg = analyze_text(text)
    text_score = max(-6, min(6, text_score))
    total = max(-10, min(10, text_score + (mood - 3) * 2))

    if total > 0:
        emotion = "긍정"
    elif total < 0:
        emotion = "부정"
    else:
        emotion = "중립"
    return emotion, total, text_score, pos, neg


# =====================================================
# 3. 데이터베이스
# =====================================================

@st.cache_resource
def get_conn():
    conn = sqlite3.connect("moodlog.db", check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS diaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            diary_date TEXT,
            content TEXT,
            emotion TEXT,
            score INTEGER
        )
    """)
    # 기존 DB와 호환되도록 새 컬럼 추가
    cols = [r[1] for r in conn.execute("PRAGMA table_info(diaries)").fetchall()]
    if "mood" not in cols:
        conn.execute("ALTER TABLE diaries ADD COLUMN mood INTEGER DEFAULT 3")
    if "tags" not in cols:
        conn.execute("ALTER TABLE diaries ADD COLUMN tags TEXT DEFAULT ''")
    conn.commit()
    return conn


conn = get_conn()


def load_df():
    df = pd.read_sql_query("SELECT * FROM diaries ORDER BY diary_date", conn)
    if not df.empty:
        df["diary_date"] = pd.to_datetime(df["diary_date"])
        df["tags"] = df["tags"].fillna("")
        df["mood"] = df["mood"].fillna(3).astype(int)
    return df


def get_entry(d):
    return conn.execute(
        "SELECT id, content, mood, tags FROM diaries WHERE diary_date = ? ORDER BY id DESC LIMIT 1",
        (str(d),),
    ).fetchone()


def save_entry(d, content, mood, tags):
    emotion, total, text_score, pos, neg = analyze_emotion(content, mood)
    existing = get_entry(d)
    if existing:
        conn.execute(
            "UPDATE diaries SET content=?, emotion=?, score=?, mood=?, tags=? WHERE id=?",
            (content, emotion, total, mood, tags, existing[0]),
        )
    else:
        conn.execute(
            "INSERT INTO diaries (diary_date, content, emotion, score, mood, tags) VALUES (?,?,?,?,?,?)",
            (str(d), content, emotion, total, mood, tags),
        )
    conn.commit()
    return emotion, total, text_score, pos, neg, bool(existing)


def calc_streak(df):
    if df.empty:
        return 0
    days = set(df["diary_date"].dt.date)
    cur = date.today()
    if cur not in days:
        cur -= timedelta(days=1)
    streak = 0
    while cur in days:
        streak += 1
        cur -= timedelta(days=1)
    return streak


# =====================================================
# 4. 사이드바 메뉴
# =====================================================

st.markdown("""
<div class="hero">
    <h1>🌱 MoodLog</h1>
    <p>나의 하루를 기록하고, 감정의 흐름을 한눈에 살펴보세요.</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## 🌱 MoodLog")
    menu = st.radio(
        "메뉴",
        ["🏠 홈", "✏️ 일기 작성", "📊 감정 분석", "📅 기록 확인"],
        label_visibility="collapsed",
    )
    st.divider()
    _df = load_df()
    st.caption(f"📖 지금까지 쓴 일기: **{len(_df)}개**")
    st.caption(f"🔥 연속 작성: **{calc_streak(_df)}일**")

# =====================================================
# 5. 홈
# =====================================================

if menu == "🏠 홈":
    df = load_df()
    today_done = (not df.empty) and (date.today() in set(df["diary_date"].dt.date))

    if df.empty:
        st.markdown('<div class="msg">👋 첫 일기를 써볼까요? 왼쪽 메뉴에서 <b>일기 작성</b>을 눌러 시작해 보세요!</div>',
                    unsafe_allow_html=True)
    else:
        recent = df[df["diary_date"] >= pd.Timestamp(date.today() - timedelta(days=6))]
        avg7 = recent["score"].mean() if not recent.empty else 0

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            card("오늘 일기", "✅ 작성 완료" if today_done else "❌ 아직이에요")
        with c2:
            card("연속 작성", f"🔥 {calc_streak(df)}일")
        with c3:
            card("총 일기 수", f"📖 {len(df)}개")
        with c4:
            color = COLORS["긍정"] if avg7 > 0 else COLORS["부정"] if avg7 < 0 else COLORS["중립"]
            card("최근 7일 평균", f"{avg7:+.1f}점", color)

        if avg7 > 2:
            msg = "요즘 기분 좋은 날이 많네요! 이 에너지를 계속 이어가 봐요 ✨"
        elif avg7 > 0:
            msg = "전반적으로 괜찮은 한 주였어요. 작은 행복을 더 찾아볼까요? 🌼"
        elif avg7 == 0:
            msg = "잔잔한 한 주였네요. 오늘은 어떤 하루였나요? 🍃"
        else:
            msg = "요즘 조금 힘든 일이 있었나 봐요. 기록하는 것만으로도 큰 힘이 돼요 💛"
        st.markdown(f'<div class="msg">{msg}</div>', unsafe_allow_html=True)

        st.subheader("최근 일기")
        for _, row in df.sort_values("diary_date", ascending=False).head(3).iterrows():
            preview = row["content"][:80] + ("..." if len(row["content"]) > 80 else "")
            st.markdown(
                f'<div class="card"><b>{row["diary_date"].strftime("%Y-%m-%d")}</b> '
                f'{badge(row["emotion"])} {tag_html(row["tags"])}'
                f'<div style="margin-top:8px;color:#52606d">{preview}</div></div>',
                unsafe_allow_html=True,
            )

# =====================================================
# 6. 일기 작성
# =====================================================

elif menu == "✏️ 일기 작성":
    st.header("✏️ 오늘의 일기")

    diary_date = st.date_input("날짜 선택", value=date.today(), max_value=date.today())
    existing = get_entry(diary_date)

    if existing:
        st.info("이 날짜에 이미 작성한 일기가 있어요. 저장하면 내용이 **수정**됩니다.")

    default_content = existing[1] if existing else ""
    default_mood = existing[2] if existing and existing[2] else 3
    default_tags = [t for t in (existing[3] or "").split(",") if t in TAGS] if existing else []

    mood = st.select_slider(
        "오늘의 기분은?", options=[1, 2, 3, 4, 5], value=default_mood,
        format_func=lambda x: MOOD_FACE[x], key=f"mood_{diary_date}",
    )
    tags = st.multiselect("오늘의 키워드 (태그)", TAGS, default=default_tags, key=f"tags_{diary_date}")
    content = st.text_area(
        "오늘 하루는 어땠나요?", value=default_content, height=220,
        placeholder="오늘 있었던 일, 느낀 감정을 자유롭게 적어 보세요.",
        key=f"content_{diary_date}",
    )
    st.caption(f"글자 수: {len(content)}자")

    if st.button("💾 저장하고 감정 분석", type="primary"):
        if content.strip():
            emotion, total, text_score, pos, neg, updated = save_entry(
                diary_date, content, mood, ",".join(tags)
            )
            st.success("일기가 수정되었어요!" if updated else "일기가 저장되었어요!")

            st.subheader("🔍 감정 분석 결과")
            c1, c2, c3 = st.columns(3)
            with c1:
                card("감정 분류", f"{EMOJI[emotion]} {emotion}", COLORS[emotion])
            with c2:
                card("종합 점수 (-10~10)", f"{total:+d}점", COLORS[emotion])
            with c3:
                card("글 분석 / 기분 점수", f"{text_score:+d} / {(mood - 3) * 2:+d}")

            gauge = go.Figure(go.Indicator(
                mode="gauge+number", value=total,
                gauge={
                    "axis": {"range": [-10, 10]},
                    "bar": {"color": COLORS[emotion]},
                    "steps": [
                        {"range": [-10, -1], "color": "#fdeaea"},
                        {"range": [-1, 1], "color": "#f1f3f5"},
                        {"range": [1, 10], "color": "#e6f6ee"},
                    ],
                },
            ))
            gauge.update_layout(height=250, margin=dict(t=30, b=10, l=30, r=30))
            st.plotly_chart(gauge, use_container_width=True)

            w1, w2 = st.columns(2)
            w1.markdown("**😊 긍정 단어**")
            w1.write(", ".join(pos) if pos else "발견되지 않았어요")
            w2.markdown("**😢 부정 단어**")
            w2.write(", ".join(neg) if neg else "발견되지 않았어요")
        else:
            st.warning("일기를 먼저 작성해 주세요.")

# =====================================================
# 7. 감정 분석
# =====================================================

elif menu == "📊 감정 분석":
    st.header("📊 나의 감정 분석")
    df_all = load_df()

    if df_all.empty:
        st.info("아직 저장된 일기가 없습니다.")
    else:
        period = st.radio("기간", ["최근 7일", "최근 30일", "최근 90일", "전체", "직접 선택"], horizontal=True)
        today = date.today()
        if period == "최근 7일":
            start, end = today - timedelta(days=6), today
        elif period == "최근 30일":
            start, end = today - timedelta(days=29), today
        elif period == "최근 90일":
            start, end = today - timedelta(days=89), today
        elif period == "전체":
            start, end = df_all["diary_date"].min().date(), today
        else:
            r = st.date_input("기간 선택", value=(today - timedelta(days=14), today))
            if isinstance(r, tuple) and len(r) == 2:
                start, end = r
            else:
                start, end = today - timedelta(days=14), today

        df = df_all[(df_all["diary_date"] >= pd.Timestamp(start)) &
                    (df_all["diary_date"] <= pd.Timestamp(end))].copy()

        if df.empty:
            st.warning("선택한 기간에 일기가 없습니다.")
        else:
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                card("일기 수", f"{len(df)}개")
            with c2:
                card("😊 긍정", f"{(df['emotion'] == '긍정').sum()}개", COLORS["긍정"])
            with c3:
                card("😐 중립", f"{(df['emotion'] == '중립').sum()}개", COLORS["중립"])
            with c4:
                card("😢 부정", f"{(df['emotion'] == '부정').sum()}개", COLORS["부정"])

            tab1, tab2, tab3, tab4 = st.tabs(["📈 감정 변화", "🥧 분포·요일", "🗓️ 감정 캘린더", "🔤 단어·태그"])

            # --- 감정 변화
            with tab1:
                df = df.sort_values("diary_date")
                df["이동평균"] = df["score"].rolling(3, min_periods=1).mean()
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df["diary_date"], y=df["score"], mode="lines+markers", name="감정 점수",
                    line=dict(color="#6C9BEF", width=2),
                    marker=dict(size=10, color=[COLORS[e] for e in df["emotion"]]),
                ))
                fig.add_trace(go.Scatter(
                    x=df["diary_date"], y=df["이동평균"], mode="lines", name="3일 이동평균",
                    line=dict(color="#f5a623", width=3, dash="dot"),
                ))
                fig.add_hline(y=0, line_dash="dash", line_color="#cbd2d9")
                fig.update_layout(
                    title="날짜별 감정 점수 변화", xaxis_title="날짜", yaxis_title="감정 점수",
                    yaxis=dict(range=[-11, 11]), template="plotly_white", hovermode="x unified",
                )
                st.plotly_chart(fig, use_container_width=True)

                best = df.loc[df["score"].idxmax()]
                worst = df.loc[df["score"].idxmin()]
                b1, b2 = st.columns(2)
                b1.success(f"🌟 가장 행복했던 날: {best['diary_date'].strftime('%Y-%m-%d')} ({best['score']:+d}점)")
                b2.error(f"🌧️ 가장 힘들었던 날: {worst['diary_date'].strftime('%Y-%m-%d')} ({worst['score']:+d}점)")

            # --- 분포 / 요일
            with tab2:
                left, right = st.columns(2)
                cnt = df["emotion"].value_counts()
                fig2 = px.pie(
                    values=cnt.values, names=cnt.index, hole=0.5, title="감정 비율",
                    color=cnt.index, color_discrete_map=COLORS,
                )
                left.plotly_chart(fig2, use_container_width=True)

                names = ["월", "화", "수", "목", "금", "토", "일"]
                df["요일"] = df["diary_date"].dt.dayofweek.map(lambda x: names[x])
                wk = df.groupby("요일")["score"].mean().reindex(names).reset_index()
                fig3 = px.bar(wk, x="요일", y="score", title="요일별 평균 감정 점수",
                              color="score", color_continuous_scale="RdYlGn",
                              range_color=[-10, 10])
                fig3.update_layout(template="plotly_white", yaxis_title="평균 점수")
                right.plotly_chart(fig3, use_container_width=True)

            # --- 캘린더
            with tab3:
                cc1, cc2 = st.columns(2)
                year = cc1.selectbox("연도", list(range(today.year - 2, today.year + 1)), index=2)
                month = cc2.selectbox("월", list(range(1, 13)), index=today.month - 1)

                month_df = df_all[(df_all["diary_date"].dt.year == year) &
                                  (df_all["diary_date"].dt.month == month)]
                score_by_day = month_df.groupby(month_df["diary_date"].dt.day)["score"].mean().to_dict()

                weeks = calendar.Calendar(firstweekday=0).monthdayscalendar(year, month)
                z, text = [], []
                for w in weeks:
                    z.append([score_by_day.get(d) if d and d in score_by_day else None for d in w])
                    text.append([str(d) if d else "" for d in w])

                heat = go.Figure(go.Heatmap(
                    z=z, text=text, texttemplate="%{text}",
                    x=["월", "화", "수", "목", "금", "토", "일"],
                    y=[f"{i + 1}주" for i in range(len(weeks))],
                    colorscale="RdYlGn", zmin=-10, zmax=10, xgap=4, ygap=4,
                    hovertemplate="점수: %{z}<extra></extra>",
                    colorbar=dict(title="점수"),
                ))
                heat.update_yaxes(autorange="reversed")
                heat.update_layout(title=f"{year}년 {month}월 감정 캘린더",
                                   template="plotly_white", height=380)
                st.plotly_chart(heat, use_container_width=True)
                st.caption("초록은 긍정, 빨강은 부정, 회색은 일기가 없는 날이에요.")

            # --- 단어 / 태그
            with tab4:
                left, right = st.columns(2)

                stop = {"오늘", "하루", "정말", "너무", "그리고", "그래서", "하지만", "진짜", "그냥", "있었다", "했다"}
                words = []
                for t in df["content"]:
                    words += [w for w in re.findall(r"[가-힣]{2,}", t) if w not in stop]
                common = Counter(words).most_common(10)
                if common:
                    wdf = pd.DataFrame(common, columns=["단어", "횟수"])
                    fig4 = px.bar(wdf, x="횟수", y="단어", orientation="h", title="자주 쓴 단어 TOP 10",
                                  color_discrete_sequence=["#6C9BEF"])
                    fig4.update_layout(template="plotly_white", yaxis=dict(autorange="reversed"))
                    left.plotly_chart(fig4, use_container_width=True)

                rows = []
                for _, r in df.iterrows():
                    for t in r["tags"].split(","):
                        if t:
                            rows.append({"태그": t, "score": r["score"]})
                if rows:
                    tdf = pd.DataFrame(rows).groupby("태그")["score"].agg(["mean", "count"]).reset_index()
                    fig5 = px.bar(tdf, x="태그", y="mean", title="태그별 평균 감정 점수",
                                  color="mean", color_continuous_scale="RdYlGn",
                                  range_color=[-10, 10], hover_data=["count"])
                    fig5.update_layout(template="plotly_white", yaxis_title="평균 점수")
                    right.plotly_chart(fig5, use_container_width=True)
                else:
                    right.info("태그를 사용하면 태그별 감정을 볼 수 있어요.")

# =====================================================
# 8. 기록 확인
# =====================================================

elif menu == "📅 기록 확인":
    st.header("📅 지난 일기")
    df = load_df()

    if df.empty:
        st.info("작성한 일기가 없습니다.")
    else:
        f1, f2, f3 = st.columns([2, 1, 1])
        keyword = f1.text_input("🔍 검색", placeholder="일기 내용에서 검색")
        emo_filter = f2.multiselect("감정", ["긍정", "중립", "부정"], default=["긍정", "중립", "부정"])
        tag_filter = f3.multiselect("태그", TAGS)

        view = df[df["emotion"].isin(emo_filter)]
        if keyword.strip():
            view = view[view["content"].str.contains(keyword.strip(), case=False, na=False)]
        if tag_filter:
            view = view[view["tags"].apply(lambda s: any(t in s.split(",") for t in tag_filter))]
        view = view.sort_values("diary_date", ascending=False)

        top1, top2 = st.columns([3, 1])
        top1.caption(f"검색 결과: **{len(view)}개**")
        csv = df.assign(diary_date=df["diary_date"].dt.strftime("%Y-%m-%d")).to_csv(index=False).encode("utf-8-sig")
        top2.download_button("⬇️ CSV 백업", csv, "moodlog_backup.csv", "text/csv")

        if view.empty:
            st.warning("조건에 맞는 일기가 없어요.")

        for _, row in view.iterrows():
            date_str = row["diary_date"].strftime("%Y-%m-%d")
            with st.expander(f"{EMOJI[row['emotion']]} {date_str}  |  {row['emotion']}  ({row['score']:+d}점)"):
                st.markdown(badge(row["emotion"]) + tag_html(row["tags"]), unsafe_allow_html=True)
                st.write("")

                new_content = st.text_area("내용", value=row["content"], height=150, key=f"edit_{row['id']}")
                new_mood = st.select_slider(
                    "기분", options=[1, 2, 3, 4, 5], value=int(row["mood"]),
                    format_func=lambda x: MOOD_FACE[x], key=f"mood_edit_{row['id']}",
                )

                b1, b2, _ = st.columns([1, 1, 3])
                if b1.button("✏️ 수정 저장", key=f"update_{row['id']}"):
                    if new_content.strip():
                        emotion, total, *_ = analyze_emotion(new_content, new_mood)
                        conn.execute(
                            "UPDATE diaries SET content=?, emotion=?, score=?, mood=? WHERE id=?",
                            (new_content, emotion, total, new_mood, int(row["id"])),
                        )
                        conn.commit()
                        st.rerun()
                    else:
                        st.warning("내용이 비어 있어요.")

                confirm = b2.checkbox("삭제 확인", key=f"confirm_{row['id']}")
                if confirm and st.button("🗑️ 삭제", key=f"delete_{row['id']}"):
                    conn.execute("DELETE FROM diaries WHERE id = ?", (int(row["id"]),))
                    conn.commit()
                    st.rerun()
