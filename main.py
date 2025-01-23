import os
import threading

from config import configuration, config_file
from loguru import logger

from fabric import Application
from widgets.pill import PillWindow
from widgets.bar import BarWindowLeft, BarWindowRight, BarWindow
from fabric.utils import exec_shell_command, monitor_file, get_relative_path


def apply_styles():
    if os.path.exists("style.css"):
        logger.info("Removing existing style.css")
        os.remove("style.css")

    logger.info("Compiling sass...")
    output = exec_shell_command(
        f"sass {configuration.get_property('styles_dir')}/style.scss style.css --no-source-map"
    )

    if output == "":
        app.set_stylesheet_from_file("style.css")
        logger.info("Successfully loaded styles!")
    else:
        logger.error("Failed to compile sass!")


if __name__ == "__main__":
    global pill_window
    pill_window = PillWindow()

    global bar_window_left
    bar_window_left = BarWindowLeft()

    global bar_window_right
    bar_window_right = BarWindowRight()

    global bar_window
    bar_window = BarWindow()

    app = Application(
        configuration.get_property("app_name"),
        bar_window,
        pill_window,
        # bar_window_left,
        # bar_window_right,
        open_inspector=True,
    )

    if not os.path.exists("style.css"):
        apply_styles()
    else:
        logger.info("Applying styles in the background...")
        threading.Thread(target=apply_styles).start()

    css_monitor = monitor_file(
        get_relative_path(configuration.get_property("styles_dir"))
    )
    css_monitor.connect("changed", lambda *_: apply_styles())

    # config_monitor = monitor_file(config_file)
    config_monitor = monitor_file(get_relative_path("default_config.toml"))
    config_monitor.connect("changed", lambda *_: configuration.load_config())

    logger.info("Starting shell...")
    app.run()
