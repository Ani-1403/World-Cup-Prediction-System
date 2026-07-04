import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import requests


st.set_page_config(page_title="World Cup Predictor", page_icon="🏆", layout="wide")
ist = pytz.timezone('Asia/Kolkata')
current_time = datetime.now(ist)


FIXTURES = [
    {"id": 1, "match": "Canada vs Morocco", "kickoff": ist.localize(datetime(2026, 7, 4, 22, 30))},
    {"id": 2, "match": "Paraguay vs France", "kickoff": ist.localize(datetime(2026, 7, 5, 2, 30))},
    {"id": 3, "match": "Brazil vs Norway", "kickoff": ist.localize(datetime(2026, 7, 6, 1, 30))},
    {"id": 4, "match": "Mexico vs England", "kickoff": ist.localize(datetime(2026, 7, 6, 5, 30))}
]


active_fixture = None
for f in FIXTURES:
    if current_time < f["kickoff"]:
        active_fixture = f
        break

st.title("World Cup Predictor Dashboard")


sheet_id = "1rzyPqXioFz2wj_Aby9kuFBafX0wsADvbM-QQTAeGJv8"
csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Predictions"

try:
    df_existing = pd.read_csv(csv_url)
 
    if "Team1_Score" not in df_existing.columns:
        st.warning("Ensure your Google Sheet has headers: Timestamp, User, Match, Team1_Score, Team2_Score, Pen_Winner, MOTM, Scorers, Points")
        st.stop()
except Exception as e:
    st.error(f"Database connection error: {e}")
    st.stop()


st.sidebar.header("User Access")
username = st.sidebar.text_input("Enter your unique name:").strip()

if not username:
    st.info("Please enter your name in the sidebar to access the dashboard.")
    st.stop()


tab1, tab2, tab3 = st.tabs(["Submit Prediction", "View Picks (Locked)", "Admin Resolution"])


with tab1:
    if not active_fixture:
        st.success("All matches completed!")
    else:
        st.header(f"Next Match: {active_fixture['match']}")
        time_left = active_fixture['kickoff'] - current_time
        st.subheader(f"Time to kickoff: {time_left.seconds // 3600}h {(time_left.seconds // 60) % 60}m")
        

        has_predicted = False
        if not df_existing.empty and "Match" in df_existing.columns:
            has_predicted = not df_existing[(df_existing['User'].str.lower() == username.lower()) & 
                                            (df_existing['Match'] == active_fixture['match'])].empty

        if has_predicted:
            st.success("You have already locked in your prediction for this match!")
        else:
            with st.form("prediction_form", clear_on_submit=True):
                team1, team2 = active_fixture['match'].split(" vs ")
                col1, col2 = st.columns(2)
                t1_score = col1.number_input(f"{team1} Predicted Score", min_value=0, max_value=20, step=1)
                t2_score = col2.number_input(f"{team2} Predicted Score", min_value=0, max_value=20, step=1)
                
                st.markdown("**Penalty Shootout Backup:**")
                pen_winner = st.selectbox("Who wins the penalty shootout? (Leave as None if no draw)", ["None", team1, team2])
                
                motm = st.text_input("Man of the Match (Last Name Only):").strip()
                scorers = st.text_input("Goalscorers (Comma-separated):").strip()
                
                submit_btn = st.form_submit_button("Lock In Prediction")
                
                if submit_btn:
                    if t1_score == t2_score and pen_winner == "None":
                        st.error("Invalid entry: You predicted a tie but did not choose a penalty winner.")
                    elif t1_score != t2_score and pen_winner != "None":
                        st.error("Invalid entry: You picked a penalty winner but did not predict a tie.")
                    else:
                        # Direct form action to append via standard API endpoint
                        form_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/formResponse"
                        st.error("Form writing actions require service account permissions or structural web forms. Viewing operational analytics.")
                        st.info("System optimized. Run deployment script.")


with tab2:
    st.header("Match Predictions")
    if df_existing.empty:
        st.write("No predictions submitted yet.")
    else:
        matches_pred = df_existing['Match'].unique()
        for m in matches_pred:
            match_dict = next((item for item in FIXTURES if item["match"] == m), None)
            
            st.subheader(f"Match: {m}")
            if match_dict and current_time < match_dict['kickoff']:
                st.warning(f"Predictions for {m} are hidden until kickoff.")
                users = df_existing[df_existing['Match'] == m]['User'].tolist()
                st.write(f"**Users locked in:** {', '.join(users)}")
            else:
                st.success(f"{m} is live! Picks revealed.")
                st.dataframe(df_existing[df_existing['Match'] == m], use_container_width=True)


with tab3:
    st.header("Admin Resolution (Update Leaderboard)")
    admin_pass = st.text_input("Admin Password:", type="password")
    
    if admin_pass == "worldcup2026":
        match_to_resolve = st.selectbox("Select Match to Score", [f['match'] for f in FIXTURES if current_time > f['kickoff']])
        
        team1, team2 = match_to_resolve.split(" vs ") if match_to_resolve else ("Team 1", "Team 2")
        act_t1 = st.number_input(f"Official {team1} Score", min_value=0, step=1)
        act_t2 = st.number_input(f"Official {team2} Score", min_value=0, step=1)
        act_pen = st.selectbox("Official Penalty Shootout Winner", ["None", team1, team2])
        act_motm = st.text_input("Official MOTM:").strip()
        act_scorers = st.text_input("Official Scorers (Comma-separated):").strip()
        
        if st.button("Calculate & Assign Points"):
            def calc_pts(row):
                if row['Match'] != match_to_resolve:
                    return row['Points']
                
                pts = 0
                p_diff = row['Team1_Score'] - row['Team2_Score']
                a_diff = act_t1 - act_t2
                
                if a_diff == 0:  
                    if p_diff == 0:
                        pts += 3 if row['Pen_Winner'] == act_pen else 1
                else:  
                    if row['Team1_Score'] == act_t1 and row['Team2_Score'] == act_t2:
                        pts += 3
                    elif (p_diff > 0 and a_diff > 0) or (p_diff < 0 and a_diff < 0):
                        pts += 2
                
                if str(row['MOTM']).strip().lower() == act_motm.lower():
                    pts += 2
                
                p_list = [s.strip().lower() for s in str(row['Scorers']).split(',') if s.strip()]
                a_list = [s.strip().lower() for s in act_scorers.split(',') if s.strip()]
                for scorer in p_list:
                    if scorer in a_list:
                        pts += 1
                        a_list.remove(scorer)
                        
                return pts

            df_existing['Points'] = df_existing.apply(calc_pts, axis=1)
            st.success(f"Scores for {match_to_resolve} processed internally.")
            
        st.divider()
        st.subheader("Total Tournament Leaderboard")
        if not df_existing.empty:
            leaderboard = df_existing.groupby('User')['Points'].sum().reset_index()
            leaderboard = leaderboard.sort_values(by='Points', ascending=False)
            st.dataframe(leaderboard, use_container_width=True)
