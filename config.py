import toml
import os

from platformdirs import user_cache_dir, user_config_dir
from loguru import logger

from fabric.utils import get_relative_path

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
            logger.info("Loading config.toml ...")
            with open(config_file) as f:
                self.config = toml.load(f)
        else:
            logger.info("config.toml not found, loading default config...")
            with open(get_relative_path("default_config.toml")) as f:
                self.config = toml.load(f)

        # self.app_name = self.config["app_settings"]["app_name"]
        # self.reveal_animation_duration = self.config["app_settings"][
        #     "reveal_animation_duration"
        # ]

        # self.styles_dir = self.parse_dir(self.config["app_settings"]["styles_dir"])
        # self.icons_dir = self.parse_dir(self.config["app_settings"]["icons_dir"])
        # self.artwork_cache_dir = self.parse_dir(
        #     self.config["app_settings"]["artwork_cache_dir"]
        # )

        # self.spacing = self.config["app_settings"]["spacing"]
        # self.artwork_size = self.config["app_settings"]["artwork_size"]
        # self.no_artwork_icon_size = self.config["app_settings"]["no_artwork_icon_size"]
        # self.icon_size = self.config["app_settings"]["icon_size"]

        self.set_css_settings()

    def get_setting(self, name: str):
        if name not in self.config["app_settings"]:
            return None

        if name.endswith("_dir"):
            return self.parse_dir(self.config["app_settings"][name])
        else:
            return self.config["app_settings"][name]

    def set_css_settings(self):
        logger.info("Applying css settings...")

        settings = ""
        for setting in self.config["css_settings"]:
            settings += f"${setting}: {self.config['css_settings'][setting]};\n"

        with open(get_relative_path("styles/_settings.scss"), "w") as f:
            f.write(settings)


configuration = Config()
