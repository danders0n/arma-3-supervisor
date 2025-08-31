from pathlib import Path

from models.config import ConfigModel
from models.server import StartModel

class Supervisor():
    """
    docstring
    """

    def __init__(self, config: ConfigModel):
        self.config = config
        self.servers = []

    def _validate_directory(self):
        reqiuers_paths = [
            self.config.directory,
            f"{self.config.directory}/configs",
            f"{self.config.directory}/userconfig",
            f"{self.config.directory}/workshop",
            f"{self.config.directory}/servermods",
            f"{self.config.directory}/{self.config.executable}",
        ]

        for path in reqiuers_paths:
            path = Path(path)
            if not path.exists():
                print(f"[!] Missing directory..  {str(path)}")
                return False
                # path.mkdir(parents=True, exist_ok=True)
        
        return True


    def start(self, config: StartModel):
        
        print(config.version)
        print(config.header)
        print(config.server)
        # Split request between arma server and auth 
        is_valid = self._validate_directory()
        # self.servers.append({"server_id": 1})
        print("Staring:", {"server_id": 1})
        return {"server_id": 1}


    def stop(self):
        print("Stop", self.config)

    
    def status(self, id: int):
        for instance in self.servers:
            if id == instance.get("server_id"):
                print (f"Requested status of {instance}")
                return instance


if __name__ == "__main__":
    pass