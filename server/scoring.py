from typing import Final

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
