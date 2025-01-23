from config import configuration
from loguru import logger
from widgets.toggle_button import ToggleButton

from fabric.widgets.box import Box
from fabric.core.fabricator import Fabricator
from fabric.utils.helpers import exec_shell_command
from fabric.bluetooth import BluetoothClient

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

nmcli = "nmcli -c no -t"


class QuickSettings(Box):
    def __init__(self, *args, **kwargs):
        super().__init__(
            name="quick_settings_container",
            orientation="v",
            *args,
            **kwargs,
        )

        logger.debug(
            f"{nmcli} d monitor {configuration.get_property('nmcli_wifi_adapter_name')}"
        )
        self.wifi_tile = ToggleButton(
            name="wifi_qs_toggle", style_classes="qs_tile", h_expand=True
        ).build(
            lambda toggle, _: Fabricator(
                poll_from=f"{nmcli} d monitor {configuration.get_property('nmcli_wifi_adapter_name')}",
                interval=0,
                stream=True,
                on_changed=lambda _, v: self.handle_wifi_update(toggle, v.strip()),
            )
        )
        self.wifi_tile.connect("on_toggled", self.toggle_wifi)
        self.update_wifi_tile(self.wifi_tile)

        self.bluetooth_tile = ToggleButton(
            name="bluetooth_qs_toggle", style_classes="qs_tile", h_expand=True
        )
        self.bluetooth_tile.connect(
            "on_toggled", lambda *_: self.bluetooth_client.toggle_power()
        )

        self.bluetooth_client = BluetoothClient()
        self.bluetooth_client.connect(
            "changed",
            lambda client: self.handle_bluetooth_update(self.bluetooth_tile, client),
        )

        self.rows = []
        self.rows.append(
            Box(
                orientation="h",
                children=[
                    self.wifi_tile,
                    self.bluetooth_tile,
                ],
                spacing=configuration.get_property("spacing"),
            )
        )
        for row in self.rows:
            row.set_homogeneous(True)

        self.children = self.rows

    def toggle_wifi(self, toggle):
        exec_shell_command(f"{nmcli} r wifi {'on' if toggle.toggled else 'off'}")

    def handle_wifi_update(self, toggle, v: str):
        [device, operation, *_] = v.split(": ")
        logger.debug(f'handling wifi update "{device}" "{operation}"')
        if device != configuration.get_property("nmcli_wifi_adapter_name"):
            return

        operations = ["connected", "disconnected", "unavailable", "connecting"]
        if operation.split()[0] not in operations:
            return

        if operation.split()[0] == "connecting":
            toggle.set_label("Connecting...")
            logger.debug("Wifi connecting...")
            return
        else:
            self.update_wifi_tile(toggle)

    def update_wifi_tile(self, toggle):
        status = exec_shell_command(f"{nmcli} r wifi").strip()
        logger.debug(f"Wifi {status}")

        active = status == "enabled"
        toggle.set_state(active)

        if active:
            active_connections = exec_shell_command(f"{nmcli} c show --active")
            for connection in [c.split(":") for c in active_connections.splitlines()]:
                if configuration.get_property("nmcli_wifi_adapter_name") in connection:
                    toggle.set_label(connection[0])
                    logger.debug(f"Wifi connected {connection[0]}")
                    break
            else:
                logger.debug("Wifi disconnected")
                toggle.set_label("Disconnected")
        else:
            toggle.set_label("Disabled")

    def handle_bluetooth_update(self, toggle, client):
        if client.state == "turning-on":
            toggle.set_label("Turning on...")
            logger.debug("Bluetooth turning on...")
            # client.scan()
            return
        elif client.state == "off":
            toggle.set_state(False)
            logger.debug("Bluetooth off")
            toggle.set_label("Off")
        elif client.state == "on":
            toggle.set_state(True)
            if client.devices:
                for device in client.devices:
                    if device.connecting:
                        toggle.set_label("Connecting...")
                        logger.debug(f"Bluetooth connecting  {device.props.name}...")
                        return
                    elif device.connected:
                        toggle.set_label(device.props.name)
                        logger.debug(f"Bluetooth connected {device.props.name}")
                        return
                else:
                    logger.debug("Bluetooth on")
                    toggle.set_label("On")

        if client.scanning:
            toggle.set_label("Scanning...")
            logger.debug("Bluetooth scanning...")
