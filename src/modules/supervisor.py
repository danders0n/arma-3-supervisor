import shutil

from pathlib import Path
from typing import Dict, Any, Tuple, Optional

from fastapi import HTTPException

from models.config import ConfigModel
from models.server import StartModel
from modules.server import Server, ServerState

REQUIRED_DIRECTORIES = ["configs", "logs", "missions", "presets", "profiles", "server"]

class Supervisor():
    """
    docstring
    """ 
    def __init__(self, server_config: ConfigModel):
        self.server_config = server_config

        self.root_directory = Path(server_config.directory)
        self.workshop_directory = Path(server_config.workshop)
        self.executable = server_config.executable
        self.max_instances = server_config.max_servers
        self.max_headless = server_config.max_headless

        self.servers = {}

        self._startup()


    def _startup(self):
        details = []

        # Check root directory existence
        if not self.root_directory.exists():
            detail = {"Error": f"{self.root_directory} not found!"}
            details.append(detail)
            print(detail)
            raise Exception({"status": 500, "detail": detail})

        # Checking for root subdirectories
        for directory in REQUIRED_DIRECTORIES:
            target_directory = self.root_directory / directory
            if not target_directory.exists():
                target_directory.mkdir(parents=True, exist_ok=True)
                detail = {"Warning": f"{target_directory} was not found... Creating"}
                details.append(detail)
                print(detail)

        # Check workshop directory existence
        if not self.workshop_directory.exists():
            self.workshop_directory.mkdir(parents=True, exist_ok=True)
            detail = {"Warning": f"{self.workshop_directory} was not found... Creating"}
            details.append(detail)
            print(detail)

        # Copy templates, configs and profiles
        template_directory = Path().resolve() / "config/arma"
        
        for i in ["basic.cfg", "server.cfg", "cba_settings.sqf"]:
            filepath = template_directory / i
            configs = self.root_directory / "configs"

            if filepath.exists():
                if (configs / i).exists():
                    detail = {"Warning": f"Overwriting... {filepath} to {configs / i}"}
                else:
                    detail = {"Info": f"Copying... {filepath} to {configs / i}"}
                shutil.copy2(filepath, configs)
            else:
                detail = {"Error": f"{filepath} not found!"}
            
            details.append(detail)
            print(detail)

        # TODO: Here check for arma updates
        # TODO: Here check for worhshop updates

        # Create instances profiles names
        profiles_directroy = self.root_directory / "profiles/home"

        # Check for profiles directory
        if not profiles_directroy.exists():
            profiles_directroy.mkdir(parents=True, exist_ok=True)
            detail = {"Warning": f"{profiles_directroy} was not found... Creating"}
            details.append(detail)
            print(detail)

        # Creating profiles files
        for i in range(1, self.max_instances + 1):
            instance_name = f"server-{i}"

            # Creating profiles files
            profile_template = template_directory / "CustomDifficulty.Arma3Profile"
            profile_dir = profiles_directroy / instance_name / f"{instance_name}.Arma3Profile"
            if profile_template.exists():
                if profile_dir.exists():
                    detail = {"Warning": f"Overwriting... {profile_template} to {profile_dir}"}
                else:
                    detail = {"Info": f"Copying... {profile_template} to {profile_dir}"}
                shutil.copy(profile_template, profile_dir)
            else:
                detail = {"Error": f"{profile_template} not found!"}
                raise Exception({"status": 500, "detail": detail})
            
            details.append(detail)
            print(detail)

        # Creating instances for supervisor
        for i in range(1, self.max_instances + 1):
            name = f"server-{i}"

            server = {name: None}
            self.servers.update(server)
            self._setup_instance_directory(name)

            detail = {"Info": f"{name} ready for deployment."}

            details.append(detail)
            print(detail)

        # TODO: Details to log


    def _setup_instance_directory(self, name: str):
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

            # workshop
            if not (instance_directory / "workshop").exists():
                #  print(f"Creating symlink to... {Path(self.server_config.directory, "workshop")}")
                 (instance_directory /"workshop").symlink_to(Path(self.server_config.directory, "workshop"))

            # keys
            if not (instance_directory / "keys").exists():
                # print("Creating directory... keys")
                shutil.copytree(master_directory / "keys", instance_directory / "keys")
            else:
                shutil.rmtree(instance_directory / "keys")
                shutil.copytree(master_directory / "keys", instance_directory / "keys")

            # userconfig
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
        
        if mission_config.server.headless not in range(0, self.server_config.max_headless + 1):
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
                server = Server(key, port, Path(self.server_config.directory), self.server_config.executable)
                self.servers[key] = server
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
            if id == server_id and srv.state != ServerState.NONE:
                srv.stop()
                self.servers[id] = None
        
        # restart instance
    
    def status(self, server_name: str):
        for id, srv in self.servers.items():
            if id == server_name and srv != None:
                return {"status": 0, "detail": srv.status() }
        
        return {"status": 1, "detail": "No server in given name!"}
    

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

