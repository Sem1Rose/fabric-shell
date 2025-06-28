from loguru import logger
from enum import IntEnum

from config import configuration
from widgets.pill.dashboard import Dashboard
from widgets.pill.app_launcher import AppLauncher
from widgets.pill.powermenu import PowerMenu
from widgets.pill.wallpaper_selector import WallpaperSelector

from fabric.widgets.box import Box
from fabric.widgets.stack import Stack
from fabric.widgets.eventbox import EventBox
from fabric.core.service import Signal, Property

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gdk  # noqa: E402


class PillApplets(IntEnum):
    DASHBOARD = 0
    POWERMENU = 1
    WALLPAPER = 2
    LAUNCHER = 3


class Pill(EventBox):
    @Signal
    def on_peeked(self, applet: int): ...
    @Signal
    def on_unpeeked(self, applet: int): ...
    @Signal
    def on_expanded(self, applet: int): ...

    @Property(int, "rw")
    def num_large_widgets(self) -> int:
        return self._num_large_widgets

    @num_large_widgets.setter
    def num_large_widgets(self, value):
        self._num_large_widgets = value

        if self._num_large_widgets < 0:
            self._num_large_widgets = 0

        if self._num_large_widgets == 0:
            self.main_container.remove_style_class("large_widget")
        else:
            self.main_container.add_style_class("large_widget")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._num_large_widgets = 0

        self.dashboard = Dashboard()
        self.powermenu = PowerMenu()
        self.wallpaper_selector = WallpaperSelector()
        self.app_launcher = AppLauncher()

        self.applets = {
            PillApplets.DASHBOARD: self.dashboard,
            PillApplets.POWERMENU: self.powermenu,
            PillApplets.WALLPAPER: self.wallpaper_selector,
            PillApplets.LAUNCHER: self.app_launcher,
        }
        self.active_applet = PillApplets.DASHBOARD

        self.stack = Stack(
            name="pill_stack",
            transition_type="slide-down",
            transition_duration=configuration.get_property(
                "pill_stack_transition_duration"
            ),
            children=[
                self.dashboard,
                self.powermenu,
                self.wallpaper_selector,
                self.app_launcher,
            ],
            h_expand=True,
        )
        self.main_container = Box(name="pill_box", children=[self.stack])

        if self.dashboard.media_player.can_reveal:
            self.inc_num_large_widgets()

        self.connect("enter-notify-event", self.mouse_enter)
        self.connect("leave-notify-event", self.mouse_leave)
        self.dashboard.media_player.connect(
            "on-show-hide",
            lambda _, v: self.inc_num_large_widgets()
            if v
            else self.dec_num_large_widgets(),
        )

        if self.dashboard.quick_settings_widget.volume_chevron:
            self.dashboard.quick_settings_widget.volume_slider.chevron.connect(
                "on-toggled",
                lambda button, *_: self.inc_num_large_widgets()
                if button.toggled
                else self.dec_num_large_widgets(),
            )

        self.dashboard.date_time_widget.connect(
            "clicked", lambda *_: self.toggle_dashboard_expand(True)
        )
        self.powermenu.connect(
            "on_action", lambda *_: self.select_pill_applet(PillApplets.DASHBOARD)
        )
        self.wallpaper_selector.connect(
            "on_selected", lambda *_: self.select_pill_applet(PillApplets.DASHBOARD)
        )
        self.app_launcher.connect(
            "on_launched", lambda *_: self.select_pill_applet(PillApplets.DASHBOARD)
        )

        self.select_pill_applet(self.active_applet)
        self.add(self.main_container)

    def mouse_enter(self, eventbox, event_crossing):
        # logger.error(
        #     f"enter: ({event_crossing.x}, {event_crossing.y}) ({event_crossing.x_root}, {event_crossing.y_root}) {event_crossing.send_event} {event_crossing.mode} {event_crossing.detail} {event_crossing.focus} {event_crossing.state}"
        # )
        match self.active_applet:
            case PillApplets.DASHBOARD:
                if self.dashboard.can_peek():
                    self.peek()
            case _:
                return

    def mouse_leave(self, eventbox, event_crossing):
        # logger.error(
        #     f"leave: ({event_crossing.x}, {event_crossing.y}) ({event_crossing.x_root}, {event_crossing.y_root}) {event_crossing.send_event} {event_crossing.mode} {event_crossing.detail} {event_crossing.focus} {event_crossing.state}"
        # )
        match self.active_applet:
            case PillApplets.DASHBOARD:
                if (
                    event_crossing.mode == Gdk.CrossingMode.NORMAL
                    and self.dashboard.can_unpeek()
                ):
                    self.unpeek()
            case _:
                return

    def select_pill_applet(self, applet, expand=False):
        if applet not in self.applets.keys():
            logger.error(f"Invalid pill applet: {applet}")
            return False

        logger.debug(f"Changing active pill applet to {applet.name.lower()}: {applet}")

        for id, widget in self.applets.items():
            self.main_container.remove_style_class(id.name.lower())
            widget.hide()

        self.active_applet = applet
        self.applets[applet].unhide(expand)
        self.main_container.add_style_class(applet.name.lower())
        self.stack.set_visible_child(self.applets[applet])

        if expand or applet != PillApplets.DASHBOARD:
            self.expand()
        else:
            self.unpeek()

        return True

    def toggle_dashboard_expand(self, peek):
        if self.active_applet != PillApplets.DASHBOARD:
            self.select_pill_applet(PillApplets.DASHBOARD, True)
            return

        if self.dashboard.can_expand():
            self.expand()
        elif peek:
            self.peek()
        else:
            self.unpeek()

    def expand(self):
        match self.active_applet:
            case PillApplets.DASHBOARD:
                self.dashboard.expand()
                self.main_container.add_style_class("peeking")
                self.current_applet_add_style_class("peeking")
                self.main_container.add_style_class("expanded")
                self.current_applet_add_style_class("expanded")

            # case _:
            #     return

        self.on_expanded(self.active_applet)

    def peek(self):
        match self.active_applet:
            case PillApplets.DASHBOARD:
                self.dashboard.peek()
                self.main_container.add_style_class("peeking")
                self.current_applet_add_style_class("peeking")
                self.main_container.remove_style_class("expanded")
                self.current_applet_remove_style_class("expanded")

            # case _:
            #     return

        self.on_peeked(self.active_applet)

    def unpeek(self):
        match self.active_applet:
            case PillApplets.DASHBOARD:
                self.dashboard.unpeek()
                self.main_container.remove_style_class("expanded")
                self.current_applet_remove_style_class("expanded")
                self.main_container.remove_style_class("peeking")
                self.current_applet_remove_style_class("peeking")

            # case _:
            #     return

        self.on_unpeeked(self.active_applet)

    def current_applet_add_style_class(self, style_class):
        self.applet_add_style_class(self.active_applet, style_class)

    def current_applet_remove_style_class(self, style_class):
        self.applet_remove_style_class(self.active_applet, style_class)

    def applet_add_style_class(self, applet, style_class):
        # if self.active_applet == applet:
        self.applets[applet].add_style_class(style_class)

    def applet_remove_style_class(self, applet, style_class):
        # if self.active_applet == applet:
        self.applets[applet].remove_style_class(style_class)

    def inc_num_large_widgets(self):
        self.num_large_widgets += 1

    def dec_num_large_widgets(self):
        self.num_large_widgets -= 1
