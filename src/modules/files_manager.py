import os
import aiofiles

from pathlib import Path
from datetime import datetime
from fastapi import UploadFile
from fastapi.responses import FileResponse

from models.config import ConfigModel

class FilesManager():
    def __init__(self, server_config: ConfigModel):
        self.root = Path(server_config.directory)
        self.missions = Path(server_config.directory,  "missions")
        self.presets = Path(server_config.directory,  "presets")

    
    async def upload(self, file: UploadFile, override: bool):
        filename = str(file.filename)
        file_type = filename.split(".")[-1]

        if file_type == "html":
            dst_path = self.presets / filename
        elif file_type == "pbo":
            dst_path = self.missions / filename
        else:
            return {"status": 1, "detail": {"file_manager.upload": "File not recognized!"}}


        if dst_path.exists() and not override:
            return {"status": 1, "detail": {"file_manager.upload": "File already exists and override set to False!"}}

        async with aiofiles.open(dst_path, "wb") as out_file:
            while chunk := await file.read(1024*1024):  # read in 1MB chunks
                await out_file.write(chunk)

        print(dst_path)
        return {"status": 0, "detail": {"file_manager.upload": f"Upload sucessfull... {file}"}}
        


    async def download(self, file : str):
        filepath = self.root / file
        if not filepath.exists():
            return {"status": 1, "detail": {"file_manager.download": f"File not found... {file}"}}
        
        return {"status": 0, "detail": "Download is disabled due to lack of idea how to write this method"}


    async def list_pbo_missions(self):
        files = {}
        for file in os.listdir(self.missions):
            stats = Path(self.missions / file).stat()
            print("ctime (datetime):", datetime.fromtimestamp(stats.st_ctime))
            files[file] = datetime.fromtimestamp(stats.st_ctime)
        
        return {"status": 0, "detail": files}


    async def list_html_presets(self):
        files = {}
        for file in os.listdir(self.presets):
            stats = Path(self.presets / file).stat()
            print("ctime (datetime):", datetime.fromtimestamp(stats.st_ctime))
            files[file] = datetime.fromtimestamp(stats.st_ctime)
        
        return {"status": 0, "detail": files}