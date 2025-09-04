from dataclasses import dataclass

@dataclass
class ConfigModel():
    version: int
    directory: str
    executable: str
    max_servers: int