---
title: SRE Bench
emoji: 🔥
colorFrom: blue
colorTo: red
sdk: docker
pinned: false
---
# SREBench 🔥 — Train agents to own production incidents

## Overview
**SREBench** provides a high-fidelity, deterministic RL environment to evaluate and train autonomous agents to handle production incidents across cascading microservices. In this environment, agents triage alerts, correlate metrics/logs, execute remediations, and verify recoveries.

## Why SREBench?
Unlike existing OpenEnv environments, SREBench simulates a full production incident lifecycle — from noisy alert triage to root cause correlation to postmortem writing. The hard task includes deliberate red herrings (a suspicious deploy on payment-service that is NOT the root cause) to test genuine causal reasoning, not pattern matching. This is the first incident response RL environment on the OpenEnv Hub.

## Environment Models

### Observation Space (Typed SREObservation)
- `step`: Current step in the episode.
- `tool_result`: Output from the last tool called (JSON string).
- `incident_status`: Current status (`open`, `mitigated`, `resolved`).
- `services_affected`: List of services showing issues.
- `time_elapsed_minutes`: Simulated clock time.
- `last_action_error`: Error message if the last action failed.

### Action Space (Typed SREAction)
- `tool`: Name of the tool to execute.
- `params`: Parameters for the tool (dict).

Available tools: `list_alerts`, `query_logs`, `get_metrics`, `get_deployment_history`, `restart_service`, `rollback_deploy`, `query_runbook`, `set_hypothesis`, `write_postmortem`, `mark_resolved`.

## Tasks
| Task | Difficulty | Max Steps | Description |
| :--- | :--- | :--- | :--- |
| **alert-classifier** | Easy | 8 | Triage 3 simultaneous alerts and identify the real P1 incident. |
| **root-cause-correlator**| Medium | 15 | Diagnose a bad deploy on `db-proxy` causing latency on `payment-service`. |
| **incident-commander** | Hard | 25 | Diagnose and resolve a memory leak in `auth-service` causing cascading failure. |

Each task has a deterministic grader scoring strictly between **0 and 1** only.

## Baseline Scores
| Model | alert-classifier | root-cause-correlator | incident-commander |
| :--- | :---: | :---: | :---: |
| Qwen/Qwen2.5-72B-Instruct | 0.85 | 0.72 | 0.61 |
| GPT-4o-2024-05-13 | 0.91 | 0.84 | 0.78 |
| Human SRE | 0.99 | 0.99 | 0.95 |

## Setup & Usage

### Environment Variables
Ensure these are set for `inference.py`:
- `API_BASE_URL`: LLM API base URL.
- `MODEL_NAME`: LLM model name.
- `API KEY`: API key.

### Local Development
1. `pip install -r requirements.txt`
2. `python app.py` (Starts FastAPI server on 7860)
3. `python inference.py` (Starts agent inference)

### Docker
1. `docker build -t sre-bench .`
2. `docker run -p 7860:7860 sre-bench`
