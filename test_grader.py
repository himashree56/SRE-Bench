import sys
import os

# Add root to path for imports
sys.path.append(os.getcwd())

from server.graders import TaskEasyGrader

def test_easy_grader():
    grader = TaskEasyGrader()
    ground_truth = {"root_cause_service": "auth-service", "root_cause_severity": "P1"}
    
    # Correct hypothesis
    history = [
        {"action": {"tool": "set_hypothesis", "params": {"hypothesis": "auth-service is P1"}}}
    ]
    
    res = grader.score(history, ground_truth, {"status": "resolved"})
    print(f"Test Correct: {res['value']} (Reason: {res['reason']})")

    # Wrong service
    history_wrong = [
        {"action": {"tool": "set_hypothesis", "params": {"hypothesis": "payment-service is P1"}}}
    ]
    res_wrong = grader.score(history_wrong, ground_truth, {"status": "resolved"})
    print(f"Test Wrong: {res_wrong['value']} (Reason: {res_wrong['reason']})")

if __name__ == "__main__":
    test_easy_grader()
