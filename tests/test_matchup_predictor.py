import json
# pyrefly: ignore [missing-import]
import pytest
from unittest.mock import patch, MagicMock

from src.agents.matchup_predictor import MatchupPredictorAgent


@pytest.fixture
def agent():
    return MatchupPredictorAgent()


class TestMatchupPredictorAgent:

    @patch("src.agents.matchup_predictor.invoke_llm")
    def test_run_with_prefetched_stats(self, mock_invoke, agent):
        mock_invoke.return_value = "Mocked LLM Matchup Verdict"

        batter_stats = {
            "name": "Virat Kohli",
            "country": "India",
            "role": "Batter",
            "batting_stats": {
                "odi": {
                    "avg": "58.6",
                    "sr": "93.5",
                    "runs": "13000",
                    "hs": "183",
                    "100s": "50",
                    "50s": "72"
                }
            }
        }
        bowler_stats = {
            "name": "Mitchell Starc",
            "country": "Australia",
            "role": "Bowler",
            "bowling_stats": {
                "odi": {
                    "wkts": "220",
                    "avg": "23.2",
                    "econ": "5.1",
                    "sr": "27.2",
                    "bbi": "6/28"
                }
            }
        }

        # Mock CricAPI to ensure it is NEVER called
        with patch.object(agent.cric_api, "get_player_stats") as mock_get_stats:
            res = agent.run(
                task="Virat Kohli vs Mitchell Starc ODI",
                batter_name="Virat Kohli",
                bowler_name="Mitchell Starc",
                batter_stats=batter_stats,
                bowler_stats=bowler_stats
            )
            
            # get_player_stats should not be called
            mock_get_stats.assert_not_called()
            assert "PLAYER MATCHUP PREDICTION" in res
            assert "Virat Kohli" in res
            assert "Mitchell Starc" in res
            assert "Mocked LLM Matchup Verdict" in res

    @patch("src.agents.matchup_predictor.invoke_llm")
    def test_run_without_prefetched_stats(self, mock_invoke, agent):
        mock_invoke.return_value = "Mocked LLM Matchup Verdict"

        batter_stats = {
            "name": "Virat Kohli",
            "country": "India",
            "role": "Batter",
            "batting_stats": {
                "odi": {
                    "avg": "58.6"
                }
            }
        }
        bowler_stats = {
            "name": "Mitchell Starc",
            "country": "Australia",
            "role": "Bowler",
            "bowling_stats": {
                "odi": {
                    "wkts": "220"
                }
            }
        }

        with patch.object(agent.cric_api, "get_player_stats") as mock_get_stats:
            mock_get_stats.side_effect = [batter_stats, bowler_stats]
            
            res = agent.run(
                task="Virat Kohli vs Mitchell Starc ODI",
                batter_name="Virat Kohli",
                bowler_name="Mitchell Starc"
            )
            
            assert mock_get_stats.call_count == 2
            assert "PLAYER MATCHUP PREDICTION" in res
            assert "Virat Kohli" in res
            assert "Mitchell Starc" in res
