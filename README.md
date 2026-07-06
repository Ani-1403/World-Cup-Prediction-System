# World Cup 2026 Predictor

A prediction game built for friends and colleagues to compete on match results across the 2026 FIFA World Cup knockout stages — from the Round of 16 all the way to the Final. Built with Streamlit, backed by Google Sheets, and designed to just work with zero database setup.

---

## What it does

Everyone in your group logs in, submits score predictions before each match kicks off, and earns points based on how accurate they were. A live leaderboard tracks who's winning the competition. The admin (you) enters the official result after each game and the app scores everyone automatically.

The bracket advances itself — once you enter the Round of 16 results, the Quarterfinal fixtures populate automatically with the correct teams. Same for the Semis and Final. You don't touch `fixtures.py` again after setup.

---

## Scoring system

| Prediction | Points |
|---|---|
| Exact score (any result) | 3 pts |
| Correct winner, wrong score | 2 pts |
| Correct draw, wrong score | 1 pt |
| Correct penalty shootout winner *(draws only)* | +1 pt bonus |
| Correct Man of the Match | +1 pt bonus |

---

## Features

### For players
- **Score prediction** — pick the scoreline for any upcoming match before it kicks off
- **Penalty winner** — if you predict a draw, a penalty shootout winner dropdown appears automatically
- **MOTM prediction** — pick one player from either team's 26-man squad as your Man of the Match pick, worth a bonus point
- **Edit predictions** — change your pick any time up until 15 minutes before kickoff, after which it locks
- **My Predictions tab** — a personal history of all your picks, showing what you predicted, what the result was, and a plain-English breakdown of exactly how your points were calculated for each match
- **Upcoming deadlines** — the sidebar shows countdowns to the next 5 matches so you always know what's closing soon

### Leaderboard
- **Main table** — sorted by total points, with exact scores as the first tiebreaker and correct results as the second
- **Form tracker** — shows each player's last 3 results (W / D / L) as a mini form guide
- **Points breakdown grid** — a full matrix of every player vs every graded match, using short 3-letter team codes (e.g. `BRA-NOR`) as column headers with a legend below, so it stays readable all the way to the Final

### For the admin
- **Admin panel** — password-protected tab to enter official results after each match
- **Confirmation dialog** — a two-step confirm before any result is submitted, to prevent fat-finger mistakes
- **Graded match lock** — once a match is graded, its entry in the dropdown becomes read-only and displays the saved result; it cannot be accidentally re-submitted
- **Audit log** — a separate sub-tab showing every graded result in bracket order with the score, penalty winner, MOTM, and the timestamp it was entered

### Security
- **PIN login** — every player sets a 4-digit PIN on their first login, stored in a separate `Pins` sheet. Subsequent logins require the correct PIN, so nobody can submit predictions under someone else's name
- **Shared API secret** — all requests from the app to Google Apps Script are authenticated with a shared secret, so the Apps Script endpoint can't be abused by anyone who finds the URL
- **Predictions hidden until kickoff** — nobody can see anyone else's picks until the match starts, preventing last-minute copying

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | [Streamlit](https://streamlit.io) |
| Storage | Google Sheets (via Apps Script web app) |
| Backend logic | Google Apps Script (`Code.gs`) |
| Hosting | [Streamlit Community Cloud](https://streamlit.io/cloud) |
| Language | Python 3.10+ |

No database, no server to maintain. Everything lives in a Google Sheet you already own.

---

## File structure

```
├── app.py           # Main Streamlit application
├── fixtures.py      # Bracket structure, kickoff times (IST), and bracket progression logic
├── squads.py        # Official 26-man squad lists for all 14 active Round of 16 teams
├── Code.gs          # Google Apps Script backend (paste into your Apps Script editor)
├── requirements.txt # Python dependencies
└── README.md
```

---

## Setup guide

### 1. Google Sheet

Create a Google Sheet with two tabs named exactly:
- `Predictions`
- `Pins`

In the `Predictions` tab, add this header row in row 1:

```
Timestamp | User | Match | Team1_Score | Team2_Score | Pen_Winner | MOTM | Scorers | Points
```

The `Pins` tab header should be:

```
User | PIN
```

Both sheets are managed automatically after this — you don't need to touch them manually.

### 2. Google Apps Script

1. In your Google Sheet, go to **Extensions → Apps Script**
2. Replace all existing code with the contents of `Code.gs`
3. Change the `SHARED_SECRET` value at the top to a long random string of your choice (e.g. from [randomkeygen.com](https://randomkeygen.com))
4. Click **Deploy → Manage deployments → Edit → New version → Deploy**
5. Copy the `/exec` URL — this is your `WEBAPP_URL`

> **Important:** Editing the script alone is not enough. You must deploy a new version every time you change `Code.gs`, otherwise the live endpoint keeps running the old code.

### 3. Streamlit secrets

Create a file at `.streamlit/secrets.toml` in the same directory as `app.py`:

```toml
WEBAPP_URL     = "https://script.google.com/macros/s/YOUR_DEPLOYMENT_ID/exec"
SHEET_ID       = "your_google_sheet_id_here"
API_SECRET     = "the_same_long_random_string_you_put_in_Code.gs"
ADMIN_PASSWORD = "your_admin_password_here"
```

If you're deploying on Streamlit Community Cloud, add these under **App settings → Secrets** instead of a local file.

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

```
streamlit
pandas
pytz
requests
```

### 5. Run locally

```bash
streamlit run app.py
```

---

## Deployment (Streamlit Community Cloud)

1. Push the repo to GitHub (make sure `secrets.toml` is in `.gitignore`)
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect your repo
3. Set the main file path to `app.py`
4. Add your secrets under **App settings → Secrets**
5. Deploy

Every push to your main branch redeploys automatically.

---

## How the bracket works

The bracket is defined statically in `fixtures.py` — all 8 Round of 16 matches are hardcoded with their kickoff times in IST. Once you grade a match in the admin panel, the winning team is automatically slotted into the correct Quarterfinal fixture. The QF, SF, and Final fixtures appear in the prediction dropdown only once both teams are known.

Kickoff times are set to IST (UTC+5:30). The conversion from FIFA's official ET schedule is `ET + 9h 30m`. Note that several matches cross midnight into the next calendar day in IST — the times in `fixtures.py` account for this correctly.

---

## Admin workflow

After each match finishes:

1. Go to the **Admin Panel** tab
2. Enter the admin password
3. Select the match from the dropdown (it will show as "needs grading")
4. Enter the final score
5. If it was a draw, select the penalty shootout winner
6. Select the official Man of the Match
7. Click **Submit Official Results**, then confirm in the dialog

Points are calculated and saved to the sheet instantly. The leaderboard updates on the next page refresh.

---

## Squad lists

`squads.py` contains the official FIFA-confirmed 26-man squads for all 14 teams still active as of the Round of 16 (Canada and Paraguay are excluded as they were eliminated). Players are listed alphabetically and appear in the MOTM dropdown when predicting a match.

For Quarterfinal, Semifinal, and Final matches, the MOTM dropdowns will show the squads of whichever teams progress, as long as those teams are in `squads.py`. If a team reaches the later rounds whose squad isn't listed (which shouldn't happen with the current bracket), the MOTM section is gracefully hidden rather than crashing.

---

## Notes

- All times are in **IST (Indian Standard Time)**
- The `ADMIN_RESULT` username is reserved — it's used internally to store official match results and cannot be registered by a player
- PIN reset is not currently self-service — if someone forgets their PIN, you'll need to manually delete their row from the `Pins` sheet in Google Sheets, after which they can set a new one on their next login
- The Google Sheets CSV export used to read data is cached by Google for up to ~60 seconds. The app adds a cache-busting parameter to minimise this, but there may be a brief delay before a freshly submitted prediction appears
