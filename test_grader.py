import sys
import os

# Add root to path for imports
sys.path.append(os.getcwd())

from server.graders import TaskEasyGrader

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
    print(f"Test Perfect: {res_perfect['value']} (Expected: 0.999)")
    assert 0.0 < res_perfect['value'] < 1.0

    # Wrong service (Failure)
    history_wrong = [
        {"action": {"tool": "set_hypothesis", "params": {"hypothesis": "payment-service is P1"}}}
    ]
    res_wrong = grader.score(history_wrong, ground_truth, {"status": "resolved"})
    print(f"Test Wrong: {res_wrong['value']} (Expected: 0.001)")
    assert 0.0 < res_wrong['value'] < 1.0
    
    # Partial success
    history_partial = [
        {"action": {"tool": "set_hypothesis", "params": {"hypothesis": "auth-service is fine"}}}
    ]
    res_partial = grader.score(history_partial, ground_truth, {"status": "resolved"})
    print(f"Test Partial: {res_partial['value']} (Expected: > 0.001 and < 0.999)")
    assert 0.0 < res_partial['value'] < 1.0

    print("All tests passed (strictly between 0 and 1)!")

if __name__ == "__main__":
    test_easy_grader()
