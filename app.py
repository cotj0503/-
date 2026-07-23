import json
import sqlite3
import streamlit as st
from openai import OpenAI

# ---------------------------------------------------------
# 1. 페이지 기본 설정 & DB 초기화
# ---------------------------------------------------------
st.set_page_config(page_title="스마트 영단어장", page_icon="📚", layout="centered")

# SQLite 데이터베이스 연결 및 테이블 생성
conn = sqlite3.connect("my_vocabulary.db", check_same_thread=False)
c = conn.cursor()
c.execute(
    """
    CREATE TABLE IF NOT EXISTS vocab (
        word TEXT PRIMARY KEY,
        meaning TEXT,
        derivatives TEXT,
        example TEXT
    )
"""
)
conn.commit()

# ---------------------------------------------------------
# 2. 사이드바 - API 키 입력받기 (보안 및 편의성)
# ---------------------------------------------------------
st.sidebar.title("⚙️ 설정")
api_key = st.sidebar.text_input(
    "OpenAI API Key를 입력하세요", type="password", help="API 키를 입력해야 검색 기능이 작동합니다."
)

if api_key:
    client = OpenAI(api_key=api_key)
else:
    client = None

# ---------------------------------------------------------
# 3. 메인 화면 - 단어 검색 및 추가
# ---------------------------------------------------------
st.title("📚 나만의 스마트 영단어장")
st.write("단어를 검색하면 뜻, 파생어, 예문을 자동으로 분석해 줍니다.")

search_word = st.text_input("검색할 영어 단어를 입력하세요:", "").strip()

if st.button("🔍 단어 검색하기", use_container_width=True):
    if not api_key:
        st.error("사이드바에 OpenAI API Key를 먼저 입력해 주세요!")
    elif not search_word:
        st.warning("단어를 입력해 주세요.")
    else:
        with st.spinner("AI가 단어 정보를 분석 중입니다..."):
            try:
                # ChatGPT에게 JSON 형식으로 데이터 요청
                prompt = f"""
                영어 단어 '{search_word}'에 대해 다음 정보를 한국어로 응답해줘.
                 반드시 JSON 형식으로만 답해줘.
                
                {{
                    "meaning": "주요 뜻 (품사 표기 포함, 예: [명] 사과)",
                    "derivatives": "주요 파생어 및 연관 단어 (예: act (동) -> action (명), active (형))",
                    "example": "영어 예문 1~2개와 한글 번역"
                }}
                """

                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                )

                result = json.loads(response.choices[0].message.content)

                # 검색 결과 세션 상태에 저장 (버튼 눌러도 안 사라지게)
                st.session_state["search_result"] = {
                    "word": search_word.lower(),
                    "meaning": result.get("meaning", ""),
                    "derivatives": result.get("derivatives", ""),
                    "example": result.get("example", ""),
                }

            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")

# 검색 결과 표시 카드
if "search_result" in st.session_state:
    res = st.session_state["search_result"]

    st.markdown("---")
    st.subheader(f"🔤 {res['word']}")
    st.markdown(f"**뜻:** {res['meaning']}")
    st.markdown(f"**파생어:** {res['derivatives']}")
    st.markdown(f"**예문:**\n{res['example']}")

    # 단어장에 저장 버튼
    if st.button("➕ 내 단어장에 추가하기", type="primary"):
        c.execute(
            "INSERT OR REPLACE INTO vocab VALUES (?, ?, ?, ?)",
            (res["word"], res["meaning"], res["derivatives"], res["example"]),
        )
        conn.commit()
        st.success(f"'{res['word']}' 단어가 내 단어장에 저장되었습니다!")
        # 저장 후 검색 결과 초기화
        del st.session_state["search_result"]
        st.rerun()

# ---------------------------------------------------------
# 4. 내 단어장 목록 조회 및 삭제
# ---------------------------------------------------------
st.markdown("---")
st.header("📖 내 저장 단어장")

# 저장된 단어 가져오기
c.execute("SELECT * FROM vocab")
saved_words = c.fetchall()

if saved_words:
    # 단어장 내 검색기능
    filter_keyword = st.text_input(
        "🔎 저장된 단어장 내 검색:", "", key="vocab_search"
    )

    for word, meaning, derivatives, example in saved_words:
        if filter_keyword.lower() in word.lower() or filter_keyword in meaning:
            with st.expander(f"📌 **{word}** : {meaning}"):
                st.write(f"**파생어:** {derivatives}")
                st.write(f"**예문:**\n{example}")

                # 삭제 버튼
                if st.button(f"🗑️ 삭제 ({word})", key=f"del_{word}"):
                    c.execute("DELETE FROM vocab WHERE word = ?", (word,))
                    conn.commit()
                    st.toast(f"'{word}' 단어가 삭제되었습니다.")
                    st.rerun()
else:
    st.info("아직 저장된 단어가 없습니다. 위에서 단어를 검색하여 추가해 보세요!")
