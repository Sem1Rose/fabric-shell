from loguru import logger
from config import configuration
import json

from fabric.utils.helpers import exec_shell_command
from fabric.core.fabricator import Fabricator

from fabric.widgets.box import Box
from fabric.widgets.label import Label


class NetworkUsage(Box):
    def __init__(self, *args, **kwargs):
        super().__init__(
            name="network_usage_widget",
            style_classes="bar_widget",
            *args,
            **kwargs,
        )

        self.icon = Label(
            name="network_usage_icon",
            markup=configuration.get_property("network_usage_download_icon"),
        )
        self.usage = Label(name="network_usage", markup="0 KB").build(
            lambda label, _: Fabricator(
                poll_from=f"vnstat -i {configuration.get_property('nmcli_wifi_adapter_name')} -l --json",
                interval=0,
                stream=True,
                on_changed=lambda _, value: self.update_usage(value),
            )
        )

        self.children = [self.icon, Box(h_expand=True), self.usage]

    def update_usage(self, value):
        try:
            data = json.loads(value)
        except Exception as e:
            logger.error(f"Error while deserializing network usage json: {e}")
            return

        if "jsonversion" in data.keys() or "index" not in data.keys():
            return

        device_stats = exec_shell_command(
            f"{configuration.get_property('nmcli_command')} d show {configuration.get_property('nmcli_wifi_adapter_name')}"
        )

        connection_state = None
        connection_strength = None
        connection_name = "unknown"
        ip_address = None
        for line in device_stats.splitlines():
            if "STATE" in line:
                state = line.split(":")[1]
                connection_state = state.split(" ")[1][1:-1]
                connection_strength = int(state.split(" ")[0])
            elif "CONNECTION" in line:
                connection_name = line.split(":")[1]
            elif "IP4.ADDRESS" in line:
                ip_address = line.split(":")[1].split("/")[0]

        if not connection_state:
            return

        if connection_state != "connected":
            self.icon.set_markup(
                configuration.get_property("network_disconnected_icon")
            )
            self.usage.set_label("Disconnected")

            self.set_tooltip_markup("Disconnected")
            return

        tx_rate = int(data["tx"]["bytespersecond"])
        rx_rate = int(data["rx"]["bytespersecond"])

        def get_size(bytes):
            factor = 1024
            bytes /= factor
            for unit in ["KB", "MB"]:
                if bytes < factor:
                    return f"{int(bytes) if bytes < 1 else (float(int(bytes * 10)) / 10) if bytes < 100 else int(bytes)} {unit}"
                bytes /= factor

        if tx_rate >= rx_rate:
            self.icon.set_markup(
                configuration.get_property("network_usage_upload_icon")
            )
            self.usage.set_label(get_size(tx_rate))
        else:
            self.icon.set_markup(
                configuration.get_property("network_usage_download_icon")
            )
            self.usage.set_label(get_size(rx_rate))

        self.set_tooltip_markup(
            (
                f"Connected to {connection_name}\nConnection strength: {connection_strength}\n"
                if connection_state
                else ""
            )
            + (f"IP Address: {ip_address}" if ip_address else "")
        )
