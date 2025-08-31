import json
import uvicorn

from fastapi import FastAPI
from pathlib import Path

# Internal imports
from modules.supervisor import Supervisor
from models.server import StartModel
from models.config import ConfigModel


def load_config(path: Path) -> ConfigModel:
    """
    Quick and Dirty loading devel.json
    TODO: Rewrite to configparser
    """
    with open(path, "r") as f:
        data = json.load(f)

    # convert dict → dataclass
    config = ConfigModel(
        version = data["version"],
        directory = data["directory"],
        executable = data["executable"]
    )
    return config

# --- SETUP SUPERVISOR ---
config = load_config(Path("config/devel.json"))
supervisor = Supervisor(config)

# --- FAST API ---
app = FastAPI()

@app.post("/server_start", summary="Try start the server")
def start(config: StartModel):
    response = supervisor.start(config)
    return response


@app.post("/server_stop", summary="Try stop the server")
def stop():
    pass


@app.get("/server_status")
def status(id: int):
    return supervisor.status(id)


@app.get("/list_servers", summary="List all running servers under supervisor")
def list_servers():
    pass


# TODO: Main functiona and config parser here somewhere some time 


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)