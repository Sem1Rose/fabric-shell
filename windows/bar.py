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
from fabric.widgets.label import Label
from fabric.widgets.box import Box
from fabric.widgets.eventbox import EventBox
from fabric.widgets.revealer import Revealer
from fabric.hyprland.widgets import Workspaces, get_hyprland_connection
from fabric.utils.helpers import FormattedString, idle_add

# from fabric.widgets.shapes.corner import Corner

from loguru import logger
from gi.repository import GLib, Gio


class BarWindow(Window):
    def __init__(self, *args, **kwargs):
        super().__init__(
            anchor="left top right",
            exclusivity="auto",
            layer="top",
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

        self.set_size_request(
            0, int(configuration.get_property("bar_height", "css_settings")[:-2])
        )

        self.main_container = Box(
            h_expand=True, v_expand=True, h_align="fill", v_align="fill"
        )
        # self.main_container.set_sensitive(False)

        self.left_container = BarWindowLeft()
        self.right_container = BarWindowRight()

        self.main_container.pack_start(self.left_container, False, False, 0)
        # self.main_container.set_center_widget(self.center_container)
        self.main_container.pack_end(self.right_container, False, False, 0)

        self.add(self.main_container)
        self.show_all()
        # self.set_default_size(10, 50)
        # self.set_resizable(False)
        # logger.error(self.get_default_size())


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

        # self.widgets = Box(
        #     name="bar_start_container",
        #     h_align="start",
        #     children=[
        #         self.workspaces_widget,
        #         self.keyboard_layout_widget,
        #         self.wallpaper_widget,
        #         self.screen_recorder_widget,
        #     ],
        # )

        # self.main_container = Box(
        #     name="bar_window_left",
        #     orientation="h",
        #     children=[
        #         self.widgets,
        #         Box(
        #             name="corner_container",
        #             orientation="v",
        #             children=[
        #                 Box(
        #                     name="corner_container",
        #                     children=[
        #                         Corner(
        #                             orientation="top-left", name="corner", h_expand=True
        #                         )
        #                     ],
        #                 ),
        #                 Box(v_expand=True),
        #             ],
        #         ),
        #     ],
        #     *args,
        #     **kwargs,
        # )
        # self.add(self.main_container)
        # self.show_all()

        self.add(
            Box(
                name="bar_start_container",
                h_align="start",
                children=[
                    self.workspaces_widget,
                    self.keyboard_layout_widget,
                    self.wallpaper_widget,
                    self.screen_recorder_widget,
                ],
            )
        )
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
                "bar_revealer_animation_duration"
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

            # if self.tray_unreveal_handler is not None:
            # if cancellable := self.tray_unreveal_handler.get_cancellable():
            # self.tray_unreveal_handler.get_cancellable().cancel()
            # self.tray_unreveal_handler = None

        # self.tray_expander = EventBox(
        #     child=Box(
        #         name="tray_container_expander",
        #         children=Label(
        #             markup=configuration.get_property("chevron_left"),
        #         ),
        #     )
        # )
        self.tray_expander = MarkupButton(
            name="tray_container_expander",
            markup=configuration.get_property("chevron_left"),
        )
        self.tray_expander.connect(
            "clicked",
            lambda *_: on_tray_expander_clicked(),
        )

        self.tray_container = EventBox(
            child=Box(
                name="tray_container",
                style_classes="bar_widget",
                children=[
                    self.tray_revealer,
                    self.tray_expander,
                ],
            )
        )

        # self.widgets = Box(
        #     name="bar_end_container",
        #     h_align="end",
        #     children=[
        #         self.network_usage_widget,
        #         self.resource_monitor_widget,
        #         self.battery_widget,
        #         self.tray_container,
        #     ],
        # )

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
        self.add(
            Box(
                name="bar_end_container",
                h_align="end",
                children=[
                    self.network_usage_widget,
                    self.resource_monitor_widget,
                    self.battery_widget,
                    self.tray_container,
                ],
            )
        )

        self.tray_hovered = False
        self.tray_unreveal_handler = None
        self.cancellable = Gio.Cancellable.new()

        def change_tray_hovered(hovered):
            self.tray_hovered = hovered

            # if not hovered and self.tray_revealer.child_revealed:
            #     start_unreveal_thread()

        def start_unreveal_thread():
            # if not self.tray_revealer.child_revealed:
            #     return
            if self.tray_unreveal_handler is not None:
                # self.tray_unreveal_handler.get_cancellable().cancel()
                # if cancellable := self.tray_unreveal_handler.get_cancellable():
                #     logger.error("cancelled")
                #     cancellable.cancel()
                self.cancellable.cancel()
                self.cancellable = Gio.Cancellable.new()
                self.tray_unreveal_handler = None

            def unreveal(*_):
                logger.warning("waiting")
                self.cancellable.set_error_if_cancelled()
                GLib.usleep(int(3 * 1e6))
                logger.warning("closing")

                if not self.tray_hovered and self.tray_revealer.child_revealed:
                    logger.warning("closed")
                    idle_add(on_tray_expander_clicked)

            # self.tray_unreveal_handler = Gio.Task.new()
            self.tray_unreveal_handler = Gio.Task.new()
            self.tray_unreveal_handler.set_return_on_cancel(True)
            self.tray_unreveal_handler.run_in_thread(unreveal)
            # self.tray_unreveal_handler = GLib.Thread.new("tray_unreveal", unreveal)

        self.tray_expander.connect(
            "enter-notify-event", lambda *_: change_tray_hovered(True)
        )
        self.tray_expander.connect(
            "leave-notify-event", lambda *_: change_tray_hovered(False)
        )
        # self.main_container = Box(
        #     name="bar_window_right",
        #     orientation="h",
        #     children=[
        #         Box(
        #             name="corner_container",
        #             orientation="v",
        #             children=[
        #                 Box(
        #                     name="corner_container",
        #                     children=[
        #                         Corner(
        #                             orientation="top-right",
        #                             name="corner",
        #                             h_expand=True,
        #                         )
        #                     ],
        #                 ),
        #                 Box(v_expand=True),
        #             ],
        #         ),
        #         self.widgets,
        #     ],
        #     *args,
        #     **kwargs,
        # )
        # self.add(self.main_container)
        # self.show_all()
