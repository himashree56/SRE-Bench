

from pydantic import Field
from typing import List, Optional, Dict, Any, Literal
from openenv.core.env_server.types import (
    Action as _BaseAction,
    Observation as _BaseObservation,
    State as _BaseState,
)


class SREAction(_BaseAction):
    """Tool-call action sent by the SRE agent.

    Inherits ``metadata`` from openenv.core.Action.
    """
    model_config = _BaseAction.model_config.copy()
    model_config["extra"] = "forbid"

    tool: str = Field(..., description="The name of the tool to execute")
    params: Dict[str, Any] = Field(default_factory=dict, description="Parameters for the tool")


class SREObservation(_BaseObservation):
    """Observation returned to the SRE agent.

    Inherits ``done``, ``reward``, and ``metadata`` from openenv.core.Observation.
    """
    model_config = _BaseObservation.model_config.copy()
    model_config["extra"] = "forbid"

    step: int = Field(..., description="Current step in the episode")
    tool_result: str = Field(..., description="JSON string output from the last tool call")
    incident_status: Literal["open", "mitigated", "resolved"] = Field(
        ..., description="Current status of the incident"
    )
    services_affected: List[str] = Field(
        default_factory=list, description="Services currently showing issues"
    )
    time_elapsed_minutes: int = Field(..., description="Simulated clock time")
    last_action_error: Optional[str] = Field(
        None, description="Error message if the last action failed"
    )


class SREState(_BaseState):
    """Full episode state for the SRE environment.

    Inherits ``episode_id`` and ``step_count`` from openenv.core.State.
    """
    history: List[Dict[str, Any]] = Field(default_factory=list)
    incident_status: str = Field(default="open")
    metrics_snapshot: Dict[str, Any] = Field(default_factory=dict)


class SREReward:
    """Internal reward object (not serialised over the wire)."""
    __slots__ = ("value", "breakdown", "reason")

    def __init__(
        self,
        value: float,
        breakdown: Optional[Dict[str, float]] = None,
        reason: Optional[str] = None,
    ):
        self.value = value
        self.breakdown: Dict[str, float] = breakdown or {}
        self.reason = reason


class StepResult:
    """Legacy helper kept for internal env usage only."""
    __slots__ = ("observation", "reward", "done", "info")

    def __init__(
        self,
        observation: SREObservation,
        reward: float,
        done: bool,
        info: Optional[Dict[str, Any]] = None,
    ):
        self.observation = observation
        self.reward = reward
        self.done = done
        self.info = info or {}

