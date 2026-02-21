import streamlit as st
import pandas as pd
import random
import time
from streamlit_gsheets import GSheetsConnection
import streamlit.components.v1 as components

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Raga AI Workshop", page_icon="🎶", layout="centered")

SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1qvhy03uzkomxsET6s60mrUC7ouJBOFpb0gosz5ZPzY0"

# --- 2. PREMIUM STYLING ---
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .stProgress > div > div > div > div { background-color: #00d4ff; }
    
    /* Table Visibility Fix */
    .stTable td, .stTable th {
        color: white !important;
        background-color: #1e2130 !important;
    }
    
    .notation-box {
        background-color: #121212; border: 2px solid #00d4ff;
        border-radius: 15px; padding: 20px; text-align: center; margin-top: 15px;
    }
    .swara { color: #00d4ff; font-size: 26px; font-family: monospace; font-weight: bold; }
    
    .visualizer-container {
        display: flex; justify-content: center; gap: 5px; height: 60px; margin: 20px 0;
    }
    .bar {
        width: 8px; background-color: #00d4ff; border-radius: 4px;
        animation: pulse 1s ease-in-out infinite;
    }
    @keyframes pulse { 0%, 100% { height: 10px; opacity: 0.5; } 50% { height: 40px; opacity: 1; } }
</style>
""", unsafe_allow_html=True)

# --- 3. DATA HELPERS ---
@st.cache_data(ttl=3600, show_spinner=False)
def load_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(spreadsheet=SPREADSHEET_URL, worksheet="SongsInfo") 
        return df.to_dict('records')
    except: return []

def save_score(group, score):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # Force fresh read to avoid header conflicts
        df = conn.read(spreadsheet=SPREADSHEET_URL, worksheet="Leaderboard", ttl=0)
        new_row = pd.DataFrame([{"Group": str(group), "Score": int(score)}])
        updated_df = pd.concat([df, new_row], ignore_index=True).fillna("")
        conn.update(spreadsheet=SPREADSHEET_URL, worksheet="Leaderboard", data=updated_df)
        return True
    except: return False

# --- 4. SESSION STATE ---
if 'phase' not in st.session_state:
    st.session_state.update({
        'phase': 'login', 'score': 0, 'lives': 3, 'q_idx': 0,
        'group': "", 'questions': [], 'current_options': [],
        'start_time': None, 'answered': False, 'leaderboard_saved': False, 
        'last_result': ""
    })

# --- PHASE 1: LOGIN ---
if st.session_state.phase == 'login':
    st.title("🎶 Raga AI Challenge")
    with st.form("login_form"):
        group_input = st.text_input("Group Name:", placeholder="Enter Team Name")
        if st.form_submit_button("🚀 START CHALLENGE"):
            if group_input:
                with st.status("🎼 Tuning AI Models...", expanded=False) as s:
                    st.write("Fetching Raga Data...")
                    raw_data = load_data()
                    time.sleep(0.7)
                    if raw_data:
                        st.session_state.update({
                            'questions': random.sample(raw_data, len(raw_data)),
                            'group': group_input, 'phase': 'playing', 'q_idx': 0, 
                            'score': 0, 'lives': 3, 'start_time': time.time()
                        })
                        s.update(label="✅ Ready!", state="complete")
                        time.sleep(0.5)
                        st.rerun()
            else:
                st.warning("Please enter a group name!")

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
        st.write(f"⏳ **{max(0, remaining)}s**")

        # AUDIO ISOLATION ENGINE (IFrame approach to force-kill audio)
        audio_url = current_q['audio_url'].replace('github.com', 'raw.githubusercontent.com').replace('/blob/', '/')
        components.html(f"""
            <style>
                .vc {{ display: flex; justify-content: center; gap: 5px; height: 40px; }}
                .bar {{ width: 8px; background-color: #00d4ff; border-radius: 4px; animation: p 1s infinite; }}
                @keyframes p {{ 0%, 100% {{ height: 10px; }} 50% {{ height: 40px; }} }}
            </style>
            <div class="vc">
                <div class="bar" style="animation-delay:0.1s"></div>
                <div class="bar" style="animation-delay:0.3s"></div>
                <div class="bar" style="animation-delay:0.5s"></div>
            </div>
            <audio autoplay loop><source src="{audio_url}" type="audio/mpeg"></audio>
        """, height=60)

        if not st.session_state.current_options:
            all_r = list(set([q['raga'] for q in st.session_state.questions]))
            opts = random.sample([r for r in all_r if r != current_q['raga']], 3) + [current_q['raga']]
            random.shuffle(opts); st.session_state.current_options = opts

        with st.form("quiz"):
            choice = st.radio("Which Raga is this?", st.session_state.current_options, index=None)
            if st.form_submit_button("SUBMIT"):
                if choice:
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
        else:
            st.error(f"❌ Wrong! It was {current_q['raga']}")
        
        time.sleep(2.5)
        st.session_state.update({'q_idx': st.session_state.q_idx + 1, 'answered': False, 'current_options': [], 'start_time': time.time()})
        st.rerun()

# --- PHASE 3: GAME OVER ---
else:
    st.title("🏆 Challenge Complete!")
    st.balloons()
    st.header(f"Final Score: {st.session_state.score}")
    
    if not st.session_state.leaderboard_saved:
        with st.status("🌟 Syncing with Hall of Fame...", expanded=True) as status:
            if save_score(st.session_state.group, st.session_state.score):
                st.session_state.leaderboard_saved = True
                status.update(label="✅ Score Saved!", state="complete")
            else:
                status.update(label="⚠️ Sync delay - reloading table...", state="complete")

    st.divider()
    st.subheader("🌟 Hall of Fame (Top 10)")
    
    with st.spinner("Fetching Hall of Fame data..."):
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            # ttl=0 is critical here to show the data immediately after saving
            lb_df = conn.read(spreadsheet=SPREADSHEET_URL, worksheet="Leaderboard", ttl=0)
            if lb_df is not None and not lb_df.empty:
                top_10 = lb_df.sort_values(by="Score", ascending=False).head(10).reset_index(drop=True)
                st.table(top_10)
            else:
                st.info("Leaderboard is currently empty.")
        except:
            st.error("Connection lost. Please refresh.")

    if st.button("Play Again"):
        st.session_state.clear(); st.rerun()