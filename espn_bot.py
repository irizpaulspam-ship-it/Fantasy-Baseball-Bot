import os
import time
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
            self.wfile.write(b"OK")
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
 
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
        time.sleep(1.5)
 
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
        lines = ["⚾ **Current Week Scoreboard**\n"]
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
        teams = sorted(league.teams, key=lambda t: t.wins, reverse=True)
        lines = ["📊 **Current Standings**\n"]
        for i, team in enumerate(teams, 1):
            lines.append(
                f"{i}. **{team.team_name}** — "
                f"{team.wins}W-{team.losses}L"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"⚠️ Could not fetch standings: {e}"
 
# ─── Feature: Weekly Matchups ─────────────────────────────────────────────────
def get_matchups(league):
    try:
        box_scores = league.box_scores()
        lines = ["🗓️ **Current Week Matchups**\n"]
        for match in box_scores:
            home = match.home_team
            away = match.away_team
            lines.append(f"**{away.team_name}** vs **{home.team_name}**")
        return "\n".join(lines)
    except Exception as e:
        return f"⚠️ Could not fetch matchups: {e}"
 
# ─── Feature: Trophies ────────────────────────────────────────────────────────
def get_trophies(league):
    try:
        box_scores = league.box_scores()
 
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
 
        lines = ["🏆 **Last Week Trophies**\n"]
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
 
# ─── Feature: Transactions (daily, last 28hrs) ───────────────────────────────
def get_transactions(league):
    try:
        activity = league.recent_activity(size=25)
        lines = ["🔄 **Recent Transactions**\n"]
        found = False
 
        cutoff = datetime.utcnow() - timedelta(hours=28)
 
        for action in activity:
            action_date = getattr(action, 'date', None)
            if action_date:
                if isinstance(action_date, int):
                    action_date = datetime.utcfromtimestamp(action_date / 1000)
                if action_date < cutoff:
                    continue
 
            for team, move, player in action.actions:
                if move in ("WAIVER ADDED", "FA ADDED", "DROPPED", "ADDED"):
                    emoji = "➕" if "ADDED" in move else "➖"
                    clean_move = (move
                        .replace('WAIVER ADDED', 'Added (Waiver)')
                        .replace('FA ADDED', 'Added (FA)')
                        .replace('ADDED', 'Added (FA)')
                        .replace('DROPPED', 'Dropped'))
                    player_name = player if isinstance(player, str) else player.name
                    lines.append(f"{emoji} **{team.team_name}** — {clean_move}: {player_name}")
                    found = True
 
        if not found:
            lines.append("No transactions completed since last report.")
        return "\n".join(lines)
    except Exception as e:
        return f"⚠️ Could not fetch transactions: {e}"
 
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
 
# ─── Feature: Division Rankings ──────────────────────────────────────────────
def get_division_rankings(league):
    try:
        divisions = {}
        for team in league.teams:
            div = getattr(team, "division_id", None)
            div_name = getattr(team, "division_name", f"Division {div}")
            if div_name not in divisions:
                divisions[div_name] = []
            divisions[div_name].append(team)
 
        if not divisions:
            return "🏟️ **Division Rankings** — No divisions found in this league."
 
        def get_streak(team):
            outcomes = getattr(team, "outcomes", [])
            if not outcomes:
                return "—"
            streak_char = outcomes[-1]
            count = 0
            for result in reversed(outcomes):
                if result == streak_char:
                    count += 1
                else:
                    break
            if streak_char == "W" and count >= 3:
                return f"🔥 W{count}"
            elif streak_char == "W":
                return f"W{count}"
            else:
                return f"L{count}"
 
        division_emojis = ["⚡", "🌊", "🔥", "💨"]
        lines = ["🏟️ **Division Rankings**\n"]
 
        for i, (div_name, teams) in enumerate(sorted(divisions.items())):
            emoji = division_emojis[i] if i < len(division_emojis) else "🏟️"
            lines.append(f"**{emoji} {div_name}**")
            sorted_teams = sorted(teams, key=lambda t: (t.wins, t.points_for), reverse=True)
            for rank, team in enumerate(sorted_teams, 1):
                streak = get_streak(team)
                lines.append(
                    f"{rank}. **{team.team_name}** — "
                    f"{team.wins}W-{team.losses}L | "
                    f"{team.points_for:.1f} pts | "
                    f"{streak}"
                )
            lines.append("")
 
        return "\n".join(lines).strip()
    except Exception as e:
        return f"⚠️ Could not fetch division rankings: {e}"
 
# ─── Schedule logic ───────────────────────────────────────────────────────────
def should_run(task: str) -> bool:
    """
    Monday    : Matchups + Trophies + Transactions
    Tuesday   : Scoreboard + Transactions
    Wednesday : Scoreboard + Transactions
    Thursday  : Scoreboard + Standings + Transactions
    Friday    : Scoreboard + Transactions
    Saturday  : Scoreboard + Injury Alerts + Transactions
    Sunday    : Scoreboard + Division Rankings + Transactions
    """
    day = datetime.now().weekday()  # 0=Mon ... 6=Sun
    schedule = {
        "scoreboard":        [1, 2, 3, 4, 5, 6],
        "matchups":          [0],
        "trophies":          [0],
        "standings":         [3],
        "injury_alerts":     [5],
        "division_rankings": [6],
        "transactions":      [0, 1, 2, 3, 4, 5, 6],
    }
    return day in schedule.get(task, [])
 
# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    # ── Time window check (8am-10am Eastern) ──────────────────────────────────
    now = datetime.utcnow() - timedelta(hours=4)
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
        time.sleep(2)

    league = get_league()
 
    task_map = {
        "matchups":          get_matchups,
        "trophies":          get_trophies,
        "scoreboard":        get_scoreboard,
        "standings":         get_standings,
        "injury_alerts":     get_injury_alerts,
        "division_rankings": get_division_rankings,
        "transactions":      get_transactions,
    }
 
    for task, fn in task_map.items():
        if should_run(task):
            msg = fn(league)
            send_discord(msg)
            print(f"[{task}] sent.")
            time.sleep(2)
        else:
            print(f"[{task}] skipped (not scheduled today).")
 
# ─── Entry point ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    threading.Thread(target=start_server, daemon=True).start()
    main()
    threading.Event().wait()

