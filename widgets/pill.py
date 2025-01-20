from config import configuration

from widgets.date_time import DateTimeWidget
from widgets.media_controls import MediaControls

from fabric.widgets.box import Box


class Pill(Box):
    def __init__(self, **kwargs):
        super().__init__(orientation="v", name="pill", **kwargs)

        self.date_time_widget = DateTimeWidget()
        self.media_controls_widget = MediaControls()

        self.children = [self.date_time_widget, self.media_controls_widget]
