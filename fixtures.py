import pandas as pd
from datetime import datetime
import pytz

ist = pytz.timezone('Asia/Kolkata')


RO16_DEFS = [
    {"id": "R16_1", "match": "Canada vs Morocco", "kickoff": ist.localize(datetime(2026, 7, 4, 22, 30)), "next": "QF1_A"},      # Jul 4, 1:00 PM ET
    {"id": "R16_2", "match": "Paraguay vs France", "kickoff": ist.localize(datetime(2026, 7, 5, 2, 30)), "next": "QF1_B"},      # Jul 4, 5:00 PM ET
    {"id": "R16_3", "match": "Brazil vs Norway", "kickoff": ist.localize(datetime(2026, 7, 6, 1, 30)), "next": "QF3_A"},        # Jul 5, 4:00 PM ET
    {"id": "R16_4", "match": "Mexico vs England", "kickoff": ist.localize(datetime(2026, 7, 6, 5, 30)), "next": "QF3_B"},       # Jul 5, 8:00 PM ET
    {"id": "R16_5", "match": "Portugal vs Spain", "kickoff": ist.localize(datetime(2026, 7, 7, 0, 30)), "next": "QF2_A"},       # Jul 6, 3:00 PM ET
    {"id": "R16_6", "match": "USA vs Belgium", "kickoff": ist.localize(datetime(2026, 7, 7, 5, 30)), "next": "QF2_B"},         # Jul 6, 8:00 PM ET
    {"id": "R16_7", "match": "Argentina vs Egypt", "kickoff": ist.localize(datetime(2026, 7, 7, 21, 30)), "next": "QF4_A"},     # Jul 7, 12:00 PM ET
    {"id": "R16_8", "match": "Switzerland vs Colombia", "kickoff": ist.localize(datetime(2026, 7, 8, 1, 30)), "next": "QF4_B"}  # Jul 7, 4:00 PM ET
]

ADVANCED_SCHEDULES = {
    "QF1": {"time": ist.localize(datetime(2026, 7, 10, 1, 30)), "next": "SF1_A"},   # Jul 9, 4:00 PM ET
    "QF2": {"time": ist.localize(datetime(2026, 7, 11, 0, 30)), "next": "SF1_B"},   # Jul 10, 3:00 PM ET
    "QF3": {"time": ist.localize(datetime(2026, 7, 12, 2, 30)), "next": "SF2_A"},   # Jul 11, 5:00 PM ET
    "QF4": {"time": ist.localize(datetime(2026, 7, 12, 6, 30)), "next": "SF2_B"},   # Jul 11, 9:00 PM ET
    "SF1": {"time": ist.localize(datetime(2026, 7, 15, 0, 30)), "next": "F_A"},     # Jul 14, 3:00 PM ET
    "SF2": {"time": ist.localize(datetime(2026, 7, 16, 0, 30)), "next": "F_B"},     # Jul 15, 3:00 PM ET
    "FINAL": {"time": ist.localize(datetime(2026, 7, 20, 0, 30)), "next": None}     # Jul 19, 3:00 PM ET
}

ROUND_LABELS = {
    "RO16": "Round of 16",
    "QF": "Quarterfinal",
    "SF": "Semifinal",
    "FINAL": "Final",
}


def _extract_winners(df):
    """
    Reads ADMIN_RESULT rows from the predictions dataframe and figures out
    who won each graded match. Any malformed row (bad score, missing 'vs',
    NaNs) is skipped rather than allowed to crash fixture generation.
    """
    winners = {}

    if df is None or df.empty or 'User' not in df.columns:
        return winners

    admin_results = df[df['User'].astype(str).str.strip().str.upper() == 'ADMIN_RESULT']

    for _, row in admin_results.iterrows():
        try:
            m_label = str(row['Match']).strip()
            if ' vs ' not in m_label:
                continue
            t1, t2 = [t.strip() for t in m_label.split(' vs ', 1)]

            s1 = int(float(row['Team1_Score']))
            s2 = int(float(row['Team2_Score']))

            if s1 > s2:
                winners[m_label] = t1
            elif s2 > s1:
                winners[m_label] = t2
            else:
                pen = str(row.get('Pen_Winner', '')).strip()
                if pen and pen.lower() not in ('none', 'nan', ''):
                    winners[m_label] = pen
                # else: draw with no valid penalty winner recorded yet -
                # leave this match unresolved rather than guessing.
        except (ValueError, TypeError, KeyError):
            # Malformed admin row (blank score, weird team names, etc.)
            # Skip it instead of taking down the whole bracket.
            continue

    return winners


def get_active_fixtures(df):
    """
    Parses completed match results directly from the database sheet, traces
    the winning trajectories through the bracket, and constructs the list of
    fixtures (played, live, and upcoming) from Round of 16 to the Final.

    Never raises: any malformed input results in that portion of the bracket
    simply not being built yet, rather than an exception.
    """
    try:
        winners = _extract_winners(df)
    except Exception:
        winners = {}

    slots = {}
    fixtures_list = []

    # Step 1: Round of 16 (always fully defined)
    for item in RO16_DEFS:
        fixtures_list.append({
            "match": item["match"],
            "kickoff": item["kickoff"],
            "round": ROUND_LABELS["RO16"],
        })
        if item["match"] in winners and winners[item["match"]]:
            slots[item["next"]] = winners[item["match"]]

    # Step 2: Quarterfinals
    for qf in ["QF1", "QF2", "QF3", "QF4"]:
        tA, tB = slots.get(f"{qf}_A"), slots.get(f"{qf}_B")
        if tA and tB:
            m_title = f"{tA} vs {tB}"
            fixtures_list.append({
                "match": m_title,
                "kickoff": ADVANCED_SCHEDULES[qf]["time"],
                "round": ROUND_LABELS["QF"],
            })
            if m_title in winners and winners[m_title]:
                slots[ADVANCED_SCHEDULES[qf]["next"]] = winners[m_title]

    # Step 3: Semifinals
    for sf in ["SF1", "SF2"]:
        tA, tB = slots.get(f"{sf}_A"), slots.get(f"{sf}_B")
        if tA and tB:
            m_title = f"{tA} vs {tB}"
            fixtures_list.append({
                "match": m_title,
                "kickoff": ADVANCED_SCHEDULES[sf]["time"],
                "round": ROUND_LABELS["SF"],
            })
            if m_title in winners and winners[m_title]:
                slots[ADVANCED_SCHEDULES[sf]["next"]] = winners[m_title]

    # Step 4: Final
    tA, tB = slots.get("F_A"), slots.get("F_B")
    if tA and tB:
        m_title = f"{tA} vs {tB}"
        fixtures_list.append({
            "match": m_title,
            "kickoff": ADVANCED_SCHEDULES["FINAL"]["time"],
            "round": ROUND_LABELS["FINAL"],
        })

    return fixtures_list
