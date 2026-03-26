# ⚾ ESPN Fantasy Baseball Discord Bot

Posts scores, standings, matchups, power rankings, trophies, waiver wire activity, and injury alerts to your Discord channel.

---

## 📅 Posting Schedule

| Day       | What gets posted                        |
|-----------|-----------------------------------------|
| Monday    | Scoreboard, Trophies                    |
| Tuesday   | Standings, Power Rankings               |
| Wednesday | Waiver Report, Upcoming Matchups        |
| Thursday  | Injury / Lineup Alerts                  |
| Friday    | Scoreboard                              |
| Sunday    | Scoreboard, Injury Alerts               |

---

## 🚀 Deploy on Render (Free)

### Step 1 — Push this code to GitHub
Upload all these files to a new GitHub repository.

### Step 2 — Create a new Render service
1. Go to https://render.com and sign in
2. Click **New → Cron Job**
3. Connect your GitHub repo
4. Set **Schedule** to `0 9 * * *` (runs every day at 9 AM — only posts on scheduled days)
5. Set **Build Command** to: `pip install -r requirements.txt`
6. Set **Start Command** to: `python espn_bot.py`

### Step 3 — Add your Environment Variables
In Render → your service → **Environment**, add these:

| Variable            | Value                                      |
|---------------------|--------------------------------------------|
| LEAGUE_ID           | Your ESPN league ID number                 |
| LEAGUE_YEAR         | 2025                                       |
| ESPN_S2             | Your espn_s2 cookie value                  |
| SWID                | Your SWID cookie value (with {} is fine)   |
| DISCORD_WEBHOOK_URL | Your Discord channel webhook URL           |
| INIT_MSG            | (optional) Message to send on startup      |

---

## 🔑 How to get your ESPN cookies (ESPN_S2 and SWID)

1. Log into ESPN Fantasy on Chrome
2. Right-click anywhere → **Inspect**
3. Click **Application** tab at the top
4. On the left: **Storage → Cookies → https://www.espn.com**
5. Find `espn_s2` and `SWID` — copy their values

> ⚠️ Treat these like passwords. Don't share them with anyone.

---

## 🔗 How to get your Discord Webhook URL

1. Open your Discord server
2. Go to **Server Settings → Integrations → Webhooks**
3. Click **New Webhook**
4. Pick the channel you want the bot to post in
5. Click **Copy Webhook URL**
