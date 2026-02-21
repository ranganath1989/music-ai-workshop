import streamlit as st
import pandas as pd
import random
import time
from streamlit_gsheets import GSheetsConnection
import streamlit.components.v1 as components

# --- 1. CONFIGURATION & UI HIDER ---
st.set_page_config(page_title="Raga AI Workshop", page_icon="🎶", layout="centered", initial_sidebar_state="collapsed")

hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            header {visibility: hidden;}
            footer {visibility: hidden;}
            #stDecoration {display:none;}
            [data-testid="stStatusWidget"] {visibility: hidden;}
            .stDeployButton {display:none;}
            .viewerBadge_container__1QSob {display:none !important;}
            .viewerBadge_link__3_79W {display:none !important;}
            .main { background-color: #0e1117; }
            .stTable td, .stTable th { color: white !important; background-color: #1e2130 !important; }
            .notation-box { background-color: #121212; border: 2px solid #00d4ff; border-radius: 15px; padding: 20px; text-align: center; }
            .swara { color: #00d4ff; font-size: 26px; font-family: monospace; font-weight: bold; }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1qvhy03uzkomxsET6s60mrUC7ouJBOFpb0gosz5ZPzY0"

# --- 2. DATA HELPERS ---
@st.cache_data(ttl=3600, show_spinner=False)
def load_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        return conn.read(spreadsheet=SPREADSHEET_URL, worksheet="SongsInfo").to_dict('records')
    except: return []

def save_score(group, score):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(spreadsheet=SPREADSHEET_URL, worksheet="Leaderboard", ttl=0)
        new_row = pd.DataFrame([{"Group": str(group), "Score": int(score)}])
        updated_df = pd.concat([df, new_row], ignore_index=True).fillna("")
        conn.update(spreadsheet=SPREADSHEET_URL, worksheet="Leaderboard", data=updated_df)
        return True
    except: return False

# --- 3. SESSION STATE ---
if 'phase' not in st.session_state:
    st.session_state.update({
        'phase': 'login', 'score': 0, 'lives': 3, 'q_idx': 0, 'group': "", 
        'questions': [], 'current_options': [], 'start_time': None, 
        'answered': False, 'leaderboard_saved': False, 'last_result': ""
    })

# --- PHASE 1: LOGIN ---
if st.session_state.phase == 'login':
    st.title("🎶 Raga AI Challenge")
    with st.form("login"):
        group_input = st.text_input("Group Name:", placeholder="Enter Team Name")
        if st.form_submit_button("🚀 START CHALLENGE"):
            if group_input:
                with st.status("🎼 Tuning AI Models...", expanded=True) as status:
                    raw_data = load_data()
                    time.sleep(0.7)
                    if raw_data:
                        st.session_state.update({
                            'questions': random.sample(raw_data, len(raw_data)),
                            'group': group_input, 'phase': 'playing', 'q_idx': 0, 
                            'score': 0, 'lives': 3, 'start_time': time.time()
                        })
                        status.update(label="✅ Ready!", state="complete")
                        time.sleep(0.5)
                        st.rerun()

# --- PHASE 2: PLAYING ---
elif st.session_state.phase == 'playing':
    if st.session_state.lives <= 0 or st.session_state.q_idx >= len(st.session_state.questions):
        st.session_state.phase = 'game_over'; st.rerun()

    current_q = st.session_state.questions[st.session_state.q_idx]

    c1, c2 = st.columns(2)
    c1.metric("Score", st.session_state.score)
    c2.markdown(f"<div style='text-align:right; font-size:24px;'>{'❤️' * st.session_state.lives}</div>", unsafe_allow_html=True)

    if not st.session_state.answered:
        elapsed = time.time() - st.session_state.start_time
        remaining = int(60 - elapsed)
        if remaining <= 0:
            st.session_state.answered = True; st.session_state.lives -= 1; st.session_state.last_result = "timeout"; st.rerun()
        
        st.progress(max(0.0, remaining / 60))
        
        audio_url = current_q['audio_url'].replace('github.com', 'raw.githubusercontent.com').replace('/blob/', '/')
        components.html(f"""
            <style>
                .vc {{ display: flex; justify-content: center; gap: 5px; height: 40px; }}
                .bar {{ width: 8px; background-color: #00d4ff; border-radius: 4px; animation: p 1s infinite; }}
                @keyframes p {{ 0%, 100% {{ height: 10px; }} 50% {{ height: 40px; }} }}
            </style>
            <div class="vc">
                <div class="bar" style="animation-delay:0.1s"></div><div class="bar" style="animation-delay:0.3s"></div><div class="bar" style="animation-delay:0.5s"></div>
            </div>
            <audio autoplay loop id="aud"><source src="{audio_url}" type="audio/mpeg"></audio>
        """, height=60)

        if not st.session_state.current_options:
            all_r = list(set([q['raga'] for q in st.session_state.questions]))
            opts = random.sample([r for r in all_r if r != current_q['raga']], 3) + [current_q['raga']]
            random.shuffle(opts); st.session_state.current_options = opts

        with st.form("quiz"):
            choice = st.radio("Which Raga?", st.session_state.current_options, index=None)
            if st.form_submit_button("SUBMIT"):
                if choice:
                    components.html("""<script>var p = parent.document.getElementById("aud"); if(p){p.pause(); p.src=""; p.remove();}</script>""", height=0)
                    st.session_state.answered = True
                    if choice == current_q['raga']: 
                        st.session_state.score += 10
                        st.session_state.last_result = "correct"
                    else: 
                        st.session_state.lives -= 1
                        st.session_state.last_result = "wrong"
                    st.rerun()

        with st.expander("💡 Hint"):
            st.markdown(f"<div class='notation-box'><div class='swara'>{current_q['notation']}</div></div>", unsafe_allow_html=True)
        time.sleep(1); st.rerun()

    else:
        if st.session_state.last_result == "correct":
            st.balloons(); st.success("✅ Correct!")
        else: st.error(f"❌ It was {current_q['raga']}")
        time.sleep(2.5)
        st.session_state.update({'q_idx': st.session_state.q_idx + 1, 'answered': False, 'current_options': [], 'start_time': time.time()})
        st.rerun()

# --- PHASE 3: GAME OVER ---
else:
    st.title("🏆 Challenge Complete!")
    st.balloons()
    if not st.session_state.leaderboard_saved:
        with st.status("🌟 Syncing Score...", expanded=True):
            save_score(st.session_state.group, st.session_state.score)
            st.session_state.leaderboard_saved = True

    st.subheader("🌟 Hall of Fame (Top 10)")
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        lb_df = conn.read(spreadsheet=SPREADSHEET_URL, worksheet="Leaderboard", ttl=0)
        st.table(lb_df.sort_values(by="Score", ascending=False).head(10).reset_index(drop=True))
    except: st.error("Table sync failed.")

    if st.button("Play Again"):
        st.session_state.clear(); st.rerun()