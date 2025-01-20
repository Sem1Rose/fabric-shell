import os
import threading

from config import configuration, config_file

from fabric import Application
from widgets.pill import Pill
from fabric.widgets.wayland import WaylandWindow as Window
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.datetime import DateTime
from fabric.utils import exec_shell_command, monitor_file, get_relative_path


class PillWindow(Window):
    def __init__(self, **kwargs):
        super().__init__(
            name="pill-window",
            anchor="top",
            exclusivity="none",
            layer="top",
            visible=False,
            **kwargs,
        )

        self.pill = Pill()
        self.add(self.pill)

        self.show_all()


class BarWindow(Window):
    def __init__(self, **kwargs):
        super().__init__(
            name="bar-window",
            anchor="left top right",
            exclusivity="auto",
            layer="top",
            visible=False,
            **kwargs,
        )

        self.date_time = DateTime()
        self.children = CenterBox(center_children=self.date_time)

        self.show_all()


def apply_styles():
    if os.path.exists("style.css"):
        os.remove("style.css")

    exec_shell_command(
        f"sass {configuration.styles_dir}/style.scss style.css --no-source-map"
    )

    app.set_stylesheet_from_file("style.css")


css_monitor = monitor_file(get_relative_path(configuration.styles_dir))
css_monitor.connect("changed", lambda *_: apply_styles())

if __name__ == "__main__":
    global pill_window
    pill_window = PillWindow()

    global bar_window
    bar_window = BarWindow()

    app = Application(configuration.app_name, pill_window, bar_window)

    if not os.path.exists("style.css"):
        apply_styles()
    else:
        threading.Thread(target=apply_styles).start()

    # config_monitor = monitor_file(config_file)
    config_monitor = monitor_file(get_relative_path("default_config.toml"))
    config_monitor.connect("changed", lambda *_: configuration.load_config())

    app.run()
