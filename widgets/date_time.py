import time

from fabric.core.fabricator import Fabricator
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label

from config import configuration

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402


class DateTimeWidget(Button):
    def __init__(self, **kwargs):
        super().__init__(name="date_time_widget", **kwargs)

        self.day_label = DateTime(formatter=r"%b %e", name="day", v_expand=True)
        self.time_label = DateTime(formatter=r"%R", name="time", v_expand=True)
        self.date_label = DateTime(formatter=r"%a", name="date", v_expand=True)

        self.add(
            Box(
                orientation="h",
                h_expand=True,
                children=[
                    self.date_label,
                    Box(h_expand=True),
                    self.time_label,
                    Box(h_expand=True),
                    self.day_label,
                ],
            )
        )


class Calendar(Gtk.Calendar):
    def __init__(self, **kwargs):
        super().__init__(name="calendar_widget", **kwargs)

        # self.set_property("show-heading", False)
        # self.set_property("show-day-names", False)
        # self.set_property("show-details", False)
        # self.set_property("show-week-numbers", False)


class DateTime(Label):
    def __init__(
        self,
        formatter: str = "%I:%M %p",
        interval: int = 1000,
        **kwargs,
    ):
        super().__init__(
            **kwargs,
        )

        self.build(
            lambda label, _: Fabricator(
                poll_from=lambda *_: self.format_time(formatter),
                interval=interval,
                on_changed=lambda _, v: label.set_label(v),
            )
        )

        self.set_sensitive(False)

    def format_time(self, formatter) -> str:
        return time.strftime(formatter)
