from pathlib import Path

from models.config import ConfigModel
from models.server import StartModel
from modules.server import Server

class Supervisor():
    """
    docstring
    """

    def __init__(self, config: ConfigModel):
        self.config = config
        self.servers = []

    def __validate_directory(self):
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
        server = Server("server-1", self.config, config.server)
        status, error_list = server.start()

        if status != 0:
            return 1, error_list
        self.servers.append({"id": 1, "server": server})
        # Split request between arma server and auth

        return {"server_id": 1}


    def stop(self, id: int):
        print(self.servers)
        for i, server in enumerate(self.servers):
            if server.get("id") == id:
                self.servers.pop(i)
                server.get("server").stop()

    
    def status(self, id: int):
        print(self.servers)
        is_valid = self.__validate_directory()


if __name__ == "__main__":
    pass