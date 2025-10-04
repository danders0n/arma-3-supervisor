from enum import Enum
from pydantic import BaseModel


class HeaderModel(BaseModel):
    origin: str
    request: str
    authorization: str


class MissionModel(BaseModel):
    name: str = "JO Stray Dog"
    password: str = "dupa@1234"
    admin_password: str = "asterix@7890"
    signatures: int = -1
    players: int = 64
    mission: str = "ibc_jo_stray_dog.tem_kujari.pbo"
    preset: str = "ibc_jo_stray_dog.html"
    headless: int = 0
    skill_ai: int = 1
    precision_ai: float = 0.3


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
