import re
import uuid
import shutil
import asyncio

from pathlib import Path
from datetime import datetime, timedelta

from models.server import MissionModel, ServerState

class Server():
    def __init__(self, name:str, port: int, root_directory: Path, executable: str):
        self.uuid = str(uuid.uuid4())
        self.state = ServerState.NONE
        self.name = name
        self.port = port
        self.start_time = None
        self.hostname = None
        self.password = None
        self.admin_password = None
        self.mission = None
        self.map = None
        self.players_count = 0
        self.mods_count = 0
        self.root_directory = root_directory
        self.directory = root_directory / name
        self.executable = root_directory / name / executable
        self.directory_logs = self.root_directory / "logs" / name 

        self.mods = {}
        self.players = {}
        self.messages = {            
            "server_errors": [],
            "server_messages": []
        }


    def _parser_html_preset(self, preset: Path) -> int:
        """
        
        """
        status = 0
        mods_id, mods_names = [], []
        preset_path = Path(self.root_directory, "presets", preset)

        if not preset_path.exists():
            self.messages["server_errors"].append(f"parser_html: Preset file not found... {preset_path}")
            status = 1

         # Reading preset
        with open(preset_path) as file:
            html = file.read()

            regex_id = r"filedetails\/\?id=(\d+)\""
            matches_id = re.finditer(regex_id, html, re.MULTILINE)

            regex_name = r"\"DisplayName\">(.*?)<\/td>"
            matches_name = re.finditer(regex_name, html, re.MULTILINE)

            # Can be made in one loop but is really needed?
            for match in matches_id:
                mods_id.append(match.group(1))
            for match in matches_name:
                mods_names.append(match.group(1))

        if len(mods_id) != len(mods_names):
            self.messages["server_errors"].append(f"{__name__}: parsing failed, mismatched IDs and Names. {preset_path}")
            status = 1 
        
        if status == 0:
            self.mods = dict(zip(mods_id, mods_names))
            self.mods_count = len(self.mods)

        return status
        

    def _verify_workshop(self):
        """
        Verify mods for existence and keys
        """
        status = 0
        missing_mods, mods_without_keys = [], []
        workshop_directory = self.root_directory / "workshop"

        for id, name in self.mods.items():
            mod_path = workshop_directory / id

            # check if mods exists in workshop directory
            if not mod_path.exists():
                missing_mods.append({id: name})
                print(f"Workshop item: {id}: {name} not found!")
            
            # check if mod have any keys
            keys = list(mod_path.glob("*/*.bikey"))
            if len(keys) > 0:
                for key in keys:
                    shutil.copy2(key, self.directory / "keys" / key.name)
                self.signatures = 2
            else:
                print(f"{mod_path} Keys Not Found!")
                mods_without_keys.append({id: name})
                self.signatures = 0

        # TODO: Download new mods
        return status


    def _parser_profile(self):
        src = self.root_directory / "profiles/home/server/server.Arma3Profile"
        dst = Path("/opt/arma-3/profiles/home/", self.name)
        if not dst.exists():
            dst.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst / f"{self.name}.Arma3Profile")
        

    def _parser_server_config(self, mission_config: MissionModel):
        template_path = self.root_directory / "configs/server.cfg"
        config_path = self.root_directory / "configs" / f"{self.name}.cfg"

        print(template_path)
        print(config_path)

        # if signatures were not set then used based on keys availability
        if mission_config.signatures != -1:
            signatures = mission_config.signatures
        else:
            signatures = self.signatures
            
        self.hostname = mission_config.name
        self.password = mission_config.password
        self.admin_password = mission_config.admin_password
        self.mission = mission_config.mission[:-4] # -4 for .pbo cuz arma

        # TODO: arguments verification
        mapping_dictionary = {
            "TAG": "ASTERIX",
            "NAME": self.hostname,
            "PASSWORD": self.password,
            "ADMINPASSWORD": self.admin_password,
            "PLAYERS": mission_config.players,
            "SIGNATURES": signatures,
            "MISSION": self.mission
        }

        text = template_path.read_text()

        for tag, value in mapping_dictionary.items():
            text = text.replace(f"[{tag}]", str(value))
            print(f"Writing: {tag}: {value}")

        config_path.write_text(text)
        return config_path


    def _parser_start_arguments(self):
        args = [
           str(self.executable), 
            "-name=" + str(self.name),
            "-port=" + str(self.port),
            "-profiles=/opt/arma-3/profiles/",
            "-cfg=/opt/arma-3/configs/basic.cfg",
            "-config=" + str(self.root_directory / "configs" / f"{self.name}.cfg"),
            "-loadMissionToMemory",
            "-hugePages",
            "-maxFileCacheSize=8192",
            "-bandwidthAlg=2",
            "-debug",
            "-filePatching"
        ]
        args_mods = "-mod=\""
        for id, name in self.mods.items():
            mod_path = f"workshop/{id};"
            args_mods += mod_path
        args_mods = args_mods[:-1]
        args_mods += "\""

        args.append(args_mods)
        return args, args_mods

    def _parser_start_headless_args(self, name, password, mods ):
        args = [
            str(self.executable), "-client", 
            "-name=" + name,
            "-profiles=/opt/arma-3/profiles/",
            "-connect=127.0.0.1", "-port=" + str(self.port),
            "-password=" + str(password)
        ]
        args.append(mods)

        return args


    def _log_analyzer(self, line):
        RE_STARTUP = re.compile(r"Dedicated host created", re.IGNORECASE)
        RE_READY = re.compile(r"Connected to Steam servers", re.IGNORECASE)
        RE_MISSION = re.compile(r"Mission (.+?) read from bank", re.IGNORECASE)
        RE_CONNECTED = re.compile(r"Player (.+?) connected \(id=(\d+)\)", re.IGNORECASE)
        RE_DISCONNECTED = re.compile(r"Player (.+?) disconnected\.", re.IGNORECASE)

        if match := RE_STARTUP.search(line):
            self.state = ServerState.STARTUP
            print(f"{self.name} changed state to: {self.state.name}")

        if match := RE_READY.search(line):
            self.state = ServerState.READY
            print(f"{self.name} changed state to: {self.state.name}")

        if match := RE_MISSION.search(line):
            mission_map = match.groups()[0]
            mission, map = mission_map.split(".", 1)

            self.mission = mission
            self.map = map

            print(f"{self.name} loaded mission: {mission} on map: {map}")

        if match := RE_CONNECTED.search(line):
            name, uid = match.groups()

            self.players[uid] = { "Player": name, 
                                "Connected": datetime.now(), 
                                "Disconnected": datetime.min, 
                                "Playtime": datetime.min
                                }
            self.players_count += 1

        if match := RE_DISCONNECTED.search(line):
            name = match.groups()[0]

            for key, val in self.players.items():
                print(key, val, name)
                if val["Player"] == name:
                    self.players[key]["Disconnected"] = datetime.now()
                    self.players[key]["Playtime"] += self.players[key]["Disconnected"] - self.players[key]["Connected"]
            
            self.players_count -= 1


        if "SetServerState" in line:
            print(line)


    async def _read_stream(self, stream, file_path: Path, is_server = False):
        """
        Realtime stream catcher
        """
        if stream is None:
            return

        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "a") as f:
            while True:
                line = await stream.readline()
                if not line:
                    break
                decoded_line = line.decode().rstrip()
                if is_server:
                    self._log_analyzer(decoded_line)
                f.write(decoded_line + "\n")
                f.flush()


    async def start(self, mission_config: MissionModel):
        status = self._parser_html_preset(Path(mission_config.preset))
        if status == 0:
            self._verify_workshop()
        self._parser_profile()
        self._parser_server_config(mission_config)
        args, mods = self._parser_start_arguments()

        if status != 0:
            self.state = ServerState.FATAL
            return 1, self.messages

        self.start_time = datetime.now()
        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
        log_file = self.directory_logs / f"{timestamp}_{self.uuid}_{self.name}.log"

        self.process = await asyncio.create_subprocess_exec(
            *args,
            cwd=self.directory,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )
        asyncio.create_task(self._read_stream(self.process.stdout, log_file, True))

        self.state = ServerState.INIT
        print(f"Starting {self.name} on port {self.port}")

        # Handle Headless
        if mission_config.headless > 0:
            self.headless = {}

            for i in range(1, mission_config.headless + 1):
                hc_name = "headless-" + str(i)
                hc_args = self._parser_start_headless_args(hc_name, mission_config.password, mods)
                log_file_hc = self.directory_logs / f"{timestamp}_{self.uuid}_{hc_name}.log"

                hc_process = await asyncio.create_subprocess_exec(
                    *hc_args,
                    cwd=self.directory,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT
                )
                asyncio.create_task(self._read_stream(hc_process.stdout, log_file_hc))

                self.headless[hc_name] = hc_process

                print(f"Starting {hc_name} that will connect to {self.name}")
        

    def stop(self):
        if hasattr(self, "process") and self.process.returncode is None:
            print(f"Requesting stop for {self.name}")
            self.process.terminate()
            self.state = ServerState.SHUTDOWN
        
        if hasattr(self, "headless") and self.process.returncode is None:
            for hc, process in self.headless.items():
                print(f"Requesting stop for {hc}")
                process.terminate()


    def status(self):
        if self.start_time != None:
            now = datetime.now()
            uptime = str(now - self.start_time)
        else:
            uptime = "00:00:00"

        status = {
            "uuid": self.uuid,
            "state": self.state.name,
            "uptime": uptime, 
            "port": self.port,
            "mission": self.mission,
            "hostname": self.hostname,
            "password": self.password,
            "admin_password": self.admin_password,
            "map": self.map,
            "signatures": self.signatures,
            "players_count": self.players_count,
            "mods_count": self.mods_count,
            "player": self.players,
            "mods": self.mods
        }
        
        return status