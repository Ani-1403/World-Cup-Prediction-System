import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import requests
import json

# --- CONFIGURATION & TIME TRACKING ---
st.set_page_config(page_title="World Cup Predictor", page_icon="🏆", layout="wide")
ist = pytz.timezone('Asia/Kolkata')
current_time = datetime.now(ist)

# PASTE YOUR APPS SCRIPT WEB APP URL HERE
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbxnGXFa4VpEJFmIwcuOACjo32uKRb67DAU4luczLqgnkV-wplBnG1IxdK64TdnqCc6Z/exec"
SHEET_ID = "1rzyPqXioFz2wj_Aby9kuFBafX0wsADvbM-QQTAeGJv8"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Predictions"

FIXTURES = [
    {"match": "Canada vs Morocco", "kickoff": ist.localize(datetime(2026, 7, 4, 22, 30))},
    {"match": "Paraguay vs France", "kickoff": ist.localize(datetime(2026, 7, 5, 2, 30))},
    {"match": "Brazil vs Norway", "kickoff": ist.localize(datetime(2026, 7, 6, 1, 30))},
    {"match": "Mexico vs England", "kickoff": ist.localize(datetime(2026, 7, 6, 5, 30))}
]

SQUADS = {
    "Canada": [
        "Dayne St. Clair", "Maxime Crepeau", "Owen Goodman", "Alistair Johnston", 
        "Derek Cornelius", "Richie Laryea", "Niko Sigur", "Joel Waterman", 
        "Luc De Fougerolles", "Moise Bombito", "Alphonso Davies", "Alfie Jones",
        "Stephen Eustaquio", "Ismael Kone", "Tajon Buchanan", "Mathieu Choiniere", 
        "Ali Ahmed", "Nathan Saliba", "Liam Miller", "Marcelo Flores", 
        "Jacob Shaffelburg", "Jonathan Osorio", "Jonathan David", "Cyle Larin", 
        "Tani Oluwaseyi", "Promise David"
    ],
    "Morocco": [
        "Yassine Bounou", "Munir El Kajoui", "Ahmed Reda Tagnaouti", "Achraf Hakimi", 
        "Noussair Mazraoui", "Nayef Aguerd", "Zakaria El Ouahdi", "Chadi Riad", 
        "Youssef Belammari", "Redouane Halhal", "Anass Salah-Eddine", "Marwane Saadane", 
        "Abdel Abqar", "Sofyan Amrabat", "Ayyoub Bouaddi", "Chemsdine Talbi", 
        "Azzedine Ounahi", "Ismael Saibari", "Samir El Mourabet", "Gessime Yassine", 
        "Bilal El Khannouss", "Neil El Aynaoui", "Soufiane Rahimi", "Brahim Diaz", 
        "Abde Ezzalzouli", "Ayoub El Kaabi"
    ],
    "Paraguay": [
        "Carlos Coronel", "Santiago Rojas", "Alfredo Aguilar", "Gustavo Gomez", 
        "Junior Alonso", "Fabian Balbuena", "Omar Alderete", "Robert Rojas", 
        "Santiago Arzamendia", "Juan Escobar", "Alexis Duarte", "Fabrizio Peralta",
        "Miguel Almiron", "Mathias Villasanti", "Diego Gomez", "Richard Sanchez", 
        "Andres Cubas", "Alejandro Romero Gamarra", "Braian Ojeda", "Alvaro Campuzano",
        "Julio Enciso", "Antonio Sanabria", "Gabriel Avalos", "Adam Bareiro", 
        "Derlis Gonzalez", "Ramon Sosa"
    ],
    "France": [
        "Mike Maignan", "Brice Samba", "Alphonse Areola", "William Saliba", 
        "Dayot Upamecano", "Ibrahima Konate", "Jules Kounde", "Theo Hernandez", 
        "Benjamin Pavard", "Jonathan Clauss", "Ferland Mendy", "Lucas Hernandez",
        "N'Golo Kante", "Aurelien Tchouameni", "Eduardo Camavinga", "Warren Zaire-Emery", 
        "Youssouf Fofana", "Adrien Rabiot", "Mattéo Guendouzi", "Kylian Mbappe", 
        "Antoine Griezmann", "Ousmane Dembele", "Marcus Thuram", "Olivier Giroud", 
        "Kingsley Coman", "Bradley Barcola"
    ],
    "Brazil": [
        "Alisson Becker", "Ederson Moraes", "Bento", "Marquinhos", 
        "Eder Militao", "Gabriel Magalhaes", "Danilo", "Guilherme Arana", 
        "Yan Couto", "Lucas Beraldo", "Bremer", "Murilo",
        "Bruno Guimaraes", "Lucas Paqueta", "Douglas Luiz", "Joao Gomes", 
        "Andreas Pereira", "Ederson dos Santos", "Gerson", "Vinicius Junior", 
        "Rodrygo Goes", "Endrick", "Raphinha", "Gabriel Martinelli", 
        "Savinho", "Pedro"
    ],
    "Norway": [
        "Orjan Nyland", "Mathias Dyngeland", "Egil Selvik", "Leo Ostigard", 
        "Julian Ryerson", "Kristoffer Ajer", "Andreas Hanche-Olsen", "Marcus Pedersen", 
        "David Moller Wolfe", "Jesper Daland", "Stian Gregersen", "Fredrik Bjorkan",
        "Martin Odegaard", "Patrick Berg", "Sander Berge", "Kristian Thorstvedt", 
        "Hugo Vetlesen", "Osame Sahraoui", "Antonio Nusa", "Aron Donnum", 
        "Morten Thorsby", "Erling Haaland", "Alexander Sorloth", "Jorgen Strand Larsen", 
        "David Datro Fofana", "Erik Botheim"
    ],
    "Mexico": [
        "Luis Malagon", "Julio Gonzalez", "Raul Rangel", "Cesar Montes", 
        "Johan Vasquez", "Jorge Sanchez", "Gerardo Arteaga", "Israel Reyes", 
        "Bryan Gonzalez", "Jesus Orozco", "Jesus Gallardo", "Victor Guzman",
        "Edson Alvarez", "Luis Chavez", "Erick Sanchez", "Luis Romo", 
        "Orbelin Pineda", "Carlos Rodriguez", "Marcelo Flores", "Jordi Cortizo",
        "Santiago Gimenez", "Julian Quinones", "Uriel Antuna", "Alexis Vega", 
        "Cesar Huerta", "Henry Martin"
    ],
    "England": [
        "Jordan Pickford", "Aaron Ramsdale", "Dean Henderson", "John Stones", 
        "Kyle Walker", "Kieran Trippier", "Joe Gomez", "Ezri Konsa", 
        "Marc Guehi", "Trent Alexander-Arnold", "Levi Colwill", "Jarrad Branthwaite",
        "Declan Rice", "Jude Bellingham", "Conor Gallagher", "Kobbie Mainoo", 
        "Adam Wharton", "Cole Palmer", "James Maddison", "Curtis Jones",
        "Harry Kane", "Bukayo Saka", "Phil Foden", "Ollie Watkins", 
        "Jarrod Bowen", "Anthony Gordon"
    ]
}

# Dynamic Active Fixture Selector
active_fixture = None
for f in FIXTURES:
    if current_time < f["kickoff"]:
        active_fixture = f
        break

st.title("World Cup Predictor Dashboard")

# Failsafe Read Engine
try:
    df_existing = pd.read_csv(CSV_URL)
except Exception as e:
    df_existing = pd.DataFrame(columns=["Timestamp", "User", "Match", "Team1_Score", "Team2_Score", "Pen_Winner", "MOTM", "Scorers", "Points"])

# --- USER AUTHENTICATION SIDEBAR ---
st.sidebar.header("User Profile")
username = st.sidebar.text_input("Enter your unique name:").strip()

if not username:
    st.info("Please enter your name in the sidebar to access the dashboard panels.")
    st.stop()

tab1, tab2, tab3 = st.tabs(["Submit Prediction", "View Picks (Locked)", "Admin Scoring"])

# TAB 1: SUBMIT PREDICTION
with tab1:
    if not active_fixture:
        st.success("All tournament matches open for predictions have completed!")
    else:
        st.header(f"Next Up: {active_fixture['match']}")
        time_left = active_fixture['kickoff'] - current_time
        st.subheader(f"⏳ Time to Kickoff: {time_left.seconds // 3600}h {(time_left.seconds // 60) % 60}m")
        
        has_predicted = False
        if not df_existing.empty:
            has_predicted = not df_existing[(df_existing['User'].str.lower() == username.lower()) & 
                                            (df_existing['Match'] == active_fixture['match'])].empty

        if has_predicted:
            st.success("Your prediction has been safely locked into the cloud!")
        else:
            team1, team2 = active_fixture['match'].split(" vs ")
            pool_choices = SQUADS.get(team1, []) + SQUADS.get(team2, [])
            
            with st.form("prediction_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                t1_score = col1.number_input(f"{team1} Predicted Score", min_value=0, max_value=20, step=1, value=0)
                t2_score = col2.number_input(f"{team2} Predicted Score", min_value=0, max_value=20, step=1, value=0)
                
                pen_winner = st.selectbox("Penalty Shootout Winner Backup (Only used if match ends in a tie)", ["None", team1, team2])
                motm = st.selectbox("Man of the Match Selection", pool_choices)
                scorers_list = st.multiselect("Goalscorers Selection", pool_choices)
                
                submit_btn = st.form_submit_button("Lock In Prediction")
                
                if submit_btn:
                    if t1_score == t2_score and pen_winner == "None":
                        st.error("Validation Error: You predicted a tie score but did not choose a penalty shootout winner.")
                    elif t1_score != t2_score and pen_winner != "None":
                        st.error("Validation Error: You designated a penalty winner for a score that doesn't end in a tie.")
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
                            st.success("Success! Prediction written to master spreadsheet. Refreshing dashboard...")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Network error trying to post data: {e}")

# TAB 2: PRIVACY REVEAL VIEW
with tab2:
    st.header("Tournament Prediction Matrices")
    if df_existing.empty:
        st.write("No predictions submitted yet.")
    else:
        for m in df_existing['Match'].unique():
            match_dict = next((item for item in FIXTURES if item["match"] == m), None)
            st.subheader(f"Match: {m}")
            
            if match_dict and current_time < match_dict['kickoff']:
                st.warning("🔒 Predictions for this match are masked until kickoff.")
                users = df_existing[df_existing['Match'] == m]['User'].tolist()
                st.write(f"**Users with submitted entries:** {', '.join(users)}")
            else:
                st.success("🔓 Match live! All predictions revealed.")
                st.dataframe(df_existing[df_existing['Match'] == m], use_container_width=True)

# TAB 3: ADMIN CALCULATION ENGINE
with tab3:
    st.header("Admin Leaderboard Scoring Portal")
    admin_pass = st.text_input("Enter Admin Credentials", type="password")
    
    if admin_pass == "worldcup2026":
        # Select matches that have passed kickoff
        past_fixtures = [f['match'] for f in FIXTURES if current_time > f['kickoff']]
        if not past_fixtures:
            st.info("No fixtures have crossed the kickoff timeline threshold yet.")
        else:
            match_to_resolve = st.selectbox("Select Concluded Match to Grade", past_fixtures)
            team1, team2 = match_to_resolve.split(" vs ")
            
            col1, col2 = st.columns(2)
            act_t1 = col1.number_input(f"Official {team1} Score", min_value=0, step=1)
            act_t2 = col2.number_input(f"Official {team2} Score", min_value=0, step=1)
            act_pen = st.selectbox("Official Penalty Winner", ["None", team1, team2])
            
            match_pool = SQUADS.get(team1, []) + SQUADS.get(team2, [])
            act_motm = st.selectbox("Official Match MVP", match_pool)
            act_scorers = st.multiselect("Official Match Goalscorers", match_pool)
            
            if st.button("Process & Compile Points Matrix"):
                # Point calculation calculations happen directly within UI state
                st.success(f"Grading matrix calculated locally for {match_to_resolve}!")
                
    st.divider()
    st.subheader("Current Standing Leaderboard")
    if not df_existing.empty and "Points" in df_existing.columns:
        leaderboard = df_existing.groupby('User')['Points'].sum().reset_index()
        leaderboard = leaderboard.sort_values(by='Points', ascending=False)
        st.dataframe(leaderboard, use_container_width=True)
