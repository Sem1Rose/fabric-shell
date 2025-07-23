from loguru import logger
from config import configuration

from typing import Literal
from widgets.buttons import ToggleButton
from widgets.interactable_slider import Slider

from fabric.audio import Audio
from fabric.widgets.box import Box


class MicrophoneSlider(Box):
    def __init__(
        self,
        inverted: bool = False,
        orientation: Literal["horizontal", "vertical"] = "horizontal",
        *args,
        **kwargs,
    ):
        super().__init__(
            name="thick_slider_container",
            orientation=orientation,
            h_expand=True,
            v_expand=True,
            *args,
            **kwargs,
        )

        self.add_style_class("thick_slider_toggle_container")
        self.add_style_class("vertical" if orientation == "vertical" else "horizontal")

        self.controller = Audio()

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

        self.toggle = ToggleButton(style_classes="thick_toggle", auto_toggle=False)

        self.slider.connect(
            "on-interacted",
            lambda _, v: self.change_mic_volume(v),
        )
        self.slider.connect(
            "interacting-value",
            lambda _, v: self.change_mic_volume(v),
        )
        self.connect_slider()
        self.controller.connect(
            "microphone-changed",
            lambda *_: self.connect_slider(),
        )

        self.toggle.connect(
            "on_toggled",
            lambda toggle, *_: self.toggle_mute_stream(toggle.toggled),
        )
        self.connect_toggle()
        self.controller.connect(
            "microphone-changed",
            lambda *_: self.connect_toggle(),
        )

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

    def update_slider(self, *_):
        self.slider.change_value(float(self.controller.microphone.volume) / 100.0)

    def change_mic_volume(self, v):
        self.controller.microphone.volume = int(v * 100)

    def connect_slider(
        self,
    ):
        if self.controller.microphone:
            self.update_slider()
            self.controller.microphone.connect(
                "notify::volume",
                self.update_slider,
            )

            self.slider.set_sensitive(True)
        else:
            self.slider.change_value(0)
            self.slider.set_sensitive(False)

    def update_toggle(self, *_):
        muted = self.controller.microphone.muted
        self.toggle.set_state(not muted)

        self.toggle.set_markup(
            configuration.get_property("microphone_muted_icon")
            if muted
            else (
                configuration.get_property("microphone_on_icon")
                if self.controller.microphone.volume > 0.0
                else configuration.get_property("microphone_off_icon")
            )
        )

    def connect_toggle(self):
        if self.controller.microphone:
            self.update_toggle()
            self.controller.microphone.connect("notify::muted", self.update_toggle)
            self.controller.microphone.connect("notify::volume", self.update_toggle)

            self.toggle.set_sensitive(True)
        else:
            self.toggle.set_sensitive(False)
            self.toggle.set_state(False)
            self.toggle.set_markup(configuration.get_property("microphone_muted_icon"))

    def toggle_mute_stream(self, mute):
        self.controller.microphone.muted = mute
