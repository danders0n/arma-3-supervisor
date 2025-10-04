from enum import Enum
from pydantic import BaseModel


class ResponseModel(BaseModel):
    status: int
    details: list[dict]


class SupervisorState(Enum):
    NONE = 0
    INIT = 1
    STARTUP = 2
    UPD_SERVER = 3
    UPD_WORKSHOP = 4
    RUNNING = 5
    SHUTDOWN = 7
    DEGRADED = 8
    FATAL = 9