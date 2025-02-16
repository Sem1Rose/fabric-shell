from fabric.widgets.scale import Scale
from widgets.animator import Animator


class SmoothScale(Scale):
    def __init__(
        self, animation_duration, animation_curve=(0.0, 0.0, 1.0, 1.0), **kwargs
    ):
        super().__init__(**kwargs)
        self.animator = (
            Animator(
                # edit the following parameters to customize the animation
                bezier_curve=animation_curve,
                duration=animation_duration,
                min_value=self.min_value,
                max_value=self.value,
                tick_widget=self,
                notify_value=lambda p, *_: self.set_value(p.value),
            )
            .build()
            .play()
            .unwrap()
        )

    def animate_value(self, value: float):
        self.animator.pause()
        self.animator.min_value = self.value
        self.animator.max_value = value
        self.animator.play()
        return
