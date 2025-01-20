import os
import threading

import config

from fabric import Application
from widgets.pill import Pill
from fabric.widgets.wayland import WaylandWindow as Window
from fabric.widgets.centerbox import CenterBox
from fabric.utils import exec_shell_command, monitor_file, get_relative_path


class Bar(Window):
    def __init__(self, **kwargs):
        super().__init__(
            name="pillet",
            anchor="left top right",
            exclusivity="exclusive",
            layer="top",
            visible=False,
            **kwargs,
        )

        self.pill = Pill()
        self.center_box = CenterBox(center_children=self.pill)
        self.add(self.center_box)

        self.show_all()


def apply_style():
    if os.path.exists("style.css"):
        os.remove("style.css")

    exec_shell_command(f"sass {config.styles_dir}/style.scss style.css --no-source-map")

    app.set_stylesheet_from_file("style.css")


if __name__ == "__main__":
    global bar
    bar = Bar()
    app = Application(config.app_name, bar)

    if not os.path.exists("style.css"):
        apply_style()
    else:
        threading.Thread(target=apply_style).start()

    css_monitor = monitor_file(get_relative_path(config.styles_dir))
    css_monitor.connect("changed", lambda *_: apply_style())

    # config_monitor = monitor_file(f"{get_relative_path(config_file)}/config.toml")
    # config_monitor.connect("changed", lambda *_: config.load_config())

    app.run()
