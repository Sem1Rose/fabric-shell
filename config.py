import toml
import os
from fabric.utils import get_relative_path
from platformdirs import user_cache_dir, user_config_dir

config_file = f"{user_config_dir('fabric-shell')}/config.toml"


class Config:
    def parse_dir(self, dir: str) -> str:
        if dir.startswith("user_cache_dir"):
            if dir.__contains__("-"):
                dir_name = "-".join(dir.split("-")[1:])
                return f"{user_cache_dir()}/{dir_name}"
            else:
                return user_cache_dir
        elif dir.startswith("user_config_dir"):
            if dir.__contains__("-"):
                dir_name = "-".join(dir.split("-")[1:])
                return f"{user_config_dir()}/{dir_name}"
            else:
                return user_config_dir

        return dir

    def __init__(self):
        self.load_config()

    def load_config(self):
        if os.path.exists(config_file):
            with open(config_file) as f:
                self.config = toml.load(f)
        else:
            with open(get_relative_path("default_config.toml")) as f:
                self.config = toml.load(f)

        self.app_name = self.config["app_name"]

        self.styles_dir = self.parse_dir(self.config["styles_dir"])
        self.icons_dir = self.parse_dir(self.config["icons_dir"])
        self.artwork_cache_dir = self.parse_dir(self.config["artwork_cache_dir"])

        self.spacing = self.config["spacing"]
        self.artwork_size = self.config["artwork_size"]
        self.no_artwork_icon_size = self.config["no_artwork_icon_size"]
        self.icon_size = self.config["icon_size"]


configuration = Config()

# from platformdirs import user_cache_dir, user_config_dir

# app_name = "fabric-shell"

# styles_dir = "styles"
# icons_dir = "icons"
# artwork_cache_dir = user_cache_dir("artworks")
# config_dir = user_config_dir("fabric-shell")

# spacing = 5
# artwork_size = 120
# no_artwork_icon_size = 40
# icon_size = 24
