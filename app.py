import io
import json
import time
from datetime import datetime

import pandas as pd
import pytz
import requests
import streamlit as st

from fixtures import get_active_fixtures

st.set_page_config(page_title="World Cup Predictor", layout="wide")

IST = pytz.timezone("Asia/Kolkata")
EXPECTED_COLS = [
    "Timestamp", "User", "Match", "Team1_Score", "Team2_Score",
    "Pen_Winner", "MOTM", "Scorers", "Points"
]


def get_secret(key, default=""):
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


# --- Configuration -----------------------------------------------------
# Prefer st.secrets (Settings -> Secrets in Streamlit Cloud, or
# .streamlit/secrets.toml locally) over hardcoding these in source.
WEBAPP_URL = get_secret(
    "WEBAPP_URL",
    "https://script.google.com/macros/s/AKfycbxnGXFa4VpEJFmIwcuOACjo32uKRb67DAU4luczLqgnkV-wplBnG1IxdK64TdnqCc6Z/exec",
)
SHEET_ID = get_secret("SHEET_ID", "1rzyPqXioFz2wj_Aby9kuFBafX0wsADvbM-QQTAeGJv8")
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Predictions"

API_SECRET = get_secret("API_SECRET", "Kenkanekii14033!!")
ADMIN_PASSWORD = get_secret("ADMIN_PASSWORD", "worldcup2026")

if not API_SECRET:
    st.sidebar.warning(
        "API_SECRET is not set in st.secrets. Requests to the Apps Script "
        "will be rejected until you set the same secret in both places.",
        icon="⚠️",
    )


def now_ist():
    return datetime.now(IST)


# --- Data loading --------------------------------------------------------
def load_predictions():
    """
    Fetches the Predictions sheet as CSV with a cache-busting query param
    (Google's gviz export is otherwise cached for around a minute, which
    can make a just-submitted prediction invisible for a while).
    Never raises: on any failure, returns an empty (but correctly shaped)
    dataframe plus an error string the caller can choose to display.
    """
    url = f"{CSV_URL}&cachebust={int(time.time() * 1000)}"
    try:
        resp = requests.get(url, timeout=10, headers={"Cache-Control": "no-cache"})
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text))

        if len(df.columns) == len(EXPECTED_COLS):
            df.columns = EXPECTED_COLS
        else:
            return pd.DataFrame(columns=EXPECTED_COLS), (
                f"Sheet has {len(df.columns)} columns, expected {len(EXPECTED_COLS)}. "
                "Check the header row in your Google Sheet."
            )

        for col in ["Team1_Score", "Team2_Score", "Points"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["Points"] = df["Points"].fillna(0)
        df["User"] = df["User"].astype(str)
        df["Match"] = df["Match"].astype(str)

        return df, None
    except Exception as e:
        return pd.DataFrame(columns=EXPECTED_COLS), str(e)


def post_to_backend(payload):
    """POST to the Apps Script and interpret its JSON {status, message} reply.
    Returns (ok: bool, message: str)."""
    payload = dict(payload)
    payload["secret"] = API_SECRET
    try:
        res = requests.post(WEBAPP_URL, data=json.dumps(payload), timeout=15)
        res.raise_for_status()
        try:
            body = res.json()
        except ValueError:
            return False, f"Unexpected response from server: {res.text[:300]}"

        if body.get("status") == "success":
            return True, body.get("message", "Success.")
        return False, body.get("message", "Server rejected the request.")
    except requests.exceptions.RequestException as e:
        return False, f"Network error: {e}"


df_existing, load_err = load_predictions()
if load_err:
    st.sidebar.error(f"Could not load latest predictions: {load_err}")

FIXTURES = get_active_fixtures(df_existing)
current_time = now_ist()

st.title("World Cup Predictor")

# --- Session state ---------------------------------------------------
if "username" not in st.session_state:
    st.session_state.username = None
if "just_submitted" not in st.session_state:
    st.session_state.just_submitted = set()  # matches submitted this session

st.sidebar.header("User Profile")

if st.sidebar.button("🔄 Refresh data"):
    st.rerun()

if not st.session_state.username:
    input_name = st.sidebar.text_input("Enter your name:").strip()
    if st.sidebar.button("Login"):
        key = input_name.lower()
        if not input_name:
            st.sidebar.error("Name cannot be empty.")
        elif key == "admin_result":
            st.sidebar.error("Reserved username.")
        else:
            # If someone already predicted under a different-cased version
            # of this name, snap to that existing casing so the same
            # person doesn't fragment into two "different" leaderboard
            # entries just by typing their name differently.
            canonical = input_name
            if not df_existing.empty:
                existing_users = df_existing[df_existing["User"].str.lower() != "admin_result"]["User"]
                match = existing_users[existing_users.str.lower() == key]
                if not match.empty:
                    canonical = match.iloc[0]
            st.session_state.username = canonical
            st.rerun()
    st.info("Enter your name in the sidebar and click Login to continue.")
    st.stop()
else:
    st.sidebar.success(f"Logged in as: **{st.session_state.username}**")

username = st.session_state.username
username_key = username.strip().lower()

tab1, tab2, tab3 = st.tabs(["Prediction", "Leaderboard", "Admin Panel"])


with tab1:
    open_fixtures = [f for f in FIXTURES if current_time < f["kickoff"]]

    if not open_fixtures:
        st.success("No open matches available for prediction right now.")
    else:
        match_options = [f"{f['match']}  ·  {f['round']}" for f in open_fixtures]
        selected_str = st.selectbox("Select Match to Predict", match_options)
        active_fixture = open_fixtures[match_options.index(selected_str)]

        time_left = active_fixture["kickoff"] - current_time
        st.write(
            f"**Kickoff in:** {time_left.days}d "
            f"{time_left.seconds // 3600}h {(time_left.seconds // 60) % 60}m"
        )

        has_predicted = active_fixture["match"] in st.session_state.just_submitted
        if not has_predicted and not df_existing.empty:
            has_predicted = not df_existing[
                (df_existing["User"].str.strip().str.lower() == username_key)
                & (df_existing["Match"].str.strip().str.lower() == active_fixture["match"].strip().lower())
            ].empty

        if has_predicted:
            st.success("You have already submitted a prediction for this match.")
        else:
            team1, team2 = active_fixture["match"].split(" vs ")

            col1, col2 = st.columns(2)
            t1_score = col1.number_input(f"{team1} Score", min_value=0, max_value=25, step=1, value=0)
            t2_score = col2.number_input(f"{team2} Score", min_value=0, max_value=25, step=1, value=0)

            pen_winner = "None"
            if t1_score == t2_score:
                pen_winner = st.selectbox("Penalty Winner (Required for Draws)", ["None", team1, team2])
            else:
                st.info("Match is not a draw. Penalty selection disabled.")

            if st.button("Submit Prediction"):
                if t1_score == t2_score and pen_winner == "None":
                    st.error("Draws require a penalty shootout winner.")
                else:
                    payload = {
                        "action": "predict",
                        "user": username,
                        "match": active_fixture["match"],
                        "t1_score": int(t1_score),
                        "t2_score": int(t2_score),
                        "pen_winner": pen_winner,
                        "motm": "N/A",
                        "scorers": "N/A",
                    }
                    ok, message = post_to_backend(payload)
                    if ok:
                        st.session_state.just_submitted.add(active_fixture["match"])
                        st.success(message)
                        time.sleep(1.0)
                        st.rerun()
                    else:
                        st.error(message)


with tab2:
    st.header("Leaderboard")

    public_df = df_existing[df_existing["User"].str.strip().str.lower() != "admin_result"].copy()

    if not public_df.empty:
        public_df["user_key"] = public_df["User"].str.strip().str.lower()
        leaderboard = public_df.groupby("user_key").agg(
            Points=("Points", "sum"),
            User=("User", "first"),
        ).reset_index(drop=True)
        leaderboard = leaderboard[["User", "Points"]].sort_values(by="Points", ascending=False)
        st.dataframe(leaderboard, use_container_width=True, hide_index=True)
    else:
        st.info("No scores calculated yet.")

    st.divider()
    st.header("All User Predictions")

    if df_existing.empty:
        st.write("No predictions submitted yet.")
    else:
        seen_matches = [m for m in df_existing["Match"].unique() if str(m).strip()]
        for m in seen_matches:
            match_dict = next(
                (item for item in FIXTURES if item["match"].strip().lower() == str(m).strip().lower()),
                None,
            )
            st.subheader(f"Match: {m}")

            if match_dict is None or current_time < match_dict["kickoff"]:
                st.warning("Predictions are hidden until kickoff.")
                users = df_existing[
                    (df_existing["Match"].str.strip().str.lower() == str(m).strip().lower())
                    & (df_existing["User"].str.strip().str.lower() != "admin_result")
                ]["User"].tolist()
                st.write(f"**Submitted by:** {', '.join(users) if users else 'None'}")
            else:
                match_public_df = df_existing[
                    (df_existing["Match"].str.strip().str.lower() == str(m).strip().lower())
                    & (df_existing["User"].str.strip().str.lower() != "admin_result")
                ]
                display_df = match_public_df.drop(columns=["MOTM", "Scorers", "Timestamp"], errors="ignore")
                st.dataframe(display_df, use_container_width=True, hide_index=True)

with tab3:
    st.header("Admin Panel")
    admin_pass = st.text_input("Admin Password", type="password")

    if admin_pass and admin_pass != ADMIN_PASSWORD:
        st.error("Incorrect password.")
    elif admin_pass == ADMIN_PASSWORD:
        past_fixtures = [f for f in FIXTURES if current_time > f["kickoff"]]

        if not past_fixtures:
            st.info("No matches have kicked off yet.")
        else:
            graded_matches = set()
            if not df_existing.empty:
                graded_matches = set(
                    df_existing[df_existing["User"].str.strip().str.lower() == "admin_result"]["Match"]
                    .str.strip()
                    .str.lower()
                )

            labels = []
            for f in past_fixtures:
                tag = " (already graded)" if f["match"].strip().lower() in graded_matches else " (needs grading)"
                labels.append(f"{f['match']}  ·  {f['round']}{tag}")

            selected_label = st.selectbox("Select Match to Grade", labels)
            match_to_resolve = past_fixtures[labels.index(selected_label)]["match"]
            team1, team2 = match_to_resolve.split(" vs ")

            col1, col2 = st.columns(2)
            act_t1 = col1.number_input(f"{team1} Final Score", min_value=0, max_value=25, step=1, value=0)
            act_t2 = col2.number_input(f"{team2} Final Score", min_value=0, max_value=25, step=1, value=0)

            act_pen = "None"
            if act_t1 == act_t2:
                act_pen = st.selectbox("Penalty Winner (if draw)", ["None", team1, team2])
            else:
                st.info("Match is not a draw. Penalty selection disabled.")

            st.caption(
                "Scoring: exact score = 3pts · correct outcome, wrong score = 2pts · "
                "correct draw, wrong score = 1pt · correct penalty-shootout winner on a draw = +1pt bonus."
            )

            if st.button("Submit Official Results"):
                if act_t1 == act_t2 and act_pen == "None":
                    st.error("This is a draw - select the penalty shootout winner.")
                else:
                    payload = {
                        "action": "grade",
                        "match": match_to_resolve,
                        "act_t1": int(act_t1),
                        "act_t2": int(act_t2),
                        "act_pen": act_pen,
                    }
                    ok, message = post_to_backend(payload)
                    if ok:
                        st.success(message)
                        time.sleep(1.0)
                        st.rerun()
                    else:
                        st.error(message)
    else:
        st.info("Enter the admin password to grade matches.")
