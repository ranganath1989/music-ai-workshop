import streamlit as st
import pandas as pd
import random
from streamlit_gsheets import GSheetsConnection

# --- APP CONFIG ---
st.set_page_config(page_title="Raga AI Workshop", layout="centered")

# --- CUSTOM CSS FOR MUSICAL INTERFACE ---
st.markdown("""
<style>
    .notation-box {
        background-color: #121212;
        border: 2px solid #00d4ff;
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        margin: 10px 0;
    }
    .swara {
        color: #00d4ff;
        font-size: 24px;
        font-family: 'Courier New', monospace;
        letter-spacing: 8px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_input=True)

# --- DATA FETCHING ---
@st.cache_data(ttl=60) # Refreshes from sheet every 1 minute
def load_data():
    # Replace with your actual public Google Sheet URL
    url = "YOUR_PUBLIC_GOOGLE_SHEET_URL_HERE"
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=url)
    return df.to_dict('records')

# --- SESSION INITIALIZATION ---
if 'state' not in st.session_state:
    st.session_state.state = {
        'phase': 'login',
        'group': '',
        'score': 0,
        'lives': 3,
        'q_idx': 0,
        'questions': [],
        'hint_active': False
    }

s = st.session_state.state

# --- PHASE 1: LOGIN ---
if s['phase'] == 'login':
    st.title("🎵 Raga AI Challenge")
    st.write("Welcome to the Music Workshop!")
    
    with st.form("join"):
        group_name = st.text_input("Group Name")
        if st.form_submit_button("Start Challenge"):
            if group_name:
                data = load_data()
                random.shuffle(data)
                s['questions'] = data
                s['group'] = group_name
                s['phase'] = 'playing'
                st.rerun()

# --- PHASE 2: PLAYING ---
elif s['phase'] == 'playing':
    if s['lives'] <= 0 or s['q_idx'] >= len(s['questions']):
        s['phase'] = 'game_over'
        st.rerun()

    current = s['questions'][s['q_idx']]
    
    st.header(f"Team: {s['group']}")
    col1, col2 = st.columns(2)
    col1.metric("Score", s['score'])
    col2.metric("Lives Left", "❤️" * s['lives'])

    st.divider()
    st.info(f"Question {s['q_idx'] + 1}: Listen to the song and identify the Raga.")

    # MUSICAL GRAPHIC CLUE
    if st.button("✨ Activate AI Notation Analysis"):
        s['hint_active'] = True

    if s['hint_active']:
        st.markdown(f"""
        <div class="notation-box">
            <p style="color: gray; font-size: 12px;">AI FREQUENCY PATTERN (AROHANA)</p>
            <div class="swara">{current['notation']}</div>
            <p style="color: #00d4ff; font-size: 14px; margin-top:10px;">Clue: {random.choice(current['clues'].split(';'))}</p>
        </div>
        """, unsafe_allow_input=True)

    # OPTIONS
    all_ragas = list(set([q['raga'] for q in s['questions']]))
    wrong = [r for r in all_ragas if r != current['raga']]
    options = random.sample(wrong, 3) + [current['raga']]
    random.shuffle(options)

    with st.form("ans"):
        choice = st.radio("What is the Raga?", options)
        if st.form_submit_button("Submit Answer"):
            if choice == current['raga']:
                s['score'] += 10
                st.toast("Correct!", icon="✅")
            else:
                s['lives'] -= 1
                st.toast("Wrong Raga!", icon="❌")
            
            s['q_idx'] += 1
            s['hint_active'] = False
            st.rerun()

# --- PHASE 3: GAME OVER ---
else:
    st.balloons()
    st.title("🏆 Challenge Complete!")
    st.subheader(f"{s['group']}, your final score is {s['score']}")
    st.write("Show this screen to the host for the leaderboard!")
    if st.button("Restart"):
        st.session_state.clear()
        st.rerun()