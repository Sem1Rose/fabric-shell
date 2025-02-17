from loguru import logger

from config import configuration
from widgets.date_time import DateTimeWidget
from widgets.media_controls import MediaControls
from widgets.quick_settings import QuickSettings

from fabric.widgets.box import Box
from fabric.widgets.revealer import Revealer


class Dashboard(Box):
    def __init__(self, *args, **kwargs):
        super().__init__(
            name="pill_dashboard", orientation="v", h_expand=True, *args, **kwargs
        )

        self.expanded = False
        self.peeking = False

        self.date_time_widget = DateTimeWidget()
        self.quick_settings_widget = QuickSettings()
        self.media_controls_widget = MediaControls()
        # self.calendar_widget = Box(
        #     name="calendar_container",
        #     orientation="h",
        #     children=[
        #         Box(h_expand=True),
        #         Calendar(),
        #         Box(h_expand=True),
        #     ],
        # )

        self.date_time_widget.set_can_focus(False)

        self.quick_settings_revealer = Revealer(
            name="quick_settings_revealer",
            child=self.quick_settings_widget,
            transition_type="slide-down",
            transition_duration=configuration.get_property(
                "media_player_reveal_animation_duration"
            ),
        )
        self.media_controls_revealer = Revealer(
            name="media_controls_revealer",
            child=self.media_controls_widget,
            transition_type="slide-down",
            transition_duration=configuration.get_property(
                "media_player_reveal_animation_duration"
            ),
        )
        # self.calendar_revealer = Revealer(
        #     name="calendar_revealer",
        #     child=self.calendar_widget,
        #     transition_type="slide-down",
        #     transition_duration=configuration.get_property(
        #         "media_player_reveal_animation_duration"
        #     ),
        # )

        self.children = [
            self.date_time_widget,
            self.quick_settings_revealer,
            self.media_controls_revealer,
            # self.calendar_revealer,
        ]

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
        self.media_controls_revealer.reveal()
        # self.calendar_revealer.reveal()

        self.quick_settings_widget.add_style("revealed")
        self.media_controls_widget.add_style("revealed")
        # self.calendar_widget.add_style("revealed")

    def peek(self):
        self.peeking = True
        self.expanded = False

        self.quick_settings_revealer.unreveal()
        self.media_controls_revealer.reveal()
        # self.calendar_revealer.unreveal()

        self.quick_settings_widget.remove_style("revealed")
        self.media_controls_widget.add_style("revealed")
        # self.calendar_widget.remove_style("revealed")

        self.quick_settings_widget.hide_popups()

        logger.debug("Peeking")

    def unpeek(self):
        self.peeking = False
        self.expanded = False

        self.quick_settings_revealer.unreveal()
        self.media_controls_revealer.unreveal()
        # self.calendar_revealer.unreveal()

        self.quick_settings_widget.remove_style("revealed")
        self.media_controls_widget.remove_style("revealed")
        # self.calendar_widget.remove_style("revealed")

        self.quick_settings_widget.hide_popups()

        logger.debug("Shrinking")

    def hide(self, *args):
        self.unpeek()
        self.add_style_class("hidden")

    def unhide(self, expand, *args):
        self.expand if expand else self.unpeek()
        self.remove_style_class("hidden")
