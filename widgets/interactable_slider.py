from widgets.smooth_scale import SmoothScale

from fabric.core.service import Signal
from fabric.core.fabricator import Fabricator
from fabric.widgets.scale import Scale


class Slider(Scale):
    @Signal
    def on_interacted(self, value: float): ...

    @Signal
    def on_polled(self, value: float): ...

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

    def begin_interact(self):
        self.interacting = True

    def end_interact(self):
        self.interacting = False
        self.on_interacted(self.value)

    def change_value(self, value):
        if not self.interacting and value is not None:
            # self.animate_value(value)
            self.set_value(value)

        self.on_polled(value)
