import json
import uvicorn
import logging.config


from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile
# from fastapi.responses import StreamingResponse, FileResponse
from pathlib import Path
from contextlib import asynccontextmanager


# Internal imports
from modules.supervisor import Supervisor
from modules.files_manager import FilesManager
from models.server import StartModel
from models.config import ConfigModel


def load_config(path: Path) -> ConfigModel:
    with open(path, "r") as f:
        data = json.load(f)
    return ConfigModel(**data)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    config = load_config(Path("config/devel.json"))
    app.state.supervisor = Supervisor(config)
    app.state.files_manager = FilesManager(config)

    app.state.supervisor.startup()

    yield # <- Here There Be Dragons

    # --- SHUTDOWN ---
    app.state.supervisor.shutdown()

logger = logging.getLogger("app")

# --- FAST API ---
app = FastAPI(lifespan = lifespan)

    
@app.post("/start", summary="Try start the server", tags=["server"])
async def start(mission_config: StartModel, background_tasks: BackgroundTasks):
    response = app.state.supervisor.validate_start(mission_config)

    if response.status != 0:
        raise HTTPException( status_code=400, detail=response.details)
    else:
        background_tasks.add_task(app.state.supervisor.start, mission_config)

    return response.details


@app.delete("/stop", summary="Try stop the server", tags=["server"])
async def stop(name: str, background_tasks: BackgroundTasks):
    response = app.state.supervisor.validate_stop(name)
    
    if response.status != 0:
        raise HTTPException( status_code=400, detail=response.details)
    else:
        background_tasks.add_task(app.state.supervisor.stop, name)

    return response.details


@app.get("/status", tags=["server"])
def status(name: str):
    return app.state.supervisor.status(name)


@app.get("/list_servers", summary="List all running servers under supervisor")
def list_servers():
    return app.state.supervisor.list_servers()


@app.post("/upload")
async def upload_file(file : UploadFile, override: bool = False):
    upload = await app.state.files_manager.upload(file, override) 
    if upload["status"] != 0:
        if status != 0:
            raise HTTPException( status_code=400, detail=upload["detail"])
    return upload["detail"]


@app.post("/download")
async def download_file(file: str):
    return await app.state.files_manager.download(file)


@app.post("/list_missions")
async def list_missions():
    return await app.state.files_manager.list_pbo_missions()


@app.post("/list_presets")
async def list_presets():
    return await app.state.files_manager.list_html_presets()

# TODO: Main functiona and config parser here somewhere some time 


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)