from loguru import logger
from config import configuration

from fabric.utils.helpers import (
    invoke_repeater,
    exec_shell_command,
    exec_shell_command_async,
    # FormattedString,
)
from widgets.helpers.formatted_exec import formatted_exec_shell_command
from widgets.circular_progress_icon import CircularProgressIcon
from fabric.core.service import Property

from fabric.widgets.box import Box
from gi.repository import GLib


class BatteryWidget(Box):
    def __init__(self, *args, **kwargs):
        super().__init__(
            name="battery_widget",
            style_classes="bar_widget",
            *args,
            **kwargs,
        )
        self.warned_low_battery = False
        self.execed_suspend_commands = False
        self.primary_previous_state = ""
        self.blocks = {}

        invoke_repeater(
            1000,
            self.update_battery_levels,
        )

    def update_battery_levels(self):
        (
            self.add_style_class
            if configuration.get_property("battery_widget_compact")
            else self.remove_style_class
        )("compact")

        output = exec_shell_command(
            configuration.get_property("battery_list_devices_command")
        )
        devices = list(
            filter(lambda x: "battery" in x or "headset" in x, output.splitlines())
        )

        processed_devices = {}
        for device in devices:
            info = formatted_exec_shell_command(
                configuration.get_property("battery_device_info_command"),
                device=device,
            ).splitlines()

            state = "discharging"
            name = "Unknown"
            percentage = None
            for line in info:
                if "model" in line:
                    name = line.split(": ")[1].strip()
                elif "percentage" in line:
                    percentage = line.split(": ")[1].strip()
                elif "state" in line:
                    state = line.split(": ")[1].strip()

            if percentage is None:
                continue

            try:
                percentage_float = float(percentage[:-1]) / 100.0
            except Exception:
                percentage_float = 0.0

            if name == "Primary":
                if (
                    # self.primary_previous_state != state
                    state == "discharging" or state == "unknown"
                ):
                    if (
                        percentage_float * 100
                        < configuration.get_property("battery_warning_level")
                        and not self.warned_low_battery
                    ):
                        self.warned_low_battery = True
                        exec_shell_command_async(
                            f"fabric-cli execute {configuration.get_property('app_name')} \"urgent_osd.show_urgent_osd('battery')\""
                        )

                        # self.primary_previous_state = state
                    elif (
                        percentage_float * 100
                        < configuration.get_property("battery_hibernate_level")
                        and not self.execed_suspend_commands
                    ):
                        self.execed_suspend_commands = True

                        exec_shell_command_async(
                            f'fabric-cli execute {configuration.get_property("app_name")} "urgent_osd.hide_urgent_osd()"'
                        )

                        logger.warning("Suspending due to low charge!")

                        lock_commands = " ".join(
                            [
                                f"{command};"
                                for command in configuration.get_property(
                                    "power_menu_lock_commands"
                                )
                            ]
                        )
                        suspend_commands = " ".join(
                            [
                                f"{command};"
                                for command in configuration.get_property(
                                    "power_menu_suspend_commands"
                                )
                            ]
                        )

                        # def suspend():
                        exec_shell_command(f"sh -c '{lock_commands}'")
                        exec_shell_command(f"sh -c '{suspend_commands}'")

                        # GLib.Thread.new("suspend", suspend)
                else:
                    self.warned_low_battery = False
                    self.execed_suspend_commands = False
                    exec_shell_command_async(
                        f'fabric-cli execute {configuration.get_property("app_name")} "urgent_osd.hide_urgent_osd()"'
                    )

            if "headset" in device:
                icon = configuration.get_property("battery_widget_headset_icon")
            elif "battery" in device:
                icon = (
                    configuration.get_property("battery_widget_battery_charging_icon")
                    if state in ("charging", "fully-charged")
                    else (
                        configuration.get_property("battery_widget_battery_full_icon")
                        if percentage_float >= 0.7
                        else configuration.get_property(
                            "battery_widget_battery_half_full_icon"
                        )
                        if percentage_float >= 0.3
                        else configuration.get_property(
                            "battery_widget_battery_empty_icon"
                        )
                    )
                )
            else:
                icon = configuration.get_property("battery_widget_battery_unknown_icon")

            processed_devices[device] = (name, percentage_float, icon, state)
        # logger.warning([device[0] for device in processed_devices.values()])

        if len(processed_devices) == 0:
            self.add_style_class("empty")
        else:
            self.remove_style_class("empty")

        replacement_blocks = []
        for block in [key for key in self.blocks.keys()]:
            if block not in processed_devices:
                replacement_blocks.append(self.blocks.pop(block))

        children = [
            child
            for child in self.children
            if isinstance(child, BatteryBlock) and child._device in processed_devices
        ]
        # logger.warning([child._device_name for child in children])

        if len(processed_devices) != 0 and len(children) == 0:
            for dev in processed_devices.keys():
                if processed_devices[dev][0] == "Primary":
                    first_device = dev
                    first_item = False
                    break
            else:
                first_item = True
                first_device = None
        elif len(children) != 0:
            first_item = False
            first_device = children[-1]._device
        else:
            first_item = False

        for device, (name, percentage, icon, state) in processed_devices.items():
            if device in self.blocks:
                self.blocks[device][0].bulk_set(
                    icon=icon,
                    percentage=percentage,
                    device=device,
                    name=name,
                    state=state,
                    show_label=not configuration.get_property("battery_widget_compact"),
                )

                if (
                    first_device is not None
                    and device == first_device
                    and self.blocks[device][1] is not None
                ):
                    self.remove(self.blocks[device][1])
                    self.blocks[device] = (self.blocks[device][0], None)
            elif len(replacement_blocks) != 0:
                new_block = replacement_blocks[0]
                del replacement_blocks[0]
                new_block[0].bulk_set(
                    icon=icon,
                    percentage=percentage,
                    device=device,
                    name=name,
                    state=state,
                    show_label=not configuration.get_property("battery_widget_compact"),
                )
                self.blocks[device] = new_block

                if (
                    first_device is not None
                    and device == first_device
                    and self.blocks[device][1] is not None
                ):
                    self.remove(self.blocks[device][1])
                    self.blocks[device] = (self.blocks[device][0], None)

                self.reorder_child(new_block, 0)
                if self.blocks[device][1] is not None:
                    self.reorder_child(self.blocks[device][1], 1)
            else:
                make_first = first_item or (
                    first_device is not None and device == first_device
                )

                new_block = BatteryBlock(
                    add_label=not configuration.get_property("battery_widget_compact")
                )
                new_block.bulk_set(
                    icon=icon,
                    percentage=percentage,
                    device=device,
                    name=name,
                    state=state,
                    show_label=not configuration.get_property("battery_widget_compact"),
                )

                if make_first:
                    new_spacer = None
                else:
                    new_spacer = Box(
                        style_classes="circular_progress_block_spacer",
                        v_expand=True,
                    )

                self.blocks[device] = (new_block, new_spacer)

                self.add(new_block)
                if not make_first:
                    self.add(new_spacer)

                if not make_first:
                    self.reorder_child(new_block, 0)
                    self.reorder_child(new_spacer, 1)

                first_item = False

        for block in replacement_blocks:
            self.remove(block[0])
            if block[1] is not None:
                self.remove(block[1])

            del block

        return True


class BatteryBlock(CircularProgressIcon):
    @Property(str, "rw", default_value="")
    def state(self) -> str:
        return self._state

    @state.setter
    def state(self, value: str):
        self._state = value

        self.update_state()

    @Property(str, "rw", default_value="")
    def device_name(self) -> str:
        return self._device_name

    @device_name.setter
    def device_name(self, value: str):
        self._device_name = value

    @Property(str, "rw", default_value="")
    def device(self) -> str:
        return self._device

    @device.setter
    def device(self, value: str):
        self._device = value

        self.update_state()
        # self.update_tooltip()

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(
            tooltip_markup=configuration.get_property("battery_widget_tooltip_markup"),
            *args,
            **kwargs,
        )
        self._device = ""
        self._device_name = ""
        self._state = ""

    def bulk_set(
        self,
        device: str | None = None,
        name: str | None = None,
        state: str | None = None,
        **kwargs,
    ):
        if state is not None:
            self.state = state
        if name is not None:
            self.device_name = name
        if device is not None:
            self.device = device
        super().bulk_set(**kwargs)

    def update_state(self):
        self.icon.add_style_class("charging") if self._state in (
            "charging",
            "fully-charged",
        ) and "headset" not in self._device else self.icon.remove_style_class(
            "charging"
        )

    def update_tooltip(self):
        super().update_tooltip(
            name=self._device_name,
            state=self._state,
        )
