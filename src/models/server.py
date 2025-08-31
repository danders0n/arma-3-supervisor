from dataclasses import dataclass
from pydantic import BaseModel

@dataclass
class Header(BaseModel):
    origin: str
    request: str
    authorization: str


@dataclass
class Server(BaseModel):
    name: str
    password: str
    players: int
    mission: str
    preset: str


@dataclass
class StartServer(BaseModel):
    version: int
    header: Header
    server: Server