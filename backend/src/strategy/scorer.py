def normalize(value: float, min_val: float, max_val: float) -> float:
    if max_val <= min_val:
        return 0.0
    clamped = max(min_val, min(max_val, value))
    return (clamped - min_val) / (max_val - min_val)


def score_opportunity(
    deviation: float,
    time_remaining_pct: float,
    deviation_weight: float = 0.6,
    time_weight: float = 0.4,
) -> float:
    dev_score = normalize(deviation, 0.05, 0.30)
    time_score = normalize(time_remaining_pct, 0.25, 0.90)
    return round(deviation_weight * dev_score + time_weight * time_score, 4)
