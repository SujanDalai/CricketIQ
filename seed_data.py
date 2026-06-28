import sqlite3

def seed_database():
    conn = sqlite3.connect('cricket_data.db')
    cursor = conn.cursor()

    players = [
        ("virat kohli", "batter", None, "right-handed", None, None),
        ("rohit sharma", "batter", None, "right-handed", None, None),
        ("mitchell starc", "bowler", "Australia", None, "left-arm fast", "inswing yorker, left-arm angle outside off to right-handers"),
        ("james anderson", "bowler", "England", None, "right-arm swing", "late swing both ways, seam movement on English pitches"),
        ("pat cummins", "bowler", "Australia", None, "right-arm fast", "steep bounce, seam movement, relentless line and length"),
        ("stuart broad", "bowler", "England", None, "right-arm fast-medium", "away movement to right-handers, reverse swing with old ball"),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO players (name, role, country, batting_style, bowling_style, speciality) VALUES (?, ?, ?, ?, ?, ?)",
        players
    )

    traits = [
        ("virat kohli", "weakness", "left-arm pace outside off stump"),
        ("virat kohli", "weakness", "moving ball early in Test innings"),
        ("virat kohli", "strength", "chase situations"),
        ("virat kohli", "strength", "ODI middle overs"),
        ("virat kohli", "strength", "cover drive"),

        ("rohit sharma", "weakness", "short-pitched deliveries"),
        ("rohit sharma", "weakness", "bounce outside off stump in T20s"),
        ("rohit sharma", "strength", "powerplay ODI"),
        ("rohit sharma", "strength", "pull shot"),
        ("rohit sharma", "strength", "home conditions"),

        ("mitchell starc", "strength", "new ball swing"),
        ("mitchell starc", "strength", "death yorkers"),
        ("mitchell starc", "strength", "left-arm angle vs right-handers"),
        ("mitchell starc", "weakness", "expensive in T20s"),
        ("mitchell starc", "weakness", "flat pitches"),

        ("james anderson", "strength", "swing in English conditions"),
        ("james anderson", "strength", "seam movement"),
        ("james anderson", "strength", "patience"),
        ("james anderson", "weakness", "flat subcontinental pitches"),
        ("james anderson", "weakness", "T20 format"),
        ("james anderson", "weakness", "high bounce pitches"),

        ("pat cummins", "strength", "steep bounce"),
        ("pat cummins", "strength", "seam off the pitch"),
        ("pat cummins", "strength", "pressure bowling"),
        ("pat cummins", "weakness", "slower wickets"),
        ("pat cummins", "weakness", "subcontinental conditions"),

        ("stuart broad", "strength", "away swing"),
        ("stuart broad", "strength", "reverse swing"),
        ("stuart broad", "strength", "English conditions"),
        ("stuart broad", "strength", "T20 death bowling"),
        ("stuart broad", "weakness", "flat pitches"),
        ("stuart broad", "weakness", "subcontinental spin-friendly tracks"),
    ]
    cursor.executemany(
        "INSERT INTO player_traits (player_name, trait_type, description) VALUES (?, ?, ?)",
        traits
    )

    batting_innings = [
        ("virat kohli", 54, "ODI", "Australia", "Mumbai", "win", "mitchell starc"),
        ("virat kohli", 82, "T20", "England", "Delhi", "win", "james anderson"),
        ("virat kohli", 13, "Test", "Australia", "Perth", "loss", "mitchell starc"),
        ("virat kohli", 67, "ODI", "England", "London", "win", "stuart broad"),
        ("virat kohli", 39, "T20", "Australia", "Sydney", "loss", "pat cummins"),

        ("rohit sharma", 72, "ODI", "England", "Mumbai", "win", "james anderson"),
        ("rohit sharma", 31, "T20", "Australia", "Sydney", "loss", "pat cummins"),
        ("rohit sharma", 55, "Test", "England", "Lord's", "win", "stuart broad"),
        ("rohit sharma", 90, "ODI", "Australia", "Mumbai", "win", "mitchell starc"),
        ("rohit sharma", 18, "T20", "England", "London", "loss", "stuart broad"),
    ]
    cursor.executemany(
        "INSERT INTO batting_innings (batter_name, runs, format, opposition, venue, result, vs_bowler) VALUES (?, ?, ?, ?, ?, ?, ?)",
        batting_innings
    )

    bowling_spells = [
        ("mitchell starc", 3, "Test", "India", "Perth", 2.8),
        ("mitchell starc", 1, "ODI", "India", "Mumbai", 5.1),
        ("mitchell starc", 2, "Test", "England", "Melbourne", 3.2),
        ("mitchell starc", 4, "ODI", "England", "Sydney", 4.7),
        ("mitchell starc", 1, "T20", "India", "Delhi", 8.2),

        ("james anderson", 2, "Test", "India", "Lord's", 2.1),
        ("james anderson", 1, "Test", "Australia", "Birmingham", 2.5),
        ("james anderson", 3, "Test", "India", "Edgbaston", 2.3),
        ("james anderson", 0, "ODI", "India", "Mumbai", 5.8),
        ("james anderson", 2, "Test", "Pakistan", "Lord's", 2.0),

        ("pat cummins", 2, "Test", "India", "Perth", 2.6),
        ("pat cummins", 3, "ODI", "India", "Sydney", 4.8),
        ("pat cummins", 1, "T20", "India", "Melbourne", 7.1),
        ("pat cummins", 2, "Test", "England", "Adelaide", 2.9),
        ("pat cummins", 2, "ODI", "England", "Lord's", 5.2),

        ("stuart broad", 3, "Test", "India", "Lord's", 2.4),
        ("stuart broad", 2, "Test", "Australia", "Birmingham", 2.8),
        ("stuart broad", 1, "ODI", "India", "London", 5.5),
        ("stuart broad", 4, "Test", "India", "Edgbaston", 2.2),
        ("stuart broad", 2, "T20", "India", "London", 7.8),
    ]
    cursor.executemany(
        "INSERT INTO bowling_spells (bowler_name, wickets, format, opposition, venue, economy) VALUES (?, ?, ?, ?, ?, ?)",
        bowling_spells
    )

    format_stats = [
        ("mitchell starc", "Test", 3.0, 2.5),
        ("mitchell starc", "ODI", 4.9, 2.5),
        ("mitchell starc", "T20", 8.2, 1.0),

        ("james anderson", "Test", 2.3, 2.0),
        ("james anderson", "ODI", 5.8, 0.5),
        ("james anderson", "T20", None, None),

        ("pat cummins", "Test", 2.75, 2.0),
        ("pat cummins", "ODI", 5.0, 2.5),
        ("pat cummins", "T20", 7.1, 1.0),

        ("stuart broad", "Test", 2.47, 2.4),
        ("stuart broad", "ODI", 5.5, 1.0),
        ("stuart broad", "T20", 7.8, 2.0),
    ]
    cursor.executemany(
        "INSERT INTO format_stats (bowler_name, format, avg_economy, avg_wickets) VALUES (?, ?, ?, ?)",
        format_stats
    )

    head_to_head = [
        ("virat kohli", "mitchell starc", 8, 4, 187, 46.75),
        ("rohit sharma", "mitchell starc", 6, 2, 201, 100.5),
        ("virat kohli", "james anderson", 10, 7, 134, 19.14),
        ("rohit sharma", "james anderson", 8, 3, 198, 66.0),
        ("virat kohli", "pat cummins", 7, 2, 210, 105.0),
        ("rohit sharma", "pat cummins", 6, 4, 98, 24.5),
        ("virat kohli", "stuart broad", 9, 3, 245, 81.67),
        ("rohit sharma", "stuart broad", 7, 5, 112, 22.4),
    ]
    cursor.executemany(
        "INSERT INTO head_to_head (batter_name, bowler_name, innings, dismissals, runs_conceded, avg_conceded) VALUES (?, ?, ?, ?, ?, ?)",
        head_to_head
    )

    venues = [
        ("perth", "high", "high", "low", "low", "pace bowlers"),
        ("mumbai", "medium", "low", "high", "low", "batters and spinners"),
        ("lord's", "medium", "medium", "low", "high", "swing bowlers"),
        ("edgbaston", "medium", "medium", "low", "high", "swing bowlers"),
        ("sydney", "medium", "medium", "medium", "low", "balanced"),
        ("melbourne", "medium", "medium", "low", "medium", "pace bowlers"),
        ("delhi", "low", "low", "high", "low", "spinners and batters"),
        ("birmingham", "medium", "medium", "low", "high", "swing bowlers"),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO venues (name, pace, bounce, spin, swing, favours) VALUES (?, ?, ?, ?, ?, ?)",
        venues
    )

    conn.commit()
    conn.close()
    print("All sample data inserted successfully!")

if __name__ == '__main__':
    seed_database()