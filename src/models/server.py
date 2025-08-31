from dataclasses import dataclass
from pydantic import BaseModel

@dataclass
class HeaderModel(BaseModel):
    origin: str
    request: str
    authorization: str


@dataclass
class MissionModel(BaseModel):
    name: str
    password: str
    players: int
    mission: str
    preset: str


@dataclass
class StartModel(BaseModel):
    version: int
    header: HeaderModel
    server: MissionModel