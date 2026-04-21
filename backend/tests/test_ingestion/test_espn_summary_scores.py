from src.ingestion.espn_events import _score_from_context, _score_from_play


def test_score_from_context_reads_header_competitors():
    home, away = _score_from_context(
        {
            "header": {
                "competitions": [
                    {
                        "competitors": [
                            {"homeAway": "home", "score": "3"},
                            {"homeAway": "away", "score": "2"},
                        ]
                    }
                ]
            }
        }
    )
    assert (home, away) == (3, 2)


def test_score_from_play_prefers_play_scores():
    home, away = _score_from_play(
        {"homeScore": "97", "awayScore": "93"},
        {},
    )
    assert (home, away) == (97, 93)
