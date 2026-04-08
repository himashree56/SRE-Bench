from typing import Final

<<<<<<< Updated upstream
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
=======
MIN_FINAL_SCORE: Final[float] = 0.01
MAX_FINAL_SCORE: Final[float] = 0.99


def clamp_task_score(score: float) -> float:
    """Clamp to a strict in-range interval so final scores are never 0 or 1.
    
    This should be used for the FINAL task score returned at episode end.
    For intermediate steps, a reward of 0.0 should be returned if using
    a sparse reward model.
    """
    if score != score:  # NaN guard
        return MIN_FINAL_SCORE
    return float(min(MAX_FINAL_SCORE, max(MIN_FINAL_SCORE, score)))
>>>>>>> Stashed changes
