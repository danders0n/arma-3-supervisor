import shutil
import uuid
import re


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
        server = {
                "uuid": str(uuid.uuid4()),
                "name": name,
                "port": port,
                "status": "READY",
                "info": None, 
                "server": None
            }
        
        # Create instance directory
        instance_directory = Path(self.server_config.directory, name)
        master_directory = Path(self.server_config.directory, "server")
        
        if not instance_directory.exists():
            instance_directory.mkdir(parents=True)
            for i in master_directory.iterdir():
                if i.name not in ["keys", "userconfig"]:
                    # print(f"Creating symlink to... {i.name}")
                    (instance_directory / i.name).symlink_to(i)

            if not (instance_directory / "keys").exists():
                # print("Creating directory... keys")
                shutil.copytree(master_directory / "keys", instance_directory / "keys")

            if not (instance_directory / "userconfig").exists():
                # print("Creating directory... userconfig")
                (instance_directory / "userconfig").mkdir(parents=True)

        print(f'Server instance with UUID: {server["uuid"]} created!' )
        return server
                


    def validate_start_request(self, mission_config: StartModel) -> Tuple[int, dict]:
        """
        Preprocessing of input data, to quicly respond via API
        """
        status = 0
        msgs = {
            "supervisor_errors": [],
            "supervisor_messages": [],
        }

        if mission_config.version != 1:
            print (f"ERROR:\tSupervisor: Unsupported request schema version!")
            msgs["supervisor_errors"].append("Unsupported request schema version!")
            status = 1
            
        for val in [mission_config.server.name, mission_config.server.password, mission_config.server.admin_password]:
            if not re.match(r"^[A-Za-z0-9_-]+$", val):
                print (f"ERROR:\tSupervisor: Cought forbidden character: only letters, numbers, _ and - allowed")
                msgs["supervisor_errors"].append("Cought forbidden character: only letters, numbers, _ and - allowed")
                status = 1

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
        assigned_instance_idx = -1
        for i, instance in enumerate(self.servers):
            if instance["status"] == "READY":
                assigned_instance_idx = i
                break
            if i == self.server_config.max_servers -1:
                return 1, {"supervisor_error": f"Max limit ({self.server_config.max_servers}) reached! Supervisor cannot launch more instances"}

        name = self.servers[assigned_instance_idx]["name"]
        port = self.servers[assigned_instance_idx]["port"]
        server = Server(self.server_config, name, port, mission_config.server)

        status, error_list = server.start()


        self.servers[assigned_instance_idx]["status"] = "Running"
        self.servers[assigned_instance_idx]["server"] = server
        print(self.servers[assigned_instance_idx])

        # Split request between arma server and auth
        print(status, error_list)
        return status, error_list


    def stop(self, id: int):
        print(self.servers)
        for i, server in enumerate(self.servers):
            if server.get("id") == id:
                self.servers.pop(i)
                server.get("server").stop()

    
    def status(self, uuid: str):
        srv_status = None
        for server in self.servers:
            if server["uuid"] == uuid:
                srv_status = {
                    "name": server["name"], "port": server["port"], 
                    "status": server["status"], "info": server["info"]
                }
                break
            else:
                srv_status = {"supervisor_error": f"Instance with UUID: {uuid} not found!"}

        print(f"Status request: {srv_status}")
        return srv_status


if __name__ == "__main__":
    pass