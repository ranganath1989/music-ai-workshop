import streamlit as st
import pandas as pd
import random
from streamlit_gsheets import GSheetsConnection

# --- 1. APP CONFIGURATION ---
st.set_page_config(page_title="Raga AI Workshop", page_icon="🎶", layout="centered")

# --- 2. CUSTOM CSS FOR A CLEAN INTERFACE ---
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .notation-box {
        background-color: #121212;
        border: 2px solid #00d4ff;
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        margin: 15px 0;
        box-shadow: 0 0 15px rgba(0, 212, 255, 0.2);
    }
    .swara {
        color: #00d4ff;
        font-size: 26px;
        font-family: 'Courier New', monospace;
        letter-spacing: 6px;
        font-weight: bold;
    }
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3em;
        font-weight: bold;
    }
    /* Larger radio options for mobile tapping */
    div[data-baseweb="radio"] > div {
        padding: 15px;
        border-radius: 10px;
        background-color: #1e1e1e;
        margin-bottom: 8px;
        border: 1px solid #333;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. DATA FETCHING ---
@st.cache_data(ttl=60)
def load_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read()
        return df.to_dict('records')
    except Exception as e:
        st.error(f"Spreadsheet Error: {e}")
        return []

# --- 4. SESSION STATE INITIALIZATION ---
if 'phase' not in st.session_state:
    st.session_state.phase = 'login'
    st.session_state.score = 0
    st.session_state.lives = 3
    st.session_state.q_idx = 0
    st.session_state.group = ""
    st.session_state.questions = []
    st.session_state.hint_active = False
    st.session_state.current_options = []

# --- PHASE 1: LOGIN ---
if st.session_state.phase == 'login':
    st.title("🎶 Raga AI Challenge")
    st.write("Listen to the song and identify the Raga. Good luck!")
    
    with st.form("login_form"):
        group_input = st.text_input("Group Name:", placeholder="Team Name")
        submit = st.form_submit_button("🚀 START GAME")
        
        if submit:
            if group_input:
                raw_data = load_data()
                if raw_data:
                    shuffled = raw_data.copy()
                    random.shuffle(shuffled)
                    st.session_state.questions = shuffled
                    st.session_state.group = group_input
                    st.session_state.phase = 'playing'
                    st.rerun()
                else:
                    st.error("No songs found in the database!")
            else:
                st.warning("Please enter your team name.")

# --- PHASE 2: PLAYING ---
elif st.session_state.phase == 'playing':
    if st.session_state.lives <= 0 or st.session_state.q_idx >= len(st.session_state.questions):
        st.session_state.phase = 'game_over'
        st.rerun()

    current_q = st.session_state.questions[st.session_state.q_idx]
    
    # --- HEADER ---
    st.subheader(f"👥 {st.session_state.group}")
    c1, c2 = st.columns(2)
    c1.metric("Score", st.session_state.score)
    c2.metric("Lives Left", "❤️" * st.session_state.lives)
    st.write(f"Question {st.session_state.q_idx + 1} of {len(st.session_state.questions)}")

    # --- AUTO-PLAY AUDIO ENGINE ---
    if pd.notna(current_q.get('audio_url')):
        # Using a unique key (q_idx) ensures the audio element reloads for every new song
        st.markdown(f"""
            <audio autoplay key="audio_{st.session_state.q_idx}">
                <source src="{current_q['audio_url']}" type="audio/mpeg">
            </audio>
        """, unsafe_allow_html=True)
        st.caption("🔈 Playing song snippet...")

    st.divider()

    # --- HINT LOGIC ---
    if st.button("✨ Need a Hint? Reveal AI Notation"):
        st.session_state.hint_active = True

    if st.session_state.hint_active:
        st.markdown(f"""
        <div class="notation-box">
            <p style="color: gray; font-size: 11px;">AI NOTATION ANALYSIS</p>
            <div class="swara">{current_q['notation']}</div>
            <p style="color: #00d4ff; font-size: 14px; margin-top:10px;">
                💡 {random.choice(str(current_q['clues']).split(';'))}
            </p>
        </div>
        """, unsafe_allow_html=True)

    # --- OPTIONS PERSISTENCE ---
    # We generate options once per question index so they don't reshuffle on every click
    if not st.session_state.current_options or len(st.session_state.current_options) == 0:
        all_ragas = list(set([q['raga'] for q in st.session_state.questions]))
        wrong = [r for r in all_ragas if r != current_q['raga']]
        options = random.sample(wrong, min(3, len(wrong))) + [current_q['raga']]
        random.shuffle(options)
        st.session_state.current_options = options

    # --- SUBMISSION FORM ---
    with st.form("answer_form"):
        choice = st.radio("Which Raga is this song based on?", st.session_state.current_options, index=None)
        submitted = st.form_submit_button("SUBMIT ANSWER")
        
        if submitted:
            if choice:
                if choice == current_q['raga']:
                    st.session_state.score += 10
                    st.toast("Correct!", icon="✅")
                else:
                    st.session_state.lives -= 1
                    st.toast(f"Wrong! It was {current_q['raga']}", icon="❌")
                
                # Prepare for next question
                st.session_state.q_idx += 1
                st.session_state.hint_active = False
                st.session_state.current_options = [] # Clear options for next round
                st.rerun()
            else:
                st.warning("Please select an option before submitting!")

# --- PHASE 3: GAME OVER ---
else:
    st.balloons()
    st.title("🏆 Final Score: " + str(st.session_state.score))
    st.subheader(f"Well played, Team {st.session_state.group}!")
    st.write("Show this screen to the organizers for the final leaderboard.")
    
    if st.button("Play Again"):
        st.session_state.clear()
        st.rerun()