def normalize(value: float, min_val: float, max_val: float) -> float:
    if max_val <= min_val:
        return 0.0
    clamped = max(min_val, min(max_val, value))
    return (clamped - min_val) / (max_val - min_val)


def _score_deficit(
    *,
    home_score: int | None,
    away_score: int | None,
    sport: str,
) -> float:
    if home_score is None or away_score is None:
        return 0.0

    deficit = abs(home_score - away_score)
    ranges = {
        "nhl": (1, 3),
        "nba": (3, 12),
        "mlb": (1, 4),
        "nfl": (3, 14),
        "soccer": (1, 2),
        "ufc": (1, 2),
    }
    min_deficit, max_deficit = ranges.get(sport, (1, 4))
    return normalize(deficit, min_deficit, max_deficit)


def _source_bonus(market_source: str | None) -> float:
    if market_source == "kalshi_demo":
        return 0.12
    if market_source == "synthetic":
        return -0.08
    return 0.0


def score_opportunity(
    deviation: float,
    time_remaining_pct: float,
    *,
    sport: str = "",
    home_score: int | None = None,
    away_score: int | None = None,
    market_source: str | None = None,
    deviation_weight: float = 0.5,
    time_weight: float = 0.25,
    deficit_weight: float = 0.25,
) -> float:
    dev_score = normalize(deviation, 0.05, 0.30)
    time_score = normalize(time_remaining_pct, 0.25, 0.90)
    deficit_score = _score_deficit(
        home_score=home_score,
        away_score=away_score,
        sport=sport,
    )
    base = (
        deviation_weight * dev_score
        + time_weight * time_score
        + deficit_weight * deficit_score
        + _source_bonus(market_source)
    )
    return round(max(0.0, min(1.0, base)), 4)
