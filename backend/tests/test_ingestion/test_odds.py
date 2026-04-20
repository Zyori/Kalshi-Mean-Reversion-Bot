import pytest

from src.ingestion.odds import american_to_implied_prob


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
