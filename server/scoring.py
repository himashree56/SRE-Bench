from typing import Final

MIN_TASK_SCORE: Final[float] = 0.1
MAX_TASK_SCORE: Final[float] = 0.9


def clamp_task_score(score: float) -> float:
    """Clamp to a strict in-range interval so scores are strictly between 0 and 1."""
    if score != score:  # NaN guard
        return MIN_TASK_SCORE
    if score < MIN_TASK_SCORE:
        return MIN_TASK_SCORE
    if score > MAX_TASK_SCORE:
        return MAX_TASK_SCORE
    return float(score)
