from typing import Final

MIN_TASK_SCORE: Final[float] = 0.1
MAX_TASK_SCORE: Final[float] = 0.99


def clamp_task_score(score: float) -> float:
    """Clamp to a strict in-range interval so scores are never 0 or 1."""
    if score != score:  # NaN guard
        return MIN_TASK_SCORE
    if score < MIN_TASK_SCORE:
        return MIN_TASK_SCORE
    if score >= 1.0:
        return MAX_TASK_SCORE
    return float(score)
