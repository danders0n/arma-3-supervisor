import re
import uuid
import shutil
import subprocess

from pathlib import Path
from typing import Tuple

from models.server import MissionModel


class Server():
    def __init__(self, name:str, port: int, root_directory: Path, executable: str):
        self.uuid = str(uuid.uuid4())
        self.name = name
        self.port = port
        self.root_directory = root_directory
        self.directory = root_directory / name
        self.executable = root_directory / name / executable

        self.mods = {}
        self.state = "Ready"
        self.messages = {            
            "server_errors": [],
            "server_messages": []
        }


    def __parser_html_preset(self, preset: Path) -> int:
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
        

    def __verify_workshop(self):
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


    def __parser_server_config(self, mission_config: MissionModel):
        template_path = self.root_directory / "configs/server.cfg"
        config_path = self.root_directory / "configs" / f"{self.name}.cfg"

        print()
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
            "MISSSION": mission_config.mission[:-4]
        }

        text = template_path.read_text()

        for tag, value in mapping_dictionary.items():
            text = text.replace(f"[{tag}]", str(value))
            # print(f"Writing: {value}")

        config_path.write_text(text)
        return config_path


    def __parser_start_arguments(self):
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
        arg_mods = "-mod=\""
        for id, name in self.mods.items():
            mod_path = f"workshop/{id};"
            arg_mods += mod_path
        arg_mods = arg_mods[:-1]
        arg_mods += "\""

        args.append(arg_mods)
        return(args)


    def start(self, mission_config: MissionModel):
        status = 0
        status = self.__parser_html_preset(Path(mission_config.preset))

        if status == 0:
            self.__verify_workshop()
        
        args = self.__parser_start_arguments()

        if status != 0:
            return 1, self.messages
        else:
            self.process = subprocess.Popen(args, cwd=self.directory)
            return 0, {}


    def stop(self):
        if hasattr(self, "process") and self.process.poll() is None:
            self.process.terminate()
