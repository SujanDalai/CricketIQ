# Temporary dataset (we'll replace with CricAPI later)

PLAYER_STATS = {
    "virat kohli": {
        "format": "all",
        "batting_style": "right-handed",
        "recent_matches": [
            {"runs": 57, "format": "ODI",  "opposition": "Australia", "venue": "Mumbai",  "result": "win",  "vs_bowler": "mitchell starc"},
            {"runs": 89, "format": "T20",  "opposition": "England",   "venue": "Delhi",   "result": "win",  "vs_bowler": "ben stokes"},
            {"runs": 98, "format": "Test", "opposition": "Australia", "venue": "Perth",   "result": "loss", "vs_bowler": "mitchell starc"},
            {"runs": 96, "format": "ODI",  "opposition": "England",   "venue": "London",  "result": "win",  "vs_bowler": "jofra archer"},
            {"runs": 49, "format": "T20",  "opposition": "Australia", "venue": "Sydney",  "result": "loss", "vs_bowler": "pat cummins"},
        ],
        "weaknesses": ["left-arm pace outside off stump", "moving ball early in Test innings"],
        "strengths":  ["chase situations", "ODI middle overs", "cover drive"],
    },
    "rohit sharma": {
        "format": "all",
        "batting_style": "right-handed",
        "recent_matches": [
            {"runs": 72, "format": "ODI",  "opposition": "England",   "venue": "Mumbai", "result": "win",  "vs_bowler": "ben stokes"},
            {"runs": 64, "format": "T20",  "opposition": "Australia", "venue": "Sydney", "result": "loss", "vs_bowler": "pat cummins"},
            {"runs": 55, "format": "Test", "opposition": "England",   "venue": "Lord's", "result": "win",  "vs_bowler": "jofra archer"},
            {"runs": 90, "format": "ODI",  "opposition": "Australia", "venue": "Mumbai", "result": "win",  "vs_bowler": "mitchell starc"},
            {"runs": 48, "format": "T20",  "opposition": "England",   "venue": "London", "result": "loss", "vs_bowler": "jofra archer"},
        ],
        "weaknesses": ["yorker deliveries", "bounce outside off stump in T20s"],
        "strengths":  ["powerplay ODI", "pull shot", "home conditions"],
    },
    "ms dhoni": {
        "format": "all",
        "batting_style": "right-handed",
        "recent_matches": [
            {"runs": 91, "format": "ODI",  "opposition": "Australia", "venue": "Sydney", "result": "win",  "vs_bowler": "pat cummins"},
            {"runs": 57, "format": "ODI",  "opposition": "England",   "venue": "London", "result": "win",  "vs_bowler": "ben stokes"},
            {"runs": 61, "format": "Test", "opposition": "England",   "venue": "Lord's", "result": "loss", "vs_bowler": "jofra archer"},
            {"runs": 46, "format": "T20",  "opposition": "Australia", "venue": "Melbourne", "result": "loss", "vs_bowler": "mitchell starc"},
            {"runs": 84, "format": "T20",  "opposition": "England",   "venue": "Birmingham", "result": "win",  "vs_bowler": "jofra archer"},
        ],
        "weaknesses": ["wide short balls", "spin bowling"],
        "strengths":  ["yorkers and the iconic helicopter shot", "huge power ability to hit all around the park"],
    },
}

BOWLER_STATS = {
    "mitchell starc": {
        "country": "Australia",
        "bowling_style": "left-arm fast",
        "speciality": "inswing yorker, left-arm angle outside off to right-handers",
        "recent_wickets": [
            {"wickets": 3, "format": "Test", "opposition": "India",   "venue": "Perth",     "economy": 2.8},
            {"wickets": 1, "format": "ODI",  "opposition": "India",   "venue": "Mumbai",    "economy": 5.1},
            {"wickets": 2, "format": "Test", "opposition": "England", "venue": "Melbourne", "economy": 3.2},
            {"wickets": 4, "format": "ODI",  "opposition": "England", "venue": "Sydney",    "economy": 4.7},
            {"wickets": 1, "format": "T20",  "opposition": "India",   "venue": "Delhi",     "economy": 8.2},
        ],
        "format_economy":      {"Test": 3.0, "ODI": 4.9, "T20": 8.2},
        "format_avg_wickets":  {"Test": 2.5, "ODI": 2.5, "T20": 1.0},
        "strengths":  ["new ball swing", "death yorkers", "left-arm angle vs right-handers"],
        "weaknesses": ["expensive in T20s", "flat pitches"],
        "head_to_head": {
            "virat kohli":  {"innings": 8, "dismissals": 4, "runs_conceded": 187, "avg_conceded": 46.75},
            "rohit sharma": {"innings": 6, "dismissals": 2, "runs_conceded": 201, "avg_conceded": 100.5},
            "ms dhoni":     {"innings": 5, "dismissals": 2, "runs_conceded": 95,  "avg_conceded": 47.5},
        },
    },
    "ben stokes": {
        "country": "England",
        "bowling_style": "right-arm swing",
        "speciality": "late swing both ways, seam movement on English pitches",
        "recent_wickets": [
            {"wickets": 2, "format": "Test", "opposition": "India",     "venue": "Lord's",    "economy": 2.1},
            {"wickets": 1, "format": "Test", "opposition": "Australia", "venue": "Birmingham","economy": 2.5},
            {"wickets": 3, "format": "Test", "opposition": "India",     "venue": "Edgbaston", "economy": 2.3},
            {"wickets": 0, "format": "ODI",  "opposition": "India",     "venue": "Mumbai",    "economy": 5.8},
            {"wickets": 2, "format": "Test", "opposition": "Pakistan",  "venue": "Lord's",    "economy": 2.0},
        ],
        "format_economy":     {"Test": 2.3, "ODI": 5.8, "T20": None},
        "format_avg_wickets": {"Test": 2.0, "ODI": 0.5, "T20": None},
        "strengths":  ["swing in English conditions", "seam movement", "patience"],
        "weaknesses": ["flat subcontinental pitches", "T20 format", "high bounce pitches"],
        "head_to_head": {
            "virat kohli":  {"innings": 10, "dismissals": 7, "runs_conceded": 134, "avg_conceded": 19.14},
            "rohit sharma": {"innings": 8,  "dismissals": 3, "runs_conceded": 198, "avg_conceded": 66.0},
            "ms dhoni":     {"innings": 6,  "dismissals": 3, "runs_conceded": 110, "avg_conceded": 36.67},
        },
    },
    "pat cummins": {
        "country": "Australia",
        "bowling_style": "right-arm fast",
        "speciality": "steep bounce, seam movement, relentless line and length",
        "recent_wickets": [
            {"wickets": 2, "format": "Test", "opposition": "India",   "venue": "Perth",     "economy": 2.6},
            {"wickets": 3, "format": "ODI",  "opposition": "India",   "venue": "Sydney",    "economy": 4.8},
            {"wickets": 1, "format": "T20",  "opposition": "India",   "venue": "Melbourne", "economy": 7.1},
            {"wickets": 2, "format": "Test", "opposition": "England", "venue": "Adelaide",  "economy": 2.9},
            {"wickets": 2, "format": "ODI",  "opposition": "England", "venue": "Lord's",    "economy": 5.2},
        ],
        "format_economy":     {"Test": 2.75, "ODI": 5.0, "T20": 7.1},
        "format_avg_wickets": {"Test": 2.0,  "ODI": 2.5, "T20": 1.0},
        "strengths":  ["steep bounce", "seam off the pitch", "pressure bowling"],
        "weaknesses": ["slower wickets", "subcontinental conditions"],
        "head_to_head": {
            "virat kohli":  {"innings": 7, "dismissals": 2, "runs_conceded": 210, "avg_conceded": 105.0},
            "rohit sharma": {"innings": 6, "dismissals": 4, "runs_conceded": 98,  "avg_conceded": 24.5},
            "ms dhoni":     {"innings": 4, "dismissals": 1, "runs_conceded": 80,  "avg_conceded": 80.0},
        },
    },
    "jofra archer": {
        "country": "England",
        "bowling_style": "right-arm fast-medium",
        "speciality": "away movement to right-handers, reverse swing with old ball",
        "recent_wickets": [
            {"wickets": 3, "format": "Test", "opposition": "India",     "venue": "Lord's",    "economy": 2.4},
            {"wickets": 2, "format": "Test", "opposition": "Australia", "venue": "Birmingham","economy": 2.8},
            {"wickets": 1, "format": "ODI",  "opposition": "India",     "venue": "London",    "economy": 5.5},
            {"wickets": 4, "format": "Test", "opposition": "India",     "venue": "Edgbaston", "economy": 2.2},
            {"wickets": 2, "format": "T20",  "opposition": "India",     "venue": "London",    "economy": 7.8},
        ],
        "format_economy":     {"Test": 2.47, "ODI": 5.5, "T20": 7.8},
        "format_avg_wickets": {"Test": 2.4,  "ODI": 1.0, "T20": 2.0},
        "strengths":  ["away swing", "reverse swing", "English conditions", "T20 death bowling"],
        "weaknesses": ["flat pitches", "subcontinental spin-friendly tracks"],
        "head_to_head": {
            "virat kohli":  {"innings": 9, "dismissals": 3, "runs_conceded": 245, "avg_conceded": 81.67},
            "rohit sharma": {"innings": 7, "dismissals": 5, "runs_conceded": 112, "avg_conceded": 22.4},
            "ms dhoni":     {"innings": 5, "dismissals": 2, "runs_conceded": 90,  "avg_conceded": 45.0},
        },
    },
}

PITCH_CONDITIONS = {
    "perth":      {"pace": "high",   "bounce": "high",   "spin": "low",    "swing": "low",   "favours": "pace bowlers"},
    "mumbai":     {"pace": "medium", "bounce": "low",    "spin": "high",   "swing": "low",   "favours": "batters and spinners"},
    "lord's":     {"pace": "medium", "bounce": "medium", "spin": "low",    "swing": "high",  "favours": "swing bowlers"},
    "edgbaston":  {"pace": "medium", "bounce": "medium", "spin": "low",    "swing": "high",  "favours": "swing bowlers"},
    "sydney":     {"pace": "medium", "bounce": "medium", "spin": "medium", "swing": "low",   "favours": "balanced"},
    "melbourne":  {"pace": "medium", "bounce": "medium", "spin": "low",    "swing": "medium","favours": "pace bowlers"},
    "delhi":      {"pace": "low",    "bounce": "low",    "spin": "high",   "swing": "low",   "favours": "spinners and batters"},
    "birmingham": {"pace": "medium", "bounce": "medium", "spin": "low",    "swing": "high",  "favours": "swing bowlers"},
}

# ---------------------------------------------------------------------------
# Bowler groups by nationality
# ---------------------------------------------------------------------------
BOWLER_GROUPS = {
    "australian": ["mitchell starc", "pat cummins"],
    "australia":  ["mitchell starc", "pat cummins"],
    "english":    ["ben stokes", "jofra archer"],
    "england":    ["ben stokes", "jofra archer"],
}


def resolve_bowlers(text: str) -> list[str]:
    """
    Given a query string, return a list of individual bowler names to analyse.

    Resolution order:
    1. If one or more nationality group keywords are detected
       (e.g. "australian", "english"), expand them to their member bowlers.
    2. If specific bowler names are mentioned, use those.
    3. If nothing is found, return all known bowlers as a fallback.

    Examples
    --------
    >>> resolve_bowlers("how will kohli bat against australian bowlers?")
    ['mitchell starc', 'pat cummins']

    >>> resolve_bowlers("analysis for ben stokes vs kohli")
    ['ben stokes']

    >>> resolve_bowlers("general analysis")
    ['mitchell starc', 'ben stokes', 'pat cummins', 'jofra archer']
    """
    text_lower = text.lower()
    found: list[str] = []

    # 1. Check for group keywords first
    for keyword, members in BOWLER_GROUPS.items():
        if keyword in text_lower:
            for bowler in members:
                if bowler not in found:
                    found.append(bowler)

    # 2. Also pick up any individually named bowlers
    for bowler in BOWLER_STATS:
        if bowler in text_lower and bowler not in found:
            found.append(bowler)

    # 3. Fallback: all bowlers
    if not found:
        found = list(BOWLER_STATS.keys())

    return found

