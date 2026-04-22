import pytest

from src.ingestion.odds import _parse_odds_response, american_to_implied_prob


class TestAmericanToImpliedProb:
    def test_negative_odds(self):
        prob = american_to_implied_prob(-150)
        assert prob == pytest.approx(0.60)

    def test_positive_odds(self):
        prob = american_to_implied_prob(150)
        assert prob == pytest.approx(0.40)

    def test_even_money(self):
        prob = american_to_implied_prob(100)
        assert prob == pytest.approx(0.50)

    def test_heavy_favorite(self):
        prob = american_to_implied_prob(-300)
        assert prob == pytest.approx(0.75)

    def test_heavy_underdog(self):
        prob = american_to_implied_prob(300)
        assert prob == pytest.approx(0.25)

    def test_minus_100(self):
        prob = american_to_implied_prob(-100)
        assert prob == pytest.approx(0.50)

    def test_complementary(self):
        p1 = american_to_implied_prob(-150)
        p2 = american_to_implied_prob(150)
        assert p1 + p2 == pytest.approx(1.0)


def test_parse_odds_response_extracts_spreads_totals_and_team_totals():
    rows = _parse_odds_response(
        [
            {
                "home_team": "Boston Celtics",
                "away_team": "New York Knicks",
                "commence_time": "2026-04-22T23:00:00Z",
                "bookmakers": [
                    {
                        "key": "draftkings",
                        "markets": [
                            {
                                "key": "h2h",
                                "outcomes": [
                                    {"name": "Boston Celtics", "price": -150},
                                    {"name": "New York Knicks", "price": 130},
                                ],
                            },
                            {
                                "key": "spreads",
                                "outcomes": [
                                    {"name": "Boston Celtics", "price": -110, "point": -4.5},
                                    {"name": "New York Knicks", "price": -110, "point": 4.5},
                                ],
                            },
                            {
                                "key": "totals",
                                "outcomes": [
                                    {"name": "Over", "price": -110, "point": 223.5},
                                    {"name": "Under", "price": -110, "point": 223.5},
                                ],
                            },
                            {
                                "key": "team_totals",
                                "outcomes": [
                                    {
                                        "name": "Over",
                                        "description": "Boston Celtics",
                                        "price": -110,
                                        "point": 114.5,
                                    },
                                    {
                                        "name": "Over",
                                        "description": "New York Knicks",
                                        "price": -110,
                                        "point": 109.0,
                                    },
                                ],
                            },
                        ],
                    }
                ],
            }
        ],
        "nba",
    )

    assert len(rows) == 1
    row = rows[0]
    assert row["home_prob"] == pytest.approx(0.6)
    assert row["away_prob"] == pytest.approx(0.4348)
    assert row["home_spread"] == pytest.approx(-4.5)
    assert row["away_spread"] == pytest.approx(4.5)
    assert row["total_points"] == pytest.approx(223.5)
    assert row["home_team_total"] == pytest.approx(114.5)
    assert row["away_team_total"] == pytest.approx(109.0)
