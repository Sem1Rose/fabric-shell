import os

from config import configuration, config_file
from loguru import logger

from fabric import Application
from fabric.utils import monitor_file, get_relative_path
from widgets.helpers.formatted_exec import formatted_exec_shell_command

from windows.pill import PillWindow, PillApplets
from windows.osd import OSDWindow, UrgentOSDWindow
from windows.bar import BarWindowLeft, BarWindowRight, BarWindow

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
        # idle_add(app.set_stylesheet_from_file, "style.css")
        app.set_stylesheet_from_file("style.css")
        logger.info("Successfully loaded styles!")
    else:
        # idle_add(app.set_stylesheet_from_string, "")
        app.set_stylesheet_from_string("")
        logger.error("Failed to compile sass!")


if __name__ == "__main__":
    global osd_window
    osd_window = OSDWindow()

    global urgent_osd
    urgent_osd = UrgentOSDWindow()

    # global bar_window_left
    # bar_window_left = BarWindowLeft()

    # global bar_window_right
    # bar_window_right = BarWindowRight()

    global bar_window
    bar_window = BarWindow()

    global pill_window
    pill_window = PillWindow()

    app = Application(
        configuration.get_property("app_name"),
        osd_window,
        urgent_osd,
        # bar_window_left,
        # bar_window_right,
        pill_window,
        bar_window,
        open_inspector=configuration.get_property("debug"),
    )

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

    logger.info(f"Starting shell... pid:{os.getpid()}")
    app.run()
