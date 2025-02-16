from config import configuration
from loguru import logger

from widgets.buttons import ToggleButton, QSToggleButton, ChevronButton
from widgets.interactable_slider import Slider
from widgets.helpers.formatted_exec import formatted_exec_shell_command_async

from fabric.widgets.box import Box
from fabric.widgets.stack import Stack
from fabric.widgets.overlay import Overlay
from fabric.widgets.label import Label

from fabric.audio import Audio
from fabric.core.fabricator import Fabricator
from fabric.utils.helpers import (
    exec_shell_command,
    exec_shell_command_async,
    FormattedString,
)
from fabric.bluetooth import BluetoothClient

# import gi

# gi.require_version("Gtk", "3.0")
# from gi.repository import Gtk  # noqa: E402


class QuickSettings(Box):
    def __init__(self, *args, **kwargs):
        super().__init__(
            name="quick_settings_container",
            orientation="v",
            *args,
            **kwargs,
        )

        self.audio_controller = Audio()

        self.wifi_toggle = QSToggleButton(
            name="wifi_qs_toggle",
            h_expand=True,
            add_chevron=True,
        ).build(
            lambda toggle, _: Fabricator(
                poll_from=f"{configuration.get_property('nmcli_command')} d monitor {configuration.get_property('nmcli_wifi_adapter_name')}",
                interval=0,
                stream=True,
                on_changed=lambda _, v: self.handle_wifi_update(v.strip()),
            )
        )
        self.wifi_toggle.connect("on_toggled", self.toggle_wifi)
        self.update_wifi_tile()

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

        if backlight_device := configuration.get_property("backlight_device"):
            self.backlight_device = backlight_device
        else:
            devices = exec_shell_command(
                configuration.get_property("brightness_list_devices_command")
            )
            for device in devices.splitlines():
                if "backlight" in device:
                    self.backlight_device = device.split(",")[0]
                    break

        def update_brightness_icon(value):
            self.brightness_icon.set_markup(
                configuration.get_property("brightness_high_icon")
                if self.brightness_slider.value
                > configuration.get_property("qs_brightness_high_threshold")
                else configuration.get_property("brightness_low_icon")
            )

        self.brightness_icon = Label(name="qs_brightness_icon")

        self.brightness_slider = Slider(
            name="brightness_slider",
            style_classes="qs_slider",
            h_expand=True,
            poll_command=FormattedString(
                configuration.get_property("get_brightness_command")
            ).format(device=self.backlight_device),
            poll_interval=200,
            poll_stream=False,
            poll_value_processor=lambda v: float(v) / 255,
            # animation_duration=0.1,
            # animation_curve=(0.3, 0, 0.35, 1),
        )
        self.brightness_slider.connect(
            "on_interacted",
            lambda _, v: formatted_exec_shell_command_async(
                configuration.get_property("set_brightness_command"),
                device=self.backlight_device,
                value=int(v * 255),
            ),
        )
        self.brightness_slider.connect(
            "on_polled",
            lambda _, v: update_brightness_icon(int(v * 255)),
        )

        self.volume_slider = Slider(
            name="volume_slider",
            style_classes="qs_slider",
            h_expand=True,
            poll=False,
            # poll_command=configuration.get_property("get_volume_command"),
            # poll_interval=200,
            # poll_stream=False,
            # poll_value_processor=lambda v: float(v) / 100,
            # animation_duration=0.1,
            # animation_curve=(0.3, 0, 0.35, 1),
        )

        # self.audio_controller.speaker.connect(
        #     "notify::volume",
        #     self.volume_slider.change_value(int(self.audio_controller.speaker.volume)),
        # )
        def update_volume_slider(*_):
            self.volume_slider.change_value(
                float(self.audio_controller.speaker.volume) / 100.0
            )

        def connect_volume_slider():
            if self.audio_controller.speaker:
                # if self.audio_controller.speaker.is_connected(update_volume_slider):
                #     self.audio_controller.speaker.disconnect_by_func(
                #         update_volume_slider
                #     )

                update_volume_slider()
                self.audio_controller.speaker.connect(
                    "notify::volume",
                    update_volume_slider,
                )

                self.volume_slider.set_sensitive(True)
            else:
                self.volume_slider.change_value(0)
                self.volume_slider.set_sensitive(False)

        connect_volume_slider()
        self.audio_controller.connect(
            "speaker-changed",
            lambda *_: connect_volume_slider(),
        )

        def change_volume(v):
            self.audio_controller.speaker.volume = int(v * 100)

        self.volume_slider.connect(
            "on_interacted",
            lambda _, v: change_volume(v),
            #     formatted_exec_shell_command_async(
            #     configuration.get_property("set_volume_command"),
            #     value=int(v * 100),
            # ),
        )

        def update_volume_toggle(*_):
            muted = self.audio_controller.speaker.muted
            self.volume_toggle.set_state(muted)

            self.volume_toggle.set_markup(
                configuration.get_property("volume_muted_icon")
                if muted
                else (
                    configuration.get_property("volume_high_icon")
                    if self.audio_controller.speaker.volume
                    > configuration.get_property("qs_volume_high_threshold")
                    else configuration.get_property("volume_low_icon")
                    if self.audio_controller.speaker.volume > 0.0
                    else configuration.get_property("volume_off_icon")
                )
            )

        self.volume_toggle = ToggleButton(
            name="qs_volume_toggle",
            # ).build(
            #     lambda toggle, _: Fabricator(
            #         poll_from=configuration.get_property("get_volume_mute_command"),
            #         interval=200,
            #         on_changed=lambda _, value: (
            #             toggle.set_state(value == "true"),
            #             update_volume_toggle(value),
            #         ),
            #     )
        )

        # self.audio_controller.speaker.connect(
        #     "notify::is-muted",
        #     (
        #         self.volume_toggle.set_state(not self.audio_controller.speaker.muted),
        #         update_volume_toggle(self.audio_controller.speaker.muted),
        #     ),
        # )
        def connect_volume_toggle():
            if self.audio_controller.speaker:
                # if self.audio_controller.speaker.is_connected(update_volume_toggle):
                #     self.audio_controller.speaker.disconnect_by_func(
                #         update_volume_toggle,
                #     )

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
                    configuration.get_property("volume_muted_icon")
                )
                self.volume_toggle.set_sensitive(False)

        connect_volume_toggle()
        self.audio_controller.connect(
            "speaker-changed",
            lambda *_: connect_volume_toggle(),
        )

        def toggle_mute_stream(mute):
            self.audio_controller.speaker.muted = mute

        self.volume_toggle.connect(
            "on_toggled",
            lambda toggle, *_: toggle_mute_stream(toggle.toggled),
            # lambda *_: exec_shell_command_async(
            #     configuration.get_property("volume_toggle_mute_command")
            # ),
        )

        self.volume_chevron = ChevronButton(
            name="qs_volume_chevron", orientation="v", h_align="end", v_align="end"
        )

        self.volume_toggle_overlay = Overlay(
            child=self.volume_toggle, overlays=self.volume_chevron
        )

        self.rows = []
        self.rows.append(
            Box(
                style_classes="qs_row",
                orientation="h",
                children=[
                    self.wifi_toggle,
                    self.bluetooth_toggle,
                ],
                spacing=configuration.get_property("spacing"),
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
                children=[self.volume_toggle_overlay, self.volume_slider],
            ),
        )

        homogenous_rows = [0]
        for row in homogenous_rows:
            self.rows[row].set_homogeneous(True)

        self.children = self.rows
        self.chevrons = [
            self.wifi_toggle.chevron_button,
            self.bluetooth_toggle.chevron_button,
            self.volume_chevron,
        ]

    def toggle_wifi(self, toggle, *args):
        exec_shell_command_async(
            f"{configuration.get_property('nmcli_command')} r wifi {'on' if toggle.toggled else 'off'}"
        )

    def handle_wifi_update(self, v: str):
        [device, operation, *_] = v.split(": ")
        logger.debug(f'handling wifi update "{device}" "{operation}"')
        if device != configuration.get_property("nmcli_wifi_adapter_name"):
            return

        operations = ["connected", "disconnected", "unavailable", "connecting"]
        if operation.split()[0] not in operations:
            return

        if operation.split()[0] == "connecting":
            self.wifi_toggle.set_label("Connecting...")
            self.wifi_toggle.set_icon(
                configuration.get_property("network_connecting_icon")
            )

            logger.debug("Wifi connecting...")
            return
        else:
            self.update_wifi_tile()

    def update_wifi_tile(self):
        status = exec_shell_command(
            f"{configuration.get_property('nmcli_command')} r wifi"
        ).strip()
        logger.debug(f"Wifi {status}")

        active = status == "enabled"
        self.wifi_toggle.set_state(active)

        if active:
            active_connections = exec_shell_command(
                f"{configuration.get_property('nmcli_command')} c show --active"
            )
            for connection in [c.split(":") for c in active_connections.splitlines()]:
                if configuration.get_property("nmcli_wifi_adapter_name") in connection:
                    self.wifi_toggle.set_label(connection[0])
                    self.wifi_toggle.set_icon(
                        configuration.get_property("wifi_connected_icon")
                    )
                    logger.debug(f"Wifi connected {connection[0]}")
                    break
            else:
                self.wifi_toggle.set_label("Disconnected")
                self.wifi_toggle.set_icon(
                    configuration.get_property("network_disconnected_icon")
                )
                logger.debug("Wifi disconnected")
        else:
            self.wifi_toggle.set_label("Disabled")
            self.wifi_toggle.set_icon(
                configuration.get_property("network_disconnected_icon")
            )

    def handle_bluetooth_update(self, client):
        if client.state == "turning-on":
            self.bluetooth_toggle.set_label("Turning on...")
            self.bluetooth_toggle.set_icon(
                configuration.get_property("bluetooth_disconnected_icon")
            )
            logger.debug("Bluetooth turning on...")
            # client.scan()
            return
        elif client.state == "off":
            self.bluetooth_toggle.set_state(False)
            logger.debug("Bluetooth off")
            self.bluetooth_toggle.set_label("Off")
            self.bluetooth_toggle.set_icon(
                configuration.get_property("bluetooth_disconnected_icon")
            )
        elif client.state == "on":
            self.bluetooth_toggle.set_state(True)
            if client.devices:
                for device in client.devices:
                    if device.connecting:
                        self.bluetooth_toggle.set_label("Connecting...")
                        self.bluetooth_toggle.set_icon(
                            configuration.get_property("bluetooth_connecting_icon")
                        )
                        logger.debug(f"Bluetooth connecting  {device.props.name}...")
                        return
                    elif device.connected:
                        self.bluetooth_toggle.set_label(device.props.name)
                        self.bluetooth_toggle.set_icon(
                            configuration.get_property("bluetooth_connected_icon")
                        )
                        logger.debug(f"Bluetooth connected {device.props.name}")
                        return
                else:
                    logger.debug("Bluetooth on")
                    self.bluetooth_toggle.set_label("On")
                    self.bluetooth_toggle.set_icon(
                        configuration.get_property("bluetooth_disconnected_icon")
                    )

        if client.scanning:
            self.bluetooth_toggle.set_label("Scanning...")
            self.bluetooth_toggle.set_icon(
                configuration.get_property("bluetooth_connecting_icon")
            )
            logger.debug("Bluetooth scanning...")

    def hide_popups(self):
        for chevron in self.chevrons:
            chevron.toggle() if chevron.toggled else None
