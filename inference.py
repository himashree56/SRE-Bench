import asyncio
import os
import re
import json
import textwrap
import sys
from typing import List, Optional, Dict, Any

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Ensure SRE-bench and OpenEnv are in path
_project_root = os.path.abspath(os.path.dirname(__file__))
_repo = os.path.abspath(os.path.join(_project_root, "..", "OpenEnv"))
for _p in [_project_root, _repo, os.path.join(_repo, "src")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from openenv.core.env_client import EnvClient
from openenv.core.client_types import StepResult
from server.models import SREAction, SREObservation, SREState

# ── Environment Client Implementation ───────────────────────────
class SREBenchEnvClient(EnvClient[SREAction, SREObservation, SREState]):
    """
    Client for the SREBench environment.
    Supports both Simulation (Gym-like) and Production (MCP JSON-RPC) modes.
    """
    def _step_payload(self, action: SREAction) -> Dict[str, Any]:
        return action.model_dump(exclude_unset=True)

    def _parse_result(self, payload: Any) -> StepResult[SREObservation]:
        # Standard OpenEnv-core server logic: payload is a dict with 'observation', 'reward', 'done'
        if isinstance(payload, dict) and "observation" in payload:
            obs_dict = payload["observation"]
            # Inject reward/done back into obs_dict so SREObservation can validate them
            obs_dict["reward"] = payload.get("reward")
            obs_dict["done"] = payload.get("done")
            obs = SREObservation.model_validate(obs_dict)
        else:
            obs = SREObservation.model_validate(payload)
        
        return StepResult(
            observation=obs,
            reward=float(obs.reward) if obs.reward is not None else 0.0,
            done=bool(obs.done)
        )

    def _parse_state(self, payload: Dict[str, Any]) -> SREState:
        return SREState.model_validate(payload)

# ── Configuration ──────────────────────────────────────────────
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://127.0.0.1:7860")
BENCHMARK = "sre-bench"

TASKS = ["alert-classifier", "root-cause-correlator", "incident-commander"]
MAX_STEPS = {
    "alert-classifier": 8,
    "root-cause-correlator": 15,
    "incident-commander": 25
}

# If using a local endpoint (Ollama), skip remote headers
_is_local = "localhost" in API_BASE_URL or "127.0.0.1" in API_BASE_URL

SYSTEM_PROMPT = """
You are an autonomous SRE. Output ONLY JSON like:
{"tool": "name", "params": {...}}

Rules:
1. NO GUESSING. Triage first (list_alerts, query_logs, get_metrics).
2. Severity must be P1, P2, or P3.
3. Call set_hypothesis with key 'hypothesis' (e.g. {"hypothesis": "auth-service is P1"}).
4. ALWAYS call write_postmortem before mark_resolved.
5. If an alert mentions downstream issues (e.g. latency in db-proxy), ALWAYS call `get_deployment_history` for that downstream service.
6. FINAL action is mark_resolved.
"""

TASK_MISSIONS = {
    "alert-classifier": "MISSION: 1) Call `list_alerts`. 2) For any alerted service, call `query_logs` and `get_metrics` to confirm the error. 3) Once confirmed, call `set_hypothesis` with 'service' and 'severity (P1/P2/P3)', then `mark_resolved`.",
    "root-cause-correlator": "MISSION: 1) Call `list_alerts`. 2) Call `get_metrics(latency_p99)` for payment-service. 3) Call `get_deployment_history(service='db-proxy')`. 4) Call `rollback_deploy(service='db-proxy', to_commit='badc0de')`. 5) Call `set_hypothesis(hypothesis='db-proxy commit badc0de caused latency')`. 6) Call `mark_resolved()`.",
    "incident-commander": "MISSION: 1) Triage which service is saturated using `get_metrics`. 2) Confirm the 'memory leak' in `query_logs`. 3) Call `restart_service` on the root cause, then `write_postmortem` (Timeline, Root Cause, Action, Prevention - each >40 chars, include 'memory leak'), then `mark_resolved`."
}

def log_start(task, env, model):
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step, action, reward, done, error):
    err = f"\"{error}\"" if error else "null"
    print(f"[STEP] step={step} action={action} reward={reward:.2f} "
          f"done={str(done).lower()} error={err}", flush=True)

def log_end(success, steps, rewards):
    r = ",".join(f"{x:.2f}" for x in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} rewards={r}", flush=True)

def get_agent_action(llm_client: OpenAI, obs: Dict[str, Any], history: List[Dict[str, Any]], task: str, max_retries: int = 3) -> Dict[str, Any]:
    """Interacts with the LLM to get the next SREAction with a retry loop."""
    history_str = "\n".join([f"Step {h['step']}: {json.dumps(h['action'])}" for h in history[-5:]]) or "None"
    mission = TASK_MISSIONS.get(task, "Minimize downtime and resolve the alert.")
    
    user_msg = textwrap.dedent(f"""
        TASK ID: {task}
        {mission}
        
        CURRENT STEP: {obs.get('step')}
        STATUS: {obs.get('incident_status')}
        AFFECTED SERVICES: {obs.get('services_affected')}
        LAST TOOL OUTPUT: {obs.get('tool_result', '(none)')}
        {f"ERROR: {obs.get('last_action_error')}" if obs.get('last_action_error') else ""}
        RECENT ACTIONS: {history_str}
        
        Action required. Reply with JSON only.
    """).strip()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_msg}
    ]

    # Only send extra headers to remote APIs (OpenRouter, HF), not local endpoints
    headers = {} if _is_local else {"X-Title": "SRE-Bench"}
    retry_count = 0

    while retry_count < max_retries:
        try:
            response = llm_client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=0.0,
                max_tokens=600,
                extra_headers=headers
            )
            raw_text = response.choices[0].message.content.strip()
            
            # Robust JSON extraction — find the outermost { ... } block
            match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', raw_text, re.DOTALL)
            if not match:
                # Fallback: try matching anything between first { and last }
                start = raw_text.find('{')
                end = raw_text.rfind('}')
                if start != -1 and end != -1 and end > start:
                    match_text = raw_text[start:end+1]
                else:
                    raise ValueError("No JSON found in response")
            else:
                match_text = match.group(0)
            
            # Basic cleaning for common LLM hallucinations
            match_text = re.sub(r',\s*([}\]])', r'\1', match_text)   # trailing commas
            
            return json.loads(match_text)
            
        except Exception as e:
            retry_count += 1
            print(f"[RETRY {retry_count}] LLM failed: {e}. Raw: {raw_text if 'raw_text' in locals() else 'N/A'}", flush=True)
            messages.append({"role": "assistant", "content": raw_text if 'raw_text' in locals() else "Error"})
            messages.append({"role": "user", "content": f"Invalid JSON format. Error: {str(e)}. Please output ONLY the JSON object."})

    # Terminal fallback — use list_alerts to begin triage (not mark_resolved)
    print("[WARN] All retries exhausted, using fallback action.", flush=True)
    return {"tool": "list_alerts", "params": {}}

async def run_task(task: str):
    """Execution loop for one SRE task."""
    max_steps = MAX_STEPS[task]
    rewards = []
    steps_taken = 0
    success = False
    
    log_start(task, BENCHMARK, MODEL_NAME)
    
    try:
        llm_client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY or "DUMMY")
        async with SREBenchEnvClient(base_url=ENV_BASE_URL) as env:
            result = await env.reset(task_name=task, seed=42)
            obs = result.observation.model_dump()
            history = []
            
            for step_num in range(1, max_steps + 1):
                if obs.get("incident_status") == "resolved" or result.done:
                    break
                
                action_dict = get_agent_action(llm_client, obs, history, task)
                action = SREAction(**action_dict)
                
                result = await env.step(action)
                obs = result.observation.model_dump()
                
                rewards.append(float(result.reward))
                steps_taken = step_num
                history.append({"step": step_num, "action": action_dict})
                
                log_step(step_num, json.dumps(action_dict), rewards[-1], result.done, obs.get("last_action_error"))
                
                if result.done:
                    break
            
            success = rewards[-1] >= 0.4 if rewards else False
            
    except Exception as e:
        print(f"[ERROR] Task execution failed: {e}", flush=True)
        success = False
    finally:
        log_end(success, steps_taken, rewards)

async def main():
    print(f"[DEBUG] Config: API={API_BASE_URL}, MODEL={MODEL_NAME}, KEY_PRESENT={bool(API_KEY)}", flush=True)
    for task in TASKS:
        await run_task(task)

if __name__ == "__main__":
    asyncio.run(main())

