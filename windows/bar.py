from typing import Self
from config import configuration

import config
from widgets.bar.tray import Tray
from widgets.bar.battery import BatteryWidget
from widgets.bar.resource_monitor import ResourceMonitor
from widgets.bar.network_usage import NetworkUsage
from widgets.bar.screen_recorder import ScreenRecorder

from widgets.buttons import WorkspaceMarkupButton
from widgets.corner import Corner
from widgets.keyboard_layout import KeyboardLayout, NiriKeyboardLayout
from widgets.helpers.niri.widgets import Workspaces as NiriWorkspaces

from fabric.widgets.wayland import WaylandWindow as Window
from fabric.widgets.box import Box
from fabric.hyprland.widgets import Workspaces
from fabric.utils.helpers import FormattedString, idle_add

from loguru import logger


class BarWindow(Window):
    instances: list[Self] = []

    def __init__(self, *args, **kwargs):
        super().__init__(
            anchor="left top right",
            exclusivity="auto",
            layer="top",
            style="background-color: transparent;",
            # pass_through=True,
            visible=False,
            # margin="-1px 0px 0px 0px",
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

        self.main_container = Box(
            h_expand=True, v_expand=True, h_align="fill", v_align="fill"
        )
        # self.main_container.set_sensitive(False)

        add_left_container = (
            configuration.filter_bar_widgets(
                configuration.get_property("bar_widgets")["left"]
            ).__len__()
            > 0
        )
        add_right_container = (
            configuration.filter_bar_widgets(
                configuration.get_property("bar_widgets")["right"]
            ).__len__()
            > 0
        )

        if add_left_container:
            self.left_container = BarWindowLeft()
            self.main_container.pack_start(self.left_container, False, False, 0)

        # self.main_container.set_center_widget(self.center_container)
        if add_right_container:
            self.right_container = BarWindowRight()
            self.main_container.pack_end(self.right_container, False, False, 0)

        if add_left_container or add_right_container:
            self.add(self.main_container)
        else:
            self.set_size_request(
                0, int(configuration.get_property("bar_height", "css_settings")[:-2])
            )

        self.show_all()
        # self.set_default_size(10, 50)
        # self.set_resizable(False)
        # logger.error(self.get_default_size())

        BarWindow.instances.append(self)


def read_widgets(main_container, side):
    added_widgets = []
    widgets = configuration.get_property("bar_widgets")[side]
    widgets = widgets[::-1] if side == "right" else widgets
    for widget in widgets:
        if widget in added_widgets:
            logger.warning(f"Duplicate widget found in the {side} bar: {widget}")
            continue

        match widget:
            case "workspaces":
                def default_workspace_button_factory(id):
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

                if configuration.window_manager == "agnostic":
                    pass
                elif configuration.window_manager == "hyprland":
                    main_container.add(
                        Workspaces(
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
                                    int(
                                        configuration.get_property(
                                            "workspaces_widget_num_workspaces"
                                        )
                                    )
                                )
                            ],
                            buttons_factory=default_workspace_button_factory,
                        )
                    )
                elif configuration.window_manager == "niri":
                    main_container.add(
                        NiriWorkspaces(
                            name="workspaces_widget",
                            style_classes="bar_widget",
                            empty_scroll=True,
                            invert_scroll=True,
                            static_workspace_buttons=True,
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
                                    int(
                                        configuration.get_property(
                                            "workspaces_widget_num_workspaces"
                                        )
                                    )
                                )
                            ],
                            buttons_factory=default_workspace_button_factory,
                        )
                    )
            case "wallpaper":
                main_container.add(
                    Box(name="wallpaper_widget", style_classes="bar_widget")
                )
            case "key_layout":
                if configuration.window_manager == "agnostic":
                    pass
                elif configuration.window_manager == "hyprland":
                    main_container.add(
                        KeyboardLayout(
                            name="keyboard_layout_widget",
                            keyboard=name
                            if (
                                name := configuration.get_property(
                                    "switchxkblayout_keyboard_name"
                                )
                            )
                            else ".*",
                            formatter=FormattedString("{language}"),
                            language_formatter=lambda x: x[:2].upper(),
                            vexpand=True,
                        )
                    )
                elif configuration.window_manager == "niri":
                    main_container.add(
                        NiriKeyboardLayout(
                            name="keyboard_layout_widget",
                            language_formatter=lambda x: x[:2].upper(),
                            vexpand=True,
                        )
                    )

            case "recorder":
                main_container.add(ScreenRecorder())

            case "tray":
                main_container.add(Tray(dir="right" if side == "left" else "left"))

            case "battery":
                main_container.add(BatteryWidget())

            case "res_monitor":
                main_container.add(ResourceMonitor())

            case "net_monitor":
                main_container.add(NetworkUsage())

            case "net_monitor_wifi":
                main_container.add(NetworkUsage(type="wifi"))

            case "net_monitor_eth":
                main_container.add(NetworkUsage(type="ethernet"))

            case _:
                logger.warning(f"Unknown widget found in the {side} bar: {widget}")
                continue

        added_widgets.append(widget)


# class BarWindowLeft(Window):
class BarWindowLeft(Box):
    def __init__(self, *args, **kwargs):
        super().__init__(
            name="bar_window_left",
            orientation="h",
            # anchor="left top",
            # layer="top",
            # exclusivity="normal",
            # visible=False,
            *args,
            **kwargs,
        )

        self.main_container = Box(
            name="bar_start_container",
            h_align="start",
            children=[
                # self.workspaces_widget,
                # self.wallpaper_widget,
                # self.keyboard_layout_widget,
                # self.screen_recorder_widget,
            ],
        )

        read_widgets(self.main_container, "left")

        self.add(self.main_container)
        self.add(
            Box(
                name="corner_container",
                orientation="v",
                children=[
                    Box(
                        name="corner_container",
                        children=[
                            Corner(orientation="top-left", name="corner", h_expand=True)
                        ],
                    ),
                    Box(v_expand=True),
                ],
            )
        )


# class BarWindowRight(Window):
class BarWindowRight(Box):
    def __init__(self, *args, **kwargs):
        super().__init__(
            name="bar_window_right",
            orientation="h",
            # anchor="top right",
            # exclusivity="normal",
            # layer="top",
            # visible=False,
            *args,
            **kwargs,
        )

        self.main_container = Box(
            name="bar_end_container",
            h_align="end",
            children=[
                # self.network_usage_widget,
                # self.resource_monitor_widget,
                # self.battery_widget,
                # self.tray_widget,
            ],
        )

        read_widgets(self.main_container, "right")

        self.add(
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
        )
        self.add(self.main_container)
