import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import requests
import json
from squads import SQUADS
from fixtures import get_active_fixtures

st.set_page_config(page_title="World Cup Predictor Suite", page_icon="🏆", layout="wide")
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

# Automatically resolve the complete active schedule timeline matrix
FIXTURES = get_active_fixtures(df_existing)

active_fixture = None
for f in FIXTURES:
    if current_time < f["kickoff"]:
        active_fixture = f
        break

st.title("🏆 2026 World Cup Bracket Predictor")
st.sidebar.header("User Context Dashboard")
username = st.sidebar.text_input("Enter your assigned participant handle:").strip()

if not username:
    st.info("Enter your identifying handle via the sidebar profile panel to manage entries.")
    st.stop()
if username == "ADMIN_RESULT":
    st.error("System configuration error: Restricted system token entry detected.")
    st.stop()

tab1, tab2, tab3 = st.tabs(["Active Match Portal", "Global Analytics Grid", "Tournament Admin Node"])

with tab1:
    if not active_fixture:
        st.success("All matches scheduled across active configurations have reached lock constraints.")
    else:
        st.header(f"Upcoming Target Matchup: {active_fixture['match']}")
        time_left = active_fixture['kickoff'] - current_time
        st.subheader(f"Window Closes In: {time_left.days}d {time_left.seconds // 3600}h {(time_left.seconds // 60) % 60}m")
        
        has_predicted = False
        if not df_existing.empty:
            has_predicted = not df_existing[(df_existing['User'].str.lower() == username.lower()) & 
                                            (df_existing['Match'] == active_fixture['match'])].empty

        if has_predicted:
            st.success("Your prediction profile for this fixture is securely logged inside the database cluster.")
        else:
            team1, team2 = active_fixture['match'].split(" vs ")
            pool_choices = sorted(SQUADS.get(team1, ["Player A", "Player B"]) + SQUADS.get(team2, ["Player C", "Player D"]))
            
            with st.form("submission_entry_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                t1_score = col1.number_input(f"{team1} Projections", min_value=0, max_value=25, step=1, value=0)
                t2_score = col2.number_input(f"{team2} Projections", min_value=0, max_value=25, step=1, value=0)
                
                pen_winner = st.selectbox("Sudden Death Shootout Backup Selection", ["None", team1, team2])
                motm = st.selectbox("Select Expected Man of the Match Performance", pool_choices)
                scorers_list = st.multiselect("Designate Projected Scorers Matrix", pool_choices)
                
                if st.form_submit_button("Transmit Prediction Matrix"):
                    if t1_score == t2_score and pen_winner == "None":
                        st.error("Validation Halt: Draw projections demand an associated Shootout Backup choice.")
                    elif t1_score != t2_score and pen_winner != "None":
                        st.error("Validation Halt: Conflict identified between structural winner and Shootout Backup allocation.")
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
                            requests.post(WEBAPP_URL, data=json.dumps(payload))
                            st.success("Data cleanly transmitted to the Google Apps Script engine. Resetting matrix...")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Transmission link processing failure: {e}")

with tab2:
    st.header("Public Distribution Framework")
    if df_existing.empty:
        st.write("Awaiting initial participant transactions.")
    else:
        for m in df_existing['Match'].unique():
            match_dict = next((item for item in FIXTURES if item["match"] == m), None)
            st.subheader(f"Fixture Focus: {m}")
            
            if match_dict and current_time < match_dict['kickoff']:
                st.warning("Content masked. Lock conditions remain active until kickoff threshold is met.")
                users = df_existing[(df_existing['Match'] == m) & (df_existing['User'] != 'ADMIN_RESULT')]['User'].tolist()
                st.write(f"**Entries Verified:** {', '.join(users) if users else 'None yet'}")
            else:
                st.success("Kickoff confirmed. Showing all user picks.")
                public_df = df_existing[(df_existing['Match'] == m) & (df_existing['User'] != 'ADMIN_RESULT')]
                st.dataframe(public_df, use_container_width=True)

with tab3:
    st.header("Tournament Operations Node")
    admin_pass = st.text_input("Operational Authentication Key", type="password")
    
    if admin_pass == "worldcup2026":
        past_fixtures = [f['match'] for f in FIXTURES if current_time > f['kickoff']]
        if not past_fixtures:
            st.info("System logs show no fixture items have successfully cleared lock deadlines yet.")
        else:
            match_to_resolve = st.selectbox("Choose Targeted Concluded Fixture to Resolve", past_fixtures)
            team1, team2 = match_to_resolve.split(" vs ")
            
            col1, col2 = st.columns(2)
            act_t1 = col1.number_input(f"Official Regular Time {team1} Score", min_value=0, step=1, value=0)
            act_t2 = col2.number_input(f"Official Regular Time {team2} Score", min_value=0, step=1, value=0)
            act_pen = st.selectbox("Official Penalty Shootout Winner", ["None", team1, team2])
            
            match_pool = sorted(SQUADS.get(team1, ["Player A"]) + SQUADS.get(team2, ["Player B"]))
            act_motm = st.selectbox("Official MVP Selection", match_pool)
            act_scorers = st.multiselect("Official Match Scorers Collection", match_pool)
            
            if st.button("Commit Resolution & Advance Brackets"):
                if df_existing[df_existing['User'] != 'ADMIN_RESULT'].empty:
                    st.error("Point calculation execution abandoned: Empty target array.")
                else:
                    def calc_row_points(row):
                        if row['User'] == 'ADMIN_RESULT':
                            return 0
                        if row['Match'] != match_to_resolve:
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
                    df_existing = df_existing[~((df_existing['User'] == 'ADMIN_RESULT') & (df_existing['Match'] == match_to_resolve))]
                    
                    new_admin_row = pd.DataFrame([{
                        "Timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S"),
                        "User": "ADMIN_RESULT",
                        "Match": match_to_resolve,
                        "Team1_Score": act_t1,
                        "Team2_Score": act_t2,
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
                        st.success("Target match data recorded! Downstream brackets calculated. Reloading application layer...")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to post to cloud endpoint: {e}")
                
    st.divider()
    st.subheader("Global Standings Master List")
    public_leaderboard = df_existing[df_existing['User'] != 'ADMIN_RESULT']
    if not public_leaderboard.empty and "Points" in public_leaderboard.columns:
        leaderboard = public_leaderboard.groupby('User')['Points'].sum().reset_index()
        leaderboard = leaderboard.sort_values(by='Points', ascending=False)
        st.dataframe(leaderboard, use_container_width=True)
