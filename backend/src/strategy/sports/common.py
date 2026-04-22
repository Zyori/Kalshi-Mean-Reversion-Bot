def favorite_behind(
    *,
    home_score: int,
    away_score: int,
    is_home_favorite: bool,
) -> bool:
    return (is_home_favorite and home_score < away_score) or (
        not is_home_favorite and away_score < home_score
    )


def score_deficit(home_score: int, away_score: int) -> int:
    return abs(home_score - away_score)


STRUCTURAL_EVENT_TOKENS: tuple[str, ...] = (
    "red card",
    "goalie pulled",
    "empty net",
    "injury",
    "ejection",
    "disqualification",
    "knockout",
)

HIGH_LEVERAGE_EVENT_TOKENS: tuple[str, ...] = (
    "timeout",
    "technical",
    "flagrant",
    "turnover",
    "steal",
    "interception",
    "fumble",
    "red zone",
    "penalty",
)

SCORING_EVENT_TOKENS: tuple[str, ...] = (
    "goal",
    "home run",
    "touchdown",
    "field goal",
    "safety",
    "double",
    "triple",
    "single",
    "walk",
    "layup",
    "jumper",
    "three point",
    "free throw",
    "dunk",
)


SPORT_SEGMENTS: dict[str, int] = {
    "nhl": 3,
    "nba": 4,
    "mlb": 9,
    "nfl": 4,
    "soccer": 2,
    "ufc": 3,
}

SPREAD_CANDIDATE_EDGES: dict[str, tuple[float, float]] = {
    "nhl": (1.0, 2.0),
    "nba": (3.0, 8.0),
    "mlb": (1.0, 2.5),
    "nfl": (3.0, 7.0),
    "soccer": (0.8, 1.5),
    "ufc": (1.0, 1.5),
}

SPREAD_STRUCTURAL_EDGES: dict[str, float] = {
    "nhl": 3.0,
    "nba": 12.0,
    "mlb": 4.0,
    "nfl": 14.0,
    "soccer": 2.5,
    "ufc": 2.0,
}

TOTAL_CANDIDATE_EDGES: dict[str, tuple[float, float]] = {
    "nhl": (0.8, 2.0),
    "nba": (8.0, 24.0),
    "mlb": (1.0, 3.0),
    "nfl": (4.0, 14.0),
    "soccer": (0.6, 1.5),
    "ufc": (0.5, 1.0),
}

TOTAL_STRUCTURAL_EDGES: dict[str, float] = {
    "nhl": 3.0,
    "nba": 30.0,
    "mlb": 4.0,
    "nfl": 18.0,
    "soccer": 2.0,
    "ufc": 1.5,
}

TEAM_TOTAL_CANDIDATE_EDGES: dict[str, tuple[float, float]] = {
    "nhl": (0.5, 1.5),
    "nba": (4.0, 12.0),
    "mlb": (0.5, 2.0),
    "nfl": (2.0, 8.0),
    "soccer": (0.4, 1.0),
    "ufc": (0.5, 1.0),
}

TEAM_TOTAL_STRUCTURAL_EDGES: dict[str, float] = {
    "nhl": 2.0,
    "nba": 16.0,
    "mlb": 3.0,
    "nfl": 10.0,
    "soccer": 1.5,
    "ufc": 1.5,
}


def parse_progress(sport: str, period: str) -> float:
    try:
        current = int(period)
    except (TypeError, ValueError):
        return 0.0

    total = SPORT_SEGMENTS.get(sport, 4)
    return min(max(current / max(total, 1), 0.0), 1.0)


def is_structural_event(event_text: str) -> bool:
    return any(token in event_text for token in STRUCTURAL_EVENT_TOKENS)


def is_high_leverage_event(event_text: str) -> bool:
    return any(token in event_text for token in HIGH_LEVERAGE_EVENT_TOKENS)


def is_scoring_event(event_text: str) -> bool:
    return any(token in event_text for token in SCORING_EVENT_TOKENS)


def classify_spread_reversion(
    *,
    sport: str,
    event_text: str,
    home_score: int,
    away_score: int,
    period: str,
    opening_spread_home: float | None,
) -> str:
    if opening_spread_home is None:
        return "neutral"

    if is_structural_event(event_text):
        return "structural_shift"

    progress = parse_progress(sport, period)
    cover_edge = abs((home_score - away_score) + float(opening_spread_home))
    min_edge, max_edge = SPREAD_CANDIDATE_EDGES.get(sport, (1.0, 4.0))
    structural_edge = SPREAD_STRUCTURAL_EDGES.get(sport, 6.0)

    if progress >= 0.7 and cover_edge >= structural_edge:
        return "structural_shift"

    if progress == 0.0 or progress > 0.8:
        return "neutral"

    if (
        min_edge <= cover_edge <= max_edge
        and (is_scoring_event(event_text) or is_high_leverage_event(event_text))
    ):
        return "reversion_candidate"

    return "neutral"


def classify_total_reversion(
    *,
    sport: str,
    event_text: str,
    home_score: int,
    away_score: int,
    period: str,
    opening_total: float | None,
) -> str:
    if opening_total is None:
        return "neutral"

    if is_structural_event(event_text):
        return "structural_shift"

    progress = parse_progress(sport, period)
    if progress <= 0.1:
        return "neutral"

    projected_total = (home_score + away_score) / max(progress, 0.15)
    total_edge = abs(projected_total - float(opening_total))
    min_edge, max_edge = TOTAL_CANDIDATE_EDGES.get(sport, (2.0, 8.0))
    structural_edge = TOTAL_STRUCTURAL_EDGES.get(sport, 10.0)

    if progress >= 0.75 and total_edge >= structural_edge:
        return "structural_shift"

    if progress > 0.85:
        return "neutral"

    if (
        min_edge <= total_edge <= max_edge
        and (is_scoring_event(event_text) or is_high_leverage_event(event_text))
    ):
        return "reversion_candidate"

    return "neutral"


def classify_team_total_reversion(
    *,
    sport: str,
    event_text: str,
    home_score: int,
    away_score: int,
    period: str,
    opening_team_total: float | None,
    team_total_side: str | None,
) -> str:
    if opening_team_total is None or team_total_side not in {"home", "away"}:
        return "neutral"

    if is_structural_event(event_text):
        return "structural_shift"

    progress = parse_progress(sport, period)
    if progress <= 0.1:
        return "neutral"

    team_score = home_score if team_total_side == "home" else away_score
    projected_total = team_score / max(progress, 0.15)
    total_edge = abs(projected_total - float(opening_team_total))
    min_edge, max_edge = TEAM_TOTAL_CANDIDATE_EDGES.get(sport, (1.0, 4.0))
    structural_edge = TEAM_TOTAL_STRUCTURAL_EDGES.get(sport, 6.0)

    if progress >= 0.75 and total_edge >= structural_edge:
        return "structural_shift"

    if progress > 0.85:
        return "neutral"

    if (
        min_edge <= total_edge <= max_edge
        and (is_scoring_event(event_text) or is_high_leverage_event(event_text))
    ):
        return "reversion_candidate"

    return "neutral"
