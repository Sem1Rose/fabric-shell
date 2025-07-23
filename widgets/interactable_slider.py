from math import floor
from venv import logger
from widgets.smooth_scale import SmoothScale

from fabric.core.service import Signal
from fabric.core.fabricator import Fabricator
from fabric.widgets.scale import Scale


class Slider(Scale):
    @Signal
    def on_interacted(self, value: float): ...

    @Signal
    def on_polled(self, value: float): ...

    @Signal
    def interacting_value(self, value: float): ...

    def __init__(
        self,
        poll_command="",
        poll_value_processor=lambda v: v,
        poll_interval=400,
        poll_stream=True,
        poll=False,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.previous_value = 0
        self.interacting = False
        if poll:
            self.build(
                lambda scale, _: Fabricator(
                    poll_from=poll_command,
                    interval=poll_interval,
                    stream=poll_stream,
                    on_changed=lambda _, value: self.change_value(
                        poll_value_processor(value)
                    ),
                )
            )

        self.connect("button-press-event", lambda *_: self.begin_interact())
        self.connect("button-release-event", lambda *_: self.end_interact())

    def on_value_changed(self, _):
        value = floor(self.value * 25)
        if value != self.previous_value:
            self.interacting_value(self.value)
            self.previous_value = value

    def begin_interact(self):
        self.interacting = True
        self.connect("value-changed", self.on_value_changed)

    def end_interact(self):
        self.interacting = False
        self.disconnect_by_func(self.on_value_changed)
        self.on_interacted(self.value)

    def change_value(self, value):
        if self.interacting or value is None:
            return

        self.set_value(value)
        self.on_polled(value)
