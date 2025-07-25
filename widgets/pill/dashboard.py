from enum import IntEnum
from loguru import logger
from config import configuration

from widgets.pill.applet import Applet
from widgets.pill.date_time import DateTimeWidget
from widgets.pill.music_ticker import MusicTicker
from widgets.media_player import MediaPlayer
from widgets.quick_settings import QuickSettings
from widgets.calendar import Calendar

from fabric.widgets.revealer import Revealer
from fabric.widgets.stack import Stack
from fabric.widgets.box import Box


class QuickGlanceWidgets(IntEnum):
    DATETIME = 0
    MUSICTICKER = 1


class Dashboard(Applet, Box):
    def __init__(self, *args, **kwargs):
        Box.__init__(
            self,
            name="pill_dashboard",
            style_classes="pill_applet",
            orientation="v",
            h_expand=True,
            *args,
            **kwargs,
        )

        self.expanded = False
        self.peeking = False
        self.widgets = {}
        self.revealers = []

        self.date_time_widget = DateTimeWidget()
        self.date_time_widget.set_can_focus(False)

        self.music_ticker_widget = MusicTicker()
        self.music_ticker_widget.set_can_focus(False)

        self.music_ticker_widget.connect(
            "music-tick",
            lambda *_: not self.peeking
            and not self.expanded
            and self.change_quick_glance_widget(QuickGlanceWidgets.MUSICTICKER),
        )
        self.music_ticker_widget.connect(
            "do-hide",
            lambda *_: self.change_quick_glance_widget(QuickGlanceWidgets.DATETIME),
        )

        self.quick_glance_widget_stack = Stack(
            transition_type="slide-down",
            transition_duration=150,
            h_expand=True,
            children=[
                self.date_time_widget,
                self.music_ticker_widget,
            ],
        )

        self.quick_glance_widgets = {
            QuickGlanceWidgets.DATETIME: self.date_time_widget,
            QuickGlanceWidgets.MUSICTICKER: self.music_ticker_widget,
        }
        self.active_quick_glance_widget = QuickGlanceWidgets.DATETIME

        self.change_quick_glance_widget(self.active_quick_glance_widget)

        self.quick_glance_widget = Box(
            name="pill_quick_glance",
            h_expand=True,
            children=self.quick_glance_widget_stack,
        )

        self.quick_settings_widget = QuickSettings()
        self.quick_settings_revealer = Revealer(
            name="quick_settings_revealer",
            child=self.quick_settings_widget,
            transition_type="slide-down",
            transition_duration=configuration.get_property(
                "pill_revealer_animation_duration"
            ),
        )
        self.widgets["qs"] = self.quick_settings_widget
        self.revealers.append(self.quick_settings_revealer)

        self.add(self.quick_glance_widget)
        self.add(self.quick_settings_revealer)

        self.media_player = None
        self.calendar_widget = None
        if configuration.get_property("dashboard_widgets"):
            w = []
            for widget in configuration.get_property("dashboard_widgets"):
                if widget in w:
                    logger.warning(f"Duplicate widget found in the dashboard: {widget}")
                    continue

                match widget:
                    case "media-player":
                        self.media_player = MediaPlayer()

                        self.media_player.connect(
                            "on_show_hide",
                            lambda _, can_reveal: (
                                self.media_player.reveal(),
                                self.add_style_class("media_player"),
                            )
                            if can_reveal and (self.peeking or self.expanded)
                            else (
                                self.media_player.unreveal(),
                                self.remove_style_class("media_player"),
                            ),
                        )

                        self.widgets[widget] = self.media_player
                        self.add(self.media_player)
                    case "calendar":
                        self.calendar_widget = Calendar(orientation="h")
                        self.calendar_revealer = Revealer(
                            name="calendar_revealer",
                            child=self.calendar_widget,
                            transition_type="slide-down",
                            transition_duration=configuration.get_property(
                                "pill_revealer_animation_duration"
                            ),
                        )

                        self.widgets[widget] = self.calendar_widget
                        self.revealers.append(self.calendar_revealer)
                        self.add(self.calendar_revealer)
                    case _:
                        logger.warning(f"Unknown widget found in the dashboard: {widget}")
                        continue

                w.append(widget)

    def can_peek(self):
        return not self.expanded and not self.peeking

    def can_unpeek(self):
        return self.peeking

    def can_expand(self):
        return not self.expanded

    def expand(self):
        logger.debug("Expanding")
        self.peeking = False
        self.expanded = True

        for revealer in self.revealers:
            revealer.child_revealed = True
        # self.quick_settings_revealer.reveal()
        # self.calendar_revealer.reveal()

        for widget in self.widgets.values():
            widget.add_style("revealed")
        # self.quick_settings_widget.add_style("revealed")
        # self.media_player.add_style("revealed")
        # self.calendar_widget.add_style("revealed")

        if self.media_player:
            if self.media_player.try_reveal():
                self.add_style_class("media_player")
            else:
                self.remove_style_class("media_player")

        self.change_quick_glance_widget(QuickGlanceWidgets.DATETIME)

    def peek(self):
        self.peeking = True
        self.expanded = False

        for revealer in self.revealers:
            revealer.child_revealed = False
        # self.calendar_revealer.unreveal()
        # self.quick_settings_revealer.unreveal()

        self.remove_style_class("media_player")
        for widget in self.widgets.values():
            widget.remove_style("revealed")
        # self.quick_settings_widget.remove_style("revealed")
        # self.calendar_widget.remove_style("revealed")
        # self.media_player.remove_style("revealed")

        if self.media_player:
            if self.media_player.try_reveal():
                self.add_style_class("media_player")
            else:
                self.remove_style_class("media_player")
        # else:
        #     self.calendar_revealer.reveal()
        #     self.calendar_widget.add_style("revealed")

        self.quick_settings_widget.hide_popups()

        logger.debug("Peeking")
        self.change_quick_glance_widget(QuickGlanceWidgets.DATETIME)

    def unpeek(self):
        self.peeking = False
        self.expanded = False

        for revealer in self.revealers:
            revealer.child_revealed = False

        if self.media_player:
            self.media_player.unreveal()

        # self.quick_settings_revealer.unreveal()
        # self.media_player.unreveal()
        # self.calendar_revealer.unreveal()

        self.remove_style_class("media_player")
        for widget in self.widgets.values():
            widget.remove_style("revealed")
        # self.quick_settings_widget.remove_style("revealed")
        # self.media_player.remove_style("revealed")
        # self.calendar_widget.remove_style("revealed")

        self.quick_settings_widget.hide_popups()

        logger.debug("Shrinking")
        self.change_quick_glance_widget(QuickGlanceWidgets.DATETIME)

    def change_quick_glance_widget(self, widget):
        if widget == "date-time" or widget == QuickGlanceWidgets.DATETIME:
            widget = QuickGlanceWidgets.DATETIME
        elif widget == "music-ticker" or widget == QuickGlanceWidgets.MUSICTICKER:
            widget = QuickGlanceWidgets.MUSICTICKER
        else:
            logger.error(f"Unknown quick glance widget {widget}")
            return

        self.quick_glance_widget_stack.set_visible_child(
            self.quick_glance_widgets[widget]
        )
        self.active_quick_glance_widget = widget

    def hide(self, *args):
        Applet.hide(self, *args)

        self.unpeek()

    def unhide(self, expand, *args):
        Applet.unhide(self, *args)
        self.change_quick_glance_widget(QuickGlanceWidgets.DATETIME)

        self.expand() if expand else self.unpeek()
