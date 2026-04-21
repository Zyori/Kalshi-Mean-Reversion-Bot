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
