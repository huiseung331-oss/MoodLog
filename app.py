import re
import calendar
from collections import Counter
from datetime import date, datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import streamlit as st

# =====================================================
# 1. 기본 설정 & 디자인
# =====================================================

st.set_page_config(page_title="MoodLog", page_icon="🌱", layout="wide")

COLORS = {"긍정": "#34C38F", "중립": "#94A3B8", "부정": "#FF6B81"}
EMOJI = {"긍정": "😊", "중립": "😐", "부정": "😢"}
MOOD_FACE = {1: "😭 매우 나쁨", 2: "😟 나쁨", 3: "😐 보통", 4: "🙂 좋음", 5: "😄 매우 좋음"}
TAGS = ["학교", "친구", "가족", "공부", "동아리", "운동", "휴식", "고민", "취미"]
DAY_NAMES = ["월", "화", "수", "목", "금", "토", "일"]
SCALE = [[0, "#FF6B81"], [0.5, "#F1F3F9"], [1, "#34C38F"]]

st.markdown("""
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');

.stApp, .stApp p, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4,
.stApp input, .stApp textarea, .stApp button, .stApp li {
    font-family: 'Pretendard', -apple-system, sans-serif;
}
.stApp {background: #F5F6FB;}
.block-container {padding-top: 2.2rem; max-width: 1080px;}
#MainMenu, footer {visibility: hidden;}

/* ---------- 히어로 ---------- */
.hero {
    position: relative; overflow: hidden;
    background: linear-gradient(120deg, #6C5CE7 0%, #8E7CF3 45%, #4FACFE 100%);
    padding: 34px 38px; border-radius: 26px; color: white; margin-bottom: 26px;
    box-shadow: 0 14px 34px rgba(108, 92, 231, 0.28);
}
.hero::after {
    content: ""; position: absolute; right: -50px; top: -60px;
    width: 230px; height: 230px; border-radius: 50%;
    background: rgba(255,255,255,0.14);
}
.hero::before {
    content: ""; position: absolute; right: 110px; bottom: -90px;
    width: 180px; height: 180px; border-radius: 50%;
    background: rgba(255,255,255,0.10);
}
.hero .hello {font-size: 0.95rem; opacity: 0.85; margin-bottom: 4px;}
.hero h1 {margin: 0; font-size: 2.1rem; font-weight: 800; color: white; padding: 0;}
.hero p {margin: 8px 0 0 0; opacity: 0.92; font-size: 1rem; color: white;}

/* ---------- 카드 ---------- */
.card {
    background: white; border-radius: 20px; padding: 20px 22px;
    box-shadow: 0 4px 18px rgba(30, 41, 59, 0.06);
    border: 1px solid #EEF0F6; margin-bottom: 14px;
    transition: transform .2s ease, box-shadow .2s ease;
}
.card:hover {transform: translateY(-3px); box-shadow: 0 10px 26px rgba(30,41,59,0.10);}
.card .label {color: #94A3B8; font-size: 0.82rem; font-weight: 600; letter-spacing: .02em;}
.card .value {font-size: 1.75rem; font-weight: 800; color: #1E293B; margin-top: 4px;}

.badge {
    display: inline-block; padding: 4px 12px; border-radius: 999px;
    color: white; font-size: 0.78rem; font-weight: 700; margin-right: 6px;
}
.tag {
    display: inline-block; padding: 3px 11px; border-radius: 999px;
    background: #EEEBFF; color: #6C5CE7; font-size: 0.76rem; font-weight: 600; margin-right: 4px;
}
.msg {
    background: linear-gradient(90deg, #F0EDFF, #EAF6FF);
    border-radius: 18px; padding: 18px 22px; font-size: 1.02rem;
    color: #3B3F73; margin: 6px 0 22px 0; border: 1px solid #E3E2FA;
}
.section-title {font-size: 1.15rem; font-weight: 800; color: #1E293B; margin: 22px 0 12px 0;}

/* ---------- 최근 7일 스트립 ---------- */
.week {display: flex; gap: 12px; justify-content: space-between;}
.day {flex: 1; text-align: center;}
.dot {
    width: 54px; height: 54px; border-radius: 18px; margin: 0 auto;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.5rem; color: white;
    box-shadow: 0 4px 12px rgba(30,41,59,0.10);
}
.dot.empty {background: #EEF0F6; color: #CBD5E1; box-shadow: none; font-size: 1rem;}
.dn {margin-top: 8px; font-size: 0.8rem; color: #64748B; font-weight: 600;}
.dn.today {color: #6C5CE7; font-weight: 800;}

/* ---------- 사이드바 ---------- */
section[data-testid="stSidebar"] {background: white; border-right: 1px solid #EEF0F6;}
.brand {font-size: 1.5rem; font-weight: 800; color: #6C5CE7; margin-bottom: 8px;}
section[data-testid="stSidebar"] div[role="radiogroup"] > label {
    padding: 11px 16px; border-radius: 14px; margin-bottom: 6px;
    transition: all .15s ease; width: 100%; cursor: pointer;
}
section[data-testid="stSidebar"] div[role="radiogroup"] > label:hover {background: #F1EFFF;}
section[data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child {display: none;}
section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {
    background: linear-gradient(120deg, #6C5CE7, #8E7CF3);
    box-shadow: 0 6px 16px rgba(108,92,231,0.30);
}
section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) p {
    color: white !important; font-weight: 700;
}

/* ---------- 버튼 ---------- */
.stButton > button, .stDownloadButton > button {
    border-radius: 14px; padding: 0.55rem 1.3rem; font-weight: 700;
    border: 1px solid #E3E2FA; transition: all .15s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover {
    border-color: #6C5CE7; color: #6C5CE7; transform: translateY(-1px);
}
.stButton > button[kind="primary"] {
    background: linear-gradient(120deg, #6C5CE7, #8E7CF3);
    color: white; border: none; box-shadow: 0 6px 16px rgba(108,92,231,0.30);
}
.stButton > button[kind="primary"]:hover {color: white; box-shadow: 0 10px 22px rgba(108,92,231,0.40);}

/* ---------- 입력창 / 탭 / 확장 ---------- */
.stTextArea textarea, .stTextInput input {border-radius: 14px; border: 1px solid #E3E2FA; background: white;}
.stTabs [data-baseweb="tab-list"] {gap: 8px; border-bottom: none;}
.stTabs [data-baseweb="tab"] {
    background: white; border-radius: 12px; padding: 8px 18px;
    border: 1px solid #EEF0F6; font-weight: 600;
}
.stTabs [aria-selected="true"] {background: #6C5CE7 !important; color: white !important; border-color: #6C5CE7;}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {display: none;}
div[data-testid="stExpander"] {
    background: white; border-radius: 18px; border: 1px solid #EEF0F6;
    box-shadow: 0 3px 12px rgba(30,41,59,0.04); overflow: hidden;
}
div[data-testid="stVerticalBlockBorderWrapper"] {border-radius: 20px;}
h2, h3 {font-weight: 800 !important; color: #1E293B;}
</style>
""", unsafe_allow_html=True)


def card(label, value, color="#1E293B"):
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


def style_fig(fig, height=None):
    fig.update_layout(
        template="plotly_white",
        font=dict(family="Pretendard, sans-serif", color="#334155"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=55, b=30, l=10, r=10),
        title_font_size=16,
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#EEF0F6")
    if height:
        fig.update_layout(height=height)
    return fig


def emo_from_score(s):
    return "긍정" if s > 0 else "부정" if s < 0 else "중립"


# =====================================================
# 2. 감정 사전 (어간: 강도) + 부정 표현 처리
# =====================================================

EMOTION_DICT = {
    "긍정": {
        "행복": 2, "즐겁": 2, "신나": 2, "좋": 1, "뿌듯": 2,
        "기쁘": 2, "설레": 2, "감사": 1, "만족": 1, "재밌": 1, "최고": 3,
        "사랑": 2, "웃": 1, "편안": 1, "평화": 1, "성공": 2, "자랑": 1,
        "고마": 1, "상쾌": 1, "든든": 1, "대박": 2,
    },
    "부정": {
        "우울": 2, "슬프": 2, "속상": 2, "외롭": 2, "짜증": 2, "화났": 2,
        "화가": 2, "힘들": 2, "불안": 2, "걱정": 1, "실망": 2, "괴롭": 3,
        "지치": 1, "피곤": 1, "싫": 1, "무서": 2, "답답": 2, "눈물": 2,
        "스트레스": 2, "망했": 3, "최악": 3, "포기": 2, "재미없": 2, "나쁘": 2,
    },
}

# 절(clause)의 경계: 여기서 문장 의미가 바뀐다고 보고 부정 검사를 멈춤
CLAUSE_BREAK = re.compile(r"[.!?,~\n]|지만|는데|은데|인데|그런데|그래서|하지만|그리고|면서")

# 단어 바로 뒤: (활용 어미 0~3글자) + 지/진/지는/지도/지가 + 않/못/안  (예: 좋지 않았다, 행복하지는 않았다)
NEG_AFTER = re.compile(r"^[가-힣]{0,3}?\s*(지는|지도|지가|지|진)\s*(않|못|안|아니)")
# 단어 바로 앞: 안/못  (예: 안 좋았다, 안좋아, 못 웃었다)
NEG_BEFORE = re.compile(r"(?:^|\s)(안|못)\s*$")


def is_negated(text, start, end):
    """단어가 속한 '절' 안에서만 부정 표현이 있는지 검사"""
    after = text[end:end + 12]
    m = CLAUSE_BREAK.search(after)
    if m:
        after = after[:m.start()]
    if NEG_AFTER.search(after):
        return True

    before = CLAUSE_BREAK.split(text[:start])[-1]
    return bool(NEG_BEFORE.search(before))


def analyze_text(text):
    """글에서 감정 점수와 발견된 단어를 계산 (부정 표현이면 방향을 뒤집고 강도는 1 낮춤)"""
    score = 0
    pos_found, neg_found = [], []

    for polarity, words in EMOTION_DICT.items():
        sign = 1 if polarity == "긍정" else -1
        for word, weight in words.items():
            for m in re.finditer(word, text):
                if is_negated(text, m.start(), m.end()):
                    actual_sign = -sign
                    actual_weight = max(1, weight - 1)
                    label = f"{word} (부정 표현)"
                else:
                    actual_sign = sign
                    actual_weight = weight
                    label = word
                score += actual_sign * actual_weight
                (pos_found if actual_sign > 0 else neg_found).append(label)

    return score, pos_found, neg_found


def analyze_emotion(text, mood):
    """글 점수 + 직접 고른 기분 → 종합 점수(-10~10)와 감정 분류"""
    text_score, pos, neg = analyze_text(text)
    text_score = max(-6, min(6, text_score))
    total = max(-10, min(10, text_score + (mood - 3) * 2))
    return emo_from_score(total), total, text_score, pos, neg


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
# 4. 사이드바 & 히어로
# =====================================================

_h = datetime.now().hour
GREETING = "좋은 아침이에요 ☀️" if _h < 12 else "좋은 오후예요 🌤️" if _h < 18 else "좋은 저녁이에요 🌙"

with st.sidebar:
    st.markdown('<div class="brand">🌱 MoodLog</div>', unsafe_allow_html=True)
    menu = st.radio(
        "메뉴",
        ["🏠  홈", "✏️  일기 작성", "📊  감정 분석", "📅  기록 확인"],
        label_visibility="collapsed",
    )
    st.divider()
    _df = load_df()
    st.caption(f"📖 지금까지 쓴 일기 **{len(_df)}개**")
    st.caption(f"🔥 연속 작성 **{calc_streak(_df)}일**")

st.markdown(f"""
<div class="hero">
<div class="hello">{GREETING}</div>
<h1>MoodLog</h1>
<p>나의 하루를 기록하고, 감정의 흐름을 한눈에 살펴보세요.</p>
</div>
""", unsafe_allow_html=True)

# =====================================================
# 5. 홈
# =====================================================

if menu.endswith("홈"):
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
            card("오늘 일기", "✅ 완료" if today_done else "📝 아직")
        with c2:
            card("연속 작성", f"🔥 {calc_streak(df)}일")
        with c3:
            card("총 일기 수", f"📖 {len(df)}개")
        with c4:
            card("최근 7일 평균", f"{avg7:+.1f}점", COLORS[emo_from_score(avg7)])

        if avg7 > 2:
            msg = "요즘 기분 좋은 날이 많네요! 이 에너지를 계속 이어가 봐요 ✨"
        elif avg7 > 0:
            msg = "전반적으로 괜찮은 한 주였어요. 작은 행복을 더 찾아볼까요? 🌼"
        elif avg7 == 0:
            msg = "잔잔한 한 주였네요. 오늘은 어떤 하루였나요? 🍃"
        else:
            msg = "요즘 조금 힘든 일이 있었나 봐요. 기록하는 것만으로도 큰 힘이 돼요 💛"
        st.markdown(f'<div class="msg">{msg}</div>', unsafe_allow_html=True)

        st.markdown('<div class="section-title">🗓️ 최근 7일</div>', unsafe_allow_html=True)
        by_day = df.groupby(df["diary_date"].dt.date)["score"].mean().to_dict()
        strip = '<div class="card"><div class="week">'
        for i in range(6, -1, -1):
            d = date.today() - timedelta(days=i)
            cls = "dn today" if i == 0 else "dn"
            if d in by_day:
                e = emo_from_score(by_day[d])
                dot = f'<div class="dot" style="background:{COLORS[e]}">{EMOJI[e]}</div>'
            else:
                dot = '<div class="dot empty">·</div>'
            strip += f'<div class="day">{dot}<div class="{cls}">{DAY_NAMES[d.weekday()]} {d.day}</div></div>'
        strip += "</div></div>"
        st.markdown(strip, unsafe_allow_html=True)

        st.markdown('<div class="section-title">📖 최근 일기</div>', unsafe_allow_html=True)
        for _, row in df.sort_values("diary_date", ascending=False).head(3).iterrows():
            preview = row["content"][:80] + ("..." if len(row["content"]) > 80 else "")
            st.markdown(
                f'<div class="card"><b>{row["diary_date"].strftime("%Y-%m-%d")}</b> &nbsp;'
                f'{badge(row["emotion"])}{tag_html(row["tags"])}'
                f'<div style="margin-top:10px;color:#64748B">{preview}</div></div>',
                unsafe_allow_html=True,
            )

# =====================================================
# 6. 일기 작성
# =====================================================

elif menu.endswith("일기 작성"):
    st.header("✏️ 오늘의 일기")

    diary_date = st.date_input("날짜 선택", value=date.today(), max_value=date.today())
    existing = get_entry(diary_date)

    if existing:
        st.info("이 날짜에 이미 작성한 일기가 있어요. 저장하면 내용이 **수정**됩니다.")

    default_content = existing[1] if existing else ""
    default_mood = existing[2] if existing and existing[2] else 3
    default_tags = [t for t in (existing[3] or "").split(",") if t in TAGS] if existing else []

    with st.container(border=True):
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
        save_clicked = st.button("💾 저장하고 감정 분석", type="primary")

    if save_clicked:
        if content.strip():
            emotion, total, text_score, pos, neg, updated = save_entry(
                diary_date, content, mood, ",".join(tags)
            )
            st.success("일기가 수정되었어요!" if updated else "일기가 저장되었어요!")

            st.markdown('<div class="section-title">🔍 감정 분석 결과</div>', unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            with c1:
                card("감정 분류", f"{EMOJI[emotion]} {emotion}", COLORS[emotion])
            with c2:
                card("종합 점수 (-10~10)", f"{total:+d}점", COLORS[emotion])
            with c3:
                card("글 분석 / 기분 점수", f"{text_score:+d} / {(mood - 3) * 2:+d}")

            gauge = go.Figure(go.Indicator(
                mode="gauge+number", value=total,
                number={"font": {"size": 44, "color": COLORS[emotion]}},
                gauge={
                    "axis": {"range": [-10, 10]},
                    "bar": {"color": COLORS[emotion], "thickness": 0.35},
                    "borderwidth": 0,
                    "steps": [
                        {"range": [-10, -1], "color": "#FFE8EC"},
                        {"range": [-1, 1], "color": "#F1F3F9"},
                        {"range": [1, 10], "color": "#DFF6EC"},
                    ],
                },
            ))
            style_fig(gauge, 260)
            with st.container(border=True):
                st.plotly_chart(gauge, use_container_width=True)

            w1, w2 = st.columns(2)
            with w1:
                with st.container(border=True):
                    st.markdown("**😊 긍정 신호**")
                    st.write(", ".join(pos) if pos else "발견되지 않았어요")
            with w2:
                with st.container(border=True):
                    st.markdown("**😢 부정 신호**")
                    st.write(", ".join(neg) if neg else "발견되지 않았어요")
        else:
            st.warning("일기를 먼저 작성해 주세요.")

# =====================================================
# 7. 감정 분석
# =====================================================

elif menu.endswith("감정 분석"):
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

            tab1, tab2, tab3, tab4 = st.tabs(
                ["📈 감정 변화", "🥧 분포·요일", "🗓️ 감정 캘린더", "🔤 단어·태그"]
            )

            # ---------- 탭1: 감정 변화 ----------
            with tab1:
                df = df.sort_values("diary_date")
                df["이동평균"] = df["score"].rolling(3, min_periods=1).mean()
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df["diary_date"], y=df["score"], mode="lines+markers", name="감정 점수",
                    line=dict(color="#8E7CF3", width=3, shape="spline"),
                    marker=dict(size=12, color=[COLORS[e] for e in df["emotion"]],
                                line=dict(color="white", width=2)),
                    fill="tozeroy", fillcolor="rgba(142,124,243,0.10)",
                ))
                fig.add_trace(go.Scatter(
                    x=df["diary_date"], y=df["이동평균"], mode="lines", name="3일 이동평균",
                    line=dict(color="#FFA94D", width=3, dash="dot"),
                ))
                fig.add_hline(y=0, line_dash="dash", line_color="#CBD5E1")
                fig.update_layout(
                    title="날짜별 감정 점수 변화", xaxis_title="날짜", yaxis_title="감정 점수",
                    yaxis=dict(range=[-11, 11]), hovermode="x unified",
                    legend=dict(orientation="h", y=1.12, x=1, xanchor="right"),
                )
                style_fig(fig)
                with st.container(border=True):
                    st.plotly_chart(fig, use_container_width=True)

                best = df.loc[df["score"].idxmax()]
                worst = df.loc[df["score"].idxmin()]
                b1, b2 = st.columns(2)
                b1.success(f"🌟 가장 행복했던 날: {best['diary_date'].strftime('%Y-%m-%d')} ({best['score']:+d}점)")
                b2.error(f"🌧️ 가장 힘들었던 날: {worst['diary_date'].strftime('%Y-%m-%d')} ({worst['score']:+d}점)")

            # ---------- 탭2: 분포 / 요일 ----------
            with tab2:
                left, right = st.columns(2)

                cnt = df["emotion"].value_counts()
                fig2 = px.pie(
                    values=cnt.values, names=cnt.index, hole=0.6, title="감정 비율",
                    color=cnt.index, color_discrete_map=COLORS,
                )
                fig2.update_traces(textinfo="percent+label",
                                   marker=dict(line=dict(color="white", width=3)))
                fig2.update_layout(showlegend=False)
                style_fig(fig2, 380)
                with left.container(border=True):
                    st.plotly_chart(fig2, use_container_width=True)

                df["요일"] = df["diary_date"].dt.dayofweek.map(lambda x: DAY_NAMES[x])
                wk = df.groupby("요일")["score"].mean().reindex(DAY_NAMES).reset_index()
                fig3 = px.bar(
                    wk, x="요일", y="score", title="요일별 평균 감정 점수",
                    color="score", color_continuous_scale=SCALE, range_color=[-10, 10],
                )
                fig3.update_layout(yaxis_title="평균 점수", coloraxis_showscale=False)
                style_fig(fig3, 380)
                with right.container(border=True):
                    st.plotly_chart(fig3, use_container_width=True)

            # ---------- 탭3: 감정 캘린더 ----------
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
                    z.append([score_by_day.get(d) if d else None for d in w])
                    text.append([str(d) if d else "" for d in w])

                heat = go.Figure(go.Heatmap(
                    z=z, text=text, texttemplate="%{text}",
                    x=DAY_NAMES,
                    y=[f"{i + 1}주" for i in range(len(weeks))],
                    colorscale=SCALE, zmin=-10, zmax=10, xgap=6, ygap=6,
                    hovertemplate="점수: %{z}<extra></extra>",
                    colorbar=dict(title="점수"),
                ))
                heat.update_yaxes(autorange="reversed")
                heat.update_layout(title=f"{year}년 {month}월 감정 캘린더")
                style_fig(heat, 400)
                with st.container(border=True):
                    st.plotly_chart(heat, use_container_width=True)
                st.caption("초록은 긍정, 빨강은 부정, 빈 칸은 일기가 없는 날이에요.")

            # ---------- 탭4: 단어 / 태그 ----------
            with tab4:
                left, right = st.columns(2)

                stop = {"오늘", "하루", "정말", "너무", "그리고", "그래서", "하지만",
                        "진짜", "그냥", "있었다", "했다"}
                words = []
                for t in df["content"]:
                    words += [w for w in re.findall(r"[가-힣]{2,}", t) if w not in stop]
                common = Counter(words).most_common(10)

                with left.container(border=True):
                    if common:
                        wdf = pd.DataFrame(common, columns=["단어", "횟수"])
                        fig4 = px.bar(wdf, x="횟수", y="단어", orientation="h",
                                      title="자주 쓴 단어 TOP 10",
                                      color_discrete_sequence=["#8E7CF3"])
                        fig4.update_layout(yaxis=dict(autorange="reversed"))
                        style_fig(fig4, 400)
                        st.plotly_chart(fig4, use_container_width=True)
                    else:
                        st.info("분석할 단어가 아직 없어요.")

                rows = []
                for _, r in df.iterrows():
                    for t in r["tags"].split(","):
                        if t:
                            rows.append({"태그": t, "score": r["score"]})

                with right.container(border=True):
                    if rows:
                        tdf = (pd.DataFrame(rows).groupby("태그")["score"]
                               .agg(["mean", "count"]).reset_index())
                        fig5 = px.bar(
                            tdf, x="태그", y="mean", title="태그별 평균 감정 점수",
                            color="mean", color_continuous_scale=SCALE,
                            range_color=[-10, 10], hover_data=["count"],
                        )
                        fig5.update_layout(yaxis_title="평균 점수", coloraxis_showscale=False)
                        style_fig(fig5, 400)
                        st.plotly_chart(fig5, use_container_width=True)
                    else:
                        st.info("일기에 태그를 달면 태그별 감정을 볼 수 있어요.")

# =====================================================
# 8. 기록 확인
# =====================================================

elif menu.endswith("기록 확인"):
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
            view = view[view["content"].str.contains(keyword.strip(), case=False, na=False, regex=False)]
        if tag_filter:
            view = view[view["tags"].apply(lambda s: any(t in s.split(",") for t in tag_filter))]
        view = view.sort_values("diary_date", ascending=False)

        top1, top2 = st.columns([3, 1])
        top1.caption(f"검색 결과: **{len(view)}개**")
        csv = (df.assign(diary_date=df["diary_date"].dt.strftime("%Y-%m-%d"))
                 .to_csv(index=False).encode("utf-8-sig"))
        top2.download_button("⬇️ CSV 백업", csv, "moodlog_backup.csv", "text/csv")

        if view.empty:
            st.warning("조건에 맞는 일기가 없어요.")

        for _, row in view.iterrows():
            date_str = row["diary_date"].strftime("%Y-%m-%d")
            with st.expander(f"{EMOJI[row['emotion']]} {date_str}  |  {row['emotion']}  ({row['score']:+d}점)"):
                st.markdown(badge(row["emotion"]) + tag_html(row["tags"]), unsafe_allow_html=True)
                st.write("")

                new_content = st.text_area("내용", value=row["content"], height=150,
                                           key=f"edit_{row['id']}")
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
