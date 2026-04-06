import requests
import json

base_url = "http://127.0.0.1:7860"

print("--- Testing Reset ---")
reset_payload = {"task_name": "alert-classifier", "seed": 42}
r = requests.post(f"{base_url}/reset", json=reset_payload)
print(f"Status: {r.status_code}")
print(f"Body: {r.text}")

if r.status_code == 200:
    print("\n--- Testing Step ---")
    step_payload = {
        "action": {
            "tool": "list_alerts",
            "params": {}
        }
    }
    r = requests.post(f"{base_url}/step", json=step_payload)
    print(f"Status: {r.status_code}")
    print(f"Body: {r.text}")
