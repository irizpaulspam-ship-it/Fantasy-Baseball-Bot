import os
import tempfile
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timedelta
from espn_api.baseball import League
 
# ─── Config from environment variables ───────────────────────────────────────
LEAGUE_ID        = int(os.environ["LEAGUE_ID"])
LEAGUE_YEAR      = int(os.environ.get("LEAGUE_YEAR", datetime.now().year))
ESPN_S2          = os.environ.get("ESPN_S2", "")
SWID             = os.environ.get("SWID", "")
DISCORD_WEBHOOK  = os.environ["DISCORD_WEBHOOK_URL"]
INIT_MSG         = os.environ.get("INIT_MSG", "")
 
# ─── Tiny web server so Render stays alive ────────────────────────────────────
class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/run":
            threading.Thread(target=main).start()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot triggered!")
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Fantasy Baseball Bot is running!")
 
    def log_message(self, format, *args):
        pass  # Suppress noisy request logs
 
def start_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), PingHandler)
    print(f"Web server running on port {port}")
    server.serve_forever()
 
# ─── Discord helper ───────────────────────────────────────────────────────────
def send_discord(message: str):
    if not message or not message.strip():
        return
    chunks = [message[i:i+1900] for i in range(0, len(message), 1900)]
    for chunk in chunks:
        payload = {"content": chunk}
        r = requests.post(DISCORD_WEBHOOK, json=payload)
        r.raise_for_status()
 
# ─── League connection ────────────────────────────────────────────────────────
def get_league():
    kwargs = dict(league_id=LEAGUE_ID, year=LEAGUE_YEAR)
    if ESPN_S2 and SWID:
        kwargs["espn_s2"] = ESPN_S2
        kwargs["swid"]    = SWID
    return League(**kwargs)
 
# ─── Feature: Scoreboard ──────────────────────────────────────────────────────
def get_scoreboard(league):
    try:
        box_scores = league.box_scores()
        current_week = league.current_week
        lines = [f"⚾ **Week {current_week} Scoreboard**\n"]
        for match in box_scores:
            home = match.home_team
            away = match.away_team
            home_score = match.home_score
            away_score = match.away_score
            lines.append(
                f"**{away.team_name}** {away_score:.1f}  vs  "
                f"{home_score:.1f} **{home.team_name}**"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"⚠️ Could not fetch scoreboard: {e}"
 
# ─── Feature: Standings ───────────────────────────────────────────────────────
def get_standings(league):
    try:
        teams = sorted(league.teams, key=lambda t: (t.wins, t.points_for), reverse=True)
        lines = ["📊 **Current Standings**\n"]
        for i, team in enumerate(teams, 1):
            lines.append(
                f"{i}. **{team.team_name}** — "
                f"{team.wins}W-{team.losses}L  "
                f"({team.points_for:.1f} pts)"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"⚠️ Could not fetch standings: {e}"
 
# ─── Feature: Weekly Matchups ─────────────────────────────────────────────────
def get_matchups(league):
    try:
        box_scores = league.box_scores()
        current_week = league.current_week
        lines = [f"🗓️ **Week {current_week} Matchups**\n"]
        for match in box_scores:
            home = match.home_team
            away = match.away_team
            lines.append(f"**{away.team_name}** vs **{home.team_name}**")
        return "\n".join(lines)
    except Exception as e:
        return f"⚠️ Could not fetch matchups: {e}"
 
# ─── Feature: Power Rankings ──────────────────────────────────────────────────
def get_power_rankings(league):
    try:
        current_week = league.current_week
        if current_week < 2:
            return "📈 **Power Rankings** — Not enough data yet!"
        rankings = league.power_rankings(week=current_week - 1)
        lines = ["📈 **Power Rankings**\n"]
        for i, (score, team) in enumerate(rankings, 1):
            lines.append(f"{i}. **{team.team_name}** — {float(score):.2f}")
        return "\n".join(lines)
    except Exception as e:
        return f"⚠️ Could not fetch power rankings: {e}"
 
# ─── Feature: Trophies ────────────────────────────────────────────────────────
def get_trophies(league):
    try:
        box_scores = league.box_scores()
        current_week = league.current_week
 
        scores = []
        margins = []
        for match in box_scores:
            if match.home_score is None or match.away_score is None:
                continue
            scores.append((match.home_score, match.home_team))
            scores.append((match.away_score, match.away_team))
            diff = abs(match.home_score - match.away_score)
            winner = match.home_team if match.home_score > match.away_score else match.away_team
            loser  = match.away_team if match.home_score > match.away_score else match.home_team
            margins.append((diff, winner, loser, match.home_score, match.away_score))
 
        if not scores:
            return "🏆 **Trophies** — No completed games yet this week."
 
        scores.sort(key=lambda x: x[0], reverse=True)
        high_score_val, high_score_team = scores[0]
        low_score_val,  low_score_team  = scores[-1]
 
        margins.sort(key=lambda x: x[0], reverse=True)
        biggest_win_diff, biggest_win_team, biggest_win_loser, bw_hs, bw_as = margins[0]
        closest_win_diff, closest_win_team, closest_win_loser, cw_hs, cw_as = margins[-1]
 
        lines = [f"🏆 **Week {current_week} Trophies**\n"]
        lines.append(f"🔥 **High Score:** {high_score_team.team_name} — {high_score_val:.1f} pts")
        lines.append(f"💩 **Low Score:** {low_score_team.team_name} — {low_score_val:.1f} pts")
        lines.append(
            f"💪 **Biggest Win:** {biggest_win_team.team_name} "
            f"(+{biggest_win_diff:.1f} over {biggest_win_loser.team_name})"
        )
        lines.append(
            f"😬 **Closest Win:** {closest_win_team.team_name} "
            f"(+{closest_win_diff:.1f} over {closest_win_loser.team_name})"
        )
        return "\n".join(lines)
    except Exception as e:
        return f"⚠️ Could not fetch trophies: {e}"
 
# ─── Feature: Waiver Report ───────────────────────────────────────────────────
def get_waiver_report(league):
    try:
        activity = league.recent_activity(size=25)
        lines = ["📋 **Recent Waiver / FA Activity**\n"]
        found = False
        for action in activity:
            for team, move, player in action.actions:
                if move in ("WAIVER ADDED", "FA ADDED", "DROPPED"):
                    emoji = "➕" if "ADDED" in move else "➖"
                    clean_move = (move
                        .replace('_', ' ')
                        .replace('WAIVER ADDED', 'Added (Waiver)')
                        .replace('FA ADDED', 'Added (FA)')
                        .replace('DROPPED', 'Dropped'))
                    lines.append(f"{emoji} **{team.team_name}** — {clean_move}: {player.name}")
                    found = True
        if not found:
            lines.append("No recent waiver activity.")
        return "\n".join(lines)
    except Exception as e:
        return f"⚠️ Could not fetch waiver report: {e}"
 
# ─── Feature: Injury / Lineup Alerts ─────────────────────────────────────────
def get_injury_alerts(league):
    try:
        lines = ["🚨 **Injury & Lineup Alerts**\n"]
        alerts = []
        for team in league.teams:
            roster = team.roster
            for player in roster:
                status = getattr(player, "injuryStatus", "ACTIVE")
                if status and status not in ("ACTIVE", "NORMAL", "NA", ""):
                    clean_status = (status
                        .replace('_', ' ')
                        .replace('DAY DL', 'DAY IL'))
                    alerts.append(
                        f"⚠️ **{team.team_name}**: {player.name} — {clean_status}"
                    )
        if alerts:
            lines.extend(alerts)
        else:
            lines.append("✅ No injury alerts right now.")
        return "\n".join(lines)
    except Exception as e:
        return f"⚠️ Could not fetch injury alerts: {e}"
 
# ─── Schedule logic ───────────────────────────────────────────────────────────
def should_run(task: str) -> bool:
    """
    Monday   : Scoreboard, Trophies
    Tuesday  : Standings, Power Rankings
    Wednesday: Waiver Report, Matchups
    Thursday : Injury/Lineup Alerts
    Friday   : Scoreboard
    Saturday : (quiet)
    Sunday   : Scoreboard, Injury Alerts
    """
    day = datetime.now().weekday()  # 0=Mon ... 6=Sun
    schedule = {
        "scoreboard":     [0, 4, 6],
        "trophies":       [0],
        "standings":      [1],
        "power_rankings": [1],
        "waiver_report":  [2],
        "matchups":       [2],
        "injury_alerts":  [3, 6],
    }
    return day in schedule.get(task, [])
 
# ─── Main (runs on ping or startup) ──────────────────────────────────────────
def main():
    # ── Time window check (8am-10am Eastern) ──────────────────────────────────
    now = datetime.utcnow() - timedelta(hours=4)  # UTC-4 = Eastern Daylight Time
    if not (8 <= now.hour < 10):
        print(f"Outside posting window ({now.hour}:00 ET). Skipping.")
        return
 
    # ── Once-per-day check ────────────────────────────────────────────────────
    today = now.strftime("%Y-%m-%d")
    flag_file = os.path.join(tempfile.gettempdir(), f"bot_ran_{today}.flag")
    if os.path.exists(flag_file):
        print(f"Already ran today ({today}). Skipping.")
        return
    open(flag_file, "w").close()
 
    # ── Run ───────────────────────────────────────────────────────────────────
    if INIT_MSG:
        send_discord(INIT_MSG)
 
    league = get_league()
 
    task_map = {
        "scoreboard":     get_scoreboard,
        "standings":      get_standings,
        "matchups":       get_matchups,
        "power_rankings": get_power_rankings,
        "trophies":       get_trophies,
        "waiver_report":  get_waiver_report,
        "injury_alerts":  get_injury_alerts,
    }
 
    for task, fn in task_map.items():
        if should_run(task):
            msg = fn(league)
            send_discord(msg)
            print(f"[{task}] sent.")
        else:
            print(f"[{task}] skipped (not scheduled today).")
 
# ─── Entry point ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Start the web server in the background
    threading.Thread(target=start_server, daemon=True).start()
    # Run the bot once on startup
    main()
    # Keep the process alive so Render doesn't shut down
    threading.Event().wait()
