import os
import sys

# Ensure SRE-bench is in path
_here = os.path.dirname(__file__)
_project_root = os.path.abspath(_here)
_repo = os.path.abspath(os.path.join(_project_root, "..", "OpenEnv"))

for _p in [os.getcwd(), _project_root, _repo, os.path.join(_repo, "src")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from openenv.core import create_app
from server.env import SREBenchEnv
from server.models import SREAction, SREObservation

# Initial configuration
MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT_ENVS", "10"))

# Create the OpenEnv-compliant FastAPI app
app = create_app(
    env=SREBenchEnv,
    action_cls=SREAction,
    observation_cls=SREObservation,
    max_concurrent_envs=MAX_CONCURRENT,
)

# Custom metadata/tasks endpoint
@app.get("/tasks", tags=["Environment Info"])
async def list_tasks():
    """Lists all available task names for SREBench."""
    return ["alert-classifier", "root-cause-correlator", "incident-commander"]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
