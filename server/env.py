import json
import datetime
from typing import Dict, List, Any, Optional

from openenv.core.env_server.interfaces import Environment

from server.models import SREObservation, SREAction, SREReward, SREState
from server.simulator import SyntheticIncidentSimulator
from server.graders import TaskEasyGrader, TaskMediumGrader, TaskHardGrader
from server.scoring import clamp_task_score
from server.tasks.task_easy import get_easy_task
from server.tasks.task_medium import get_medium_task
from server.tasks.task_hard import get_hard_task

# The default reward for every non-terminal step.
# Must be strictly > 0 so the Meta grader never sees 0.0.
_STEP_REWARD: float = 0.05


class SREBenchEnv(Environment[SREAction, SREObservation, SREState]):
    """
    SREBench environment — extends openenv.core.Environment.

    Each instance is fully isolated (no shared mutable state), so
    the server can safely create one per WebSocket session.
    """

    # Each instance is isolated — safe for concurrent WebSocket sessions
    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self):
        super().__init__()
        self.simulator = SyntheticIncidentSimulator()
        self.scenario: Optional[Dict[str, Any]] = None
        self.task_config: Optional[Dict[str, Any]] = None
        self.observation: Optional[SREObservation] = None
        self._done = False
        self.history: List[Dict[str, Any]] = []
        self.investigated_services: set = set()
        self.call_signatures: set = set()
        self.last_action_error: Optional[str] = None
        self.incident_status = "open"
        # Cache the final terminal reward so post-done calls always
        # return the same valid score (never 0.0).
        self._terminal_reward: float = _STEP_REWARD

    # ------------------------------------------------------------------
    # openenv.core.Environment interface
    # ------------------------------------------------------------------

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        task_name: str = "alert-classifier",
        **kwargs: Any,
    ) -> SREObservation:
        """Reset the environment for a given task."""
        _seed = seed if seed is not None else 42
        self.simulator = SyntheticIncidentSimulator(_seed)

        if task_name == "alert-classifier":
            self.task_config = get_easy_task()
        elif task_name == "root-cause-correlator":
            self.task_config = get_medium_task()
        elif task_name == "incident-commander":
            self.task_config = get_hard_task()
        else:
            raise ValueError(f"Unknown task name: {task_name}")

        self.scenario = self.simulator.generate_scenario(task_name)
        self._done = False
        self.history = []
        self.investigated_services = set()
        self.call_signatures = set()
        self.last_action_error = None
        self.incident_status = "open"
        self._terminal_reward = _STEP_REWARD

        self.observation = SREObservation(
            step=0,
            tool_result="SRE Session Started. Investigating alerts...",
            incident_status=self.incident_status,
            services_affected=[a["service"] for a in self.scenario["alerts"]],
            time_elapsed_minutes=0,
            last_action_error=None,
            done=False,
            # Use a non-zero reward from the very first observation so the
            # Meta grader never sees None or 0.0 even on the reset obs.
            reward=_STEP_REWARD,
        )
        return self.observation

    def step(
        self,
        action: SREAction,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> SREObservation:
        """Execute one tool call and return the observation (with reward/done)."""
        if self.observation is None:
            self.reset()

        # Episode already finished — return the cached terminal reward so the
        # grader always sees the clamped final score, never 0.0.
        if self._done:
            self.observation.done = True
            self.observation.reward = self._terminal_reward
            return self.observation

        self.observation.step += 1
        self.observation.time_elapsed_minutes += 2
        self.last_action_error = None

        # 1. Execute Tool
        result_str = self._execute_tool(action)
        self.observation.tool_result = result_str
        self.observation.last_action_error = self.last_action_error
        self.observation.incident_status = self.incident_status

        # 2. Check Termination
        assert self.task_config is not None
        if self.observation.step >= self.task_config["max_steps"]:
            self._done = True

        # 3. Save history
        self.history.append({
            "step": self.observation.step,
            "action": action.model_dump(exclude={"metadata"}),
            "reward": _STEP_REWARD,   # placeholder, updated below
            "observation": self.observation.model_copy(deep=True),
        })

        # 4. Compute Reward
        reward_obj = self._compute_reward(action)

        # Update history with final reward value
        self.history[-1]["reward"] = reward_obj.value

        # 5. Embed done + reward into observation
        self.observation.done = self._done
        self.observation.reward = reward_obj.value
        self.observation.metadata = {"reward_breakdown": reward_obj.breakdown}

        return self.observation

    @property
    def state(self) -> SREState:
        """Current episode state (openenv.core.Environment.state property)."""
        return SREState(
            episode_id=getattr(self.simulator, "incident_id", None),
            step_count=self.observation.step if self.observation else 0,
            history=self.history,
            incident_status=self.incident_status,
            metrics_snapshot=(
                self.scenario["metrics"] if self.scenario else {}
            ),
        )

    def get_state(self) -> Dict[str, Any]:
        """Legacy dict-style state (used by graders internally)."""
        return {
            "observation": self.observation.model_dump() if self.observation else {},
            "history": self.history,
            "status": self.incident_status,
            "metrics_snapshot": self.scenario["metrics"] if self.scenario else {},
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _execute_tool(self, action: SREAction) -> str:
        tool = action.tool
        params = action.params

        try:
            if tool == "query_logs":
                service = params.get("service")
                logs = self.scenario["logs"].get(service, [])
                last_n = params.get("last_n", 5)
                return json.dumps(logs[-last_n:])

            elif tool == "get_metrics":
                service = params.get("service")
                metric_name = params.get("metric")
                window = params.get("window_minutes", 60)

                all_service_metrics = self.scenario["metrics"].get(service, {})

                current_time = self.simulator.start_time + datetime.timedelta(
                    minutes=self.observation.time_elapsed_minutes
                )
                cutoff = current_time - datetime.timedelta(minutes=window)

                filtered_metrics = {}
                metrics_to_search = (
                    [metric_name] if metric_name else all_service_metrics.keys()
                )

                for mname in metrics_to_search:
                    series = all_service_metrics.get(mname, {})
                    filtered_series = {}
                    for ts_str, val in series.items():
                        try:
                            ts = datetime.datetime.fromisoformat(ts_str)
                            if ts >= cutoff:
                                filtered_series[ts_str] = val
                        except ValueError:
                            filtered_series[ts_str] = val
                    filtered_metrics[mname] = filtered_series

                return json.dumps(filtered_metrics)

            elif tool == "list_alerts":
                severity = params.get("severity")
                alerts = self.scenario["alerts"]
                if severity:
                    alerts = [a for a in alerts if a["severity"] == severity]
                return json.dumps(alerts)

            elif tool == "get_deployment_history":
                service = params.get("service")
                deploys = self.scenario["deployments"]
                if service:
                    deploys = [d for d in deploys if d["service"] == service]
                return json.dumps(deploys)

            elif tool == "query_runbook":
                keyword = params.get("keyword", "").lower()
                runbooks = self.simulator.get_runbook_store()
                matching = [
                    rb
                    for rb in runbooks
                    if keyword in rb["title"].lower()
                    or keyword in rb["content"].lower()
                    or keyword in rb["tags"].lower()
                ]
                return json.dumps(matching)

            elif tool == "set_hypothesis":
                h = params.get("hypothesis")
                if not h:
                    service = params.get("root_cause_service", "")
                    severity = params.get("root_cause_severity", "")
                    h = f"{service} {severity}".strip()
                return f"Hypothesis recorded: {h}"

            elif tool == "escalate":
                return f"Escalated {params.get('service')}. Reason: {params.get('reason')}"

            elif tool == "rollback_deploy":
                service = params.get("service")
                to_commit = params.get("to_commit")
                gt = self.scenario["ground_truth"]
                if service == gt.get("root_cause_service") and to_commit == gt.get(
                    "correct_commit"
                ):
                    self.incident_status = "mitigated"
                    return f"SUCCESS: Rollback of {service} to {to_commit} completed."
                else:
                    return f"ERROR: Rollback failed for {service}."

            elif tool == "restart_service":
                service = params.get("service")
                gt = self.scenario["ground_truth"]
                if (
                    service == gt.get("root_cause_service")
                    and gt.get("correct_action") == "restart_service"
                ):
                    self.incident_status = "mitigated"
                    return f"SUCCESS: Service {service} restarted. Recovery observed."
                else:
                    return f"INFO: Service {service} restarted. No significant recovery."

            elif tool == "write_postmortem":
                if self.incident_status != "mitigated":
                    self.last_action_error = (
                        "Incident must be mitigated before writing postmortem."
                    )
                    return "ERROR: Request denied."
                return "Postmortem submission received."

            elif tool == "mark_resolved":
                self._done = True
                self.incident_status = "resolved"
                return "Incident marked as resolved."

            else:
                self.last_action_error = f"Unknown tool: {tool}"
                return "ERROR: Tool not found."

        except Exception as e:
            self.last_action_error = str(e)
            return f"ERROR: {str(e)}"

    def _compute_reward(self, action: SREAction) -> SREReward:
        breakdown: Dict[str, float] = {}

        # ── Terminal reward ────────────────────────────────────────────
        if self.incident_status == "resolved" or self._done:
            grader = self._get_grader()
            print(
                f"[SERVER DEBUG] Running grader for task: {self.scenario['scenario']}",
                flush=True,
            )
            print(f"[SERVER DEBUG] History size: {len(self.history)}", flush=True)

            last_hyp = next(
                (
                    h["action"]["params"].get("hypothesis", "")
                    for h in reversed(self.history)
                    if h["action"]["tool"] == "set_hypothesis"
                ),
                "NONE",
            )
            print(f"[SERVER DEBUG] Last hypothesis: {last_hyp}", flush=True)
            print(
                f"[SERVER DEBUG] Ground truth service: "
                f"{self.scenario['ground_truth'].get('root_cause_service')}",
                flush=True,
            )

            grade_res = grader.score(
                self.history, self.scenario["ground_truth"], self.get_state()
            )
            terminal_value = clamp_task_score(grade_res["value"])
            print(
                f"[SERVER DEBUG] Terminal reward: {terminal_value} "
                f"(reason: {grade_res.get('reason')})",
                flush=True,
            )

            breakdown.update(grade_res["breakdown"])

            # Cache so repeated calls after done always return the same value.
            self._terminal_reward = terminal_value

            return SREReward(
                value=terminal_value,
                breakdown=breakdown,
                reason=grade_res["reason"],
            )

        # ── Non-terminal reward ────────────────────────────────────────
        # Return a small positive constant — strictly > 0 so the Meta
        # grader never rejects the observation with 0.0.
        call_sig = f"{action.tool}:{json.dumps(action.params, sort_keys=True)}"
        is_duplicate = call_sig in self.call_signatures
        self.call_signatures.add(call_sig)

        if is_duplicate:
            breakdown["loop_penalty"] = -0.05

        return SREReward(value=_STEP_REWARD, breakdown=breakdown)

    def _get_grader(self):
        sc = self.task_config["scenario"]
        if sc == "alert-classifier":
            return TaskEasyGrader()
        if sc == "root-cause-correlator":
            return TaskMediumGrader()
        if sc == "incident-commander":
            return TaskHardGrader()
        raise ValueError(f"No grader mapped for scenario: {sc}")
