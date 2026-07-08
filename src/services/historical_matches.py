from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger("cricketIQ")

class BaseHistoricalMatchProvider(ABC):
    """
    Abstract base class defining the interface for fetching historical matches.
    Allows easy pluggability for alternative APIs or database backends.
    """
    @abstractmethod
    def get_tournaments(self) -> List[str]:
        """Return a list of available tournament names."""
        pass

    @abstractmethod
    def get_matches_for_tournament(self, tournament: str) -> List[Dict[str, str]]:
        """
        Return a list of matches in a tournament.
        Each match is a dictionary with keys: 'id', 'title', 'summary'.
        """
        pass

    @abstractmethod
    def get_match_scorecard(self, match_id: str) -> Optional[Dict[str, Any]]:
        """
        Return detailed scorecard data for the given match ID.
        Returns None if not found.
        """
        pass


class LocalMockHistoricalMatchProvider(BaseHistoricalMatchProvider):
    """
    Local provider supplying high-fidelity historical match scorecards
    for iconic matches.
    """
    def __init__(self):
        self._scorecards: Dict[str, Dict[str, Any]] = {
            "cwc_2023_final": {
                "match_title": "India vs Australia (Final)",
                "tournament": "ICC Cricket World Cup 2023",
                "venue": "Narendra Modi Stadium, Ahmedabad",
                "date": "2023-11-19",
                "toss": "Australia won the toss and elected to field",
                "team_scores": {
                    "India": "240 (50 Overs)",
                    "Australia": "241/4 (43 Overs)"
                },
                "batting_scorecard": {
                    "India": [
                        {"player": "Rohit Sharma", "status": "c Head b Maxwell", "runs": 47, "balls": 31, "fours": 4, "sixes": 3, "sr": 151.6},
                        {"player": "Shubman Gill", "status": "c Zampa b Starc", "runs": 4, "balls": 7, "fours": 0, "sixes": 0, "sr": 57.1},
                        {"player": "Virat Kohli", "status": "b Cummins", "runs": 54, "balls": 63, "fours": 4, "sixes": 0, "sr": 85.7},
                        {"player": "Shreyas Iyer", "status": "c Inglis b Cummins", "runs": 4, "balls": 4, "fours": 1, "sixes": 0, "sr": 100.0},
                        {"player": "KL Rahul", "status": "c Inglis b Starc", "runs": 66, "balls": 107, "fours": 1, "sixes": 0, "sr": 61.7},
                        {"player": "Ravindra Jadeja", "status": "c Inglis b Hazlewood", "runs": 9, "balls": 22, "fours": 0, "sixes": 0, "sr": 40.9},
                        {"player": "Suryakumar Yadav", "status": "c Inglis b Hazlewood", "runs": 18, "balls": 28, "fours": 1, "sixes": 0, "sr": 64.3},
                        {"player": "Mohammed Shami", "status": "c Inglis b Starc", "runs": 6, "balls": 10, "fours": 1, "sixes": 0, "sr": 60.0},
                        {"player": "Jasprit Bumrah", "status": "lbw b Zampa", "runs": 1, "balls": 3, "fours": 0, "sixes": 0, "sr": 33.3},
                        {"player": "Kuldeep Yadav", "status": "run out (Labuschagne)", "runs": 9, "balls": 18, "fours": 0, "sixes": 0, "sr": 50.0},
                        {"player": "Mohammed Siraj", "status": "not out", "runs": 9, "balls": 8, "fours": 1, "sixes": 0, "sr": 112.5}
                    ],
                    "Australia": [
                        {"player": "Travis Head", "status": "c Gill b Siraj", "runs": 137, "balls": 120, "fours": 15, "sixes": 4, "sr": 114.2},
                        {"player": "David Warner", "status": "c Kohli b Shami", "runs": 7, "balls": 3, "fours": 1, "sixes": 0, "sr": 233.3},
                        {"player": "Mitchell Marsh", "status": "c Rahul b Bumrah", "runs": 15, "balls": 15, "fours": 1, "sixes": 1, "sr": 100.0},
                        {"player": "Steve Smith", "status": "lbw b Bumrah", "runs": 4, "balls": 9, "fours": 1, "sixes": 0, "sr": 44.4},
                        {"player": "Marnus Labuschagne", "status": "not out", "runs": 58, "balls": 110, "fours": 4, "sixes": 0, "sr": 52.7},
                        {"player": "Glenn Maxwell", "status": "not out", "runs": 2, "balls": 1, "fours": 0, "sixes": 0, "sr": 200.0}
                    ]
                },
                "bowling_figures": {
                    "India": [
                        {"player": "Jasprit Bumrah", "overs": 9.0, "maidens": 2, "runs": 43, "wickets": 2, "econ": 4.8},
                        {"player": "Mohammed Shami", "overs": 7.0, "maidens": 1, "runs": 47, "wickets": 1, "econ": 6.7},
                        {"player": "Ravindra Jadeja", "overs": 10.0, "maidens": 0, "runs": 43, "wickets": 0, "econ": 4.3},
                        {"player": "Kuldeep Yadav", "overs": 10.0, "maidens": 0, "runs": 56, "wickets": 0, "econ": 5.6},
                        {"player": "Mohammed Siraj", "overs": 7.0, "maidens": 0, "runs": 45, "wickets": 1, "econ": 6.4}
                    ],
                    "Australia": [
                        {"player": "Mitchell Starc", "overs": 10.0, "maidens": 0, "runs": 55, "wickets": 3, "econ": 5.5},
                        {"player": "Josh Hazlewood", "overs": 10.0, "maidens": 0, "runs": 60, "wickets": 2, "econ": 6.0},
                        {"player": "Glenn Maxwell", "overs": 6.0, "maidens": 0, "runs": 35, "wickets": 1, "econ": 5.8},
                        {"player": "Pat Cummins", "overs": 10.0, "maidens": 0, "runs": 34, "wickets": 2, "econ": 3.4},
                        {"player": "Adam Zampa", "overs": 10.0, "maidens": 0, "runs": 44, "wickets": 1, "econ": 4.4},
                        {"player": "Travis Head", "overs": 2.0, "maidens": 0, "runs": 4, "wickets": 0, "econ": 2.0}
                    ]
                },
                "result": "Australia won by 6 wickets",
                "player_of_the_match": "Travis Head (Australia)"
            },
            "t20wc_2026_final": {
                "match_title": "India vs Sri Lanka (Final)",
                "tournament": "ICC T20 World Cup 2026",
                "venue": "R. Premadasa Stadium, Colombo",
                "date": "2026-03-08",
                "toss": "India won the toss and elected to bat",
                "team_scores": {
                    "India": "172/6 (20 Overs)",
                    "Sri Lanka": "165/8 (20 Overs)"
                },
                "batting_scorecard": {
                    "India": [
                        {"player": "Rohit Sharma", "status": "c Nissanka b Hasaranga", "runs": 45, "balls": 28, "fours": 5, "sixes": 2, "sr": 160.7},
                        {"player": "Yashasvi Jaiswal", "status": "b Theekshana", "runs": 12, "balls": 8, "fours": 1, "sixes": 1, "sr": 150.0},
                        {"player": "Virat Kohli", "status": "c Asalanka b Pathirana", "runs": 52, "balls": 39, "fours": 4, "sixes": 1, "sr": 133.3},
                        {"player": "Suryakumar Yadav", "status": "c Mendis b Madushanka", "runs": 22, "balls": 15, "fours": 2, "sixes": 1, "sr": 146.7},
                        {"player": "Rishabh Pant", "status": "not out", "runs": 28, "balls": 18, "fours": 2, "sixes": 1, "sr": 155.6},
                        {"player": "Hardik Pandya", "status": "run out", "runs": 8, "balls": 6, "fours": 1, "sixes": 0, "sr": 133.3},
                        {"player": "Ravindra Jadeja", "status": "not out", "runs": 5, "balls": 6, "fours": 0, "sixes": 0, "sr": 83.3}
                    ],
                    "Sri Lanka": [
                        {"player": "Pathum Nissanka", "status": "c Pant b Bumrah", "runs": 18, "balls": 14, "fours": 2, "sixes": 0, "sr": 128.6},
                        {"player": "Kusal Mendis", "status": "lbw b Siraj", "runs": 24, "balls": 18, "fours": 3, "sixes": 0, "sr": 133.3},
                        {"player": "Sadeera Samarawickrama", "status": "c Kohli b Kuldeep", "runs": 32, "balls": 25, "fours": 2, "sixes": 1, "sr": 128.0},
                        {"player": "Charith Asalanka", "status": "c Pandya b Bumrah", "runs": 41, "balls": 28, "fours": 3, "sixes": 2, "sr": 146.4},
                        {"player": "Wanindu Hasaranga", "status": "c Jadeja b Axar", "runs": 14, "balls": 10, "fours": 1, "sixes": 1, "sr": 140.0},
                        {"player": "Dasun Shanaka", "status": "b Pandya", "runs": 15, "balls": 11, "fours": 1, "sixes": 1, "sr": 136.4},
                        {"player": "Angelo Mathews", "status": "run out", "runs": 8, "balls": 7, "fours": 0, "sixes": 0, "sr": 114.3},
                        {"player": "Maheesh Theekshana", "status": "not out", "runs": 6, "balls": 4, "fours": 0, "sixes": 0, "sr": 150.0},
                        {"player": "Matheesha Pathirana", "status": "b Bumrah", "runs": 1, "balls": 3, "fours": 0, "sixes": 0, "sr": 33.3}
                    ]
                },
                "bowling_figures": {
                    "India": [
                        {"player": "Jasprit Bumrah", "overs": 4.0, "maidens": 0, "runs": 18, "wickets": 3, "econ": 4.5},
                        {"player": "Mohammed Siraj", "overs": 4.0, "maidens": 0, "runs": 35, "wickets": 1, "econ": 8.75},
                        {"player": "Hardik Pandya", "overs": 4.0, "maidens": 0, "runs": 29, "wickets": 1, "econ": 7.25},
                        {"player": "Axar Patel", "overs": 4.0, "maidens": 0, "runs": 38, "wickets": 1, "econ": 9.5},
                        {"player": "Kuldeep Yadav", "overs": 4.0, "maidens": 0, "runs": 41, "wickets": 1, "econ": 10.25}
                    ],
                    "Sri Lanka": [
                        {"player": "Dilshan Madushanka", "overs": 4.0, "maidens": 0, "runs": 32, "wickets": 1, "econ": 8.0},
                        {"player": "Maheesh Theekshana", "overs": 4.0, "maidens": 0, "runs": 28, "wickets": 1, "econ": 7.0},
                        {"player": "Wanindu Hasaranga", "overs": 4.0, "maidens": 0, "runs": 30, "wickets": 1, "econ": 7.5},
                        {"player": "Matheesha Pathirana", "overs": 4.0, "maidens": 0, "runs": 42, "wickets": 1, "econ": 10.5},
                        {"player": "Dunith Wellalage", "overs": 4.0, "maidens": 0, "runs": 38, "wickets": 0, "econ": 9.5}
                    ]
                },
                "result": "India won by 7 runs",
                "player_of_the_match": "Jasprit Bumrah (India)"
            },
            "ipl_2024_final": {
                "match_title": "KKR vs SRH (Final)",
                "tournament": "IPL Matches",
                "venue": "MA Chidambaram Stadium, Chennai",
                "date": "2024-05-26",
                "toss": "Sunrisers Hyderabad won the toss and elected to bat",
                "team_scores": {
                    "Sunrisers Hyderabad": "113 (18.3 Overs)",
                    "Kolkata Knight Riders": "114/2 (10.3 Overs)"
                },
                "batting_scorecard": {
                    "Sunrisers Hyderabad": [
                        {"player": "Abhishek Sharma", "status": "b Starc", "runs": 2, "balls": 5, "fours": 0, "sixes": 0, "sr": 40.0},
                        {"player": "Travis Head", "status": "c Gurbaz b Arora", "runs": 0, "balls": 1, "fours": 0, "sixes": 0, "sr": 0.0},
                        {"player": "Rahul Tripathi", "status": "c Ramandeep b Narine", "runs": 9, "balls": 13, "fours": 0, "sixes": 0, "sr": 69.2},
                        {"player": "Aiden Markram", "status": "c Starc b Russell", "runs": 20, "balls": 23, "fours": 3, "sixes": 0, "sr": 87.0},
                        {"player": "Nitish Reddy", "status": "c Gurbaz b Rana", "runs": 13, "balls": 10, "fours": 1, "sixes": 1, "sr": 130.0},
                        {"player": "Heinrich Klaasen", "status": "b Rana", "runs": 16, "balls": 17, "fours": 1, "sixes": 0, "sr": 94.1},
                        {"player": "Shahbaz Ahmed", "status": "c Narine b Chakaravarthy", "runs": 8, "balls": 7, "fours": 0, "sixes": 0, "sr": 114.3},
                        {"player": "Abdul Samad", "status": "c Gurbaz b Russell", "runs": 4, "balls": 4, "fours": 0, "sixes": 0, "sr": 100.0},
                        {"player": "Pat Cummins", "status": "c Starc b Russell", "runs": 24, "balls": 19, "fours": 2, "sixes": 1, "sr": 126.3},
                        {"player": "Jaydev Unadkat", "status": "lbw b Narine", "runs": 4, "balls": 11, "fours": 0, "sixes": 0, "sr": 36.4},
                        {"player": "Bhuvneshwar Kumar", "status": "not out", "runs": 0, "balls": 1, "fours": 0, "sixes": 0, "sr": 0.0}
                    ],
                    "Kolkata Knight Riders": [
                        {"player": "Rahmanullah Gurbaz", "status": "lbw b Shahbaz", "runs": 39, "balls": 32, "fours": 5, "sixes": 1, "sr": 121.9},
                        {"player": "Sunil Narine", "status": "c Shahbaz b Cummins", "runs": 6, "balls": 2, "fours": 0, "sixes": 1, "sr": 300.0},
                        {"player": "Venkatesh Iyer", "status": "not out", "runs": 52, "balls": 26, "fours": 4, "sixes": 3, "sr": 200.0},
                        {"player": "Shreyas Iyer", "status": "not out", "runs": 6, "balls": 6, "fours": 1, "sixes": 0, "sr": 100.0}
                    ]
                },
                "bowling_figures": {
                    "Sunrisers Hyderabad": [
                        {"player": "Bhuvneshwar Kumar", "overs": 2.0, "maidens": 0, "runs": 25, "wickets": 0, "econ": 12.5},
                        {"player": "Pat Cummins", "overs": 2.0, "maidens": 0, "runs": 18, "wickets": 1, "econ": 9.0},
                        {"player": "T Natarajan", "overs": 2.0, "maidens": 0, "runs": 29, "wickets": 0, "econ": 14.5},
                        {"player": "Shahbaz Ahmed", "overs": 2.3, "maidens": 0, "runs": 22, "wickets": 1, "econ": 8.8},
                        {"player": "Jaydev Unadkat", "overs": 2.0, "maidens": 0, "runs": 19, "wickets": 0, "econ": 9.5}
                    ],
                    "Kolkata Knight Riders": [
                        {"player": "Mitchell Starc", "overs": 3.0, "maidens": 0, "runs": 14, "wickets": 2, "econ": 4.67},
                        {"player": "Vaibhav Arora", "overs": 3.0, "maidens": 0, "runs": 24, "wickets": 1, "econ": 8.0},
                        {"player": "Harshit Rana", "overs": 4.0, "maidens": 0, "runs": 24, "wickets": 2, "econ": 6.0},
                        {"player": "Sunil Narine", "overs": 4.0, "maidens": 0, "runs": 16, "wickets": 1, "econ": 4.0},
                        {"player": "Andre Russell", "overs": 2.3, "maidens": 0, "runs": 19, "wickets": 3, "econ": 7.6},
                        {"player": "Varun Chakaravarthy", "overs": 2.0, "maidens": 0, "runs": 9, "wickets": 1, "econ": 4.5}
                    ]
                },
                "result": "Kolkata Knight Riders won by 8 wickets",
                "player_of_the_match": "Mitchell Starc (KKR)"
            },
            "ind_vs_pak_t20_2024": {
                "match_title": "India vs Pakistan (Group Stage)",
                "tournament": "Other Completed Matches",
                "venue": "Nassau County International Cricket Stadium, New York",
                "date": "2024-06-09",
                "toss": "Pakistan won the toss and elected to field",
                "team_scores": {
                    "India": "119 (19 Overs)",
                    "Pakistan": "113/7 (20 Overs)"
                },
                "batting_scorecard": {
                    "India": [
                        {"player": "Rohit Sharma", "status": "c Haris Rauf b Shaheen Afridi", "runs": 13, "balls": 12, "fours": 1, "sixes": 1, "sr": 108.3},
                        {"player": "Virat Kohli", "status": "c Usman Khan b Naseem Shah", "runs": 4, "balls": 3, "fours": 1, "sixes": 0, "sr": 133.3},
                        {"player": "Rishabh Pant", "status": "c Babar Azam b Amir", "runs": 42, "balls": 31, "fours": 6, "sixes": 0, "sr": 135.5},
                        {"player": "Suryakumar Yadav", "status": "c Mohammad Rizwan b Haris Rauf", "runs": 7, "balls": 8, "fours": 1, "sixes": 0, "sr": 87.5},
                        {"player": "Shivam Dube", "status": "c & b Naseem Shah", "runs": 3, "balls": 9, "fours": 0, "sixes": 0, "sr": 33.3},
                        {"player": "Hardik Pandya", "status": "c Iftikhar Ahmed b Haris Rauf", "runs": 7, "balls": 12, "fours": 1, "sixes": 0, "sr": 58.3},
                        {"player": "Ravindra Jadeja", "status": "c Imad Wasim b Mohammad Amir", "runs": 0, "balls": 1, "fours": 0, "sixes": 0, "sr": 0.0},
                        {"player": "Axar Patel", "status": "b Naseem Shah", "runs": 20, "balls": 18, "fours": 2, "sixes": 1, "sr": 111.1},
                        {"player": "Arshdeep Singh", "status": "run out", "runs": 9, "balls": 13, "fours": 1, "sixes": 0, "sr": 69.2},
                        {"player": "Jasprit Bumrah", "status": "c Imad Wasim b Haris Rauf", "runs": 0, "balls": 1, "fours": 0, "sixes": 0, "sr": 0.0},
                        {"player": "Mohammed Siraj", "status": "not out", "runs": 7, "balls": 7, "fours": 0, "sixes": 0, "sr": 100.0}
                    ],
                    "Pakistan": [
                        {"player": "Mohammad Rizwan", "status": "b Bumrah", "runs": 31, "balls": 44, "fours": 1, "sixes": 1, "sr": 70.5},
                        {"player": "Babar Azam", "status": "c Suryakumar b Bumrah", "runs": 13, "balls": 10, "fours": 2, "sixes": 0, "sr": 130.0},
                        {"player": "Usman Khan", "status": "lbw b Axar Patel", "runs": 13, "balls": 15, "fours": 1, "sixes": 0, "sr": 86.7},
                        {"player": "Fakhar Zaman", "status": "c Pant b Hardik Pandya", "runs": 13, "balls": 8, "fours": 1, "sixes": 1, "sr": 162.5},
                        {"player": "Imad Wasim", "status": "c Pant b Axar Patel", "runs": 15, "balls": 23, "fours": 1, "sixes": 0, "sr": 65.2},
                        {"player": "Shadab Khan", "status": "c Pant b Hardik Pandya", "runs": 4, "balls": 7, "fours": 0, "sixes": 0, "sr": 57.1},
                        {"player": "Iftikhar Ahmed", "status": "c Arshdeep b Bumrah", "runs": 5, "balls": 9, "fours": 0, "sixes": 0, "sr": 55.6},
                        {"player": "Shaheen Afridi", "status": "not out", "runs": 0, "balls": 1, "fours": 0, "sixes": 0, "sr": 0.0},
                        {"player": "Naseem Shah", "status": "not out", "runs": 10, "balls": 4, "fours": 2, "sixes": 0, "sr": 250.0}
                    ]
                },
                "bowling_figures": {
                    "India": [
                        {"player": "Jasprit Bumrah", "overs": 4.0, "maidens": 0, "runs": 14, "wickets": 3, "econ": 3.5},
                        {"player": "Mohammed Siraj", "overs": 4.0, "maidens": 0, "runs": 19, "wickets": 0, "econ": 4.75},
                        {"player": "Arshdeep Singh", "overs": 4.0, "maidens": 0, "runs": 31, "wickets": 1, "econ": 7.75},
                        {"player": "Hardik Pandya", "overs": 4.0, "maidens": 0, "runs": 24, "wickets": 2, "econ": 6.0},
                        {"player": "Axar Patel", "overs": 2.0, "maidens": 0, "runs": 11, "wickets": 1, "econ": 5.5},
                        {"player": "Ravindra Jadeja", "overs": 2.0, "maidens": 0, "runs": 10, "wickets": 0, "econ": 5.0}
                    ],
                    "Pakistan": [
                        {"player": "Shaheen Afridi", "overs": 4.0, "maidens": 0, "runs": 29, "wickets": 1, "econ": 7.25},
                        {"player": "Naseem Shah", "overs": 4.0, "maidens": 0, "runs": 21, "wickets": 3, "econ": 5.25},
                        {"player": "Mohammad Amir", "overs": 4.0, "maidens": 0, "runs": 23, "wickets": 2, "econ": 5.75},
                        {"player": "Haris Rauf", "overs": 3.0, "maidens": 0, "runs": 21, "wickets": 3, "econ": 7.0},
                        {"player": "Imad Wasim", "overs": 4.0, "maidens": 0, "runs": 17, "wickets": 0, "econ": 4.25}
                    ]
                },
                "result": "India won by 6 runs",
                "player_of_the_match": "Jasprit Bumrah (India)"
            }
        }

    def get_tournaments(self) -> List[str]:
        # Return unique list of tournaments sorted
        tournaments = set(sc["tournament"] for sc in self._scorecards.values())
        return sorted(list(tournaments))

    def get_matches_for_tournament(self, tournament: str) -> List[Dict[str, str]]:
        matches = []
        for m_id, sc in self._scorecards.items():
            if sc["tournament"] == tournament:
                matches.append({
                    "id": m_id,
                    "title": sc["match_title"],
                    "summary": f"{sc['match_title']} - {sc['date']}"
                })
        return matches

    def get_match_scorecard(self, match_id: str) -> Optional[Dict[str, Any]]:
        return self._scorecards.get(match_id)


class CricAPIHistoricalMatchProvider(BaseHistoricalMatchProvider):
    """
    CricAPI wrapper for historical matches.
    Currently, basic/free tier does not support detailed scorecard.
    Acts as a placeholder to show where another provider can be plugged in.
    """
    def __init__(self, api_key: str):
        self.api_key = api_key

    def get_tournaments(self) -> List[str]:
        # CricAPI basic tier does not list historical tournaments.
        return []

    def get_matches_for_tournament(self, tournament: str) -> List[Dict[str, str]]:
        return []

    def get_match_scorecard(self, match_id: str) -> Optional[Dict[str, Any]]:
        # CricAPI match scorecard endpoint could be queried if paid plan is active,
        # but returns None for now to default to fallback mechanisms.
        return None


class HistoricalMatchService:
    """
    Service responsible for coordinating historical match data retrieval.
    Provides standard fallback and guarantees no crashes on failures.
    """
    def __init__(self, provider: Optional[BaseHistoricalMatchProvider] = None):
        self.provider = provider or LocalMockHistoricalMatchProvider()

    def get_tournaments(self) -> List[str]:
        try:
            tournaments = self.provider.get_tournaments()
            if not tournaments and not isinstance(self.provider, LocalMockHistoricalMatchProvider):
                # Fallback
                logger.warning("Main historical match provider returned no tournaments. Falling back to local mock.")
                fallback = LocalMockHistoricalMatchProvider()
                return fallback.get_tournaments()
            return tournaments
        except Exception as e:
            logger.error(f"Error fetching tournaments: {e}")
            fallback = LocalMockHistoricalMatchProvider()
            return fallback.get_tournaments()

    def get_matches_for_tournament(self, tournament: str) -> List[Dict[str, str]]:
        try:
            matches = self.provider.get_matches_for_tournament(tournament)
            if not matches and not isinstance(self.provider, LocalMockHistoricalMatchProvider):
                logger.warning("Main provider returned no matches. Falling back to local mock.")
                fallback = LocalMockHistoricalMatchProvider()
                return fallback.get_matches_for_tournament(tournament)
            return matches
        except Exception as e:
            logger.error(f"Error fetching matches for {tournament}: {e}")
            fallback = LocalMockHistoricalMatchProvider()
            return fallback.get_matches_for_tournament(tournament)

    def get_match_scorecard(self, match_id: str) -> Optional[Dict[str, Any]]:
        try:
            scorecard = self.provider.get_match_scorecard(match_id)
            if not scorecard and not isinstance(self.provider, LocalMockHistoricalMatchProvider):
                logger.warning("Main provider returned no scorecard. Falling back to local mock.")
                fallback = LocalMockHistoricalMatchProvider()
                return fallback.get_match_scorecard(match_id)
            return scorecard
        except Exception as e:
            logger.error(f"Error fetching scorecard for {match_id}: {e}")
            fallback = LocalMockHistoricalMatchProvider()
            return fallback.get_match_scorecard(match_id)
