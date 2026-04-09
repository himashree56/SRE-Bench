import os
import sys



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

# Add a custom tasks endpoint if needed, though OpenEnv might have its own metadata/schema
@app.get("/tasks", tags=["Environment Info"])
async def list_tasks():
    """Lists all available task names for SREBench."""
    return ["alert-classifier", "root-cause-correlator", "incident-commander"]

def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()

