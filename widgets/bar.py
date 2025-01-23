from widgets.bar_widgets import BatteryWidget, WallpaperWidget

from fabric.widgets.wayland import WaylandWindow as Window
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.box import Box
from fabric.widgets.datetime import DateTime
from fabric.widgets.eventbox import EventBox


class BarWindow(Window):
    def __init__(self, *args, **kwargs):
        super().__init__(
            anchor="left top right",
            exclusivity="auto",
            layer="top",
            visible=True,
            child=Box(name="bar_window"),
            pass_through=True,
            *args,
            **kwargs,
        )


class BarWindowLeft(Window):
    def __init__(self, *args, **kwargs):
        super().__init__(
            name="bar_window_left",
            anchor="left top",
            exclusivity="normal",
            layer="top",
            visible=False,
            *args,
            **kwargs,
        )

        self.wallpaper_widget = WallpaperWidget()
        self.main_container = Box(
            name="bar_start_container",
            h_align="start",
            children=[self.wallpaper_widget],
        )

        self.add(self.main_container)
        self.show_all()


class BarWindowRight(Window):
    def __init__(self, *args, **kwargs):
        super().__init__(
            name="bar_window_right",
            anchor="top right",
            exclusivity="normal",
            layer="top",
            visible=False,
            *args,
            **kwargs,
        )

        self.battery_widget = BatteryWidget()

        self.main_container = Box(
            name="bar_end_container", h_align="end", children=[self.battery_widget]
        )

        self.add(self.main_container)
        self.show_all()
