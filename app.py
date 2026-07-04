import time
import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import requests
import json
from squads import SQUADS
from fixtures import get_active_fixtures

st.set_page_config(page_title="World Cup Predictor", layout="wide")
ist = pytz.timezone('Asia/Kolkata')
current_time = datetime.now(ist)

WEBAPP_URL = "https://script.google.com/macros/s/AKfycbxnGXFa4VpEJFmIwcuOACjo32uKRb67DAU4luczLqgnkV-wplBnG1IxdK64TdnqCc6Z/exec"
SHEET_ID = "1rzyPqXioFz2wj_Aby9kuFBafX0wsADvbM-QQTAeGJv8"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Predictions"

try:
    df_existing = pd.read_csv(CSV_URL)
    df_existing.columns = ["Timestamp", "User", "Match", "Team1_Score", "Team2_Score", "Pen_Winner", "MOTM", "Scorers", "Points"]
except Exception:
    df_existing = pd.DataFrame(columns=["Timestamp", "User", "Match", "Team1_Score", "Team2_Score", "Pen_Winner", "MOTM", "Scorers", "Points"])

FIXTURES = get_active_fixtures(df_existing)

st.title("World Cup Predictor")
st.sidebar.header("User Profile")
username = st.sidebar.text_input("Enter your name:").strip()

if not username:
    st.info("Enter your name in the sidebar to continue.")
    st.stop()
if username == "ADMIN_RESULT":
    st.error("Reserved username.")
    st.stop()

tab1, tab2, tab3 = st.tabs(["Prediction", "Leaderboards", "Admin Panel"])

# --- TAB 1: USER PREDICTIONS ---
with tab1:
    open_fixtures = [f for f in FIXTURES if current_time < f["kickoff"]]
    
    if not open_fixtures:
        st.success("No open matches available for prediction right now.")
    else:
        match_options = [f["match"] for f in open_fixtures]
        selected_match_str = st.selectbox("Select Match to Predict", match_options)
        
        active_fixture = next(f for f in open_fixtures if f["match"] == selected_match_str)
        
        time_left = active_fixture['kickoff'] - current_time
        st.write(f"**Kickoff in:** {time_left.days}d {time_left.seconds // 3600}h {(time_left.seconds // 60) % 60}m")
        
        has_predicted = False
        if not df_existing.empty:
            has_predicted = not df_existing[(df_existing['User'].str.lower() == username.lower()) & 
                                            (df_existing['Match'].str.strip().lower() == active_fixture['match'].strip().lower())].empty

        if has_predicted:
            st.success("You have already submitted a prediction for this match.")
        else:
            team1, team2 = active_fixture['match'].split(" vs ")
            pool_choices = sorted(SQUADS.get(team1, ["Player A"]) + SQUADS.get(team2, ["Player B"]))
            
            with st.form("prediction_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                t1_score = col1.number_input(f"{team1} Score", min_value=0, max_value=25, step=1, value=0)
                t2_score = col2.number_input(f"{team2} Score", min_value=0, max_value=25, step=1, value=0)
                
                pen_winner = st.selectbox("Penalty Winner (if draw)", ["None", team1, team2])
                motm = st.selectbox("MOTM", pool_choices)
                scorers_list = st.multiselect("Scorers", pool_choices)
                
                if st.form_submit_button("Submit Prediction"):
                    if t1_score == t2_score and pen_winner == "None":
                        st.error("Error: Draws require a penalty shootout winner.")
                    elif t1_score != t2_score and pen_winner != "None":
                        st.error("Error: Penalty winner selected but the score is not a draw.")
                    else:
                        payload = {
                            "user": username,
                            "match": active_fixture['match'],
                            "t1_score": int(t1_score),
                            "t2_score": int(t2_score),
                            "pen_winner": pen_winner,
                            "motm": motm,
                            "scorers": ", ".join(scorers_list) if scorers_list else "None"
                        }
                        try:
                            res = requests.post(WEBAPP_URL, data=json.dumps(payload))
                            
                            # This forces Python to crash and show an error if your Google URL is wrong
                            res.raise_for_status() 
                            
                            st.success("Prediction successfully locked into the database! Refreshing...")
                            
                            # Pauses the app for 1.5 seconds so you can read the message
                            time.sleep(1.5) 
                            st.rerun()
                            
                        except requests.exceptions.RequestException as e:
                            st.error("Network error: Your prediction didn't go through.")
                            st.info("Did you replace 'YOUR_DEPLOYMENT_ID' in the WEBAPP_URL on line 14?")
                            st.write(f"Technical details: {e}")

# --- TAB 2: LIVE LEADERBOARDS & USER PICKS ---
with tab2:
    st.header("Leaderboard")
    public_leaderboard = df_existing[df_existing['User'] != 'ADMIN_RESULT']
    
    if not public_leaderboard.empty and "Points" in public_leaderboard.columns:
        leaderboard = public_leaderboard.groupby('User')['Points'].sum().reset_index()
        leaderboard = leaderboard.sort_values(by='Points', ascending=False)
        st.dataframe(leaderboard, use_container_width=True)
    else:
        st.info("No scores calculated yet.")
        
    st.divider()
    
    st.header("All User Predictions")
    if df_existing.empty:
        st.write("No predictions submitted yet.")
    else:
        for m in df_existing['Match'].unique():
            # Robust lookup using normalized string matching
            match_dict = next((item for item in FIXTURES if item["match"].strip().lower() == str(m).strip().lower()), None)
            st.subheader(f"Match: {m}")
            
            # Secure Fallback: If match info is missing OR kickoff hasn't happened yet, HIDE the table
            if match_dict is None or current_time < match_dict['kickoff']:
                st.warning("Predictions are hidden until kickoff.")
                users = df_existing[(df_existing['Match'].str.strip().lower() == str(m).strip().lower()) & (df_existing['User'] != 'ADMIN_RESULT')]['User'].tolist()
                st.write(f"**Submitted by:** {', '.join(users) if users else 'None'}")
            else:
                public_df = df_existing[(df_existing['Match'].str.strip().lower() == str(m).strip().lower()) & (df_existing['User'] != 'ADMIN_RESULT')]
                st.dataframe(public_df, use_container_width=True)

# --- TAB 3: ADMIN PANEL ---
with tab3:
    st.header("Admin Panel")
    admin_pass = st.text_input("Admin Password", type="password")
    
    if admin_pass == "worldcup2026":
        past_fixtures = [f['match'] for f in FIXTURES if current_time > f['kickoff']]
        if not past_fixtures:
            st.info("No matches have kicked off yet.")
        else:
            match_to_resolve = st.selectbox("Select Match to Grade", past_fixtures)
            team1, team2 = match_to_resolve.split(" vs ")
            
            col1, col2 = st.columns(2)
            act_t1 = col1.number_input(f"{team1} Final Score", min_value=0, step=1, value=0)
            act_t2 = col2.number_input(f"{team2} Final Score", min_value=0, step=1, value=0)
            act_pen = st.selectbox("Penalty Winner (if draw)", ["None", team1, team2])
            
            match_pool = sorted(SQUADS.get(team1, ["Player A"]) + SQUADS.get(team2, ["Player B"]))
            act_motm = st.selectbox("Official MOTM", match_pool)
            act_scorers = st.multiselect("Official Scorers", match_pool)
            
            if st.button("Submit Official Results"):
                if df_existing[df_existing['User'] != 'ADMIN_RESULT'].empty:
                    st.error("No users to score.")
                else:
                    def calc_row_points(row):
                        if row['User'] == 'ADMIN_RESULT':
                            return 0
                        if str(row['Match']).strip().lower() != match_to_resolve.strip().lower():
                            return row['Points']
                        
                        pts = 0
                        p_diff = int(row['Team1_Score']) - int(row['Team2_Score'])
                        a_diff = act_t1 - act_t2
                        
                        if a_diff == 0:  
                            if p_diff == 0:
                                pts += 3 if str(row['Pen_Winner']) == act_pen else 1
                        else:  
                            if int(row['Team1_Score']) == act_t1 and int(row['Team2_Score']) == act_t2:
                                pts += 3
                            elif (p_diff > 0 and a_diff > 0) or (p_diff < 0 and a_diff < 0):
                                pts += 2
                        
                        if str(row['MOTM']).strip().lower() == act_motm.lower():
                            pts += 2
                        
                        p_list = [s.strip().lower() for s in str(row['Scorers']).split(',') if s.strip() and s.strip().lower() != 'none']
                        a_list = [s.strip().lower() for s in act_scorers]
                        for scorer in p_list:
                            if scorer in a_list:
                                pts += 1
                                a_list.remove(scorer)
                        return pts

                    df_existing['Points'] = df_existing.apply(calc_row_points, axis=1)
                    df_existing = df_existing[~((df_existing['User'] == 'ADMIN_RESULT') & (df_existing['Match'].str.strip().lower() == match_to_resolve.strip().lower()))]
                    
                    new_admin_row = pd.DataFrame([{
                        "Timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S"),
                        "User": "ADMIN_RESULT",
                        "Match": match_to_resolve,
                        "Team1_Score": act_t1,
                        "Total2_Score": act_t2,
                        "Pen_Winner": act_pen,
                        "MOTM": act_motm,
                        "Scorers": ", ".join(act_scorers) if act_scorers else "None",
                        "Points": 0
                    }])
                    
                    df_existing = pd.concat([df_existing, new_admin_row], ignore_index=True)
                    header_row = [["Timestamp", "User", "Match", "Team1_Score", "Team2_Score", "Pen_Winner", "MOTM", "Scorers", "Points"]]
                    raw_rows = df_existing.values.tolist()
                    clean_rows = [[str(cell) for cell in row] for row in raw_rows]
                    full_payload = {"action": "overwrite", "rows": header_row + clean_rows}
                    
                    try:
                        requests.post(WEBAPP_URL, data=json.dumps(full_payload))
                        st.success("Match graded and brackets advanced!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error saving data: {e}")
