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

EDIT_CUTOFF_MINUTES = 60   # edits blocked this many minutes before kickoff


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
    ("confirm_grade", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Sidebar: upcoming deadlines ─────────────────────────────────────────────
st.sidebar.header("User Profile")
if st.sidebar.button("Refresh data"):
    st.rerun()

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
            agg = (
                public_df.groupby("user_key")
                .agg(
                    Points      = ("Points", "sum"),
                    User        = ("User",   "first"),
                    Exact       = ("Points", lambda x: (x == 3).sum()),
                    CorrectResult = ("Points", lambda x: ((x == 2) | (x == 3)).sum()),
                    Played      = ("Points", "count"),
                )
                .reset_index(drop=True)
            )

            # Tiebreaker: Points desc, Exact scores desc, Correct results desc
            agg = agg.sort_values(
                by=["Points", "Exact", "CorrectResult"],
                ascending=[False, False, False]
            ).reset_index(drop=True)

            # Form: last 3 graded matches for each user (W/D/L based on pts)
            graded_ordered = [
                fix["match"] for fix in FIXTURES
                if fix["match"].strip().lower() in graded_matches
            ]
            def form_str(user_key):
                results = []
                for m in reversed(graded_ordered[-3:]):
                    row = public_df[
                        (public_df["user_key"] == user_key)
                        & (public_df["Match"].str.strip().str.lower() == m.strip().lower())
                    ]
                    if row.empty:
                        results.append("-")
                    else:
                        pts = int(row.iloc[0]["Points"])
                        results.append("W" if pts >= 3 else ("D" if pts >= 1 else "L"))
                return " ".join(reversed(results)) if results else "-"

            agg["Form (last 3)"] = agg["user_key"].apply(form_str)
            agg["Rank"] = [f"{i+1}." for i in range(len(agg))]

            display_lb = agg[["Rank", "User", "Points", "Exact", "Form (last 3)"]].rename(
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
                all_users = agg["User"].tolist()
                grid = {"Player": all_users}
                for m in played_matches:
                    col_vals = []
                    for user in all_users:
                        ukey = user.strip().lower()
                        row  = public_df[
                            (public_df["user_key"] == ukey)
                            & (public_df["Match"].str.strip().str.lower() == m.strip().lower())
                        ]
                        col_vals.append(int(row.iloc[0]["Points"]) if not row.empty else "-")
                    # Truncate long match names for column headers
                    short = m if len(m) <= 20 else m[:18] + ".."
                    grid[short] = col_vals
                grid["Total"] = [int(agg[agg["User"] == u]["Points"].values[0]) for u in all_users]
                st.dataframe(pd.DataFrame(grid), use_container_width=True, hide_index=True)

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
