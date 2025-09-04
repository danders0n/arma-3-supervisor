import json
import uvicorn


from fastapi import FastAPI, HTTPException
from pathlib import Path
from contextlib import asynccontextmanager


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

    # convert dict -> dataclass
    config = ConfigModel(
        version = data["version"],
        directory = data["directory"],
        executable = data["executable"],
        max_servers = data["max_servers"]
    )
    return config


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    config = load_config(Path("config/devel.json"))
    app.state.supervisor = Supervisor(config)

    yield # <- here magic happends

    # --- SHUTDOWN ---


# --- FAST API ---
app = FastAPI(lifespan = lifespan)

    

@app.post("/server_start", summary="Try start the server")
def start(config: StartModel):
    status, response = app.state.supervisor.start(config)
    if status != 0:
        raise HTTPException(status_code=404, detail=response)
    return response


@app.delete("/server_stop", summary="Try stop the server")
def stop(id: int):
    app.state.supervisor.stop(id)


@app.get("/server_status")
def status(id: int):
    return app.state.supervisor.status(id)


@app.get("/list_servers", summary="List all running servers under supervisor")
def list_servers():
    pass


# TODO: Main functiona and config parser here somewhere some time 


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)