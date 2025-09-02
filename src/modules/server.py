import re
import shutil
import subprocess

from pathlib import Path

from models.server import MissionModel
from models.config import ConfigModel


class Server():
    def __init__(self, config: ConfigModel, mission: MissionModel):
        self.config = config
        self.mission = mission
        self.server_directory = Path(self.config.directory, self.mission.name)
        self.mods = self.__html_preset()
    

    def __html_preset(self) -> dict:
        """
        Return dictionary of IDs and Names from HTML Preset exported from Arma 3 Launcher     
        """
        mods_id = []
        names_id = []
        mods = {}

        filepath = Path(self.config.directory, "presets", self.mission.preset)

        if not filepath.exists():
            raise FileNotFoundError

        # Reading preset
        with open(filepath) as file:
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

        for i in range(len(mods_id)):
            mods.update({mods_id[i]: names_id[i]})

        return mods
        

    def __verify_workshop(self):
        """
            Verify mods for existence and keys
        """
        missing_mods = []
        workshop_directory = self.server_directory / "workshop"
        for id, name in self.mods.items():
            mod_path = Path(workshop_directory, id)

            # check if mods exists in workshop directory
            if not mod_path.exists():
                missing_mods.append(id)
                print(f"Workshop item: {id}: {name} not found!")
            
            # check if mod have any keys
            keys = list(mod_path.glob("*/*.bikey"))
            if len(keys) > 0:
                for key in keys:
                    shutil.copy2(key, self.server_directory / "keys" / key.name)
            else:
                print(f"{mod_path} Keys Not Found!")

        # TODO: Download new mods, setup signatures based on keys


    def __parse_config(self):
        template_path = Path (self.config.directory, "configs/server.cfg")
        config_path = Path (self.config.directory, "configs", f"{self.mission.name}.cfg")

        # TODO: arguments verification
        mapping_dictionary = {
            "NAME": self.mission.name,
            "PASSWD": self.mission.password,
            "ADMINPASSWD": self.mission.admin_password,
            "PLAYERS": self.mission.players,
            "SIGNATURES": self.mission.signatures,
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
            "-name=" + str(self.mission.name),
            "-port=" + "2302",
            "-profiles=/opt/arma-3/profiles/",
            "-cfg=/opt/arma-3/configs/basic.cfg",
            "-config=" + str(self.config.directory) + "configs/" + f"{self.mission.name}.cfg",
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
            # print(f"{mod_path};")
        arg_mods = arg_mods[:-1]

        args.append(arg_mods)
        return(args)

    def start(self):
        self.__verify_workshop()
        self.__parse_config()
        args = self.__parse_arguments()
        self.process = subprocess.Popen(args, cwd=self.server_directory)

    
    def stop(self):
        pass
        