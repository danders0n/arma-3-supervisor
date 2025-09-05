import shutil
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

        self.__validate_server_setup()


    def __validate_server_setup(self):
        working_directory  = Path(self.config.directory)

        # Checking for master directory
        if not working_directory.exists():
            print(f"ERROR:  {working_directory} not found!")
            error = {"supervisor_error": f"{working_directory} not found!"}
            return error
        
        # Checking for subdirectories
        required_directories = ["configs", "logs", "missions", "presets", "profiles", "server"]
        for directory in required_directories:
            tgt_dir = working_directory / directory
            if not tgt_dir.exists():
                print(f"WARNING:  Missing directory... {tgt_dir}")
        
        # Setup instances
        for i in range(1, self.config.max_servers + 1):
            server = {
                "name": f"server-{i}",
                "port": int(f"2{i+2}02"),
                "status": "READY",
                "info": None, 
                "server": None
            }
            self.__setup_instance_directory(f"server-{i}")
            self.servers.append(server)


    def __setup_instance_directory(self, name: str):
        """
        Creates new server instance
        """
        # Create instance directory
        instance_directory = Path(self.config.directory, name)
        master_directory = Path(self.config.directory, "server")
        
        if not instance_directory.exists():
            instance_directory.mkdir(parents=True)
            for i in master_directory.iterdir():
                if i.name not in ["keys", "userconfig"]:
                    print(f"Creating symlink to... {i.name}")
                    (instance_directory / i.name).symlink_to(i)

            if not (instance_directory / "keys").exists():
                print("Creating directory... keys")
                shutil.copytree(master_directory / "keys", instance_directory / "keys")

            if not (instance_directory / "userconfig").exists():
                print("Creating directory... userconfig")
                (instance_directory / "userconfig").mkdir(parents=True)
                
    
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


if __name__ == "__main__":
    pass