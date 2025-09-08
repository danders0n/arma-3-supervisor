import shutil

from pathlib import Path
from typing import Dict, Any, Tuple, Optional

from models.config import ConfigModel
from models.server import StartModel
from modules.server import Server

REQUIRED_DIRECTORIES = ["configs", "logs", "missions", "presets", "profiles", "server"]

class Supervisor():
    """
    docstring
    """ 
    def __init__(self, server_config: ConfigModel):
        self.server_config = server_config
        self.servers = {}

        self._validate_server_setup()


    def _validate_server_setup(self):
        working_directory  = Path(self.server_config.directory)

        # Checking for master directory
        if not working_directory.exists():
            print(f"ERROR:  {working_directory} not found!")
            error = {"supervisor_error": f"{working_directory} not found!"}
            return error
        
        # Checking for subdirectories
        for directory in REQUIRED_DIRECTORIES:
            tgt_dir = working_directory / directory
            if not tgt_dir.exists():
                print(f"WARNING:  Missing directory... {tgt_dir}")
        
        # # Setup instances
        for i in range(1, self.server_config.max_servers + 1):
            server = {f"server-{i}": None}
            self.servers.update(server)


    def _setup_instance_directory(self, name: str, port: int):
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
            else:
                shutil.rmtree(instance_directory / "keys")
                shutil.copytree(master_directory / "keys", instance_directory / "keys")

            if not (instance_directory / "userconfig").exists():
                # print("Creating directory... userconfig")
                (instance_directory / "userconfig").mkdir(parents=True)

            if not (instance_directory / "mpmissions").exists():
                # print(f'Creating symlink to... {instance_directory / "mpmissions"}')
                (instance_directory /"mpmissions").symlink_to(Path(self.server_config.directory , "missions"))


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


    async def start(self, mission_config: StartModel):
        status, msgs = 1, {}

        for key, val in self.servers.items():
            if val == None:
                i = int(key[-1:])
                port = int(f"2{i+2}02")
                self._setup_instance_directory(key, port)
                server = Server(key, port, Path(self.server_config.directory), self.server_config.executable)
                self.servers[key] = server
                print(f"Starting {key} on port {port}")
                status = 0
                break

        if status == 1:
            print("No free server slots available.")
        else:
            await server.start(mission_config.server)
        # Split request between arma server and auth
        # print(status, msgs)
        return status, msgs


    def stop(self, server_id: str):
        idx = -1

        for id, srv in self.servers.items():
            if id == server_id:
                print(f"Requesting stop for {srv.name}")
                srv.stop()
                self.servers[id] = None
        
        # restart instance
    
    def status(self, server_id: str):
        status = 0
        msgs = []

        return status, msgs
    

    def list_servers(self):
        servers_list = {}

        for id, srv in self.servers.items():
            if srv != None:
                status = self.__get_server_status(srv)
                servers_list[id] = status
                pass

        return servers_list


    def __get_server_status(self, server: Server):
        status = {}
        status["uuid"] = server.uuid
        status["state"] = server.state
        status["name"] = server.name
        status["port"] = server.port
        status["mods"] = server.mods

        return status



if __name__ == "__main__":
    pass