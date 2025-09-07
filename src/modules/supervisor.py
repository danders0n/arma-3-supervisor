import shutil

from pathlib import Path
from typing import Tuple

from models.config import ConfigModel
from models.server import StartModel
from modules.server import Server


class Supervisor():
    """
    docstring
    """
    def __init__(self, server_config: ConfigModel):
        self.server_config = server_config
        self.servers = []

        self.__validate_server_setup()


    def __validate_server_setup(self):
        working_directory  = Path(self.server_config.directory)

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
        for i in range(1, self.server_config.max_servers + 1):
            server = self.__setup_instance_directory(f"server-{i}", int(f"2{i+2}02"))
            self.servers.append(server)


    def __setup_instance_directory(self, name: str, port: int):
        """
        Creates new server instance
        """
        # Create instance directory
        root_directory = Path(self.server_config.directory)
        instance_directory = root_directory / name
        master_directory =root_directory / "server"
        
        # Create directory tree 
        if not instance_directory.exists():
            instance_directory.mkdir(parents=True)
            for i in master_directory.iterdir():
                if i.name not in ["keys", "userconfig", "mpmissions"]:
                    # print(f"Creating symlink to... {i.name}")
                    (instance_directory / i.name).symlink_to(i)

            if not (instance_directory / "keys").exists():
                # print("Creating directory... keys")
                shutil.copytree(master_directory / "keys", instance_directory / "keys")

            if not (instance_directory / "userconfig").exists():
                # print("Creating directory... userconfig")
                (instance_directory / "userconfig").mkdir(parents=True)

            if not (instance_directory / "mpmissions").exists():
                # print("Creating directory... userconfig")
                (instance_directory /"mpmissions").symlink_to(Path(self.server_config.directory , "missions"))

        # Create server objects
        server = Server(name, port, root_directory, self.server_config.executable)
        print(f"Created instance: {server.name} with UUID: {server.uuid} with state {server.state}")

        return server
                

    def validate_start_request(self, mission_config: StartModel) -> Tuple[int, dict]:
        """
        Preprocessing of input data, to quicly respond via API
        """
        status = 0
        msgs = {
            "supervisor_errors": [],
            "supervisor_messages": []
        }

        if mission_config.version != 1:
            print (f"ERROR:\tSupervisor: Unsupported request schema version!")
            msgs["supervisor_errors"].append("Unsupported request schema version!")
            status = 1
            
        # for val in [mission_config.server.name, mission_config.server.password, mission_config.server.admin_password]:
        #     if not re.match(r"^[A-Za-z0-9_-]+$", val):
        #         print (f"ERROR:\tSupervisor: Cought forbidden character: only letters, numbers, _ and - allowed")
        #         msgs["supervisor_errors"].append("Cought forbidden character: only letters, numbers, _ and - allowed")
        #         status = 1

        if mission_config.server.signatures not in (-1, 0, 2):
            print (f"ERROR:\tSupervisor: Invalid signature value!")
            msgs["supervisor_errors"].append("Invalid signature value!")
            status = 1
        
        if mission_config.server.players not in range(1, 256):
            print (f"ERROR:\tSupervisor: Invalid players value!")
            msgs["supervisor_errors"].append("Invalid players value!")
            status = 1
        
        if mission_config.server.headless not in range(0, self.server_config.max_headless):
            print (f"ERROR:\tSupervisor: Invalid headless value!")
            msgs["supervisor_errors"].append("Invalid headless value!")
            status = 1
        
        path = Path(self.server_config.directory, "missions", mission_config.server.mission)
        if not path.exists(): 
            print (f"ERROR:\tSupervisor: Mission file not found... {mission_config.server.mission}")
            msgs["supervisor_errors"].append(f"Mission file not found... {mission_config.server.mission}")
            status = 1

        path = Path(self.server_config.directory, "presets", mission_config.server.preset)
        if not path.exists(): 
            print (f"ERROR:\tSupervisor: Preset file not found!")
            msgs["supervisor_errors"].append(f"Preset file not found!")
            status = 1

        if status == 0:
            msgs["supervisor_messages"].append("Git")

        return status, msgs


    def start(self, mission_config: StartModel):
        status, msgs = 0, {}
        idx = -1

        # Find free instance and assign to current request
        for i, instance in enumerate(self.servers):
            if instance.state == "Ready":
                idx = i
                print(f"Instance {i+1} - UUID: {instance.uuid} assigned to request (...)")
                break
            if i + 1 == self.server_config.max_servers:
                status = 1
                msgs = {"supervisor_errors": "Max allowed server reached!"}
        
        if status == 0:
            server = self.servers[idx]
            server.start(mission_config.server)

        # Split request between arma server and auth
        print(status, msgs)
        return status, msgs


    def stop(self, uuid: str):
        for i, instance in enumerate(self.servers):
            print(instance.uuid)
            if instance.uuid == uuid:
                print(f"Requesting stop for {instance.uuid}")
                instance.stop()

    
    def status(self, uuid: str):
        pass


if __name__ == "__main__":
    pass