import pandas as pd
from datetime import datetime
import pytz

ist = pytz.timezone('Asia/Kolkata')

# 1. Structural Bracket Definition
RO16_DEFS = [
    {"id": "R16_1", "match": "Canada vs Morocco", "kickoff": ist.localize(datetime(2026, 7, 4, 22, 30)), "next": "QF1_A"},
    {"id": "R16_2", "match": "Paraguay vs France", "kickoff": ist.localize(datetime(2026, 7, 5, 2, 30)), "next": "QF1_B"},
    {"id": "R16_3", "match": "Brazil vs Norway", "kickoff": ist.localize(datetime(2026, 7, 5, 22, 30)), "next": "QF3_A"},
    {"id": "R16_4", "match": "Mexico vs England", "kickoff": ist.localize(datetime(2026, 7, 6, 2, 30)), "next": "QF3_B"},
    {"id": "R16_5", "match": "Portugal vs Spain", "kickoff": ist.localize(datetime(2026, 7, 6, 22, 30)), "next": "QF2_A"},
    {"id": "R16_6", "match": "USA vs Belgium", "kickoff": ist.localize(datetime(2026, 7, 7, 2, 30)), "next": "QF2_B"},
    {"id": "R16_7", "match": "Argentina vs Egypt", "kickoff": ist.localize(datetime(2026, 7, 7, 22, 30)), "next": "QF4_A"},
    {"id": "R16_8", "match": "Switzerland vs Colombia", "kickoff": ist.localize(datetime(2026, 7, 8, 2, 30)), "next": "QF4_B"}
]

ADVANCED_SCHEDULES = {
    "QF1": {"time": ist.localize(datetime(2026, 7, 9, 22, 30)), "next": "SF1_A"},
    "QF2": {"time": ist.localize(datetime(2026, 7, 10, 22, 30)), "next": "SF1_B"},
    "QF3": {"time": ist.localize(datetime(2026, 7, 11, 22, 30)), "next": "SF2_A"},
    "QF4": {"time": ist.localize(datetime(2026, 7, 12, 22, 30)), "next": "SF2_B"},
    "SF1": {"time": ist.localize(datetime(2026, 7, 15, 2, 30)), "next": "F_A"},
    "SF2": {"time": ist.localize(datetime(2026, 7, 16, 2, 30)), "next": "F_B"},
    "FINAL": {"time": ist.localize(datetime(2026, 7, 19, 22, 30)), "next": None}
}

def get_active_fixtures(df):
    """
    Parses completed match tokens directly from the database sheet, traces 
    the winning trajectories, and constructs upcoming lines up to the final.
    """
    admin_results = df[df['User'] == 'ADMIN_RESULT'] if not df.empty and 'User' in df.columns else pd.DataFrame()
    
    # Trace winning results
    winners = {}
    if not admin_results.empty:
        for _, row in admin_results.iterrows():
            m_label = row['Match']
            t1, t2 = m_label.split(" vs ")
            s1, s2 = int(row['Team1_Score']), int(row['Team2_Score'])
            if s1 > s2:
                winners[m_label] = t1
            elif s2 > s1:
                winners[m_label] = t2
            else:
                winners[m_label] = str(row['Pen_Winner'])

    # Tree slots
    slots = {}

    # Step 1: Evaluate Round of 16
    fixtures_list = []
    for item in RO16_DEFS:
        fixtures_list.append({"match": item["match"], "kickoff": item["kickoff"]})
        if item["match"] in winners:
            slots[item["next"]] = winners[item["match"]]

    # Step 2: Evaluate Quarterfinals
    for qf in ["QF1", "QF2", "QF3", "QF4"]:
        tA = slots.get(f"{qf}_A")
        tB = slots.get(f"{qf}_B")
        if tA and tB:
            m_title = f"{tA} vs {tB}"
            fixtures_list.append({"match": m_title, "kickoff": ADVANCED_SCHEDULES[qf]["time"]})
            if m_title in winners:
                slots[ADVANCED_SCHEDULES[qf]["next"]] = winners[m_title]

    # Step 3: Evaluate Semifinals
    for sf in ["SF1", "SF2"]:
        tA = slots.get(f"{sf}_A")
        tB = slots.get(f"{sf}_B")
        if tA and tB:
            m_title = f"{tA} vs {tB}"
            fixtures_list.append({"match": m_title, "kickoff": ADVANCED_SCHEDULES[sf]["time"]})
            if m_title in winners:
                slots[ADVANCED_SCHEDULES[sf]["next"]] = winners[m_title]

    # Step 4: Evaluate Final
    tA = slots.get("F_A")
    tB = slots.get("F_B")
    if tA and tB:
        m_title = f"{tA} vs {tB}"
        fixtures_list.append({"match": m_title, "kickoff": ADVANCED_SCHEDULES["FINAL"]["time"]})

    return fixtures_list
