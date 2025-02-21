from config import configuration

from widgets.bar.battery import BatteryWidget
from widgets.bar.resource_monitor import ResourceMonitor
from widgets.bar.network_usage import NetworkUsage
from widgets.bar.screen_recorder import ScreenRecorder

from widgets.buttons import MarkupButton, WorkspaceMarkupButton
from widgets.system_tray import SystemTray
from widgets.corner import Corner
from widgets.keyboard_layout import KeyboardLayout

from fabric.widgets.wayland import WaylandWindow as Window
from fabric.widgets.box import Box
from fabric.widgets.revealer import Revealer
from fabric.hyprland.widgets import Workspaces, get_hyprland_connection
from fabric.utils.helpers import FormattedString

# from fabric.system_tray.widgets import SystemTray
# from fabric.widgets.shapes.corner import Corner

from loguru import logger


class BarWindow(Window):
    def __init__(self, *args, **kwargs):
        super().__init__(
            anchor="left top right",
            exclusivity="auto",
            layer="top",
            pass_through=True,
            visible=False,
            # child=Box(
            #     name="bar_window",
            #     # h_expand=True,
            #     # v_expand=True,
            #     # h_align="fill",
            #     # v_align="fill",
            # ),
            *args,
            **kwargs,
        )

        self.set_size_request(0, 49)
        self.show()
        # self.set_default_size(10, 50)
        # self.set_resizable(False)
        # logger.error(self.get_default_size())


class BarWindowLeft(Window):
    def __init__(self, *args, **kwargs):
        super().__init__(
            # name="bar_window_left",
            anchor="left top",
            layer="top",
            exclusivity="normal",
            visible=False,
            *args,
            **kwargs,
        )

        def factory(id):
            return (
                WorkspaceMarkupButton(
                    id=id,
                    name="workspace_button",
                    style_classes="outsider",
                    child=Box(
                        name="workspace_icon",
                        v_expand=False,
                        v_align="center",
                    ),
                )
                if id > 0
                else None
            )

        self.workspaces_widget = Workspaces(
            name="workspaces_widget",
            style_classes="bar_widget",
            empty_scroll=True,
            invert_scroll=True,
            buttons=[
                WorkspaceMarkupButton(
                    id=i + 1,
                    name="workspace_button",
                    child=Box(
                        name="workspace_icon",
                        v_expand=False,
                        v_align="center",
                    ),
                )
                for i in range(
                    int(configuration.get_property("workspaces_widget_num_workspaces"))
                )
            ],
            buttons_factory=factory,
        )

        self.keyboard_layout_widget = KeyboardLayout(
            name="keyboard_layout_widget",
            style_classes="bar_widget",
            keyboard=name
            if (name := configuration.get_property("switchxkblayout_keyboard_name"))
            else ".*",
            formatter=FormattedString("{language}"),
            language_formatter=lambda x: x[:2].upper(),
        )
        self.keyboard_layout_widget.connect(
            "clicked",
            lambda *_: get_hyprland_connection().send_command(
                f"switchxkblayout {configuration.get_property('switchxkblayout_keyboard_name')} next"
            ),
        )

        self.wallpaper_widget = Box(name="wallpaper_widget", style_classes="bar_widget")

        self.screen_recorder_widget = ScreenRecorder(
            style_classes="bar_widget",
        )

        self.widgets = Box(
            name="bar_start_container",
            h_align="start",
            children=[
                self.workspaces_widget,
                self.keyboard_layout_widget,
                self.wallpaper_widget,
                self.screen_recorder_widget,
            ],
        )

        self.main_container = Box(
            name="bar_window_left",
            orientation="h",
            children=[
                self.widgets,
                Box(
                    name="corner_container",
                    orientation="v",
                    children=[
                        Box(
                            name="corner_container",
                            children=[
                                Corner(
                                    orientation="top-left", name="corner", h_expand=True
                                )
                            ],
                        ),
                        Box(v_expand=True),
                    ],
                ),
            ],
            *args,
            **kwargs,
        )
        self.add(self.main_container)
        self.show_all()


class BarWindowRight(Window):
    def __init__(self, *args, **kwargs):
        super().__init__(
            # name="bar_window_right",
            anchor="top right",
            exclusivity="normal",
            layer="top",
            visible=False,
            *args,
            **kwargs,
        )

        self.network_usage_widget = NetworkUsage()
        self.resource_monitor_widget = ResourceMonitor()
        self.battery_widget = BatteryWidget()

        self.tray = SystemTray(
            name="tray_widget",
            icon_size=configuration.get_property("tray_icon_size"),
        )
        self.tray_revealer = Revealer(
            child=self.tray,
            transition_type="slide_left",
            transition_duration=configuration.get_property(
                "tray_revealer_reveal_animation_duration"
            ),
        )

        def on_tray_expander_clicked():
            if self.tray_revealer.child_revealed:
                self.tray_revealer.unreveal()
                self.tray_expander.remove_style_class("revealed")
                self.tray_expander.set_markup(
                    configuration.get_property("chevron_left")
                )
            else:
                self.tray_revealer.reveal()
                self.tray_expander.add_style_class("revealed")
                self.tray_expander.set_markup(
                    configuration.get_property("chevron_right")
                )

        self.tray_expander = MarkupButton(
            name="tray_container_expander",
            markup=configuration.get_property("chevron_left"),
        )
        self.tray_expander.connect(
            "clicked",
            lambda *_: on_tray_expander_clicked(),
        )

        self.tray_container = Box(
            name="tray_container",
            style_classes="bar_widget",
            children=[
                self.tray_revealer,
                self.tray_expander,
            ],
        )

        self.widgets = Box(
            name="bar_end_container",
            h_align="end",
            children=[
                self.network_usage_widget,
                self.resource_monitor_widget,
                self.battery_widget,
                self.tray_container,
            ],
        )

        self.main_container = Box(
            name="bar_window_right",
            orientation="h",
            children=[
                Box(
                    name="corner_container",
                    orientation="v",
                    children=[
                        Box(
                            name="corner_container",
                            children=[
                                Corner(
                                    orientation="top-right",
                                    name="corner",
                                    h_expand=True,
                                )
                            ],
                        ),
                        Box(v_expand=True),
                    ],
                ),
                self.widgets,
            ],
            *args,
            **kwargs,
        )
        self.add(self.main_container)
        self.show_all()
