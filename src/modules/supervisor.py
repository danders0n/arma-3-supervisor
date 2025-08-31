from pathlib import Path

from models.config import Config

class Supervisor():
    """
    docstring
    """

    def __init__(self, config: Config):
        self.config = config


    def _validate_directory(self):
        reqiuers_paths = [
            self.config.directory,
            f"{self.config.directory}/serverconfig",
            f"{self.config.directory}/userconfig",
            f"{self.config.directory}/workshop",
            f"{self.config.directory}/servermods",
            f"{self.config.directory}/{self.config.executable}",
        ]

        for path in reqiuers_paths:
            path = Path(path)
            if not path.exists():
                print(f"[!] Missing directory..  {str(path)}")
                return False
                # path.mkdir(parents=True, exist_ok=True)
        
        return True


    def init(self):
        """
        Wake up supervisor to do some supervising
        """
        print("Start", self.config)


    def start(self):
        pass


    def stop(self):
        print("Stop", self.config)


if __name__ == "__main__":
    pass