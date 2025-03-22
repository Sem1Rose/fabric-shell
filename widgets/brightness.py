import os
from loguru import logger

from config import configuration
from widgets.helpers.formatted_exec import formatted_exec_shell_command_async

from fabric.core.service import Property, Service, Signal
from fabric.utils import exec_shell_command, monitor_file


backlight_device = ""
if device := configuration.get_property("backlight_device"):
    backlight_device = device
    logger.info(f"Using config brightness device: {backlight_device}")
else:
    try:
        backlight_device = os.listdir("/sys/class/backlight")
        backlight_device = backlight_device[0] if backlight_device else ""
        logger.info(f"Found brightness device {backlight_device}")
    except FileNotFoundError:
        devices = exec_shell_command(
            configuration.get_property("brightness_list_devices_command")
        )
        for device in devices.splitlines():
            if "backlight" in device:
                backlight_device = device.split(",")[0]
                logger.info(f"Found brightness device {backlight_device}")
                break
        else:
            logger.error("Counldn't find a controllable brightness device.")
            backlight_device = ""


# massive thanks to [HyDePanel](https://github.com/rubiin/HyDePanel/blob/master/services/brightness.py)
class Brightness(Service):
    @Signal
    def brightness_changed(self, percentage: float): ...

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.screen_backlight_path = f"/sys/class/backlight/{backlight_device}"

        self.max_brightness = self.get_max_brightness(self.screen_backlight_path)

        if backlight_device == "":
            return

        self.screen_monitor = monitor_file(f"{self.screen_backlight_path}/brightness")
        self.screen_monitor.connect(
            "changed",
            lambda _, file, *args: self.emit(
                "brightness_changed",
                float(file.load_bytes()[0].get_data()) / self.max_brightness,
            ),
        )

    def get_max_brightness(self, path: str) -> int:
        max_brightness_path = os.path.join(path, "max_brightness")

        if os.path.exists(max_brightness_path):
            with open(max_brightness_path) as f:
                return int(f.readline())

        return 255

    @Property(float, "read-write")
    def screen_brightness(self) -> float:
        brightness_path = os.path.join(self.screen_backlight_path, "brightness")

        if os.path.exists(brightness_path):
            with open(brightness_path) as f:
                return float(f.readline()) / self.max_brightness

        return 0

    @screen_brightness.setter
    def screen_brightness(self, value: float):
        if not (0 <= value <= 1):
            value = min(1, max(value, 0))

        formatted_exec_shell_command_async(
            configuration.get_property("set_brightness_command"),
            device=backlight_device,
            value=round(value * self.max_brightness),
        )
        self.emit("brightness_changed", value)

    def set_brightness(self, value: float):
        self.screen_brightness = value


instance: Brightness | None = None


def get_brightness_service():
    global instance
    if not instance:
        instance = Brightness()

    return instance
