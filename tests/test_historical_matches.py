import pytest
from src.services.historical_matches import (
    HistoricalMatchService,
    LocalMockHistoricalMatchProvider,
    BaseHistoricalMatchProvider
)

def test_local_provider_tournaments():
    provider = LocalMockHistoricalMatchProvider()
    tournaments = provider.get_tournaments()
    assert len(tournaments) > 0
    assert "ICC Cricket World Cup 2023" in tournaments
    assert "ICC T20 World Cup 2026" in tournaments


def test_local_provider_matches():
    provider = LocalMockHistoricalMatchProvider()
    matches = provider.get_matches_for_tournament("ICC Cricket World Cup 2023")
    assert len(matches) > 0
    assert any(m["id"] == "cwc_2023_final" for m in matches)


def test_local_provider_scorecard():
    provider = LocalMockHistoricalMatchProvider()
    scorecard = provider.get_match_scorecard("cwc_2023_final")
    assert scorecard is not None
    assert scorecard["match_title"] == "India vs Australia (Final)"
    assert scorecard["tournament"] == "ICC Cricket World Cup 2023"
    assert scorecard["venue"] == "Narendra Modi Stadium, Ahmedabad"
    assert "team_scores" in scorecard
    assert "batting_scorecard" in scorecard
    assert "bowling_figures" in scorecard
    assert scorecard["result"] == "Australia won by 6 wickets"
    assert scorecard["player_of_the_match"] == "Travis Head (Australia)"


def test_service_fallback():
    # A dummy provider that returns nothing or errors out should trigger the local mock fallback
    class EmptyProvider(BaseHistoricalMatchProvider):
        def get_tournaments(self):
            return []
        def get_matches_for_tournament(self, tournament):
            return []
        def get_match_scorecard(self, match_id):
            return None

    service = HistoricalMatchService(provider=EmptyProvider())
    
    # Tournaments should fall back to mock data
    tournaments = service.get_tournaments()
    assert len(tournaments) > 0
    assert "ICC Cricket World Cup 2023" in tournaments

    # Matches should fall back to mock data
    matches = service.get_matches_for_tournament("ICC Cricket World Cup 2023")
    assert len(matches) > 0

    # Scorecard should fall back to mock data
    scorecard = service.get_match_scorecard("cwc_2023_final")
    assert scorecard is not None
    assert scorecard["match_title"] == "India vs Australia (Final)"
