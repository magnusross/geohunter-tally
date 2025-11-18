import json
import os
import argparse
import math
import sys
from datetime import date

# --- Configuration ---
DATA_FILE = "game_history.json"
PLAYERS = ["James", "Magnus", "Jake"]

# Baseline scores provided by user (assumed to be fully attended games)
LEGACY_SCORES = {"James": 3, "Magnus": 6, "Jake": 10}
LEGACY_GAMES_COUNT = sum(LEGACY_SCORES.values())


def load_data():
    """
    Loads game history from JSON.
    Structure:
    {
        "history": {
            "2023-10-27": {"winner": "James", "absent": []},
            ...
        }
    }
    """
    if not os.path.exists(DATA_FILE):
        default_data = {"history": {}}
        save_data(default_data)
        return default_data

    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        print(f"Error: Could not read {DATA_FILE}. Initializing new file.")
        return {"history": {}}


def save_data(data):
    """Saves the data to JSON."""
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except IOError as e:
        print(f"Error saving data: {e}")


def get_player_match(name):
    """Case-insensitive search for a player name."""
    for p in PLAYERS:
        if p.lower() == name.lower():
            return p
    return None


def calculate_p_value(z):
    """Calculates strictly right-tailed p-value (Probability of Z > observed)."""
    # Cumulative distribution function (CDF) for standard normal distribution
    cdf = 0.5 * (1 + math.erf(z / math.sqrt(2)))

    # We strictly want the area to the right of the curve.
    # This tests if the score is significantly *higher* than expected.
    return 1.0 - cdf


def add_win(winner_name, absent_names=None):
    """Records a win for today, ensuring no duplicates."""
    if absent_names is None:
        absent_names = []

    data = load_data()
    today_str = str(date.today())

    # 1. Check if today is already recorded
    if today_str in data["history"]:
        print(f"❌ Error: A score has already been recorded for today ({today_str}).")
        print(f"   Winner: {data['history'][today_str]['winner']}")
        sys.exit(1)

    # 2. Validate Winner
    winner_real = get_player_match(winner_name)
    if not winner_real:
        print(f"❌ Error: '{winner_name}' is not a recognized player.")
        print(f"   Players: {', '.join(PLAYERS)}")
        sys.exit(1)

    # 3. Validate Absences
    real_absent = []
    for a in absent_names:
        match = get_player_match(a)
        if match:
            real_absent.append(match)
        else:
            print(f"⚠️ Warning: Absent player '{a}' not recognized. Ignoring.")

    if winner_real in real_absent:
        print(f"❌ Error: The winner ({winner_real}) cannot be marked as absent.")
        sys.exit(1)

    if len(real_absent) == len(PLAYERS):
        print("❌ Error: All players cannot be absent.")
        sys.exit(1)

    # 4. Save
    data["history"][today_str] = {"winner": winner_real, "absent": real_absent}

    save_data(data)
    print(f"✅ Recorded win for {winner_real} on {today_str}.")
    if real_absent:
        print(f"   (Marked absent: {', '.join(real_absent)})")


def analyze_scores():
    """
    Calculates stats combining Legacy scores + Daily History.
    Adjusts 'Expected Wins' based on attendance.
    """
    data = load_data()
    history = data.get("history", {})

    # Initialize stats with Legacy data
    # We assume everyone played every game in the legacy period
    stats = {p: {"wins": 0, "games_played": 0, "expected_wins": 0.0} for p in PLAYERS}

    # Apply Legacy Scores
    num_players = len(PLAYERS)
    legacy_prob = 1.0 / num_players

    for p, wins in LEGACY_SCORES.items():
        if p in stats:
            stats[p]["wins"] += wins
            stats[p]["games_played"] += LEGACY_GAMES_COUNT
            stats[p]["expected_wins"] += LEGACY_GAMES_COUNT * legacy_prob

    # Apply History
    recent_games_count = len(history)
    total_games = LEGACY_GAMES_COUNT + recent_games_count

    for day, record in history.items():
        winner = record.get("winner")
        absent = record.get("absent", [])

        # Who actually played today?
        present_players = [p for p in PLAYERS if p not in absent]
        count_present = len(present_players)

        if count_present == 0:
            continue  # Should not happen based on add logic

        prob_win = 1.0 / count_present

        # Update stats for present players
        for p in present_players:
            stats[p]["games_played"] += 1
            stats[p]["expected_wins"] += prob_win

        # Update winner
        if winner in stats:
            stats[p]["wins"]  # Ensure key exists
            stats[winner]["wins"] += 1

    print("\n" + "=" * 65)
    print(f"🏆 CURRENT STANDINGS (Total Games: {total_games})")
    print("=" * 65)
    print(
        f"{'Player':<10} | {'Wins':<6} | {'Played':<6} | {'Win %':<6} | {'Expected':<8} | {'p-value':<8}"
    )
    print("-" * 65)

    sorted_players = sorted(
        stats.items(), key=lambda item: item[1]["wins"], reverse=True
    )

    for player, s in sorted_players:
        wins = s["wins"]
        played = s["games_played"]
        expected = s["expected_wins"]

        win_pct = (wins / played * 100) if played > 0 else 0.0

        # Standardized Residual: (Observed - Expected) / sqrt(Expected)
        if expected > 0:
            residual = (wins - expected) / math.sqrt(expected)
        else:
            residual = 0

        # Calculate STRICTLY right-tailed p-value
        p_value = calculate_p_value(residual)

        # Format p-value string
        p_str = f"{p_value:.4f}"
        if p_value < 0.05:
            p_str += " *"  # Mark significant values

        print(
            f"{player:<10} | {wins:<6} | {played:<6} | {win_pct:>5.1f}% | {expected:>8.2f} | {p_str:<8}"
        )

    print("-" * 65)
    print("Note: 'Expected' adjusts for days a player was absent.")
    print("      * Right-tail test: p < 0.05 means significantly HIGH score.")


def main():
    parser = argparse.ArgumentParser(
        description="Track daily game scores with attendance."
    )

    parser.add_argument(
        "--add", type=str, metavar="PLAYER", help="Add a win for a player for TODAY"
    )
    parser.add_argument(
        "--absent",
        nargs="+",
        metavar="PLAYER",
        help="List of players who did not play today",
    )
    parser.add_argument("--show", action="store_true", help="Show stats only")

    args = parser.parse_args()

    if args.add:
        add_win(args.add, args.absent)
        analyze_scores()
    else:
        analyze_scores()


if __name__ == "__main__":
    main()
