from config import configuration
from loguru import logger

from widgets.buttons import (
    MarkupButton,
    ToggleButton,
    QSToggleButton,
    QSTileButton,
    ChevronButton,
)
from widgets.interactable_slider import Slider
from widgets.helpers.formatted_exec import formatted_exec_shell_command_async

from fabric.widgets.box import Box
from fabric.widgets.stack import Stack
from fabric.widgets.overlay import Overlay
from fabric.widgets.revealer import Revealer
from fabric.widgets.label import Label
from widgets.popup_window import PopupWindow

from fabric.audio import Audio
from fabric.core.fabricator import Fabricator
from fabric.utils.helpers import (
    exec_shell_command,
    exec_shell_command_async,
    FormattedString,
)
from fabric.bluetooth import BluetoothClient

import gi

gi.require_version("Gtk", "3.0")
# gi.require_version("NM", "1.0")
from gi.repository import Gtk  # , NM  # noqa: E402


class QuickSettings(Box):
    def __init__(self, *args, **kwargs):
        super().__init__(
            name="quick_settings_container",
            orientation="v",
            *args,
            **kwargs,
        )

        # self.network_client = NM.Client.new(None)

        # devices = self.network_client.get_all_devices()
        # print("Real devices")
        # print("------------")
        # for d in devices:
        #     if d.is_real():
        #         print(
        #             "%s (%s): %s"
        #             % (
        #                 d.get_iface(),
        #                 d.get_type_description(),
        #                 d.get_state(),
        #             )
        #         )
        # acons = self.network_client.get_active_connections()

        # for ac in acons:
        #     print(
        #         "%s (%s) - %s" % (ac.get_id(), ac.get_uuid(), ac.get_connection_type())
        #     )
        # if len(acons) == 0:
        #     print("No active connections")

        self.audio_controller = Audio()

        self.wifi_toggle = QSToggleButton(
            name="wifi_qs_toggle",
            h_expand=True,
            add_chevron=True,
        )
        self.wifi_toggle.connect("on_toggled", self.toggle_wifi)
        self.update_wifi_tile()
        Fabricator(
            poll_from=f"{configuration.try_get_property('nmcli_command')} d monitor {configuration.try_get_property('nmcli_wifi_adapter_name')}",
            interval=0,
            stream=True,
            on_changed=lambda _, v: self.handle_wifi_update(v.strip()),
        )

        self.wifi_popup = Gtk.Popover()
        self.wifi_popup.set_name("wifi_qs_popup")
        self.wifi_popup_box = Box(name="wifi_qs_popup_container")
        self.wifi_popup.add(self.wifi_popup_box)
        self.wifi_popup.set_default_widget(self.wifi_popup_box)
        self.wifi_popup.set_relative_to(self.wifi_toggle)
        self.wifi_popup.set_constrain_to(0)
        self.wifi_popup.set_pointing_to(self.wifi_toggle.get_allocation())
        self.wifi_popup.set_size_request(0, 0)

        # self.popup_window = PopupWindow(name="ass", parent=self.get_parent())
        # self.popup_window.children = [self.wifi_popup]

        # self.wifi_toggle_overlay = Overlay(
        #     child=self.wifi_toggle, overlays=self.wifi_popup
        # )
        # self.wifi_toggle_overlay.set_overlay_pass_through(self.wifi_popup, True)

        self.bluetooth_toggle = QSToggleButton(
            name="bluetooth_qs_toggle",
            h_expand=True,
            add_chevron=True,
        )
        self.bluetooth_toggle.connect(
            "on_toggled", lambda *_: self.bluetooth_client.toggle_power()
        )

        self.bluetooth_client = BluetoothClient()
        self.bluetooth_client.connect(
            "changed",
            lambda client: self.handle_bluetooth_update(client),
        )

        self.backlight_device = ""
        if backlight_device := configuration.try_get_property("backlight_device"):
            self.backlight_device = backlight_device
        else:
            devices = exec_shell_command(
                configuration.try_get_property("brightness_list_devices_command")
            )
            for device in devices.splitlines():
                if "backlight" in device:
                    self.backlight_device = device.split(",")[0]
                    break
            else:
                logger.error("Counldn't find a controllable brightness device.")

        self.brightness_icon = Label(name="qs_brightness_icon")
        self.brightness_slider = Slider(
            name="brightness_slider",
            style_classes="qs_slider",
            h_expand=True,
            poll_command=FormattedString(
                configuration.try_get_property("get_brightness_command")
            ).format(device=self.backlight_device),
            poll_interval=200,
            poll_stream=False,
            poll_value_processor=lambda v: float(v) / 255,
            # animation_duration=0.1,
            # animation_curve=(0.3, 0, 0.35, 1),
        )
        self.volume_slider = Slider(
            name="volume_slider",
            style_classes="qs_slider",
            h_expand=True,
            poll=False,
        )
        self.volume_toggle = ToggleButton(name="qs_volume_toggle")
        self.volume_chevron = ChevronButton(
            name="qs_volume_chevron", orientation="v", h_align="end", v_align="end"
        )
        self.volume_toggle_overlay = Overlay(
            child=self.volume_toggle, overlays=self.volume_chevron
        )

        self.speakers_holder = Box(name="qs_speakers_container", orientation="v")
        self.speakers_container = Box(
            h_expand=True,
            orientation="v",
            children=[
                Box(
                    children=[
                        Label(
                            configuration.try_get_property("speakers_header_text"),
                            name="header_label",
                        ),
                        Box(h_expand=True),
                    ]
                ),
                self.speakers_holder,
            ],
        )
        self.microphones_holder = Box(name="qs_microphones_container", orientation="v")
        self.microphones_container = Box(
            h_expand=True,
            orientation="v",
            children=[
                Box(
                    children=[
                        Label(
                            configuration.try_get_property("microphones_header_text"),
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
            markup=configuration.try_get_property("speakers_tab_icon"),
        )
        self.microphone_tab_button = MarkupButton(
            style_classes="tab_button",
            markup=configuration.try_get_property("microphones_tab_icon"),
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
            transition_duration=300,
        )

        def update_brightness_icon(value):
            self.brightness_icon.set_markup(
                configuration.try_get_property("brightness_high_icon")
                if self.brightness_slider.value
                > configuration.try_get_property("qs_brightness_high_threshold")
                else configuration.try_get_property("brightness_low_icon")
            )

        def update_volume_slider(*_):
            self.volume_slider.change_value(
                float(self.audio_controller.speaker.volume) / 100.0
            )

        def change_volume(v):
            self.audio_controller.speaker.volume = int(v * 100)

        def connect_volume_slider():
            if self.audio_controller.speaker:
                update_volume_slider()
                self.audio_controller.speaker.connect(
                    "notify::volume",
                    update_volume_slider,
                )

                self.volume_slider.set_sensitive(True)
            else:
                self.volume_slider.change_value(0)
                self.volume_slider.set_sensitive(False)

        def update_volume_toggle(*_):
            muted = self.audio_controller.speaker.muted
            self.volume_toggle.set_state(muted)

            self.volume_toggle.set_markup(
                configuration.try_get_property("volume_muted_icon")
                if muted
                else (
                    configuration.try_get_property("volume_high_icon")
                    if self.audio_controller.speaker.volume
                    > configuration.try_get_property("qs_volume_high_threshold")
                    else configuration.try_get_property("volume_low_icon")
                    if self.audio_controller.speaker.volume > 0.0
                    else configuration.try_get_property("volume_off_icon")
                )
            )

        def connect_volume_toggle():
            if self.audio_controller.speaker:
                update_volume_toggle()
                self.audio_controller.speaker.connect(
                    "notify::muted", update_volume_toggle
                )
                self.audio_controller.speaker.connect(
                    "notify::volume", update_volume_toggle
                )

                self.volume_toggle.set_sensitive(True)
            else:
                self.volume_toggle.set_state(False)
                self.volume_toggle.set_markup(
                    configuration.try_get_property("volume_muted_icon")
                )
                self.volume_toggle.set_sensitive(False)

        def toggle_mute_stream(mute):
            self.audio_controller.speaker.muted = mute

        self.volume_chevron.connect(
            "on-toggled",
            lambda button, *_: self.populate_sp_mic_containers()
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

        self.brightness_slider.connect(
            "on_interacted",
            lambda _, v: formatted_exec_shell_command_async(
                configuration.try_get_property("set_brightness_command"),
                device=self.backlight_device,
                value=int(v * 255),
            ),
        )
        self.brightness_slider.connect(
            "on_polled",
            lambda _, v: update_brightness_icon(int(v * 255)),
        )

        self.volume_slider.connect(
            "on_interacted",
            lambda _, v: change_volume(v),
        )
        connect_volume_slider()
        self.audio_controller.connect(
            "speaker-changed",
            lambda *_: connect_volume_slider(),
        )

        self.volume_toggle.connect(
            "on_toggled",
            lambda toggle, *_: toggle_mute_stream(toggle.toggled),
        )
        connect_volume_toggle()
        self.audio_controller.connect(
            "speaker-changed",
            lambda *_: connect_volume_toggle(),
        )

        self.rows = []
        self.rows.append(
            Box(
                style_classes="qs_row",
                orientation="h",
                children=[
                    # Box(
                    #     children=[
                    self.wifi_toggle,
                    # self.wifi_popup,
                    #     ]
                    # ),
                    self.bluetooth_toggle,
                ],
            )
        )
        self.rows.append(
            Box(
                style_classes="qs_row",
                children=[self.brightness_icon, self.brightness_slider],
            ),
        )
        self.rows.append(
            Box(
                style_classes="qs_row",
                orientation="v",
                children=[
                    Box(children=[self.volume_toggle_overlay, self.volume_slider]),
                    self.speakers_microphones_revealer,
                ],
            ),
        )

        homogenous_rows = [0]
        for row in homogenous_rows:
            self.rows[row].set_homogeneous(True)
            self.rows[row].add_style_class("homogeneous")

        self.children = self.rows
        self.chevrons = [
            self.wifi_toggle.chevron_button,
            self.bluetooth_toggle.chevron_button,
            self.volume_chevron,
        ]

    def toggle_wifi(self, toggle, *args):
        exec_shell_command_async(
            f"{configuration.try_get_property('nmcli_command')} r wifi {'on' if toggle.toggled else 'off'}"
        )

    def handle_wifi_update(self, v: str):
        [device, operation, *_] = v.split(": ")
        logger.debug(f'handling wifi update "{device}" "{operation}"')
        if device != configuration.try_get_property("nmcli_wifi_adapter_name"):
            return

        operations = ["connected", "disconnected", "unavailable", "connecting"]
        if operation.split()[0] not in operations:
            return

        if operation.split()[0] == "connecting":
            self.wifi_toggle.set_label("Connecting...")
            self.wifi_toggle.set_icon(
                configuration.try_get_property("network_connecting_icon")
            )

            logger.debug("Wifi connecting...")
            return
        else:
            self.update_wifi_tile()

    def update_wifi_tile(self):
        status = exec_shell_command(
            f"{configuration.try_get_property('nmcli_command')} r wifi"
        ).strip()
        logger.debug(f"Wifi {status}")

        active = status == "enabled"
        self.wifi_toggle.set_state(active)

        if active:
            active_connections = exec_shell_command(
                f"{configuration.try_get_property('nmcli_command')} c show --active"
            )
            for connection in [c.split(":") for c in active_connections.splitlines()]:
                if (
                    configuration.try_get_property("nmcli_wifi_adapter_name")
                    in connection
                ):
                    self.wifi_toggle.set_label(connection[0])
                    self.wifi_toggle.set_icon(
                        configuration.try_get_property("wifi_connected_icon")
                    )
                    logger.debug(f"Wifi connected {connection[0]}")
                    break
            else:
                self.wifi_toggle.set_label("Disconnected")
                self.wifi_toggle.set_icon(
                    configuration.try_get_property("network_disconnected_icon")
                )
                logger.debug("Wifi disconnected")
        else:
            self.wifi_toggle.set_label("Disabled")
            self.wifi_toggle.set_icon(
                configuration.try_get_property("network_disconnected_icon")
            )

    def handle_bluetooth_update(self, client):
        if client.state == "turning-on":
            self.bluetooth_toggle.set_label("Turning on...")
            self.bluetooth_toggle.set_icon(
                configuration.try_get_property("bluetooth_disconnected_icon")
            )
            logger.debug("Bluetooth turning on...")
            # client.scan()
            return
        elif client.state == "off":
            self.bluetooth_toggle.set_state(False)
            logger.debug("Bluetooth off")
            self.bluetooth_toggle.set_label("Off")
            self.bluetooth_toggle.set_icon(
                configuration.try_get_property("bluetooth_disconnected_icon")
            )
        elif client.state == "on":
            self.bluetooth_toggle.set_state(True)
            if client.devices:
                for device in client.devices:
                    if device.connecting:
                        self.bluetooth_toggle.set_label("Connecting...")
                        self.bluetooth_toggle.set_icon(
                            configuration.try_get_property("bluetooth_connecting_icon")
                        )
                        logger.debug(f"Bluetooth connecting  {device.props.name}...")
                        return
                    elif device.connected:
                        self.bluetooth_toggle.set_label(device.props.name)
                        self.bluetooth_toggle.set_icon(
                            configuration.try_get_property("bluetooth_connected_icon")
                        )
                        logger.debug(f"Bluetooth connected {device.props.name}")
                        return
                else:
                    logger.debug("Bluetooth on")
                    self.bluetooth_toggle.set_label("On")
                    self.bluetooth_toggle.set_icon(
                        configuration.try_get_property("bluetooth_disconnected_icon")
                    )

        if client.scanning:
            self.bluetooth_toggle.set_label("Scanning...")
            self.bluetooth_toggle.set_icon(
                configuration.try_get_property("bluetooth_connecting_icon")
            )
            logger.debug("Bluetooth scanning...")

    def set_default_sink(self, speaker):
        if speaker._stream:
            self.audio_controller._control.set_default_sink(speaker._stream)

            self.populate_sp_mic_containers(default_sink=speaker)
            return True

        return False

    def set_default_source(self, microphone):
        if microphone._stream:
            self.audio_controller._control.set_default_source(microphone._stream)

            self.populate_sp_mic_containers(default_source=microphone)
            return True

        return False

    def populate_sp_mic_containers(self, default_sink=None, default_source=None, *_):
        for child in self.speakers_holder.children:
            self.speakers_holder.remove(child)
        for child in self.microphones_holder.children:
            self.microphones_holder.remove(child)

        self.speakers_microphones_revealer.reveal()

        def speaker_factory(speaker):
            if not speaker.icon_name:
                icon = configuration.try_get_property("speakers_unknown_icon")
            elif "audio-card" in speaker.icon_name:
                icon = configuration.try_get_property("speakers_built_in_icon")
            elif "headset" in speaker.icon_name:
                icon = configuration.try_get_property("speakers_headphones_icon")
            else:
                icon = configuration.try_get_property("speakers_unknown_icon")

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
            elif speaker == self.audio_controller.speaker:
                button.add_style_class("active")

            return button

        def microphone_factory(microphone):
            icon = configuration.try_get_property("microphones_icon")

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
            elif microphone == self.audio_controller.microphone:
                button.add_style_class("active")

            return button

        for speaker in [
            speaker_factory(speaker) for speaker in self.audio_controller.speakers
        ]:
            self.speakers_holder.add(speaker)

        for microphone in [
            microphone_factory(microphone)
            for microphone in self.audio_controller.microphones
        ]:
            self.microphones_holder.add(microphone)

    def unreveal_sp_mic_containers(self):
        try:
            self.audio_controller.disconnect_by_func(self.populate_sp_mic_containers)
        except Exception:
            pass
        self.speakers_microphones_revealer.unreveal()
        self.speakers_microphones_stack.set_visible_child(self.speakers_container)
        self.speaker_tab_button.add_style_class("active")
        self.microphone_tab_button.remove_style_class("active")

    def hide_popups(self):
        for chevron in self.chevrons:
            chevron.toggle() if chevron.toggled else None

    def add_style(self, style):
        self.add_style_class(style)

    def remove_style(self, style):
        self.remove_style_class(style)
