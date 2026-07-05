import io
import json
import time
from datetime import datetime

import pandas as pd
import pytz
import requests
import streamlit as st

from fixtures import get_active_fixtures
from squads import get_combined_squad

st.set_page_config(page_title="World Cup Predictor", layout="wide")

IST = pytz.timezone("Asia/Kolkata")
EXPECTED_COLS = [
    "Timestamp", "User", "Match", "Team1_Score", "Team2_Score",
    "Pen_Winner", "MOTM", "Scorers", "Points"
]

# Matches played before MOTM feature existed — no squad dropdowns
MOTM_DISABLED_MATCHES = {
    "canada vs morocco",
    "paraguay vs france",
}


def get_secret(key, default=""):
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


WEBAPP_URL = get_secret(
    "WEBAPP_URL",
    "https://script.google.com/macros/s/AKfycbxnGXFa4VpEJFmIwcuOACjo32uKRb67DAU4luczLqgnkV-wplBnG1IxdK64TdnqCc6Z/exec",
)
SHEET_ID = get_secret("SHEET_ID", "1rzyPqXioFz2wj_Aby9kuFBafX0wsADvbM-QQTAeGJv8")
CSV_URL = (
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
    "/gviz/tq?tqx=out:csv&sheet=Predictions"
)
API_SECRET     = get_secret("API_SECRET",     "Kenkanekii14033!!")
ADMIN_PASSWORD = get_secret("ADMIN_PASSWORD", "worldcup2026")

if not API_SECRET:
    st.sidebar.warning(
        "API_SECRET is not set in st.secrets. Requests will be rejected "
        "until you set the same secret in both places."
    )


def now_ist():
    return datetime.now(IST)


def load_predictions():
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
        df["User"]  = df["User"].astype(str)
        df["Match"] = df["Match"].astype(str)
        return df, None
    except Exception as e:
        return pd.DataFrame(columns=EXPECTED_COLS), str(e)


def post_to_backend(payload):
    payload = dict(payload)
    payload["secret"] = API_SECRET
    try:
        res = requests.post(WEBAPP_URL, data=json.dumps(payload), timeout=15)
        res.raise_for_status()
        try:
            body = res.json()
        except ValueError:
            return False, f"Unexpected server response: {res.text[:300]}"
        if body.get("status") == "success":
            return True, body.get("message", "Success.")
        return False, body.get("message", "Server rejected the request.")
    except requests.exceptions.RequestException as e:
        return False, f"Network error: {e}"


# ── Bootstrap ──────────────────────────────────────────────────────────────
df_existing, load_err = load_predictions()
if load_err:
    st.sidebar.error(f"Could not load latest predictions: {load_err}")

FIXTURES     = get_active_fixtures(df_existing)
current_time = now_ist()

st.title("World Cup 2026 Predictor")

if "username"       not in st.session_state: st.session_state.username       = None
if "just_submitted" not in st.session_state: st.session_state.just_submitted = set()
if "editing_match"  not in st.session_state: st.session_state.editing_match  = None

st.sidebar.header("User Profile")
if st.sidebar.button("Refresh data"):
    st.rerun()

# ── Login ──────────────────────────────────────────────────────────────────
if not st.session_state.username:
    input_name = st.sidebar.text_input("Enter your name:").strip()
    if st.sidebar.button("Login"):
        key = input_name.lower()
        if not input_name:
            st.sidebar.error("Name cannot be empty.")
        elif key == "admin_result":
            st.sidebar.error("Reserved username.")
        else:
            canonical = input_name
            if not df_existing.empty:
                existing_users = df_existing[df_existing["User"].str.lower() != "admin_result"]["User"]
                hit = existing_users[existing_users.str.lower() == key]
                if not hit.empty:
                    canonical = hit.iloc[0]
            st.session_state.username = canonical
            st.rerun()
    st.info("Enter your name in the sidebar and click Login to continue.")
    st.stop()
else:
    st.sidebar.success(f"Logged in as: **{st.session_state.username}**")

username     = st.session_state.username
username_key = username.strip().lower()

tab1, tab2, tab3 = st.tabs(["Prediction", "Leaderboard", "Admin Panel"])

# ══════════════════════════════════════════════════════════════════════════
# TAB 1 — Prediction
# ══════════════════════════════════════════════════════════════════════════
with tab1:
    open_fixtures = [fix for fix in FIXTURES if current_time < fix["kickoff"]]

    if not open_fixtures:
        st.success("No open matches available for prediction right now.")
    else:
        match_options  = [f"{fix['match']}  |  {fix['round']}" for fix in open_fixtures]
        selected_str   = st.selectbox("Select Match to Predict", match_options)
        active_fixture = open_fixtures[match_options.index(selected_str)]
        match_name     = active_fixture["match"]
        match_key      = match_name.strip().lower()

        time_left = active_fixture["kickoff"] - current_time
        days  = time_left.days
        hours = time_left.seconds // 3600
        mins  = (time_left.seconds // 60) % 60
        st.write(f"**Kickoff in:** {days}d {hours}h {mins}m")

        # Find existing prediction for this user + match
        existing_row = None
        if not df_existing.empty:
            mask = (
                (df_existing["User"].str.strip().str.lower()  == username_key)
                & (df_existing["Match"].str.strip().str.lower() == match_key)
            )
            rows = df_existing[mask]
            if not rows.empty:
                existing_row = rows.iloc[0]

        has_predicted = (
            match_name in st.session_state.just_submitted
            or existing_row is not None
        )

        team1, team2 = match_name.split(" vs ")

        # ── Already predicted: show summary + edit button ─────────────────
        if has_predicted and st.session_state.editing_match != match_name:
            st.success("You have already submitted a prediction for this match.")
            if existing_row is not None:
                t1_p   = int(existing_row["Team1_Score"]) if pd.notna(existing_row["Team1_Score"]) else 0
                t2_p   = int(existing_row["Team2_Score"]) if pd.notna(existing_row["Team2_Score"]) else 0
                pen_p  = str(existing_row.get("Pen_Winner", "None")).strip()
                motm_p = str(existing_row.get("MOTM", "N/A")).strip()

                pen_str  = f"  |  Pens: **{pen_p}**"  if pen_p  not in ("None", "N/A", "nan", "") else ""
                motm_str = f"  |  MOTM: **{motm_p}**" if motm_p not in ("N/A", "nan", "")         else ""
                st.info(f"Your pick: **{team1} {t1_p} – {t2_p} {team2}**{pen_str}{motm_str}")

            if st.button("Edit my prediction"):
                st.session_state.editing_match = match_name
                st.rerun()

        # ── Prediction / edit form ─────────────────────────────────────────
        else:
            is_edit = existing_row is not None

            default_t1   = int(existing_row["Team1_Score"]) if is_edit and pd.notna(existing_row["Team1_Score"]) else 0
            default_t2   = int(existing_row["Team2_Score"]) if is_edit and pd.notna(existing_row["Team2_Score"]) else 0
            default_pen  = str(existing_row.get("Pen_Winner", "None")).strip() if is_edit else "None"
            default_motm = str(existing_row.get("MOTM", "N/A")).strip()        if is_edit else "N/A"

            if is_edit:
                st.info(f"Editing your prediction for **{match_name}**. Submit to overwrite.")

            col1, col2 = st.columns(2)
            t1_score = col1.number_input(
                f"{team1} Score", min_value=0, max_value=25, step=1, value=default_t1
            )
            t2_score = col2.number_input(
                f"{team2} Score", min_value=0, max_value=25, step=1, value=default_t2
            )

            # Penalty winner
            pen_winner = "None"
            if t1_score == t2_score:
                pen_opts  = ["None", team1, team2]
                pen_idx   = pen_opts.index(default_pen) if default_pen in pen_opts else 0
                pen_winner = st.selectbox(
                    "Penalty Shootout Winner (required for draws)",
                    pen_opts, index=pen_idx
                )
            else:
                st.caption("Match is not a draw — penalty selection disabled.")

            # ── MOTM ──────────────────────────────────────────────────────
            motm_choice = "N/A"
            if match_key not in MOTM_DISABLED_MATCHES:
                squad1, squad2 = get_combined_squad(team1, team2)
                st.markdown("---")
                st.markdown("**MOTM prediction (+1 bonus point)**")
                st.caption(
                    f"Pick one player from either {team1} or {team2}. "
                    "Selecting from one team disables the other."
                )

                NO_PICK = "-- No pick --"
                t1_opts = [NO_PICK] + squad1
                t2_opts = [NO_PICK] + squad2

                # Restore saved MOTM pick when editing
                if default_motm in squad1:
                    t1_def, t2_def = t1_opts.index(default_motm), 0
                elif default_motm in squad2:
                    t1_def, t2_def = 0, t2_opts.index(default_motm)
                else:
                    t1_def, t2_def = 0, 0

                mc1, mc2 = st.columns(2)

                # Disabled when the other team already has a pick
                t1_motm = mc1.selectbox(
                    team1, t1_opts,
                    index=t1_def,
                    key="motm_t1",
                    disabled=(t2_def > 0),
                )
                t2_motm = mc2.selectbox(
                    team2, t2_opts,
                    index=t2_def,
                    key="motm_t2",
                    disabled=(t1_def > 0),
                )

                t1_picked = t1_motm != NO_PICK
                t2_picked = t2_motm != NO_PICK

                if t1_picked and not t2_picked:
                    motm_choice = t1_motm
                    st.caption(f"MOTM pick: **{motm_choice}** ({team1})")
                elif t2_picked and not t1_picked:
                    motm_choice = t2_motm
                    st.caption(f"MOTM pick: **{motm_choice}** ({team2})")
                elif not t1_picked and not t2_picked:
                    motm_choice = "N/A"
                else:
                    motm_choice = "BOTH_SELECTED"
                    st.error("Select MOTM from only one team, not both.")

            else:
                st.caption("MOTM prediction not available for this match.")

            # ── Submit / Cancel ────────────────────────────────────────────
            btn_label = "Update Prediction" if is_edit else "Submit Prediction"
            col_btn, col_cancel = st.columns([2, 1])
            submitted = col_btn.button(btn_label)
            if is_edit and col_cancel.button("Cancel"):
                st.session_state.editing_match = None
                st.rerun()

            if submitted:
                if t1_score == t2_score and pen_winner == "None":
                    st.error("Draws require a penalty shootout winner.")
                elif motm_choice == "BOTH_SELECTED":
                    st.error("Select MOTM from only one team's dropdown, not both.")
                else:
                    payload = {
                        "action":     "edit" if is_edit else "predict",
                        "user":       username,
                        "match":      match_name,
                        "t1_score":   int(t1_score),
                        "t2_score":   int(t2_score),
                        "pen_winner": pen_winner,
                        "motm":       motm_choice,
                        "scorers":    "N/A",
                    }
                    ok, message = post_to_backend(payload)
                    if ok:
                        st.session_state.just_submitted.add(match_name)
                        st.session_state.editing_match = None
                        st.success(message)
                        time.sleep(1.0)
                        st.rerun()
                    else:
                        st.error(message)


# ══════════════════════════════════════════════════════════════════════════
# TAB 2 — Leaderboard
# ══════════════════════════════════════════════════════════════════════════
with tab2:
    st.header("Leaderboard")

    public_df = df_existing[
        df_existing["User"].str.strip().str.lower() != "admin_result"
    ].copy()

    if not public_df.empty:
        public_df["user_key"] = public_df["User"].str.strip().str.lower()
        leaderboard = (
            public_df.groupby("user_key")
            .agg(Points=("Points", "sum"), User=("User", "first"))
            .reset_index(drop=True)
        )
        leaderboard = (
            leaderboard[["User", "Points"]]
            .sort_values(by="Points", ascending=False)
            .reset_index(drop=True)
        )
        leaderboard.insert(0, "Rank", [f"{i+1}." for i in range(len(leaderboard))])
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
                (item for item in FIXTURES
                 if item["match"].strip().lower() == str(m).strip().lower()),
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
                ].copy()
                display_df = match_public_df.drop(columns=["Scorers", "Timestamp"], errors="ignore")
                st.dataframe(display_df, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════
# TAB 3 — Admin Panel
# ══════════════════════════════════════════════════════════════════════════
with tab3:
    st.header("Admin Panel")
    admin_pass = st.text_input("Admin Password", type="password")

    if admin_pass and admin_pass != ADMIN_PASSWORD:
        st.error("Incorrect password.")
    elif admin_pass == ADMIN_PASSWORD:
        past_fixtures = [fix for fix in FIXTURES if current_time > fix["kickoff"]]

        if not past_fixtures:
            st.info("No matches have kicked off yet.")
        else:
            graded_matches = set()
            if not df_existing.empty:
                graded_matches = set(
                    df_existing[df_existing["User"].str.strip().str.lower() == "admin_result"]["Match"]
                    .str.strip().str.lower()
                )

            labels = []
            for fix in past_fixtures:
                tag = " (graded)" if fix["match"].strip().lower() in graded_matches else " (needs grading)"
                labels.append(f"{fix['match']}  |  {fix['round']}{tag}")

            selected_label   = st.selectbox("Select Match to Grade", labels)
            match_to_resolve = past_fixtures[labels.index(selected_label)]["match"]
            team1, team2     = match_to_resolve.split(" vs ")
            already_graded   = match_to_resolve.strip().lower() in graded_matches

            if already_graded:
                # Pull the saved result from the sheet and display it read-only
                admin_row = df_existing[
                    (df_existing["User"].str.strip().str.lower() == "admin_result")
                    & (df_existing["Match"].str.strip().str.lower() == match_to_resolve.strip().lower())
                ]
                if not admin_row.empty:
                    row      = admin_row.iloc[0]
                    res_t1   = int(float(row["Team1_Score"])) if pd.notna(row["Team1_Score"]) else "?"
                    res_t2   = int(float(row["Team2_Score"])) if pd.notna(row["Team2_Score"]) else "?"
                    res_pen  = str(row.get("Pen_Winner", "N/A")).strip()
                    res_motm = str(row.get("MOTM", "N/A")).strip()

                    pen_str  = f"  |  Pens: **{res_pen}**"  if res_pen  not in ("None", "N/A", "nan", "") else ""
                    motm_str = f"  |  MOTM: **{res_motm}**" if res_motm not in ("N/A", "nan", "")         else ""
                    st.success(
                        f"This match has already been graded: "
                        f"**{team1} {res_t1} - {res_t2} {team2}**{pen_str}{motm_str}"
                    )
                else:
                    st.success("This match has already been graded.")
            else:
                col1, col2 = st.columns(2)
                act_t1 = col1.number_input(f"{team1} Final Score", min_value=0, max_value=25, step=1, value=0)
                act_t2 = col2.number_input(f"{team2} Final Score", min_value=0, max_value=25, step=1, value=0)

                act_pen = "None"
                if act_t1 == act_t2:
                    act_pen = st.selectbox("Penalty Shootout Winner (draw)", ["None", team1, team2])
                else:
                    st.caption("Not a draw — penalty selection disabled.")

                act_motm = "N/A"
                if match_to_resolve.strip().lower() not in MOTM_DISABLED_MATCHES:
                    sq1, sq2    = get_combined_squad(team1, team2)
                    all_players = ["N/A"] + sorted(sq1 + sq2)
                    act_motm    = st.selectbox("Official MOTM", all_players)

                st.caption(
                    "Scoring: exact score = 3 pts  |  correct result, wrong score = 2 pts  |  "
                    "correct draw, wrong score = 1 pt  |  "
                    "correct penalty winner (draws only) = +1 pt  |  correct MOTM = +1 pt"
                )

                if st.button("Submit Official Results"):
                    if act_t1 == act_t2 and act_pen == "None":
                        st.error("This is a draw — select the penalty shootout winner.")
                    else:
                        payload = {
                            "action":   "grade",
                            "match":    match_to_resolve,
                            "act_t1":   int(act_t1),
                            "act_t2":   int(act_t2),
                            "act_pen":  act_pen,
                            "act_motm": act_motm,
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
