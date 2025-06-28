import os

from config import configuration, config_file
from loguru import logger

from fabric import Application
from fabric.utils import monitor_file, get_relative_path, idle_add
from widgets.helpers.formatted_exec import formatted_exec_shell_command

from windows.pill import PillWindow, PillApplets
from windows.osd import OSDWindow, UrgentOSDWindow
from windows.bar import BarWindow

# import sdbus
# from sdbus_block.networkmanager import (
#     NetworkDeviceGeneric,
#     NetworkDeviceWireless,
#     NetworkConnectionSettings,
#     NetworkManagerSettings,
#     NetworkManager,
# )
# from sdbus import sd_bus_open_system
# from sdbus_async.networkmanager import (
#     NetworkDeviceGeneric,
#     NetworkDeviceWireless,
#     NetworkConnectionSettings,
#     NetworkManagerSettings,
#     NetworkManager,
#     AccessPoint,
# )

# from sdbus_block.networkmanager.enums import DeviceType
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib  # noqa: E402, F401

logger.disable("fabric.audio")
logger.disable("fabric.widgets.wayland")
logger.disable("fabric.hyprland.widgets")


def apply_styles():
    if os.path.exists("style.css"):
        logger.info("Removing existing style.css")
        os.remove("style.css")

    logger.info("Compiling sass...")
    output = formatted_exec_shell_command(
        configuration.get_property("sass_compiler_command"),
        input=os.path.join(configuration.get_property("styles_dir"), "style.scss"),
        output="style.css",
    )

    if output == "":
        # for app in apps.values():
        # app.set_stylesheet_from_file("style.css")
        idle_add(app.set_stylesheet_from_file, "style.css")
        logger.info("Successfully loaded styles!")
    else:
        # for app in apps.values():
        # app.set_stylesheet_from_string("")
        idle_add(app.set_stylesheet_from_string, "")
        logger.error("Failed to compile sass!")


if __name__ == "__main__":
    # global osd_window
    # osd_window = OSDWindow()

    # global urgent_osd
    # urgent_osd = UrgentOSDWindow()

    global bar_window
    bar_window = BarWindow()

    global pill_window
    pill_window = PillWindow()

    app = Application(
        configuration.get_property("app_name"),
        # osd_window,
        # urgent_osd,
        pill_window,
        bar_window,
        open_inspector=configuration.get_property("debug"),
    )
    # apps = {}
    # apps["osd_app"] = Application(
    #     f"{configuration.get_property('app_name')}-osd",
    #     osd_window,
    #     open_inspector=configuration.get_property("debug"),
    # )
    # apps["urgent_osd_app"] = Application(
    #     f"{configuration.get_property('app_name')}-urgent-osd",
    #     urgent_osd,
    #     open_inspector=configuration.get_property("debug"),
    # )
    # apps["bar_app"] = Application(
    #     f"{configuration.get_property('app_name')}-bar",
    #     bar_window,
    #     open_inspector=configuration.get_property("debug"),
    # )
    # apps["pill_app"] = Application(
    #     f"{configuration.get_property('app_name')}-pill",
    #     pill_window,
    #     open_inspector=configuration.get_property("debug"),
    # )

    if not os.path.exists("style.css"):
        apply_styles()
    else:
        logger.info("Applying styles in the background...")
        GLib.Thread.new("apply-styles", apply_styles)

    css_monitor = monitor_file(
        get_relative_path(configuration.get_property("styles_dir"))
    )
    css_monitor.connect("changed", lambda *_: apply_styles())

    config_monitor = monitor_file(config_file)
    # config_monitor = monitor_file(get_relative_path("default_config.toml"))
    config_monitor.connect("changed", lambda *_: configuration.load_config())

    # sdbus.set_default_bus(sdbus.sd_bus_open_system())
    # system_bus = sd_bus_open_system()  # We need system bus
    # network_manager = NetworkManager(system_bus)
    # all_devices = {path: NetworkDeviceGeneric(path) for path in network_manager.devices}

    # wifi_devices = [
    #     NetworkDeviceWireless(path)
    #     for path, device in all_devices.items()
    #     if device.device_type == DeviceType.WIFI
    # ]

    # logger.error(wifi_devices)

    # wifi = wifi_devices[0]
    # ap = AccessPoint(wifi.active_access_point)
    # logger.error(ap)
    # nmasync = NetworkManagerAsync()

    # networwork_manager_settings = NetworkManagerSettings()
    # all_devices = {path: NetworkDeviceGeneric(path) for path in network_manager.devices}

    # wifi_devices = [
    #     NetworkDeviceWireless(path)
    #     for path, device in all_devices.items()
    #     if device.device_type == DeviceType.WIFI
    # ]

    # all_connections = [
    #     NetworkConnectionSettings(x) for x in networwork_manager_settings.connections
    # ]
    # logger.error(all_connections)

    # setting = NetworkConnectionSettings(networwork_manager_settings.connections[0])
    # setting_dataclass = setting.get_profile(False)
    # logger.error(setting_dataclass.connection)

    logger.info(f"Starting shell... pid:{os.getpid()}")
    app.run()

    # handles = []
    # for name, app in apps.items():
    #     handles.append(GLib.Thread.new(name, app.run))
    #     handles.append(GLib.Thread.new("urgent_osd", urgent_osd_app.run))
    #     handles.append(GLib.Thread.new("bar", bar_app.run))
    #     handles.append(GLib.Thread.new("pill", pill_app.run))

    # for handle in handles:
    #     handle.join()
