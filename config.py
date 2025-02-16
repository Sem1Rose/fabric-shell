import toml
import os

from platformdirs import user_cache_dir, user_config_dir, user_videos_dir
from loguru import logger

from fabric.utils import get_relative_path

config_file = os.path.join(user_config_dir("fabric-shell"), "config.toml")


class Config:
    def parse_dir(self, dir: str) -> str:
        if not isinstance(dir, str):
            return dir

        quotes = False
        if dir.startswith('"'):
            quotes = True
            dir = dir[1:-1]

        if dir.startswith("user_cache_dir"):
            if dir.__contains__("-"):
                dir_name = "-".join(dir.split("-")[1:])
                return f"{'"' if quotes else ''}{user_cache_dir()}/{dir_name}{'"' if quotes else ''}"
            else:
                return (
                    f"{'"' if quotes else ''}{user_cache_dir()}{'"' if quotes else ''}"
                )
        elif dir.startswith("user_config_dir"):
            if dir.__contains__("-"):
                dir_name = "-".join(dir.split("-")[1:])
                return f"{'"' if quotes else ''}{user_config_dir()}/{dir_name}{'"' if quotes else ''}"
            else:
                return (
                    f"{'"' if quotes else ''}{user_config_dir()}{'"' if quotes else ''}"
                )
        elif dir.startswith("user_videos_dir"):
            if dir.__contains__("-"):
                dir_name = "-".join(dir.split("-")[1:])
                return f"{'"' if quotes else ''}{user_videos_dir()}/{dir_name}{'"' if quotes else ''}"
            else:
                return (
                    f"{'"' if quotes else ''}{user_videos_dir()}{'"' if quotes else ''}"
                )

        return f"{'"' if quotes else ''}{dir}{'"' if quotes else ''}"

    def __init__(self):
        self.load_config()

    def load_config(self):
        if os.path.exists(config_file):
            logger.info("Loading config.toml ...")
            with open(config_file) as f:
                self.config = toml.load(f)
        else:
            logger.info(
                f"Configuration file not found in {config_file}, loading default config..."
            )
            with open(get_relative_path("default_config.toml")) as f:
                self.config = toml.load(f)

        self.set_css_settings()

    def get_property(
        self, name: str, section="app_settings"
    ) -> str | bool | int | None:
        if name not in self.config[section]:
            return None

        # if name.endswith("_dir") or name.endswith("_file"):
        return self.parse_dir(self.config[section][name])
        # else:
        #     return self.config[section][name]

    def set_css_settings(self):
        logger.info("Applying css settings...")

        settings = ""
        for setting in self.config["css_settings"]:
            settings += f"${setting}: {self.get_property(setting, 'css_settings')};\n"

        with open(get_relative_path("styles/_settings.scss"), "w") as f:
            f.write(settings)


configuration = Config()
