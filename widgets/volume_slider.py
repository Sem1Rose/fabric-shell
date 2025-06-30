from loguru import logger
from config import configuration

from typing import Literal
from widgets.buttons import ToggleButton, ChevronButton, MarkupButton, QSTileButton
from widgets.interactable_slider import Slider

from fabric.audio import Audio
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.overlay import Overlay
from fabric.widgets.stack import Stack
from fabric.widgets.revealer import Revealer


class VolumeSlider(Box):
    def __init__(
        self,
        add_device_selection_popup: bool = False,
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

        self.device_selection_added = (
            add_device_selection_popup and orientation == "horizontal"
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

        if self.device_selection_added:
            self.chevron = ChevronButton(
                name="qs_volume_chevron",
                orientation="v",
                h_align="start" if inverted else "end",
                v_align="end",
            )
            self.toggle_overlay = Overlay(child=self.toggle, overlays=self.chevron)

            self.speakers_holder = Box(name="qs_speakers_container", orientation="v")
            self.speakers_container = Box(
                h_expand=True,
                orientation="v",
                children=[
                    Box(
                        children=[
                            Label(
                                configuration.get_property("speakers_header_text"),
                                name="header_label",
                            ),
                            Box(h_expand=True),
                        ]
                    ),
                    self.speakers_holder,
                ],
            )
            self.microphones_holder = Box(
                name="qs_microphones_container", orientation="v"
            )
            self.microphones_container = Box(
                h_expand=True,
                orientation="v",
                children=[
                    Box(
                        children=[
                            Label(
                                configuration.get_property("microphones_header_text"),
                                name="header_label",
                            ),
                            Box(h_expand=True),
                        ]
                    ),
                    self.microphones_holder,
                ],
            )
            self.speakers_microphones_stack = Stack(
                transition_type="slide-left-right",
                transition_duration=200,
                children=[self.speakers_container, self.microphones_container],
            )

            self.speaker_tab_button = MarkupButton(
                style_classes=["tab_button", "active"],
                markup=configuration.get_property("speakers_tab_icon"),
            )
            self.microphone_tab_button = MarkupButton(
                style_classes="tab_button",
                markup=configuration.get_property("microphones_tab_icon"),
            )
            self.tabs = Box(
                children=[
                    Box(h_expand=True),
                    self.speaker_tab_button,
                    self.microphone_tab_button,
                    Box(h_expand=True),
                ]
            )
            self.speakers_microphones_revealer = Revealer(
                child=Box(
                    name="qs_speakers_microphones_container",
                    orientation="v",
                    children=[self.tabs, self.speakers_microphones_stack],
                ),
                transition_type="slide-down",
                transition_duration=configuration.get_property(
                    "pill_revealer_animation_duration"
                ),
            )

            self.chevron.connect(
                "on-toggled",
                lambda button, *_: self.populate_containers()
                if button.toggled
                else self.unreveal_sp_mic_containers(),
            )
            self.speaker_tab_button.connect(
                "clicked",
                lambda *_: (
                    self.speakers_microphones_stack.set_visible_child(
                        self.speakers_container
                    ),
                    self.speaker_tab_button.add_style_class("active"),
                    self.microphone_tab_button.remove_style_class("active"),
                ),
            )
            self.microphone_tab_button.connect(
                "clicked",
                lambda *_: (
                    self.speakers_microphones_stack.set_visible_child(
                        self.microphones_container
                    ),
                    self.microphone_tab_button.add_style_class("active"),
                    self.speaker_tab_button.remove_style_class("active"),
                ),
            )

        self.slider.connect(
            "on_interacted",
            lambda _, v: self.change_volume(v),
        )
        self.connect_slider()
        self.controller.connect(
            "speaker-changed",
            lambda *_: self.connect_slider(),
        )

        self.toggle.connect(
            "on_toggled",
            lambda toggle, *_: self.toggle_mute_stream(toggle.toggled),
        )
        self.connect_toggle()
        self.controller.connect(
            "speaker-changed",
            lambda *_: self.connect_toggle(),
        )

        self.children = (
            [
                self.toggle_overlay if self.device_selection_added else self.toggle,
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
                self.toggle_overlay if self.device_selection_added else self.toggle,
            ]
        )

    def update_slider(self, *_):
        self.slider.change_value(float(self.controller.speaker.volume) / 100.0)

    def change_volume(self, v):
        self.controller.speaker.volume = int(v * 100)

    def connect_slider(
        self,
    ):
        if self.controller.speaker:
            self.update_slider()
            self.controller.speaker.connect(
                "notify::volume",
                self.update_slider,
            )

            self.slider.set_sensitive(True)
            if self.device_selection_added:
                self.chevron.set_sensitive(True)
        else:
            self.slider.change_value(0)
            self.slider.set_sensitive(False)
            if self.device_selection_added:
                self.chevron.set_sensitive(False)
                self.chevron.set_state(False)
                self.unreveal_sp_mic_containers()

    def update_toggle(self, *_):
        muted = self.controller.speaker.muted
        self.toggle.set_state(not muted)

        self.toggle.set_markup(
            configuration.get_property("volume_muted_icon")
            if muted
            else (
                configuration.get_property("volume_high_icon")
                if self.controller.speaker.volume
                > configuration.get_property("qs_volume_high_threshold")
                else configuration.get_property("volume_low_icon")
                if self.controller.speaker.volume > 0.0
                else configuration.get_property("volume_off_icon")
            )
        )

    def connect_toggle(self):
        if self.controller.speaker:
            self.update_toggle()
            self.controller.speaker.connect("notify::muted", self.update_toggle)
            self.controller.speaker.connect("notify::volume", self.update_toggle)

            self.toggle.set_sensitive(True)
        else:
            self.toggle.set_sensitive(False)
            self.toggle.set_state(False)
            self.toggle.set_markup(configuration.get_property("volume_muted_icon"))

    def toggle_mute_stream(self, mute):
        self.controller.speaker.muted = mute

    def set_default_sink(self, speaker):
        if speaker._stream:
            self.controller._control.set_default_sink(speaker._stream)

            self.populate_containers(default_sink=speaker)
            return True

        return False

    def set_default_source(self, microphone):
        if microphone._stream:
            self.controller._control.set_default_source(microphone._stream)

            self.populate_containers(default_source=microphone)
            return True

        return False

    def populate_containers(self, default_sink=None, default_source=None, *_):
        for child in self.speakers_holder.children:
            self.speakers_holder.remove(child)
        for child in self.microphones_holder.children:
            self.microphones_holder.remove(child)

        self.speakers_microphones_revealer.reveal()

        def speaker_factory(speaker):
            if not speaker.icon_name:
                icon = configuration.get_property("speakers_unknown_icon")
            elif "audio-card" in speaker.icon_name:
                icon = configuration.get_property("speakers_built_in_icon")
            elif "headset" in speaker.icon_name:
                icon = configuration.get_property("speakers_headphones_icon")
            else:
                icon = configuration.get_property("speakers_unknown_icon")

            button = QSTileButton(
                name="speaker_button",
                centered=False,
                icon=icon,
                markup=speaker.description,
            )
            button.connect(
                "clicked",
                lambda *_: self.set_default_sink(speaker),
            )

            if default_sink:
                if speaker == default_sink:
                    button.add_style_class("active")
            elif speaker == self.controller.speaker:
                button.add_style_class("active")

            return button

        def microphone_factory(microphone):
            icon = configuration.get_property("microphones_icon")

            button = QSTileButton(
                name="microphone_button",
                centered=False,
                icon=icon,
                markup=microphone.description,
            )
            button.connect(
                "clicked",
                lambda *_: self.set_default_source(microphone),
            )

            if default_source:
                if microphone == default_source:
                    button.add_style_class("active")
            elif microphone == self.controller.microphone:
                button.add_style_class("active")

            return button

        for speaker in [
            speaker_factory(speaker) for speaker in self.controller.speakers
        ]:
            self.speakers_holder.add(speaker)

        for microphone in [
            microphone_factory(microphone) for microphone in self.controller.microphones
        ]:
            self.microphones_holder.add(microphone)

    def unreveal_sp_mic_containers(self):
        try:
            self.controller.disconnect_by_func(self.populate_containers)
        except Exception:
            pass
        self.speakers_microphones_revealer.unreveal()
        self.speakers_microphones_stack.set_visible_child(self.speakers_container)
        self.speaker_tab_button.add_style_class("active")
        self.microphone_tab_button.remove_style_class("active")
