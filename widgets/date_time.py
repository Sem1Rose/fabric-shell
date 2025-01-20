from config import configuration

from fabric.widgets.centerbox import CenterBox
from fabric.widgets.datetime import DateTime


class DateTimeWidget(CenterBox):
    def __init__(self, **kwargs):
        super().__init__(
            orientation="h",
            name="date_time",
            style_classes="widget",
            h_expand=True,
            **kwargs,
        )

        self.date_label = DateTime(formatters=r"%a", name="date")
        self.time_label = DateTime(formatters=r"%R", name="time")
        self.day_label = DateTime(formatters=r"%b %e", name="day")

        self.start_children = self.date_label
        self.center_children = self.time_label
        self.end_children = self.day_label
