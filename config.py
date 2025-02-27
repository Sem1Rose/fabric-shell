import toml
import os

import platformdirs
from platformdirs import user_config_dir
from collections.abc import Iterable

from loguru import logger

from fabric.utils import get_relative_path

config_file = os.path.join(user_config_dir("fabric-shell"), "config.toml")


class Config:
    def try_parse_dir(self, dir: str) -> str:
        if not isinstance(dir, str):
            return dir

        quotes = ""
        if dir.startswith('"'):
            quotes = '"'
            dir = dir[1:-1]

        if dir.__contains__("-"):
            user_dir = dir.split("-")[0]
            folder = "-".join(dir.split("-")[1:])
        else:
            folder = None
            user_dir = dir

        try:
            d = getattr(platformdirs, user_dir)

            if folder:
                path = os.path.normpath(os.path.join(d(), folder))
            else:
                path = d()

            return f"{quotes}{path}{quotes}"
        except Exception:
            return f"{quotes}{dir}{quotes}"

    def __init__(self):
        if not os.path.exists(get_relative_path("default_config.toml")):
            logger.critical(
                f"Couldn't find default config at {get_relative_path('default_config.toml')}, exiting.."
            )
            exit(1)

        self.default_config = toml.load(get_relative_path("default_config.toml"))

        self.load_config()

    def load_config(self):
        if os.path.exists(config_file):
            logger.info("Loading config.toml ...")
            with open(config_file) as f:
                self.config = toml.load(f)
        else:
            self.config = {}
        # else:
        #     logger.info(
        #         f"Configuration file not found in {config_file}, loading default config..."
        #     )
        #     with open(get_relative_path("default_config.toml")) as f:
        #         self.config = toml.load(f)

        self.set_css_settings()

    def get_property(
        self,
        name: str,
        sections: Iterable[str] | str = "app_settings",
        default: bool | None = None,
    ) -> str | bool | int | None:
        if default is not None:
            return self.fetch_config_prop(name, sections, default)
        else:
            if not (property := self.fetch_config_prop(name, sections)):
                property = self.fetch_config_prop(name, sections, True)

            return property

    def fetch_config_prop(
        self, name: str, sections: Iterable[str] | str = "app_settings", default=False
    ):
        config = self.default_config if default else self.config

        if isinstance(sections, str):
            if sections not in config:
                return None

            section = config[sections]
        else:
            section = config
            for i in sections:
                if i not in section:
                    return None

                section = section[i]

        if name not in section:
            return None

        return self.try_parse_dir(section[name])

    def set_css_settings(self):
        logger.info("Applying css settings...")

        settings = ""
        # for setting in self.config["css_settings"]:
        for setting in self.get_property("css_settings", [], True):
            settings += f"${setting}: {self.get_property(setting, 'css_settings')};\n"

        with open(get_relative_path("styles/_settings.scss"), "w") as f:
            f.write(settings)


configuration = Config()
