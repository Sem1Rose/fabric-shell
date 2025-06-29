from loguru import logger

from config import configuration
from widgets.pill.applet import Applet
from widgets.date_time import DateTimeWidget
from widgets.media_player import MediaPlayer
from widgets.quick_settings import QuickSettings

from fabric.widgets.box import Box
from fabric.widgets.revealer import Revealer


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

        self.date_time_widget = DateTimeWidget()
        self.date_time_widget.set_can_focus(False)

        # self.qs_populated = configuration.get_property("dashboard_qs").__len__() > 0
        self.qs_populated = True
        if self.qs_populated:
            self.quick_settings_widget = QuickSettings()
        else:
            self.quick_settings_widget = Box()

        self.media_player = MediaPlayer(
            transition_duration=configuration.get_property(
                "pill_revealer_animation_duration"
            )
        )
        # self.calendar_widget = Box(
        #     name="calendar_container",
        #     orientation="h",
        #     children=[
        #         Box(h_expand=True),
        #         Calendar(),
        #         Box(h_expand=True),
        #     ],
        # )

        self.quick_settings_revealer = Revealer(
            name="quick_settings_revealer",
            child=self.quick_settings_widget,
            transition_type="slide-down",
            transition_duration=configuration.get_property(
                "pill_revealer_animation_duration"
            ),
        )
        # self.media_player_revealer = Revealer(
        #     name="media_player_revealer",
        #     child=self.media_player_widget,
        #     transition_type="slide-down",
        #     transition_duration=configuration.get_property(
        #         "pill_revealer_animation_duration"
        #     ),
        # )
        # self.calendar_revealer = Revealer(
        #     name="calendar_revealer",
        #     child=self.calendar_widget,
        #     transition_type="slide-down",
        #     transition_duration=configuration.get_property(
        #         "pill_revealer_animation_duration"
        #     ),
        # )

        self.children = [
            self.date_time_widget,
            self.quick_settings_revealer,
            self.media_player,
            # self.media_player_revealer,
            # self.calendar_revealer,
        ]

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

        self.quick_settings_revealer.reveal()
        if self.media_player.can_reveal:
            self.media_player.reveal()
            self.add_style_class("media_player")
        else:
            self.remove_style_class("media_player")
        # self.calendar_revealer.reveal()

        self.quick_settings_widget.add_style("revealed")
        self.media_player.add_style("revealed")
        # self.calendar_widget.add_style("revealed")

    def peek(self):
        self.peeking = True
        self.expanded = False

        self.quick_settings_revealer.unreveal()
        if self.media_player.can_reveal:
            self.media_player.reveal()
            self.add_style_class("media_player")
        else:
            self.remove_style_class("media_player")
        # self.calendar_revealer.unreveal()

        self.quick_settings_widget.remove_style("revealed")
        self.media_player.add_style("revealed")
        # self.calendar_widget.remove_style("revealed")

        self.quick_settings_widget.hide_popups()

        logger.debug("Peeking")

    def unpeek(self):
        self.peeking = False
        self.expanded = False

        self.quick_settings_revealer.unreveal()
        self.media_player.unreveal()
        # self.calendar_revealer.unreveal()

        self.quick_settings_widget.remove_style("revealed")
        self.media_player.remove_style("revealed")
        # self.calendar_widget.remove_style("revealed")

        self.quick_settings_widget.hide_popups()

        logger.debug("Shrinking")

    def hide(self, *args):
        Applet.hide(self, *args)

        self.unpeek()

    def unhide(self, expand, *args):
        Applet.unhide(self, *args)

        self.expand if expand else self.unpeek()
