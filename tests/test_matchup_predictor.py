import json
# pyrefly: ignore [missing-import]
import pytest
from unittest.mock import patch, MagicMock

from src.agents.matchup_predictor import (
    MatchupPredictorAgent,
    MatchupFactor,
    HeadToHeadFactor,
    BatterRecentFormFactor,
    BowlerRecentFormFactor,
    VenueConditionsFactor,
    WeatherConditionsFactor,
    StrengthWeaknessMatchupFactor,
)


@pytest.fixture
def agent():
    return MatchupPredictorAgent()


class TestMatchupPredictorAgent:

    @patch("src.agents.matchup_predictor.ollama.chat")
    def test_end_to_end_prediction_format(self, mock_chat, agent):
        # Mock LLM verdict response
        mock_response = MagicMock()
        mock_response = {
            "message": {
                "content": "Starc has a clear edge early due to swing, but Kohli's recent ODI form suggests he will recover and score well in Mumbai."
            }
        }
        mock_chat.return_value = mock_response

        # Execute prediction
        result_str = agent.run("Will Virat Kohli score runs against Mitchell Starc at Mumbai in ODI format?")
        
        # Verify result contains the predictor marker and progress bars
        assert "=== PLAYER MATCHUP PREDICTOR ===" in result_str
        assert "Batting Dominance Probability" in result_str
        assert "Dismissal Probability" in result_str
        
        # Extract JSON
        json_start = result_str.find("{")
        json_end = result_str.rfind("}") + 1
        json_data = json.loads(result_str[json_start:json_end])
        
        # Verify required keys and schema
        assert json_data["batsman"] == "Virat Kohli"
        assert json_data["bowler"] == "Mitchell Starc"
        assert "dismissal_probability" in json_data
        assert "batting_dominance_probability" in json_data
        assert "expected_runs" in json_data
        assert "expected_strike_rate" in json_data
        assert "confidence" in json_data
        assert "key_factors" in json_data
        assert "verdict" in json_data
        
        # Verify constraint: sum of probabilities is 100%
        assert json_data["dismissal_probability"] + json_data["batting_dominance_probability"] == 100

    def test_prediction_pipeline_determinism(self, agent):
        # Run prediction twice with same input; check that values are completely identical (no randomness)
        with patch("src.agents.matchup_predictor.ollama.chat") as mock_chat:
            mock_chat.return_value = {"message": {"content": "Mocked verdict"}}
            
            res1 = agent.run("Virat Kohli vs Mitchell Starc at Perth T20")
            res2 = agent.run("Virat Kohli vs Mitchell Starc at Perth T20")
            
            assert res1 == res2

    def test_modular_factor_addition(self, agent):
        # Test that we can add/modify weights and factors easily without breaking prediction
        class CustomFatigueFactor(MatchupFactor):
            def calculate(self, context: dict) -> tuple[float, float, str]:
                # Custom factor returns a neutral score but adds fatigue description
                return 0.4, 1.0, "Batter shows mild fatigue due to recent matches."
                
        # Register new factor and change pipeline weights
        original_pipeline = agent.pipeline.copy()
        try:
            agent.pipeline["fatigue"] = (CustomFatigueFactor(), 0.05)
            # Re-scale original weights to make sum 0.95
            for k, (f, w) in original_pipeline.items():
                agent.pipeline[k] = (f, w * 0.95)
                
            with patch("src.agents.matchup_predictor.ollama.chat") as mock_chat:
                mock_chat.return_value = {"message": {"content": "Mocked verdict"}}
                res = agent.run("Virat Kohli vs Mitchell Starc at Perth T20")
                
                # Check that custom factor description is present in key factors
                json_start = res.find("{")
                json_end = res.rfind("}") + 1
                json_data = json.loads(res[json_start:json_end])
                assert any("fatigue" in f for f in json_data["key_factors"])
        finally:
            # Restore pipeline
            agent.pipeline = original_pipeline

    def test_weather_fallback_logic(self, agent):
        context = {
            "batsman": "virat kohli",
            "bowler": "mitchell starc",
            "venue": "perth",
            "format": "Test",
            "weather": {"error": "API Key Missing"},
        }
        
        # Test weather conditions factor handles errors gracefully
        factor = WeatherConditionsFactor()
        score, data_points, desc = factor.calculate(context)
        assert score == 0.5
        assert data_points == 0.5
        assert "neutral" in desc.lower()

    def test_strength_weakness_matchup(self):
        context = {
            "batsman": "ms dhoni",
            "bowler": "pat cummins",
            "venue": "mumbai",
            "format": "ODI",
        }
        
        # Test strength/weakness overlap calculation
        factor = StrengthWeaknessMatchupFactor()
        score, data_points, desc = factor.calculate(context)
        
        # Pat Cummins has "steep bounce" and "seam off the pitch"
        # MS Dhoni has weaknesses "wide short balls" and "spin bowling"
        # There shouldn't be high overlaps, so score is neutral 0.5 or close to it
        assert 0.0 <= score <= 1.0
        assert data_points == 1.5
