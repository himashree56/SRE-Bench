import sys
import os

sys.path.append(os.getcwd())

from server.graders import TaskEasyGrader, TaskMediumGrader, TaskHardGrader
from server.scoring import MIN_FINAL_SCORE, MAX_FINAL_SCORE

def test_easy_task():
    grader = TaskEasyGrader()
    ground_truth = {"root_cause_service": "auth-service", "root_cause_severity": "P1"}
    
    print("=" * 60)
    print("TESTING: alert-classifier (EASY TASK)")
    print("=" * 60)
    
    print("\n[Scenario 1] Perfect diagnosis + postmortem")
    history = [
        {"action": {"tool": "set_hypothesis", "params": {"hypothesis": "auth-service is P1"}}},
        {"action": {"tool": "mark_resolved", "params": {}}}
    ]
    result = grader.score(history, ground_truth, {"status": "resolved"})
    print(f"  Score: {result['value']:.4f}")
    print(f"  Breakdown: {result['breakdown']}")
    print(f"  Reason: {result['reason']}")
    assert 0.0 < result['value'] < 1.0, f"Score {result['value']} not in (0, 1)"
    print("  [PASSED]")
    
    print("\n[Scenario 2] Correct service, wrong severity")
    history = [
        {"action": {"tool": "set_hypothesis", "params": {"hypothesis": "auth-service is P3"}}}
    ]
    result = grader.score(history, ground_truth, {"status": "resolved"})
    print(f"  Score: {result['value']:.4f}")
    print(f"  Breakdown: {result['breakdown']}")
    assert 0.0 < result['value'] < 1.0, f"Score {result['value']} not in (0, 1)"
    print("  [PASSED]")
    
    print("\n[Scenario 3] Wrong service identified")
    history = [
        {"action": {"tool": "set_hypothesis", "params": {"hypothesis": "payment-service is P1"}}}
    ]
    result = grader.score(history, ground_truth, {"status": "resolved"})
    print(f"  Score: {result['value']:.4f}")
    print(f"  Breakdown: {result['breakdown']}")
    assert 0.0 < result['value'] < 1.0, f"Score {result['value']} not in (0, 1)"
    print("  [PASSED]")
    
    print("\n[Scenario 4] No diagnosis (only exploratory actions)")
    history = [
        {"action": {"tool": "list_alerts", "params": {}}},
        {"action": {"tool": "query_logs", "params": {"service": "auth-service"}}}
    ]
    result = grader.score(history, ground_truth, {"status": "resolved"})
    print(f"  Score: {result['value']:.4f}")
    print(f"  Breakdown: {result['breakdown']}")
    assert 0.0 < result['value'] < 1.0, f"Score {result['value']} not in (0, 1)"
    print("  [PASSED]")
    
    print("\n[Scenario 5] Fast resolution (2 steps)")
    history = [
        {"action": {"tool": "set_hypothesis", "params": {"hypothesis": "auth-service is P1"}}},
        {"action": {"tool": "mark_resolved", "params": {}}}
    ]
    result = grader.score(history, ground_truth, {"status": "resolved"})
    speed = result['breakdown'].get('speed', 0)
    print(f"  Speed bonus: {speed:.4f}")
    print(f"  Total score: {result['value']:.4f}")
    assert 0.0 < result['value'] < 1.0, f"Score {result['value']} not in (0, 1)"
    print("  [PASSED]")
    
    print("\n*** ALL alert-classifier tests passed! ***")
    return True


def test_medium_task():
    grader = TaskMediumGrader()
    ground_truth = {"root_cause_service": "db-proxy", "correct_commit": "badc0de"}
    
    print("\n" + "=" * 60)
    print("TESTING: root-cause-correlator (MEDIUM TASK)")
    print("=" * 60)
    
    print("\n[Scenario 1] Perfect rollback to correct commit")
    history = [
        {"action": {"tool": "rollback_deploy", "params": {"service": "db-proxy", "to_commit": "badc0de"}}},
        {"action": {"tool": "set_hypothesis", "params": {"hypothesis": "db-proxy commit badc0de caused latency"}}},
        {"action": {"tool": "mark_resolved", "params": {}}}
    ]
    result = grader.score(history, ground_truth, {"status": "resolved"})
    print(f"  Score: {result['value']:.4f}")
    print(f"  Breakdown: {result['breakdown']}")
    print(f"  Reason: {result['reason']}")
    assert 0.0 < result['value'] < 1.0, f"Score {result['value']} not in (0, 1)"
    print("  [PASSED]")
    
    print("\n[Scenario 2] Correct service, wrong commit")
    history = [
        {"action": {"tool": "rollback_deploy", "params": {"service": "db-proxy", "to_commit": "abc123"}}}
    ]
    result = grader.score(history, ground_truth, {"status": "resolved"})
    print(f"  Score: {result['value']:.4f}")
    print(f"  Breakdown: {result['breakdown']}")
    assert 0.0 < result['value'] < 1.0, f"Score {result['value']} not in (0, 1)"
    print("  [PASSED]")
    
    print("\n[Scenario 3] Wrong service rollback (penalty applied)")
    history = [
        {"action": {"tool": "rollback_deploy", "params": {"service": "auth-service", "to_commit": "xyz789"}}}
    ]
    result = grader.score(history, ground_truth, {"status": "resolved"})
    print(f"  Score: {result['value']:.4f}")
    print(f"  Breakdown: {result['breakdown']}")
    penalty = result['breakdown'].get('penalty', 0)
    print(f"  Penalty applied: {penalty}")
    assert 0.0 < result['value'] < 1.0, f"Score {result['value']} not in (0, 1)"
    print("  [PASSED]")
    
    print("\n[Scenario 4] Hypothesis only, no rollback")
    history = [
        {"action": {"tool": "set_hypothesis", "params": {"hypothesis": "db-proxy is causing issues"}}}
    ]
    result = grader.score(history, ground_truth, {"status": "resolved"})
    print(f"  Score: {result['value']:.4f}")
    print(f"  Breakdown: {result['breakdown']}")
    assert 0.0 < result['value'] < 1.0, f"Score {result['value']} not in (0, 1)"
    print("  [PASSED]")
    
    print("\n[Scenario 5] Partial hypothesis (service only)")
    history = [
        {"action": {"tool": "set_hypothesis", "params": {"hypothesis": "db-proxy is the issue"}}}
    ]
    result = grader.score(history, ground_truth, {"status": "resolved"})
    print(f"  Score: {result['value']:.4f}")
    print(f"  Breakdown: {result['breakdown']}")
    assert 0.0 < result['value'] < 1.0, f"Score {result['value']} not in (0, 1)"
    print("  [PASSED]")
    
    print("\n*** ALL root-cause-correlator tests passed! ***")
    return True


def test_hard_task():
    grader = TaskHardGrader()
    ground_truth = {"root_cause_service": "auth-service", "correct_action": "restart_service"}
    
    print("\n" + "=" * 60)
    print("TESTING: incident-commander (HARD TASK)")
    print("=" * 60)
    
    print("\n[Scenario 1] Perfect restart + complete postmortem")
    history = [
        {"action": {"tool": "restart_service", "params": {"service": "auth-service"}}},
        {"action": {"tool": "write_postmortem", "params": {
            "timeline": "2024-01-01 10:00 - Alert triggered. 10:15 - Memory leak identified.",
            "root_cause": "Memory leak in auth-service causing OOM errors",
            "action_taken": "Restarted auth-service to recover from memory leak",
            "prevention": "Added memory monitoring and auto-restart policies"
        }}},
        {"action": {"tool": "mark_resolved", "params": {}}}
    ]
    result = grader.score(history, ground_truth, {"status": "resolved"})
    print(f"  Score: {result['value']:.4f}")
    print(f"  Breakdown: {result['breakdown']}")
    print(f"  Reason: {result['reason']}")
    assert 0.0 < result['value'] < 1.0, f"Score {result['value']} not in (0, 1)"
    print("  [PASSED]")
    
    print("\n[Scenario 2] Correct restart, no postmortem")
    history = [
        {"action": {"tool": "restart_service", "params": {"service": "auth-service"}}}
    ]
    result = grader.score(history, ground_truth, {"status": "mitigated"})
    print(f"  Score: {result['value']:.4f}")
    print(f"  Breakdown: {result['breakdown']}")
    assert 0.0 < result['value'] < 1.0, f"Score {result['value']} not in (0, 1)"
    print("  [PASSED]")
    
    print("\n[Scenario 3] Wrong service restart (penalty applied)")
    history = [
        {"action": {"tool": "restart_service", "params": {"service": "payment-service"}}}
    ]
    result = grader.score(history, ground_truth, {"status": "resolved"})
    print(f"  Score: {result['value']:.4f}")
    print(f"  Breakdown: {result['breakdown']}")
    penalty = result['breakdown'].get('penalty', 0)
    print(f"  Destructive penalty: {penalty}")
    assert 0.0 < result['value'] < 1.0, f"Score {result['value']} not in (0, 1)"
    print("  [PASSED]")
    
    print("\n[Scenario 4] Postmortem missing memory leak keyword")
    history = [
        {"action": {"tool": "restart_service", "params": {"service": "auth-service"}}},
        {"action": {"tool": "write_postmortem", "params": {
            "timeline": "Service degraded at 10:00, recovered at 10:15.",
            "root_cause": "Service overloaded due to high traffic",
            "action_taken": "Restarted the service",
            "prevention": "Will add more capacity"
        }}}
    ]
    result = grader.score(history, ground_truth, {"status": "resolved"})
    print(f"  Score: {result['value']:.4f}")
    print(f"  Breakdown: {result['breakdown']}")
    postmortem_score = result['breakdown'].get('postmortem', 0)
    print(f"  Postmortem score (no memory/leak keyword): {postmortem_score}")
    assert 0.0 < result['value'] < 1.0, f"Score {result['value']} not in (0, 1)"
    print("  [PASSED]")
    
    print("\n[Scenario 5] No remediation actions taken")
    history = [
        {"action": {"tool": "list_alerts", "params": {}}},
        {"action": {"tool": "query_logs", "params": {"service": "auth-service"}}}
    ]
    result = grader.score(history, ground_truth, {"status": "open"})
    print(f"  Score: {result['value']:.4f}")
    print(f"  Breakdown: {result['breakdown']}")
    assert 0.0 < result['value'] < 1.0, f"Score {result['value']} not in (0, 1)"
    print("  [PASSED]")
    
    print("\n*** ALL incident-commander tests passed! ***")
    return True


def test_score_range_validation():
    print("\n" + "=" * 60)
    print("TESTING: Score Range Validation")
    print("=" * 60)
    
    easy = TaskEasyGrader()
    medium = TaskMediumGrader()
    hard = TaskHardGrader()
    
    easy_gt = {"root_cause_service": "auth-service", "root_cause_severity": "P1"}
    medium_gt = {"root_cause_service": "db-proxy", "correct_commit": "badc0de"}
    hard_gt = {"root_cause_service": "auth-service", "correct_action": "restart_service"}
    
    all_tests = [
        ("Easy", easy, [
            [{"action": {"tool": "set_hypothesis", "params": {"hypothesis": "auth-service is P1"}}}],
            [{"action": {"tool": "set_hypothesis", "params": {"hypothesis": "auth-service is P2"}}}],
            [{"action": {"tool": "set_hypothesis", "params": {"hypothesis": "wrong-service is P1"}}}],
            [{"action": {"tool": "list_alerts", "params": {}}}],
        ], easy_gt),
        
        ("Medium", medium, [
            [{"action": {"tool": "rollback_deploy", "params": {"service": "db-proxy", "to_commit": "badc0de"}}}],
            [{"action": {"tool": "rollback_deploy", "params": {"service": "db-proxy", "to_commit": "wrong"}}}],
            [{"action": {"tool": "rollback_deploy", "params": {"service": "wrong", "to_commit": "abc"}}}],
            [{"action": {"tool": "set_hypothesis", "params": {"hypothesis": "db-proxy is bad"}}}],
        ], medium_gt),
        
        ("Hard", hard, [
            [{"action": {"tool": "restart_service", "params": {"service": "auth-service"}}}],
            [{"action": {"tool": "restart_service", "params": {"service": "wrong"}}}],
            [{"action": {"tool": "list_alerts", "params": {}}}],
            [{"action": {"tool": "escalate", "params": {"service": "wrong-service"}}}],
        ], hard_gt),
    ]
    
    all_passed = True
    for task_name, grader, test_cases, ground_truth in all_tests:
        print(f"\n[{task_name} Task]")
        for i, history in enumerate(test_cases):
            result = grader.score(history, ground_truth, {"status": "resolved"})
            score = result['value']
            
            if 0.0 < score < 1.0:
                status = "[PASSED]"
            else:
                status = "[FAILED]"
                all_passed = False
            
            print(f"  Case {i+1}: {score:.4f} {status}")
    
    print("\n*** Score Range Validation Complete ***")
    return all_passed


def main():
    print("\n" + "=" * 60)
    print("  SRE-BENCH GRADER COMPREHENSIVE TESTS")
    print("=" * 60)
    print(f"MIN_FINAL_SCORE: {MIN_FINAL_SCORE}")
    print(f"MAX_FINAL_SCORE: {MAX_FINAL_SCORE}")
    print()
    
    results = []
    
    results.append(("alert-classifier (Easy)", test_easy_task()))
    results.append(("root-cause-correlator (Medium)", test_medium_task()))
    results.append(("incident-commander (Hard)", test_hard_task()))
    results.append(("Score Range Validation", test_score_range_validation()))
    
    print("\n" + "=" * 60)
    print("  FINAL RESULTS")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "[PASSED]" if passed else "[FAILED]"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("=" * 60)
        print("  *** ALL TESTS PASSED! ***")
        print("  *** All scores are strictly between 0 and 1 ***")
        print("=" * 60)
    else:
        print("=" * 60)
        print("  *** SOME TESTS FAILED! ***")
        print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
