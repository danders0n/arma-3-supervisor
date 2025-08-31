import uvicorn
import json

from fastapi import FastAPI

# internal
from modules.supervisor import Supervisor
from models.server import StartServer

app = FastAPI()

with open('config/devel.json', 'r') as file:
    config = json.load(file)

supervisor = Supervisor(config)

@app.post("/start", summary="Try start the server")
def start(config: StartServer):
    supervisor.start()
    return config


@app.post("/stop", summary="Try stop the server")
def stop():
    pass


@app.get("/status")
def status():
    pass



if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)