from loguru import logger
from config import configuration

from typing import Literal
from widgets.buttons import (
    ToggleButton,
)
from widgets.interactable_slider import Slider
from widgets.helpers.brightness import get_brightness_service

from fabric.widgets.box import Box
from fabric.core.fabricator import Fabricator
from fabric.utils.helpers import (
    exec_shell_command_async,
)


class BrightnessSlider(Box):
    def __init__(
        self,
        add_auto_brightness_toggle: bool,
        inverted: bool = False,
        orientation: Literal["horizontal", "vertical"] = "horizontal",
        *args,
        **kwargs,
    ):
        super().__init__(
            orientation=orientation,
            h_expand=True,
            v_expand=True,
            *args,
            **kwargs,
        )

        self.add_style_class("thick_slider_toggle_container")
        self.add_style_class("vertical" if orientation == "vertical" else "horizontal")

        self.toggle_added = add_auto_brightness_toggle
        self.service = get_brightness_service()

        self.slider = Slider(
            style_classes=[
                "thick_slider",
                "vertical" if orientation == "vertical" else "horizontal",
            ],
            orientation=orientation,
            inverted=(orientation == "vertical" and inverted)
            or (orientation == "horizontal" and inverted),
            h_expand=True,
            v_expand=True,
        )

        if add_auto_brightness_toggle:
            self.toggle = ToggleButton(style_classes="thick_toggle").build(
                lambda toggle, _: Fabricator(
                    poll_from=configuration.get_property(
                        "auto_brightness_check_command"
                    ),
                    interval=1000,
                    on_changed=lambda _, value: toggle.set_state(value == "active"),
                )
                if self.service.active
                else ()
            )
        else:
            self.toggle = ToggleButton(style_classes="thick_toggle")

        if self.service.active:
            self.update(self.service.screen_brightness)

            self.service.connect("brightness_changed", lambda _, v: self.update(v))

            self.slider.connect(
                "on_interacted",
                lambda _, v: self.service.set_brightness(v),
            )

            self.toggle.connect(
                "on_toggled",
                lambda toggle, *_: exec_shell_command_async(
                    configuration.get_property("auto_brightness_start_command")
                    if toggle.toggled
                    else configuration.get_property("auto_brightness_stop_command")
                ),
            )

            self.active = True
        else:
            self.toggle.set_sensitive(False)
            self.toggle.set_state(True)
            self.toggle.set_markup(configuration.get_property("brightness_off_icon"))

            self.slider.set_sensitive(False)

            self.active = False

        toggle_box = Box(
            orientation="v" if orientation == "horizontal" else "h",
            children=[
                Box(v_expand=True)
                if orientation == "horizontal"
                else Box(h_expand=True),
                self.toggle,
                Box(v_expand=True)
                if orientation == "horizontal"
                else Box(h_expand=True),
            ],
        )
        self.children = (
            [
                toggle_box,
                Box(vexpand=True, style_classes="thick_slider_toggle_spacing")
                if orientation == "horizontal"
                else Box(hexpand=True, style_classes="thick_slider_toggle_spacing"),
                self.slider,
            ]
            if not inverted
            else [
                self.slider,
                Box(vexpand=True, style_classes="thick_slider_toggle_spacing")
                if orientation == "horizontal"
                else Box(hexpand=True, style_classes="thick_slider_toggle_spacing"),
                toggle_box,
            ]
        )

    def update(self, value):
        self.slider.set_value(value)

        self.toggle.set_markup(
            configuration.get_property("auto_brightness_icon")
            if self.toggle.toggled and self.toggle_added
            else configuration.get_property("brightness_high_icon")
            if self.slider.value
            > configuration.get_property("qs_brightness_high_threshold")
            else configuration.get_property("brightness_low_icon")
        )

    def inc_brightness(self, value: float):
        if not self.service.active:
            return

        self.service.screen_brightness += value

    def decc_brightness(self, value: float):
        if not self.service.active:
            return

        self.service.screen_brightness -= value
