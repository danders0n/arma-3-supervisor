from enum import Enum

from pydantic import BaseModel

class HeaderModel(BaseModel):
    origin: str
    request: str
    authorization: str


class MissionModel(BaseModel):
    name: str
    password: str
    admin_password: str
    signatures: int
    players: int
    mission: str
    preset: str
    headless: int


class StartModel(BaseModel):
    version: int
    header: HeaderModel
    server: MissionModel


class ServerState(Enum):
    NONE = 0
    INIT = 1
    STARTUP = 2
    READY = 3
    LOADING = 4
    PLAYING = 5
    DEBRIEFING = 6
    SHUTDOWN = 7
    DEGRADED = 8
    FATAL = 9
