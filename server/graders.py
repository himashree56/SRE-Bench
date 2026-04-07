from typing import List, Dict, Any, Optional

class BaseGrader:
    def score(self, history: List[Dict[str, Any]], ground_truth: Dict[str, Any], episode_state: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

class TaskEasyGrader(BaseGrader):
    """Grader for Task 1: alert-classifier."""
    def score(self, history: List[Dict[str, Any]], ground_truth: Dict[str, Any], episode_state: Dict[str, Any]) -> Dict[str, Any]:
        diagnosis_score = 0.0
        hypothesis = next((h["action"]["params"].get("hypothesis", "") for h in reversed(history) if h["action"]["tool"] == "set_hypothesis"), "")
        
        if ground_truth["root_cause_service"] in hypothesis.lower():
            diagnosis_score += 0.4
        if ground_truth["root_cause_severity"] in hypothesis:
            diagnosis_score += 0.2
            
        speed_bonus = max(0.0, 0.2 * (1 - (len(history) / 8)))
        
        # Postmortem penalty (skipped even if not strictly required)
        had_postmortem = any(h["action"]["tool"] == "write_postmortem" for h in history)
        postmortem_penalty = -0.1 if not had_postmortem else 0.0
        
        total = diagnosis_score + speed_bonus + postmortem_penalty
        
        outcome = "Correct diagnosis" if diagnosis_score >= 0.4 else "Failed to identify root cause"
        return {
            "value": float(max(0.01, min(0.99, total))),
            "breakdown": {"diagnosis": diagnosis_score, "speed": speed_bonus, "postmortem_penalty": postmortem_penalty},
            "reason": f"{outcome}: Identified {ground_truth['root_cause_service']} ({diagnosis_score:.1f})."
        }

class TaskMediumGrader(BaseGrader):
    """Grader for Task 2: root-cause-correlator."""
    def score(self, history: List[Dict[str, Any]], ground_truth: Dict[str, Any], episode_state: Dict[str, Any]) -> Dict[str, Any]:
        rollback_score = 0.0
        commit_score = 0.0
        
        rollback_action = next((h["action"]["params"] for h in history if h["action"]["tool"] == "rollback_deploy"), None)
        if rollback_action:
            if rollback_action.get("service") == ground_truth["root_cause_service"]:
                rollback_score = 0.35
            if rollback_action.get("to_commit") == ground_truth["correct_commit"]:
                commit_score = 0.25
        
        # Flat penalty for destructive mistakes
        wrong_rollbacks = any(h["action"]["tool"] == "rollback_deploy" and h["action"]["params"].get("service") != ground_truth["root_cause_service"] for h in history)
        penalty = 0.3 if wrong_rollbacks else 0.0
        
        # Hypothesis Quality (0.20)
        hypothesis = next((h["action"]["params"].get("hypothesis", "") for h in reversed(history) if h["action"]["tool"] == "set_hypothesis"), "")
        hypothesis_score = 0.0
        if ground_truth["root_cause_service"] in hypothesis.lower():
            hypothesis_score += 0.10
        if ground_truth["correct_commit"] in hypothesis:
            hypothesis_score += 0.10
        
        efficiency = max(0.0, 0.1 * (1 - (len(history) / 15)))
        
        total = rollback_score + commit_score + hypothesis_score + efficiency - penalty
        return {
            "value": float(max(0.01, min(0.99, total))),
            "breakdown": {
                "rollback": rollback_score, 
                "commit": commit_score, 
                "hypothesis": hypothesis_score,
                "efficiency": efficiency, 
                "penalty": penalty
            },
            "reason": f"Rollback Success: {rollback_score+commit_score:.2f}. Hypothesis: {hypothesis_score:.2f}."
        }

class TaskHardGrader(BaseGrader):
    """Grader for Task 3: incident-commander."""
    def score(self, history: List[Dict[str, Any]], ground_truth: Dict[str, Any], episode_state: Dict[str, Any]) -> Dict[str, Any]:
        root_service_score = 0.0
        action_score = 0.0
        postmortem_score = 0.0
        recovery_score = 0.0
        
        # Action & Root Service
        restart_action = next((h["action"]["params"] for h in history if h["action"]["tool"] == "restart_service"), None)
        if restart_action and restart_action.get("service") == ground_truth["root_cause_service"]:
            root_service_score = 0.25
            action_score = 0.20
            
        # Metric Recovery Check
        if episode_state["status"] in ["mitigated", "resolved"]:
            recovery_score = 0.20
            
        # Postmortem Rubric (Tightened)
        postmortem = next((h["action"]["params"] for h in history if h["action"]["tool"] == "write_postmortem"), None)
        if postmortem:
            fields = ["timeline", "root_cause", "action_taken", "prevention"]
            # Length and Keyword check
            if all(postmortem.get(f) and len(str(postmortem[f])) > 30 for f in fields):
                rc_text = str(postmortem["root_cause"]).lower()
                if "memory" in rc_text or "leak" in rc_text:
                    postmortem_score = 0.20
        
        # Penalties & Bonuses
        wrong_destructive = any(h["action"]["tool"] in ["rollback_deploy", "restart_service"] and h["action"]["params"].get("service") != ground_truth["root_cause_service"] for h in history)
        destructive_penalty = 0.25 if wrong_destructive else 0.0
        
        wrong_escalations = any(h["action"]["tool"] == "escalate" and h["action"]["params"].get("service") != ground_truth["root_cause_service"] for h in history)
        blast_radius_bonus = 0.05 if not wrong_escalations else 0.0
        
        time_bonus = max(0.0, 0.10 * (1 - (len(history) / 25)))
        
        total = (root_service_score + action_score + recovery_score + postmortem_score + 
                 blast_radius_bonus + time_bonus - destructive_penalty)
                 
        return {
            "value": float(max(0.01, min(0.99, total))),
            "breakdown": {
                "root_service": root_service_score, 
                "action": action_score, 
                "recovery": recovery_score,
                "postmortem": postmortem_score, 
                "blast_radius": blast_radius_bonus,
                "time_bonus": time_bonus,
                "penalty": destructive_penalty
            },
            "reason": f"Incident Resolution Score: {total:.3f}. Remediation: {action_score+recovery_score:.2f}."
        }
