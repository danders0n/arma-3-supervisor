from dataclasses import dataclass

@dataclass
class ConfigModel():
    version: int
    directory: str
    executable: str
    workshop: str
    max_servers: int
    max_headless: int