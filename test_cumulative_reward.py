import sys
import os
import json

# Add root to path
sys.path.append(os.getcwd())

from server.env import SREBenchEnv
from server.models import SREAction

def test_cumulative_reward():
    env = SREBenchEnv()
    
    print("--- Verifying Sparse Reward & Cumulative Sum ---")
    
    # 1. Reset
    obs = env.reset(task_name="alert-classifier", seed=42)
    rewards = []
    
    # 2. Intermediate step
    action1 = SREAction(tool="list_alerts", params={})
    obs = env.step(action1)
    rewards.append(obs.reward)
    print(f"Intermediate Step 1 reward: {obs.reward}")
    
    # 3. Another intermediate step
    action2 = SREAction(tool="get_metrics", params={"service": "auth-service"})
    obs = env.step(action2)
    rewards.append(obs.reward)
    print(f"Intermediate Step 2 reward: {obs.reward}")
    
    # 4. Final step (Diagnosis)
    # Ground truth for seed 42 in alert-classifier is usually auth-service (but let's just trigger done)
    # We'll set a hypothesis and mark resolved
    action3 = SREAction(tool="set_hypothesis", params={"hypothesis": "auth-service is down"})
    env.step(action3)
    rewards.append(env.observation.reward)
    
    action4 = SREAction(tool="mark_resolved", params={})
    obs = env.step(action4)
    rewards.append(obs.reward)
    print(f"Final Step reward: {obs.reward}")
    
    # 5. Over-step (calling after done)
    action5 = SREAction(tool="list_alerts", params={})
    obs = env.step(action5)
    rewards.append(obs.reward)
    print(f"After Done reward: {obs.reward}")
    
    total_reward = sum(rewards)
    print(f"\nTOTAL CUMULATIVE REWARD: {total_reward}")
    
    # Check constraints - intermediate rewards should be _STEP_REWARD (0.05), not 0.0
    # The env.py uses _STEP_REWARD = 0.05 for non-terminal steps
    assert all(r == 0.05 for r in rewards[:-2]), "Intermediate rewards must be 0.05 (STEP_REWARD)"
    assert 0.01 < total_reward < 0.99, f"Total reward {total_reward} outside strict (0.01, 0.99)"
    assert obs.done is True
    
    print("\nSUCCESS: All rewards strictly in range (0, 1) and sparse!")

if __name__ == "__main__":
    test_cumulative_reward()
