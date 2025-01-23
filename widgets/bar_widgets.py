from loguru import logger
from widgets.rounded_image import RoundedImage

from config import configuration
from fabric.core.fabricator import Fabricator
from fabric.utils.helpers import (
    invoke_repeater,
    exec_shell_command,
    monitor_file,
    get_relative_path,
)

from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.image import Image
from fabric.widgets.overlay import Overlay
from fabric.widgets.circularprogressbar import CircularProgressBar

from gi.repository import GdkPixbuf


class BatteryWidget(Box):
    def __init__(self, *args, **kwargs):
        super().__init__(
            name="battery_widget",
            style_classes="bar_widget",
            spacing=configuration.get_property("spacing"),
            *args,
            **kwargs,
        )

        invoke_repeater(
            1000,
            self.update_battery_levels,
        )

    def update_battery_levels(self):
        output = exec_shell_command("upower -e")
        devices = list(
            filter(lambda x: "battery" in x or "headset" in x, output.splitlines())
        )

        self.children = []
        for device in devices:
            info = exec_shell_command(f"upower -i {device}").splitlines()
            for line in info:
                if "model" in line:
                    name = line.split(": ")[1].strip()
                elif "percentage" in line:
                    percentage_display = line.split(": ")[1].strip()
                elif "state" in line:
                    state = line.split(": ")[1].strip()

            percentage_float = float(percentage_display[:-1]) / 100.0

            if "headset" in device:
                icon = ""
            elif "battery" in device:
                icon = (
                    (
                        "󰁹"
                        if percentage_float >= 0.7
                        else "󰁾"
                        if percentage_float >= 0.3
                        else "󱃍"
                    )
                    if state in ("charging", "fully-charged")
                    else ""
                )
            else:
                icon = "⬤"

            box = Box(
                name="battery_item",
                children=[
                    Overlay(
                        child=CircularProgressBar(
                            name="battery_percentage", value=percentage_float, size=10
                        ),
                        overlays=[Label(icon)],
                        name="battery_percentage_container",
                    ),
                    Label(percentage_display),
                ],
            )

            self.add(box)

        return True


class WallpaperWidget(Box):
    def __init__(self, *args, **kwargs):
        super().__init__(name="wallpaper_container", *args, **kwargs)
        self.image = RoundedImage(
            name="wallpaper_widget",
            image_file="/home/semirose/.config/wallpaper/wallpapers/f2a4731bfaf719d1885202ed42dce9b1+.png",
            size=400,
        )

        monitor = monitor_file(
            get_relative_path("/home/semirose/.config/wallpaper/.current-wallpaper"),
        )
        monitor.connect("changed", lambda *_: self.update_image())

        self.update_image()

    def update_image(self):
        logger.error("updating")
        self.image.set_from_pixbuf(
            GdkPixbuf.Pixbuf.new_from_file_at_scale(
                filename=configuration.get_property("wallpaper_file"),
                width=77,
                height=40,
                preserve_aspect_ratio=True,
            )
        )
