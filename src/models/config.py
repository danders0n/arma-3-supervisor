from dataclasses import dataclass

@dataclass
class Config():
    version: int
    directory: str
    executable: str