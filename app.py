import io
import json
import time
from datetime import datetime, timedelta

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

MOTM_DISABLED_MATCHES = {
    "canada vs morocco",
    "paraguay vs france",
}

EDIT_CUTOFF_MINUTES = 15   # edits blocked this many minutes before kickoff


def get_secret(key, default=""):
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


WEBAPP_URL     = get_secret("WEBAPP_URL",     "https://script.google.com/macros/s/AKfycbxnGXFa4VpEJFmIwcuOACjo32uKRb67DAU4luczLqgnkV-wplBnG1IxdK64TdnqCc6Z/exec")
SHEET_ID       = get_secret("SHEET_ID",       "1rzyPqXioFz2wj_Aby9kuFBafX0wsADvbM-QQTAeGJv8")
CSV_URL        = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Predictions"
API_SECRET     = get_secret("API_SECRET",     "Kenkanekii14033!!")
ADMIN_PASSWORD = get_secret("ADMIN_PASSWORD", "worldcup2026")

PINS_SHEET_ID  = SHEET_ID
PINS_CSV_URL   = f"https://docs.google.com/spreadsheets/d/{PINS_SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Pins"

if not API_SECRET:
    st.sidebar.warning("API_SECRET is not set. Requests will be rejected.")


def now_ist():
    return datetime.now(IST)


# ── Data loading ────────────────────────────────────────────────────────────
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
                f"Sheet has {len(df.columns)} columns, expected {len(EXPECTED_COLS)}."
            )
        for col in ["Team1_Score", "Team2_Score", "Points"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["Points"] = df["Points"].fillna(0)
        df["User"]   = df["User"].astype(str)
        df["Match"]  = df["Match"].astype(str)
        return df, None
    except Exception as e:
        return pd.DataFrame(columns=EXPECTED_COLS), str(e)


def load_pins():
    """Returns dict {username_lower: pin_str}. Silent on failure."""
    url = f"{PINS_CSV_URL}&cachebust={int(time.time() * 1000)}"
    try:
        resp = requests.get(url, timeout=8, headers={"Cache-Control": "no-cache"})
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text))
        if df.shape[1] >= 2:
            df.columns = ["User", "PIN"] + list(df.columns[2:])
            return {str(r["User"]).strip().lower(): str(r["PIN"]).strip() for _, r in df.iterrows()}
    except Exception:
        pass
    return {}


def post_to_backend(payload):
    # In demo mode, silently succeed without hitting any real endpoint
    if st.session_state.get("demo_mode", False):
        action = payload.get("action", "")
        msgs = {
            "predict": "Demo: prediction saved (not really — demo mode is on).",
            "edit":    "Demo: prediction updated (not really — demo mode is on).",
            "grade":   "Demo: match graded (not really — demo mode is on).",
            "set_pin": "Demo: PIN set (not really — demo mode is on).",
        }
        return True, msgs.get(action, "Demo: action simulated.")

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


# ── Points explainer ────────────────────────────────────────────────────────
def explain_points(pred_row, admin_row):
    """Return a human-readable string explaining why a user got their points."""
    try:
        p1 = int(float(pred_row["Team1_Score"]))
        p2 = int(float(pred_row["Team2_Score"]))
        a1 = int(float(admin_row["Team1_Score"]))
        a2 = int(float(admin_row["Team2_Score"]))
        pen_guess  = str(pred_row.get("Pen_Winner", "None")).strip()
        motm_guess = str(pred_row.get("MOTM", "N/A")).strip()
        act_pen    = str(admin_row.get("Pen_Winner", "None")).strip()
        act_motm   = str(admin_row.get("MOTM", "N/A")).strip()

        parts = []
        base  = 0
        if p1 == a1 and p2 == a2:
            base = 3; parts.append("Exact score +3")
        elif (p1 > p2 and a1 > a2) or (p1 < p2 and a1 < a2):
            base = 2; parts.append("Correct result +2")
        elif p1 == p2 and a1 == a2:
            base = 1; parts.append("Correct draw +1")
        else:
            parts.append("Wrong result +0")

        if a1 == a2 and act_pen not in ("None", "N/A", "nan", ""):
            if pen_guess == act_pen:
                parts.append("Correct penalties +1")
            else:
                parts.append("Wrong penalties +0")

        if act_motm not in ("N/A", "nan", ""):
            if motm_guess == act_motm:
                parts.append("Correct MOTM +1")
            else:
                parts.append("Wrong MOTM +0")

        return "  |  ".join(parts)
    except Exception:
        return ""


# ── Demo mode ───────────────────────────────────────────────────────────────
# When the tournament is over the live sheet has no open matches, so the app
# looks blank to anyone visiting the GitHub/Streamlit link. Demo mode swaps
# in a realistic frozen dataset so every tab renders as if the QFs are live.

def build_demo_data():
    """
    Returns (df, pins_db, fixtures, current_time, admin_results_map) for a
    convincing mid-tournament snapshot:
      - 4 RO16 matches fully graded
      - 2 QFs fully graded
      - 1 QF open for prediction (Portugal vs France)
      - 1 QF upcoming
      - 6 realistic players with varied scores and MOTM picks
    The fake current_time is set to 3 hours before Portugal vs France kickoff
    so the countdown and edit-lock logic all behave realistically.
    """
    import pytz
    from datetime import datetime
    IST = pytz.timezone("Asia/Kolkata")

    # Fake current time: well before the open QF so predictions are still open
    fake_now = IST.localize(datetime(2026, 7, 11, 18, 0, 0))

    # Minimal fixture list (just enough to show all tabs working)
    fixtures = [
        {"match": "Brazil vs Norway",       "kickoff": IST.localize(datetime(2026, 7, 6,  1, 30)), "round": "Round of 16"},
        {"match": "Mexico vs England",       "kickoff": IST.localize(datetime(2026, 7, 6,  5, 30)), "round": "Round of 16"},
        {"match": "Portugal vs Spain",       "kickoff": IST.localize(datetime(2026, 7, 7,  0, 30)), "round": "Round of 16"},
        {"match": "USA vs Belgium",          "kickoff": IST.localize(datetime(2026, 7, 7,  5, 30)), "round": "Round of 16"},
        {"match": "Brazil vs England",       "kickoff": IST.localize(datetime(2026, 7, 10, 1, 30)), "round": "Quarterfinal"},
        {"match": "Portugal vs USA",         "kickoff": IST.localize(datetime(2026, 7, 11, 0, 30)), "round": "Quarterfinal"},
        {"match": "Portugal vs France",      "kickoff": IST.localize(datetime(2026, 7, 11, 21, 30)), "round": "Quarterfinal"},
        {"match": "Argentina vs Switzerland","kickoff": IST.localize(datetime(2026, 7, 12, 6, 30)), "round": "Quarterfinal"},
    ]

    ts = "2026-07-06 10:00:00"
    rows = [
        # ── RO16: Brazil 2-1 Norway  (MOTM: Vinicius Junior)
        ["2026-07-06 03:00:00","ADMIN_RESULT","Brazil vs Norway",       2,1,"None",       "Vinicius Junior","N/A",0],
        [ts,"Rudrajit",         "Brazil vs Norway",       2,1,"None",       "Vinicius Junior","N/A",5],  # exact+MOTM
        [ts,"Aniruddha Dey",    "Brazil vs Norway",       2,0,"None",       "Raphinha",      "N/A",2],  # correct result
        [ts,"Indranil",         "Brazil vs Norway",       3,1,"None",       "Vinicius Junior","N/A",3],  # correct result+MOTM
        [ts,"Arithromycin",     "Brazil vs Norway",       1,0,"None",       "Erling Haaland","N/A",2],  # correct result
        [ts,"Supreme leader",   "Brazil vs Norway",       0,1,"None",       "N/A",           "N/A",0],  # wrong
        [ts,"Kaustav",          "Brazil vs Norway",       2,1,"None",       "N/A",           "N/A",3],  # exact

        # ── RO16: England 1-1 (pens: England) Mexico  (MOTM: Jude Bellingham)
        ["2026-07-06 07:00:00","ADMIN_RESULT","Mexico vs England",       1,1,"England",      "Jude Bellingham","N/A",0],
        [ts,"Rudrajit",         "Mexico vs England",       0,1,"England",   "Jude Bellingham","N/A",3],  # correct result+pen+MOTM
        [ts,"Aniruddha Dey",    "Mexico vs England",       1,1,"England",   "Jude Bellingham","N/A",5],  # exact+pen+MOTM
        [ts,"Indranil",         "Mexico vs England",       0,2,"None",      "N/A",           "N/A",0],  # wrong
        [ts,"Arithromycin",     "Mexico vs England",       1,1,"Mexico",    "N/A",           "N/A",1],  # correct draw, wrong pen
        [ts,"Supreme leader",   "Mexico vs England",       2,1,"None",      "N/A",           "N/A",0],  # wrong
        [ts,"Kaustav",          "Mexico vs England",       1,1,"England",   "N/A",           "N/A",2],  # correct draw+pen

        # ── RO16: Spain 3-1 Portugal  (MOTM: Lamine Yamal)
        ["2026-07-07 02:00:00","ADMIN_RESULT","Portugal vs Spain",       1,3,"None",         "Lamine Yamal","N/A",0],
        [ts,"Rudrajit",         "Portugal vs Spain",       1,3,"None",     "Lamine Yamal",  "N/A",4],  # exact+MOTM
        [ts,"Aniruddha Dey",    "Portugal vs Spain",       0,2,"None",     "Nico Williams", "N/A",2],  # correct result
        [ts,"Indranil",         "Portugal vs Spain",       1,2,"None",     "Lamine Yamal",  "N/A",3],  # correct result+MOTM
        [ts,"Arithromycin",     "Portugal vs Spain",       2,1,"None",     "N/A",           "N/A",0],  # wrong
        [ts,"Supreme leader",   "Portugal vs Spain",       0,3,"None",     "N/A",           "N/A",2],  # correct result
        [ts,"Kaustav",          "Portugal vs Spain",       1,3,"None",     "N/A",           "N/A",3],  # exact

        # ── RO16: USA 0-0 (pens: Belgium) Belgium  (MOTM: Kevin De Bruyne)
        ["2026-07-07 07:00:00","ADMIN_RESULT","USA vs Belgium",          0,0,"Belgium",      "Kevin De Bruyne","N/A",0],
        [ts,"Rudrajit",         "USA vs Belgium",          0,0,"Belgium",  "Kevin De Bruyne","N/A",4],  # correct draw+pen+MOTM
        [ts,"Aniruddha Dey",    "USA vs Belgium",          1,0,"None",     "N/A",           "N/A",0],  # wrong
        [ts,"Indranil",         "USA vs Belgium",          0,0,"USA",      "N/A",           "N/A",1],  # correct draw, wrong pen
        [ts,"Arithromycin",     "USA vs Belgium",          0,1,"None",     "N/A",           "N/A",0],  # wrong
        [ts,"Supreme leader",   "USA vs Belgium",          0,0,"Belgium",  "N/A",           "N/A",2],  # correct draw+pen
        [ts,"Kaustav",          "USA vs Belgium",          0,0,"Belgium",  "Kevin De Bruyne","N/A",4],  # correct draw+pen+MOTM

        # ── QF1: Brazil 2-0 England  (MOTM: Vinicius Junior)
        ["2026-07-10 03:00:00","ADMIN_RESULT","Brazil vs England",       2,0,"None",         "Vinicius Junior","N/A",0],
        [ts,"Rudrajit",         "Brazil vs England",       2,0,"None",     "Vinicius Junior","N/A",4],  # exact+MOTM
        [ts,"Aniruddha Dey",    "Brazil vs England",       1,0,"None",     "N/A",           "N/A",2],  # correct result
        [ts,"Indranil",         "Brazil vs England",       3,1,"None",     "N/A",           "N/A",2],  # correct result
        [ts,"Arithromycin",     "Brazil vs England",       2,0,"None",     "N/A",           "N/A",3],  # exact
        [ts,"Supreme leader",   "Brazil vs England",       0,1,"None",     "N/A",           "N/A",0],  # wrong
        [ts,"Kaustav",          "Brazil vs England",       2,1,"None",     "N/A",           "N/A",2],  # correct result

        # ── QF2: Portugal 1-0 USA  (MOTM: Bruno Fernandes)
        ["2026-07-11 02:00:00","ADMIN_RESULT","Portugal vs USA",         1,0,"None",         "Bruno Fernandes","N/A",0],
        [ts,"Rudrajit",         "Portugal vs USA",         1,0,"None",     "Bruno Fernandes","N/A",4],  # exact+MOTM
        [ts,"Aniruddha Dey",    "Portugal vs USA",         2,0,"None",     "N/A",           "N/A",2],  # correct result
        [ts,"Indranil",         "Portugal vs USA",         1,0,"None",     "N/A",           "N/A",3],  # exact
        [ts,"Arithromycin",     "Portugal vs USA",         0,1,"None",     "N/A",           "N/A",0],  # wrong
        [ts,"Supreme leader",   "Portugal vs USA",         1,1,"Portugal", "N/A",           "N/A",0],  # wrong
        [ts,"Kaustav",          "Portugal vs USA",         1,0,"None",     "Bruno Fernandes","N/A",4],  # exact+MOTM

        # ── QF3: Portugal vs France — OPEN, predictions already submitted
        [ts,"Rudrajit",         "Portugal vs France",      2,1,"None",     "Kylian Mbappe",  "N/A",0],
        [ts,"Aniruddha Dey",    "Portugal vs France",      1,2,"None",     "Kylian Mbappe",  "N/A",0],
        [ts,"Indranil",         "Portugal vs France",      1,1,"Portugal", "Cristiano Ronaldo","N/A",0],
        [ts,"Arithromycin",     "Portugal vs France",      0,1,"None",     "Kylian Mbappe",  "N/A",0],
        [ts,"Supreme leader",   "Portugal vs France",      2,0,"None",     "N/A",           "N/A",0],
        [ts,"Kaustav",          "Portugal vs France",      1,2,"None",     "N/A",           "N/A",0],
    ]

    cols = ["Timestamp","User","Match","Team1_Score","Team2_Score","Pen_Winner","MOTM","Scorers","Points"]
    df   = pd.DataFrame(rows, columns=cols)
    for c in ["Team1_Score","Team2_Score","Points"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["Points"]    = df["Points"].fillna(0)
    df["User"]      = df["User"].astype(str)
    df["Match"]     = df["Match"].astype(str)

    admin_map = {}
    for _, row in df[df["User"] == "ADMIN_RESULT"].iterrows():
        admin_map[row["Match"].strip().lower()] = row

    # Fake PIN db — demo user logs in without a real PIN
    fake_pins = {"demo": "0000"}

    return df, fake_pins, fixtures, fake_now, admin_map


# ── Bootstrap ───────────────────────────────────────────────────────────────
df_existing, load_err = load_predictions()
if load_err:
    st.sidebar.error(f"Could not load predictions: {load_err}")

pins_db      = load_pins()
FIXTURES     = get_active_fixtures(df_existing)
current_time = now_ist()

# Build a map of graded match results for quick lookup
admin_results_map = {}
if not df_existing.empty:
    for _, row in df_existing[df_existing["User"].str.strip().str.lower() == "admin_result"].iterrows():
        admin_results_map[row["Match"].strip().lower()] = row

graded_matches = set(admin_results_map.keys())

st.title("World Cup 2026 Predictor")

# ── Session state ───────────────────────────────────────────────────────────
for key, default in [
    ("username", None), ("just_submitted", set()),
    ("editing_match", None), ("pin_verified", False),
    ("confirm_grade", None), ("demo_mode", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Sidebar: demo toggle + refresh ──────────────────────────────────────────
st.sidebar.header("User Profile")
if st.sidebar.button("Refresh data"):
    st.rerun()

st.sidebar.markdown("---")
demo_on = st.sidebar.toggle("Demo mode", value=st.session_state.demo_mode, key="demo_toggle")
if demo_on != st.session_state.demo_mode:
    st.session_state.demo_mode      = demo_on
    st.session_state.username       = None
    st.session_state.pin_verified   = False
    st.session_state.just_submitted = set()
    st.session_state.editing_match  = None
    st.rerun()

if st.session_state.demo_mode:
    df_existing, pins_db, FIXTURES, current_time, admin_results_map = build_demo_data()
    graded_matches = set(admin_results_map.keys())
    st.info(
        "**Demo mode is on.** This is a realistic mid-tournament snapshot with "
        "fictional data. Log in as **Demo** with PIN **0000** to explore every feature. "
        "Nothing you do here is saved.",
        icon="\u2139\ufe0f",
    )

upcoming = [
    fix for fix in FIXTURES
    if current_time < fix["kickoff"]
]
if upcoming:
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Upcoming deadlines**")
    for fix in upcoming[:5]:
        tl     = fix["kickoff"] - current_time
        d, h   = tl.days, tl.seconds // 3600
        m      = (tl.seconds // 60) % 60
        cutoff = fix["kickoff"] - timedelta(minutes=EDIT_CUTOFF_MINUTES)
        locked = current_time >= cutoff
        lock_str = "  (edit locked)" if locked else ""
        st.sidebar.caption(f"{fix['match']}\n{d}d {h}h {m}m{lock_str}")

# ── Login with PIN ───────────────────────────────────────────────────────────
if not st.session_state.username:
    input_name = st.sidebar.text_input("Enter your name:").strip()
    if st.sidebar.button("Login"):
        key_lower = input_name.lower()
        if not input_name:
            st.sidebar.error("Name cannot be empty.")
        elif key_lower == "admin_result":
            st.sidebar.error("Reserved username.")
        else:
            # Snap to canonical casing
            canonical = input_name
            if not df_existing.empty:
                existing_users = df_existing[df_existing["User"].str.lower() != "admin_result"]["User"]
                hit = existing_users[existing_users.str.lower() == key_lower]
                if not hit.empty:
                    canonical = hit.iloc[0]
            st.session_state.username     = canonical
            st.session_state.pin_verified = False
            st.rerun()
    st.info("Enter your name in the sidebar and click Login to continue.")
    st.stop()

username     = st.session_state.username
username_key = username.strip().lower()

# ── PIN gate ─────────────────────────────────────────────────────────────────
if not st.session_state.pin_verified:
    st.sidebar.success(f"Logged in as: **{username}**")
    is_new_user = username_key not in pins_db

    st.subheader("PIN Verification")
    if is_new_user:
        st.info(f"Welcome, **{username}**! Set a 4-digit PIN to secure your account.")
        pin_input = st.text_input("Choose a 4-digit PIN", type="password", max_chars=4)
        if st.button("Set PIN & Continue"):
            if len(pin_input) == 4 and pin_input.isdigit():
                ok, msg = post_to_backend({"action": "set_pin", "user": username, "pin": pin_input})
                if ok:
                    st.session_state.pin_verified = True
                    st.rerun()
                else:
                    st.error(f"Could not save PIN: {msg}")
            else:
                st.error("PIN must be exactly 4 digits.")
    else:
        st.info(f"Welcome back, **{username}**! Enter your PIN to continue.")
        pin_input = st.text_input("Enter your PIN", type="password", max_chars=4)
        if st.button("Verify PIN"):
            if pins_db.get(username_key) == pin_input:
                st.session_state.pin_verified = True
                st.rerun()
            else:
                st.error("Incorrect PIN.")
    st.stop()

st.sidebar.success(f"Logged in as: **{username}**")

tab1, tab2, tab3 = st.tabs(["Prediction", "Leaderboard", "Admin Panel"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Prediction
# ══════════════════════════════════════════════════════════════════════════════
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

        # Edit cutoff
        edit_cutoff   = active_fixture["kickoff"] - timedelta(minutes=EDIT_CUTOFF_MINUTES)
        edits_locked  = current_time >= edit_cutoff
        if edits_locked:
            st.warning(f"Predictions are locked {EDIT_CUTOFF_MINUTES} minutes before kickoff.")

        # Find existing prediction
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

        # ── Already predicted ──────────────────────────────────────────────
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

            if not edits_locked:
                if st.button("Edit my prediction"):
                    st.session_state.editing_match = match_name
                    st.rerun()
            else:
                st.caption("Editing is locked — too close to kickoff.")

        # ── Prediction / edit form ─────────────────────────────────────────
        else:
            is_edit = existing_row is not None

            default_t1   = int(existing_row["Team1_Score"]) if is_edit and pd.notna(existing_row["Team1_Score"]) else 0
            default_t2   = int(existing_row["Team2_Score"]) if is_edit and pd.notna(existing_row["Team2_Score"]) else 0
            default_pen  = str(existing_row.get("Pen_Winner", "None")).strip() if is_edit else "None"
            default_motm = str(existing_row.get("MOTM",       "N/A" )).strip() if is_edit else "N/A"

            if is_edit:
                st.info(f"Editing your prediction for **{match_name}**. Submit to overwrite.")

            col1, col2 = st.columns(2)
            t1_score = col1.number_input(f"{team1} Score", min_value=0, max_value=25, step=1, value=default_t1)
            t2_score = col2.number_input(f"{team2} Score", min_value=0, max_value=25, step=1, value=default_t2)

            pen_winner = "None"
            if t1_score == t2_score:
                pen_opts   = ["None", team1, team2]
                pen_idx    = pen_opts.index(default_pen) if default_pen in pen_opts else 0
                pen_winner = st.selectbox("Penalty Shootout Winner (required for draws)", pen_opts, index=pen_idx)
            else:
                st.caption("Match is not a draw — penalty selection disabled.")

            # MOTM
            motm_choice = "N/A"
            if match_key not in MOTM_DISABLED_MATCHES:
                squad1, squad2 = get_combined_squad(team1, team2)
                st.markdown("---")
                st.markdown("**MOTM prediction (+1 bonus point)**")
                st.caption(f"Pick one player from either {team1} or {team2}.")

                NO_PICK = "-- No pick --"
                t1_opts = [NO_PICK] + squad1
                t2_opts = [NO_PICK] + squad2

                if default_motm in squad1:
                    t1_def, t2_def = t1_opts.index(default_motm), 0
                elif default_motm in squad2:
                    t1_def, t2_def = 0, t2_opts.index(default_motm)
                else:
                    t1_def, t2_def = 0, 0

                mc1, mc2 = st.columns(2)
                t1_motm = mc1.selectbox(team1, t1_opts, index=t1_def, key="motm_t1", disabled=(t2_def > 0))
                t2_motm = mc2.selectbox(team2, t2_opts, index=t2_def, key="motm_t2", disabled=(t1_def > 0))

                t1_picked, t2_picked = t1_motm != NO_PICK, t2_motm != NO_PICK
                if t1_picked and not t2_picked:
                    motm_choice = t1_motm
                    st.caption(f"MOTM pick: **{motm_choice}** ({team1})")
                elif t2_picked and not t1_picked:
                    motm_choice = t2_motm
                    st.caption(f"MOTM pick: **{motm_choice}** ({team2})")
                elif t1_picked and t2_picked:
                    motm_choice = "BOTH_SELECTED"
                    st.error("Select MOTM from only one team, not both.")
            else:
                st.caption("MOTM prediction not available for this match.")

            btn_label = "Update Prediction" if is_edit else "Submit Prediction"
            col_btn, col_cancel = st.columns([2, 1])
            submitted = col_btn.button(btn_label)
            if is_edit and col_cancel.button("Cancel"):
                st.session_state.editing_match = None
                st.rerun()

            if submitted:
                if edits_locked:
                    st.error("Predictions are locked — too close to kickoff.")
                elif t1_score == t2_score and pen_winner == "None":
                    st.error("Draws require a penalty shootout winner.")
                elif motm_choice == "BOTH_SELECTED":
                    st.error("Select MOTM from only one team's dropdown, not both.")
                else:
                    payload = {
                        "action": "edit" if is_edit else "predict",
                        "user": username, "match": match_name,
                        "t1_score": int(t1_score), "t2_score": int(t2_score),
                        "pen_winner": pen_winner, "motm": motm_choice, "scorers": "N/A",
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


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Leaderboard  (sub-tabs)
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    lb_tab, my_tab, all_tab = st.tabs(["Leaderboard", "My Predictions", "All Predictions"])

    public_df = df_existing[df_existing["User"].str.strip().str.lower() != "admin_result"].copy()

    # Pre-compute per-user aggregates once
    if not public_df.empty:
        public_df["user_key"] = public_df["User"].str.strip().str.lower()

    # ── 2a: Leaderboard ────────────────────────────────────────────────────
    with lb_tab:
        if public_df.empty:
            st.info("No scores calculated yet.")
        else:
            # ── Compute exact scores properly ──────────────────────────────
            # "Exact score" means the predicted scoreline matches the official
            # result exactly. We can't derive this from Points alone (e.g.
            # 2pts result + 1pt MOTM = 3pts but is NOT an exact score).
            # We join each user's predictions against the admin result rows.

            graded_ordered = [
                fix["match"] for fix in FIXTURES
                if fix["match"].strip().lower() in graded_matches
            ]

            def count_exact(user_key):
                count = 0
                for m_key, admin_row in admin_results_map.items():
                    pred = public_df[
                        (public_df["user_key"] == user_key)
                        & (public_df["Match"].str.strip().str.lower() == m_key)
                    ]
                    if pred.empty:
                        continue
                    p = pred.iloc[0]
                    try:
                        if (int(float(p["Team1_Score"])) == int(float(admin_row["Team1_Score"])) and
                                int(float(p["Team2_Score"])) == int(float(admin_row["Team2_Score"]))):
                            count += 1
                    except (ValueError, TypeError):
                        pass
                return count

            def count_correct_results(user_key):
                count = 0
                for m_key, admin_row in admin_results_map.items():
                    pred = public_df[
                        (public_df["user_key"] == user_key)
                        & (public_df["Match"].str.strip().str.lower() == m_key)
                    ]
                    if pred.empty:
                        continue
                    p = pred.iloc[0]
                    try:
                        p1 = int(float(p["Team1_Score"]))
                        p2 = int(float(p["Team2_Score"]))
                        a1 = int(float(admin_row["Team1_Score"]))
                        a2 = int(float(admin_row["Team2_Score"]))
                        if (p1 > p2 and a1 > a2) or (p1 < p2 and a1 < a2) or (p1 == p2 and a1 == a2):
                            count += 1
                    except (ValueError, TypeError):
                        pass
                return count

            agg = (
                public_df.groupby("user_key")
                .agg(
                    Points = ("Points", "sum"),
                    User   = ("User",   "first"),
                    Played = ("Points", "count"),
                )
                .reset_index()   # keeps user_key as a column
            )

            agg["Exact"]         = agg["user_key"].apply(count_exact)
            agg["CorrectResult"] = agg["user_key"].apply(count_correct_results)

            # Tiebreaker: Points desc, Exact scores desc, Correct results desc
            agg = agg.sort_values(
                by=["Points", "Exact", "CorrectResult"],
                ascending=[False, False, False]
            ).reset_index(drop=True)

            # Form: actual points scored in each of the last 3 graded matches
            def form_str(user_key):
                last3 = graded_ordered[-3:]
                parts = []
                for m in last3:
                    row = public_df[
                        (public_df["user_key"] == user_key)
                        & (public_df["Match"].str.strip().str.lower() == m.strip().lower())
                    ]
                    parts.append(str(int(row.iloc[0]["Points"])) if not row.empty else "-")
                return "  ".join(parts) if parts else "-"

            agg["Last 3"] = agg["user_key"].apply(form_str)
            agg["Rank"]   = [f"{i+1}." for i in range(len(agg))]

            display_lb = agg[["Rank", "User", "Points", "Exact", "Last 3"]].rename(
                columns={"Exact": "Exact Scores"}
            )
            st.dataframe(display_lb, use_container_width=True, hide_index=True)

            # ── Points breakdown grid ──────────────────────────────────────
            st.markdown("---")
            st.subheader("Points breakdown by match")
            played_matches = [
                fix["match"] for fix in FIXTURES
                if fix["match"].strip().lower() in graded_matches
            ]
            if not played_matches:
                st.info("No matches graded yet.")
            else:
                def abbrev(match_str):
                    """'Brazil vs Norway' -> 'BRA-NOR'"""
                    if " vs " not in match_str:
                        return match_str[:6].upper()
                    t1, t2 = match_str.split(" vs ", 1)
                    return f"{t1.strip()[:3].upper()}-{t2.strip()[:3].upper()}"

                all_users = agg["User"].tolist()
                grid = {"Player": all_users}
                col_legend = []
                for m in played_matches:
                    short = abbrev(m)
                    col_legend.append(f"**{short}** = {m}")
                    col_vals = []
                    for user in all_users:
                        ukey = user.strip().lower()
                        row  = public_df[
                            (public_df["user_key"] == ukey)
                            & (public_df["Match"].str.strip().str.lower() == m.strip().lower())
                        ]
                        col_vals.append(int(row.iloc[0]["Points"]) if not row.empty else "-")
                    grid[short] = col_vals
                grid["Total"] = [int(agg[agg["User"] == u]["Points"].values[0]) for u in all_users]
                st.dataframe(pd.DataFrame(grid), use_container_width=True, hide_index=True)
                st.caption("  |  ".join(col_legend))

    # ── 2b: My Predictions ────────────────────────────────────────────────
    with my_tab:
        st.subheader(f"Your predictions — {username}")

        my_rows = public_df[public_df["user_key"] == username_key].copy() if not public_df.empty else pd.DataFrame()

        if my_rows.empty:
            st.info("You have not submitted any predictions yet.")
        else:
            total_pts = int(my_rows["Points"].sum())
            played_ct = len(my_rows[my_rows["Match"].str.strip().str.lower().isin(graded_matches)])
            pending_ct = len(my_rows) - played_ct
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Points", total_pts)
            c2.metric("Matches Graded", played_ct)
            c3.metric("Predictions Pending", pending_ct)
            st.markdown("---")

            for fix in FIXTURES:
                m_key = fix["match"].strip().lower()
                row_match = my_rows[my_rows["Match"].str.strip().str.lower() == m_key]
                if row_match.empty:
                    continue
                row = row_match.iloc[0]

                t1_p   = int(float(row["Team1_Score"])) if pd.notna(row["Team1_Score"]) else "?"
                t2_p   = int(float(row["Team2_Score"])) if pd.notna(row["Team2_Score"]) else "?"
                pen_p  = str(row.get("Pen_Winner", "None")).strip()
                motm_p = str(row.get("MOTM", "N/A")).strip()
                pts    = int(row["Points"])

                pen_str  = f"  |  Pens: **{pen_p}**"  if pen_p  not in ("None", "N/A", "nan", "") else ""
                motm_str = f"  |  MOTM: **{motm_p}**" if motm_p not in ("N/A", "nan", "")         else ""

                if m_key in graded_matches:
                    admin_row = admin_results_map[m_key]
                    a1 = int(float(admin_row["Team1_Score"]))
                    a2 = int(float(admin_row["Team2_Score"]))
                    t1, t2 = fix["match"].split(" vs ")
                    explanation = explain_points(row, admin_row)

                    with st.expander(f"{fix['match']}  —  {pts} pts", expanded=False):
                        st.write(f"Your pick: **{t1} {t1_p} – {t2_p} {t2}**{pen_str}{motm_str}")
                        st.write(f"Result:    **{t1} {a1} – {a2} {t2}**")
                        st.caption(explanation)
                else:
                    with st.expander(f"{fix['match']}  —  pending", expanded=False):
                        t1, t2 = fix["match"].split(" vs ")
                        # Only show prediction if kickoff has passed
                        if current_time >= fix["kickoff"]:
                            st.write(f"Your pick: **{t1} {t1_p} – {t2_p} {t2}**{pen_str}{motm_str}")
                        else:
                            st.write(f"Your pick: **{t1} {t1_p} – {t2_p} {t2}**{pen_str}{motm_str}")
                            tl = fix["kickoff"] - current_time
                            st.caption(f"Kicks off in {tl.days}d {tl.seconds // 3600}h {(tl.seconds // 60) % 60}m")

    # ── 2c: All Predictions ───────────────────────────────────────────────
    with all_tab:
        st.subheader("All User Predictions")
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
                    ].copy()
                    display_df = match_public_df.drop(columns=["Scorers", "Timestamp"], errors="ignore")
                    st.dataframe(display_df, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Admin Panel  (sub-tabs)
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.header("Admin Panel")
    admin_pass = st.text_input("Admin Password", type="password")

    if admin_pass and admin_pass != ADMIN_PASSWORD:
        st.error("Incorrect password.")
    elif admin_pass == ADMIN_PASSWORD:
        grade_tab, audit_tab = st.tabs(["Grade Match", "Audit Log"])

        # ── 3a: Grade Match ──────────────────────────────────────────────
        with grade_tab:
            past_fixtures = [fix for fix in FIXTURES if current_time > fix["kickoff"]]

            if not past_fixtures:
                st.info("No matches have kicked off yet.")
            else:
                labels = []
                for fix in past_fixtures:
                    tag = " (graded)" if fix["match"].strip().lower() in graded_matches else " (needs grading)"
                    labels.append(f"{fix['match']}  |  {fix['round']}{tag}")

                selected_label   = st.selectbox("Select Match to Grade", labels)
                match_to_resolve = past_fixtures[labels.index(selected_label)]["match"]
                team1, team2     = match_to_resolve.split(" vs ")
                already_graded   = match_to_resolve.strip().lower() in graded_matches

                if already_graded:
                    admin_row = admin_results_map.get(match_to_resolve.strip().lower())
                    if admin_row is not None:
                        res_t1   = int(float(admin_row["Team1_Score"])) if pd.notna(admin_row["Team1_Score"]) else "?"
                        res_t2   = int(float(admin_row["Team2_Score"])) if pd.notna(admin_row["Team2_Score"]) else "?"
                        res_pen  = str(admin_row.get("Pen_Winner", "N/A")).strip()
                        res_motm = str(admin_row.get("MOTM", "N/A")).strip()
                        pen_str  = f"  |  Pens: **{res_pen}**"  if res_pen  not in ("None","N/A","nan","") else ""
                        motm_str = f"  |  MOTM: **{res_motm}**" if res_motm not in ("N/A","nan","")        else ""
                        st.success(
                            f"Already graded: **{team1} {res_t1} - {res_t2} {team2}**{pen_str}{motm_str}"
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

                    # ── Confirmation dialog ────────────────────────────────
                    if st.session_state.confirm_grade != match_to_resolve:
                        if st.button("Submit Official Results"):
                            if act_t1 == act_t2 and act_pen == "None":
                                st.error("This is a draw — select the penalty shootout winner.")
                            else:
                                st.session_state.confirm_grade = match_to_resolve
                                st.rerun()
                    else:
                        pen_conf  = f", pens: {act_pen}" if act_t1 == act_t2 and act_pen != "None" else ""
                        motm_conf = f", MOTM: {act_motm}" if act_motm != "N/A" else ""
                        st.warning(
                            f"Confirm: **{team1} {act_t1} - {act_t2} {team2}**{pen_conf}{motm_conf}?"
                        )
                        cc1, cc2 = st.columns(2)
                        if cc1.button("Yes, confirm"):
                            payload = {
                                "action": "grade", "match": match_to_resolve,
                                "act_t1": int(act_t1), "act_t2": int(act_t2),
                                "act_pen": act_pen, "act_motm": act_motm,
                            }
                            ok, message = post_to_backend(payload)
                            if ok:
                                st.session_state.confirm_grade = None
                                st.success(message)
                                time.sleep(1.0)
                                st.rerun()
                            else:
                                st.error(message)
                        if cc2.button("Cancel"):
                            st.session_state.confirm_grade = None
                            st.rerun()

        # ── 3b: Audit Log ────────────────────────────────────────────────
        with audit_tab:
            st.subheader("Graded Results Log")
            if not admin_results_map:
                st.info("No matches have been graded yet.")
            else:
                rows = []
                for fix in FIXTURES:
                    m_key = fix["match"].strip().lower()
                    if m_key not in admin_results_map:
                        continue
                    row    = admin_results_map[m_key]
                    res_t1 = int(float(row["Team1_Score"])) if pd.notna(row["Team1_Score"]) else "?"
                    res_t2 = int(float(row["Team2_Score"])) if pd.notna(row["Team2_Score"]) else "?"
                    pen    = str(row.get("Pen_Winner","N/A")).strip()
                    motm   = str(row.get("MOTM","N/A")).strip()
                    ts     = str(row.get("Timestamp","")).strip()
                    rows.append({
                        "Match":   fix["match"],
                        "Round":   fix["round"],
                        "Result":  f"{res_t1} - {res_t2}",
                        "Pens":    pen  if pen  not in ("None","N/A","nan","") else "-",
                        "MOTM":    motm if motm not in ("N/A","nan","")        else "-",
                        "Graded At": ts,
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("Enter the admin password to access the admin panel.")
