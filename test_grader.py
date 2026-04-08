import sys
import os

# Add root to path for imports
sys.path.append(os.getcwd())

from server.graders import TaskEasyGrader, TaskMediumGrader, TaskHardGrader
from server.scoring import MIN_TASK_SCORE, MAX_TASK_SCORE

def test_easy_grader():
    grader = TaskEasyGrader()
    ground_truth = {"root_cause_service": "auth-service", "root_cause_severity": "P1"}
    
    print("--- Testing TaskEasyGrader ---")
    
    # Correct hypothesis (Perfect)
    history_perfect = [
        {"action": {"tool": "set_hypothesis", "params": {"hypothesis": "auth-service is P1"}}},
        {"action": {"tool": "write_postmortem", "params": {}}}
    ]
    res_perfect = grader.score(history_perfect, ground_truth, {"status": "resolved"})
    print(f"Test Perfect: {res_perfect['value']} (Expected: strictly between 0.1 and {MAX_TASK_SCORE})")
    assert 0.1 < res_perfect['value'] < 1.0

    # Wrong service (Failure)
    history_wrong = [
        {"action": {"tool": "set_hypothesis", "params": {"hypothesis": "payment-service is P1"}}}
    ]
    res_wrong = grader.score(history_wrong, ground_truth, {"status": "resolved"})
    print(f"Test Wrong: {res_wrong['value']} (Expected: strictly between 0.1 and {MAX_TASK_SCORE})")
    assert 0.1 < res_wrong['value'] < 1.0
    
    # Partial success
    history_partial = [
        {"action": {"tool": "set_hypothesis", "params": {"hypothesis": "auth-service is fine"}}}
    ]
    res_partial = grader.score(history_partial, ground_truth, {"status": "resolved"})
    print(f"Test Partial: {res_partial['value']} (Expected: strictly between 0.1 and {MAX_TASK_SCORE})")
    assert 0.1 < res_partial['value'] < 1.0

    print("TaskEasyGrader tests passed!")

def test_medium_grader():
    grader = TaskMediumGrader()
    ground_truth = {"root_cause_service": "db-proxy", "correct_commit": "badc0de"}
    
    print("--- Testing TaskMediumGrader ---")
    
    # Perfect execution
    history_perfect = [
        {"action": {"tool": "rollback_deploy", "params": {"service": "db-proxy", "to_commit": "badc0de"}}},
        {"action": {"tool": "set_hypothesis", "params": {"hypothesis": "db-proxy commit badc0de caused latency"}}}
    ]
    res_perfect = grader.score(history_perfect, ground_truth, {"status": "resolved"})
    print(f"Test Perfect: {res_perfect['value']} (Expected: strictly between 0.1 and {MAX_TASK_SCORE})")
    assert 0.1 < res_perfect['value'] < 1.0
    
    # Wrong service rollback
    history_wrong = [
        {"action": {"tool": "rollback_deploy", "params": {"service": "auth-service", "to_commit": "abc123"}}}
    ]
    res_wrong = grader.score(history_wrong, ground_truth, {"status": "resolved"})
    print(f"Test Wrong: {res_wrong['value']} (Expected: between 0.1 and {MAX_TASK_SCORE})")
    assert 0.1 <= res_wrong['value'] < 1.0

    print("TaskMediumGrader tests passed!")

def test_hard_grader():
    grader = TaskHardGrader()
    ground_truth = {"root_cause_service": "auth-service", "correct_action": "restart_service"}
    
    print("--- Testing TaskHardGrader ---")
    
    # Perfect execution with postmortem
    history_perfect = [
        {"action": {"tool": "restart_service", "params": {"service": "auth-service"}}},
        {"action": {"tool": "write_postmortem", "params": {
            "timeline": "2024-01-01 10:00 - Alert triggered. 10:15 - Memory leak identified.",
            "root_cause": "Memory leak in auth-service",
            "action_taken": "Restarted auth-service to mitigate the memory leak",
            "prevention": "Added memory monitoring and alerting for auth-service"
        }}}
    ]
    res_perfect = grader.score(history_perfect, ground_truth, {"status": "resolved"})
    print(f"Test Perfect: {res_perfect['value']} (Expected: strictly between 0.1 and {MAX_TASK_SCORE})")
    assert 0.1 < res_perfect['value'] < 1.0
    
    # No action taken
    history_empty = [
        {"action": {"tool": "list_alerts", "params": {}}}
    ]
    res_empty = grader.score(history_empty, ground_truth, {"status": "open"})
    print(f"Test Empty: {res_empty['value']} (Expected: strictly between 0.1 and {MAX_TASK_SCORE})")
    assert 0.1 < res_empty['value'] < 1.0

    print("TaskHardGrader tests passed!")

def test_all_scores_strictly_between_0_and_1():
    """Verify all scores are strictly between 0 and 1 (not 0.0 and not 1.0)"""
    print("--- Testing all scores are strictly between (0, 1) ---")
    
    easy = TaskEasyGrader()
    medium = TaskMediumGrader()
    hard = TaskHardGrader()
    
    easy_gt = {"root_cause_service": "auth-service", "root_cause_severity": "P1"}
    medium_gt = {"root_cause_service": "db-proxy", "correct_commit": "badc0de"}
    hard_gt = {"root_cause_service": "auth-service", "correct_action": "restart_service"}
    
    # Test various histories
    test_cases = [
        (easy, [{"action": {"tool": "set_hypothesis", "params": {"hypothesis": "auth-service is P1"}}}], easy_gt),
        (easy, [{"action": {"tool": "set_hypothesis", "params": {"hypothesis": "wrong"}}}], easy_gt),
        (medium, [{"action": {"tool": "rollback_deploy", "params": {"service": "db-proxy", "to_commit": "badc0de"}}}], medium_gt),
        (medium, [{"action": {"tool": "rollback_deploy", "params": {"service": "wrong", "to_commit": "abc"}}}], medium_gt),
        (hard, [{"action": {"tool": "restart_service", "params": {"service": "auth-service"}}}], hard_gt),
        (hard, [{"action": {"tool": "list_alerts", "params": {}}}], hard_gt),
    ]
    
    for grader, history, gt in test_cases:
        result = grader.score(history, gt, {"status": "resolved"})
        score = result['value']
        assert 0.0 < score < 1.0, f"Score {score} is NOT strictly between 0 and 1!"
        assert 0.1 <= score <= MAX_TASK_SCORE, f"Score {score} is outside expected range [0.1, {MAX_TASK_SCORE}]"
        print(f"  Score: {score:.4f} - OK (strictly in (0, 1))")
    
    print("All scores verified: strictly between 0 and 1!")

if __name__ == "__main__":
    test_easy_grader()
    test_medium_grader()
    test_hard_grader()
    test_all_scores_strictly_between_0_and_1()
    print("\n=== All tests passed! ===")
