import re
import uuid
import shutil
import subprocess
import asyncio

from pathlib import Path
from datetime import datetime

from models.server import MissionModel

class Server():
    def __init__(self, name:str, port: int, root_directory: Path, executable: str):
        self.uuid = str(uuid.uuid4())
        self.name = name
        self.port = port
        self.root_directory = root_directory
        self.directory = root_directory / name
        self.executable = root_directory / name / executable
        self.directory_logs = self.root_directory / "logs" / name 

        self.mods = {}
        self.state = "Open"
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

        return status
        

    def _verify_workshop(self):
        """
        Verify mods for existence and keys
        """
        status = 0
        missing_mods, mods_without_keys = [], []
        workshop_directory = self.directory / "workshop"

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


    def _parser_server_config(self, mission_config: MissionModel):
        template_path = self.root_directory / "configs/server.cfg"
        config_path = self.root_directory / "configs" / f"{self.name}.cfg"

        # if signatures were not set then used based on keys availability
        if mission_config.signatures == -1:
            signatures = mission_config.signatures
        else:
            signatures = self.signatures
            

        # TODO: arguments verification
        mapping_dictionary = {
            "NAME": mission_config.name,
            "PASSWD": mission_config.password,
            "ADMINPASSWD": mission_config.admin_password,
            "PLAYERS": mission_config.players,
            "SIGNATURES": signatures,
            "MISSSION": mission_config.mission[:-4] # -4 for .pbo cuz arma
        }

        text = template_path.read_text()

        for tag, value in mapping_dictionary.items():
            text = text.replace(f"[{tag}]", str(value))
            # print(f"Writing: {value}")

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
            # "-profile=" + name,
            "-connect=127.0.0.1", "-port=" + str(self.port),
            "-password=" + str(password)
        ]
        args.append(mods)

        return args

    async def _read_stream(self, stream, file_path: Path, callback=None):
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
                f.write(decoded_line + "\n")
                f.flush()
                if callback:
                    callback(decoded_line)


    async def start(self, mission_config: MissionModel):
        status = self._parser_html_preset(Path(mission_config.preset))
        if status == 0:
            self._verify_workshop()
        self._parser_server_config(mission_config)
        args, mods = self._parser_start_arguments()

        if status != 0:
            return 1, self.messages

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.directory_logs / f"{timestamp}_{self.uuid}_{self.name}.log"

        self.process = await asyncio.create_subprocess_exec(
            *args,
            cwd=self.directory,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )
        asyncio.create_task(self._read_stream(self.process.stdout, log_file))

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

        self.state = "Running"


    def stop(self):
        if hasattr(self, "process") and self.process.returncode is None:
            print(f"Requesting stop for {self.name}")
            self.process.terminate()
            self.state = "Open"
        
        if hasattr(self, "headless") and self.process.returncode is None:
            for hc, process in self.headless.items():
                print(f"Requesting stop for {hc}")
                process.terminate()