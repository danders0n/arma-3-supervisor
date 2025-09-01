import re

from pathlib import Path

from models.server import MissionModel
from models.config import ConfigModel


class Server():
    def __init__(self, config: ConfigModel, mission: MissionModel):
        self.config = config
        self.mission = mission
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
        

    def verify_workshop(self):
        """
            Verify mods for existence and keys
        """
        missing_mods = []
        workshop = Path(self.config.directory, self.mission.name, "workshop")
        for id, name in self.mods.items():
            mod_path = Path(workshop, id)

            # check if mods exists in workshop directory
            if not mod_path.exists():
                missing_mods.append(id)
            
            # check if mod have any keys
        
        # TODO: Download new mods

        # TODO: copy keys