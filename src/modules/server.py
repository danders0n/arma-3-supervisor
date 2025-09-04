import re
import shutil
import subprocess

from pathlib import Path
from models.server import MissionModel
from models.config import ConfigModel


class Server():
    def __init__(self, server_name:str, config: ConfigModel, mission: MissionModel):
        self.server_name = server_name
        self.config = config
        self.mission = mission
        self.server_directory = Path(self.config.directory, self.server_name)
        self.errors = {}

        self.__html_preset()
    

    def __html_preset(self) -> int:
        """
        Return dictionary of IDs and Names from HTML Preset exported from Arma 3 Launcher     
        """
        self.mods = {}

        mods_id = []
        names_id = []

        preset_filepath = Path(self.config.directory, "presets", self.mission.preset)

        if not preset_filepath.exists():
            self.errors["html_parser"] = f"{self.mission.preset} not found in presets directory"
            return 1

        # Reading preset
        with open(preset_filepath) as file:
            html = file.read()

            regex_id = r"filedetails\/\?id=(\d+)\""
            matches_id = re.finditer(regex_id, html, re.MULTILINE)

            regex_name = r"\"DisplayName\">(.*?)<\/td>"
            matches_name = re.finditer(regex_name, html, re.MULTILINE)

            # Can be made in one loop but is really needed?
            for match in matches_id:
                mods_id.append(match.group(1))
            for match in matches_name:
                names_id.append(match.group(1))

        if len(mods_id) != len(names_id):
            self.errors["html_parser"] = f"{self.mission.preset} parsing failed, mismatched IDs and Names"
            return 1

        self.mods = dict(zip(mods_id, names_id))

        return 0
        

    def __verify_workshop(self):
        """
            Verify mods for existence and keys
        """
        missing_mods = []
        mods_without_keys = []
        workshop_directory = self.server_directory / "workshop"
        for id, name in self.mods.items():
            mod_path = Path(workshop_directory, id)

            # check if mods exists in workshop directory
            if not mod_path.exists():
                missing_mods.append({id: name})
                print(f"Workshop item: {id}: {name} not found!")
            
            # check if mod have any keys
            keys = list(mod_path.glob("*/*.bikey"))
            if len(keys) > 0:
                for key in keys:
                    shutil.copy2(key, self.server_directory / "keys" / key.name)
                self.signatures = 2
            else:
                print(f"{mod_path} Keys Not Found!")
                mods_without_keys.append({id: name})
                self.signatures = 0

        # TODO: Download new mods
        return mods_without_keys, missing_mods

    def __parse_config(self):
        template_path = Path (self.config.directory, "configs/server.cfg")
        config_path = Path (self.config.directory, "configs", f"{self.server_name}.cfg")

        # if signatures were not set then used based on keys availability
        if self.mission.signatures == -1:
            signatures = self.mission.signatures
        else:
            signatures = self.signatures
            

        # TODO: arguments verification
        mapping_dictionary = {
            "NAME": self.mission.name,
            "PASSWD": self.mission.password,
            "ADMINPASSWD": self.mission.admin_password,
            "PLAYERS": self.mission.players,
            "SIGNATURES": signatures,
            "MISSSION": self.mission.mission
        }

        text = template_path.read_text()

        for tag, value in mapping_dictionary.items():
            text = text.replace(f"[{tag}]", str(value))
            # print(f"Writing: {value}")

        config_path.write_text(text)
        return config_path


    def __parse_arguments(self):
        args = [
           str(self.server_directory / self.config.executable), 
            "-name=" + str(self.server_name),
            "-port=" + "2302",
            "-profiles=/opt/arma-3/profiles/",
            "-cfg=/opt/arma-3/configs/basic.cfg",
            "-config=" + str(self.config.directory) + "configs/" + f"{self.server_name}.cfg",
            "-loadMissionToMemory",
            "-hugePages",
            "-maxFileCacheSize=8192",
            "-bandwidthAlg=2",
            "-debug",
            "-filePatching"
        ]
        arg_mods = "-mod="
        for id, name in self.mods.items():
            mod_path = self.server_directory / "workshop" / id
            arg_mods += f"{mod_path};"
        arg_mods = arg_mods[:-1]

        args.append(arg_mods)
        return(args)

    def start(self):
        self.__verify_workshop()
        # self.__parse_config()
        # args = self.__parse_arguments()

        if len(self.errors) > 0:
            return 1, self.errors
        else:
            self.process = subprocess.Popen(args, cwd=self.server_directory)
            return 0, self.process
    

    def stop(self):
        if hasattr(self, "process") and self.process.poll() is None:
            self.process.kill()