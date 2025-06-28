from loguru import logger
from config import configuration
from fabric.utils import exec_shell_command

wifi_adapter_name = None
if adapter_name := configuration.get_property("nmcli_wifi_adapter_name"):
    wifi_adapter_name = adapter_name
else:
    devices = exec_shell_command(f"{configuration.get_property('nmcli_command')} d")
    for device in devices.splitlines():
        if ":wifi:" in device:
            wifi_adapter_name = device.split(":")[0]
            break
    else:
        logger.error("Counldn't find a wifi device.")

eth_adapter_name = None
if adapter_name := configuration.get_property("nmcli_eth_adapter_name"):
    eth_adapter_name = adapter_name
else:
    devices = exec_shell_command(f"{configuration.get_property('nmcli_command')} d")
    for device in devices.splitlines():
        if ":ethernet:" in device:
            eth_adapter_name = device.split(":")[0]
            break
    else:
        logger.error("Counldn't find an ethernet device.")


def get_wifi_adapter_name():
    return wifi_adapter_name


def get_eth_adapter_name():
    return eth_adapter_name
