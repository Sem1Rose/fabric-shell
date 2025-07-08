from config import configuration
from loguru import logger

from widgets.helpers.network import get_wifi_adapter_name
from widgets.buttons import QSToggleButton
from widgets.brightness_slider import BrightnessSlider
from widgets.volume_slider import VolumeSlider
from widgets.microphone_slider import MicrophoneSlider

from fabric.widgets.box import Box
from fabric.core.fabricator import Fabricator
from fabric.utils.helpers import (
    exec_shell_command,
    exec_shell_command_async,
)
from fabric.bluetooth import BluetoothClient


class QuickSettings(Box):
    def __init__(self, *args, **kwargs):
        super().__init__(
            name="quick_settings_container",
            orientation="v",
            *args,
            **kwargs,
        )

        self.volume_chevron = False
        self.do_not_disturb = None

        self.rows = []
        self.chevrons = []

        homogenous_rows = []
        tiles = []
        sliders = []

        for i, row in enumerate(
            list(configuration.get_property("dashboard_qs")["tiles"])
        ):
            qs_row = Box(
                style_classes="qs_row",
                orientation="h",
            )

            if (isinstance(row, str) and row == "empty") or list(row).__len__() == 0:
                self.rows.append(qs_row)
                continue
            else:
                for tile in row:
                    if tile in tiles:
                        logger.warning(f"Duplicate qs tile: {tile}")
                        continue

                    match tile:
                        case "wifi":
                            self.adapter_name = get_wifi_adapter_name()

                            self.wifi_toggle = QSToggleButton(
                                name="wifi_qs_toggle",
                                h_expand=True,
                                add_menu_button=True,
                                auto_toggle=True,
                            )

                            if self.adapter_name:
                                self.wifi_toggle.connect("on_toggled", self.toggle_wifi)
                                Fabricator(
                                    poll_from=f"{configuration.get_property('nmcli_command')} d monitor {self.adapter_name}",
                                    interval=0,
                                    stream=True,
                                    on_changed=lambda _, v: self.wifi_update(v.strip()),
                                )
                            else:
                                # self.wifi_toggle.set_sensitive(False)
                                # self.wifi_toggle.icon.set_sensitive(False)
                                self.wifi_toggle.set_label("Disabled")
                                self.wifi_toggle.set_icon(
                                    configuration.get_property(
                                        "network_disconnected_icon"
                                    )
                                )

                            qs_row.add(self.wifi_toggle)
                            # self.chevrons.append(self.wifi_toggle.chevron_button)
                        case "bluetooth":
                            self.bluetooth_client = BluetoothClient()

                            self.bluetooth_toggle = QSToggleButton(
                                name="bluetooth_qs_toggle",
                                h_expand=True,
                                add_menu_button=True,
                                auto_toggle=False,
                            )
                            self.bluetooth_toggle.connect(
                                "on_toggled",
                                lambda *_: self.bluetooth_client.toggle_power(),
                            )

                            self.bluetooth_update(self.bluetooth_client)
                            self.bluetooth_client.connect(
                                "changed",
                                lambda client: self.bluetooth_update(client),
                            )

                            qs_row.add(self.bluetooth_toggle)
                            # self.chevrons.append(self.bluetooth_toggle.chevron_button)
                        case "dnd":
                            self.do_not_disturb = QSToggleButton(
                                name="dnd_qs_toggle",
                                h_expand=True,
                                add_menu_button=False,
                                auto_toggle=True,
                            )

                            self.do_not_disturb.set_label("Do not disturb")
                            self.do_not_disturb.set_state(False)
                            self.do_not_disturb.set_icon(
                                configuration.get_property("dnd_off_icon")
                            )

                            qs_row.add(self.do_not_disturb)
                        case "empty":
                            qs_row.add(Box())
                        case _:
                            logger.warning(f"Unknown qs tile: {tile}")
                            continue

                    if tile != "empty":
                        tiles.append(tile)

            self.rows.append(qs_row)
            homogenous_rows.append(i)

        for slider in configuration.get_property("dashboard_qs")["sliders"]:
            qs_row = Box(
                style_classes="qs_row",
                orientation="v",
            )

            if slider in sliders:
                logger.warning(f"Duplicate qs slider: {slider}")
                continue

            if slider == "volume" or slider.startswith("volume-"):
                add_device_selection = False
                inverted = False
                orientation = "horizontal"
                if (modifiers := slider.split("-")).__len__() > 1:
                    for modifier in modifiers[1::]:
                        match modifier:
                            case "d":
                                add_device_selection = True
                                self.volume_chevron = True
                            case "i":
                                inverted = True
                            case "v":
                                orientation = "vertical"
                            case _:
                                logger.warning(
                                    f"Unknown modifier '{modifier}' for slider '{slider}'"
                                )

                self.volume_slider = VolumeSlider(
                    add_device_selection_popup=add_device_selection,
                    inverted=inverted,
                    orientation=orientation,
                )

                qs_row.add(self.volume_slider)
                if add_device_selection:
                    qs_row.add(self.volume_slider.speakers_microphones_revealer)
                    self.chevrons.append(self.volume_slider.chevron)
            elif slider == "microphone" or slider.startswith("microphone-"):
                inverted = False
                orientation = "horizontal"
                if (modifiers := slider.split("-")).__len__() > 1:
                    for modifier in modifiers[1::]:
                        match modifier:
                            case "i":
                                inverted = True
                            case "v":
                                orientation = "vertical"
                            case _:
                                logger.warning(
                                    f"Unknown modifier '{modifier}' for slider '{slider}'"
                                )

                self.microphone_slider = MicrophoneSlider(
                    inverted=inverted,
                    orientation=orientation,
                )

                qs_row.add(self.microphone_slider)
            elif slider == "brightness":
                self.brightness_slider = BrightnessSlider(True)
                qs_row.add(self.brightness_slider)
            elif slider == "empty":
                qs_row.add(Box())
            else:
                logger.warning(f"Unknown qs slider: {slider}")
                continue

            if slider != "empty":
                sliders.append(slider)

            self.rows.append(qs_row)

        for row in homogenous_rows:
            self.rows[row].set_homogeneous(True)
            self.rows[row].add_style_class("homogeneous")

        self.children = self.rows

        if self.rows.__len__() == 0:
            self.add_style_class("empty")

    def toggle_wifi(self, toggle, *args):
        exec_shell_command_async(
            f"{configuration.get_property('nmcli_command')} r wifi {'on' if toggle.toggled else 'off'}"
        )

    def wifi_update(self, v: str):
        [device, operation, *_] = v.split(": ")
        logger.debug(f'handling wifi update "{device}" "{operation}"')
        if device != self.adapter_name:
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
                if self.adapter_name in connection:
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
            self.wifi_toggle.set_label("Off")
            self.wifi_toggle.set_icon(
                configuration.get_property("network_disconnected_icon")
            )

    def bluetooth_update(self, client):
        if client.state == "absent":
            self.bluetooth_toggle.set_sensitive(False)
            self.bluetooth_toggle.icon.set_sensitive(False)
            self.bluetooth_toggle.set_state(False)
            self.bluetooth_toggle.set_label("Disabled")
            self.bluetooth_toggle.set_icon(
                configuration.get_property("bluetooth_disconnected_icon")
            )
        elif client.state == "turning-on":
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

    def add_style(self, style):
        self.add_style_class(style)

    def remove_style(self, style):
        self.remove_style_class(style)
