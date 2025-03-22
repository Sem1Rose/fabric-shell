from config import configuration
from loguru import logger

from fabric.core.service import Property
from fabric.utils.helpers import FormattedString
from fabric.widgets.box import Box
from fabric.widgets.circularprogressbar import CircularProgressBar
from fabric.widgets.label import Label
from fabric.widgets.overlay import Overlay


class CircularProgressIcon(Box):
    @Property(bool, "rw", default_value=False)
    def show_label(self) -> bool:
        return self._show_label

    @show_label.setter
    def show_label(self, value: bool):
        if self._show_label and not value:
            self.remove(self.label)
        elif not self._show_label and value:
            self.add(self.label)

        self._show_label = value

    @Property(float, "rw", default_value=0.0)
    def percentage(self) -> float:
        return self._percentage

    @percentage.setter
    def percentage(self, value: float):
        self._percentage = value

        self.label.set_markup(f"{int(self._percentage * 100)}%")
        self.circ_progress.value = self._percentage

    @Property(str, "rw", default_value="")
    def icon_value(self) -> str:
        return self._icon

    @icon_value.setter
    def icon_value(self, value: str):
        self._icon = value
        self.icon.set_markup(self._icon)

    @Property(str, "rw", default_value="")
    def tooltip(self) -> str:
        return self._tooltip_markup

    @tooltip.setter
    def tooltip(self, value: str):
        self._tooltip_markup = value

    def __init__(
        self,
        add_label=False,
        tooltip_markup="{icon}: {percentage}%",
        *args,
        **kwargs,
    ):
        super().__init__(
            name="circular_progress_block",
            *args,
            **kwargs,
        )
        self._icon = ""
        self._percentage = 0.0
        self._show_label = add_label
        self._tooltip_markup = tooltip_markup

        match configuration.get_property("circular_progress_empty_part"):
            case "bottom":
                circ_progress_empty_base_angle = 90
            case "right":
                circ_progress_empty_base_angle = 0
            case "top":
                circ_progress_empty_base_angle = 270
            case "left":
                circ_progress_empty_base_angle = 180
            case _:
                circ_progress_empty_base_angle = 0

        circ_progress_start_angle = circ_progress_empty_base_angle + (
            float(configuration.get_property("circular_progress_empty_angle")) / 2
        )
        circ_progress_end_angle = (
            360
            + circ_progress_empty_base_angle
            - (float(configuration.get_property("circular_progress_empty_angle")) / 2)
        )

        self.icon = Label(name="circular_progress_icon")
        self.label = Label(name="circular_progress_label")
        self.circ_progress = CircularProgressBar(
            name="circular_progress",
            value=0,
            h_expand=True,
            v_expand=True,
            start_angle=circ_progress_start_angle,
            end_angle=circ_progress_end_angle,
            child=self.icon,
        )

        self.children = [
            Box(
                name="circular_progress_container",
                children=[self.circ_progress],
            )
        ]

        if self._show_label:
            self.add(self.label)

    def bulk_set(
        self,
        icon: str | None = None,
        percentage: float | None = None,
        show_label: bool | None = None,
    ):
        if icon is not None:
            self.icon_value = icon
        if percentage is not None:
            self.percentage = percentage
        if show_label is not None:
            self.show_label = show_label

        self.update_tooltip()

    def update_tooltip(self, **kwargs):
        self.set_tooltip_markup(
            FormattedString(self._tooltip_markup).format(
                icon=self._icon, percentage=f"{int(self._percentage * 100)}%", **kwargs
            )
        )
