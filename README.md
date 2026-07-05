# Tournament Knockout Stage Prediction System

An end-to-end cloud-hosted application built to automate prediction tournament brackets, leaderboards, and scoring calculations for tournament knockout stages. The system relies on a Streamlit application interface backed by a headless Google Sheets database layer to prevent manual spreadsheet data corruption.

---

## System Architecture

The application is structured into three decoupled layers:
* **Ingestion Layer (GUI):** A clean input form handling user submissions, field validation, and dynamic entry locking based on match kickoff timers.
* **Storage Layer (Cloud DB):** A secure Google Sheets instance acting as the storage relational matrix, completely hidden from user modification.
* **Engine Layer (Scoring Framework):** A vector-based logical matrix running on Pandas that computes points for final match states including extra time and penalty shootouts.

---

## Tournament Rules and Scoring Logic

To maintain competition integrity, the platform processes point allocation through a strict conditional hierarchy. Points are non-stacking for the match outcome to prevent massive single-match lead gaps.

### 1. Match Outcomes
* **Exact Score Match (3 Points):** Awarded if a user correctly predicts the precise final score line at the conclusion of the match (including Extra Time if played).
* **Correct Outcome (2 Points):** Awarded if a user correctly identifies the winning team, but misses the exact score line(non draw)

### 2. Draw and Penalty Shootout Conditions
* **Draw Definition:** If a match goes to a penalty shootout, the score line at the end of 120 minutes is structurally a tie.
* **Clutch Draw (3 Points):** Awarded if a user correctly predicts the tie score.
* **Partial Draw (1 Point):** Awarded if a user correctly predicts that the match ends in a tie, but misses the exact score.
* **Penalty Bonus (1 Point):** Awarded if a user predicts who wins the penalty shootout after predicting a draw.

### 3. Bonus : ** +1 Point for guessing the MOTM correctly.

---

## Pre-Match Privacy Engineering

To ensure absolute confidentiality and prevent tactical copy-pasting, the system enforces a strict time-lock protocol:
* **Before Kickoff:** The dashboard hides all competitor picks. The interface only prints a confirmation list indicating which users have locked in an entry.
* **After Kickoff:** The submission system immediately locks the match ID. The privacy mask drops, revealing a complete comparative matrix of everyone's predictions to the entire league.

---

## Setup and Deployment

### Repository Structure
Ensure your local project directory contains these files before pushing to remote version control:
* app.py (The core controller and interface script)
* requirements.txt (Specifies library dependencies for the runtime environment)

### External Dependency Specification
Your requirements.txt must declare the following pinning:

    streamlit>=1.35.0
    pandas>=2.0.0
    st-gsheets-connection>=0.0.6
    pytz>=2024.1

### Google Sheets Configuration
1. Create a blank workbook on Google Sheets.
2. Label the active worksheet tab precisely as: Predictions
3. Establish the database schema by populating Row 1 with these exact headers across columns A through I:
   Timestamp | User | Match | Team1_Score | Team2_Score | Pen_Winner | MOTM | Scorers | Points

### Streamlit Platform Deployment
1. Connect your GitHub account to the Streamlit Community Cloud dashboard.
2. Deploy a new application sourcing the repository, using main as the production branch and app.py as the entrypoint.
3. Access Advanced Settings, navigate to the Secrets management field, and link your database via the following configuration block:

    [connections.gsheets]
    public_gsheets_url = "https://docs.google.com/spreadsheets/d/YOUR_TARGET_SHEET_ID_HERE/edit?usp=sharing"
