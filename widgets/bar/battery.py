from loguru import logger
from config import configuration

from fabric.utils.helpers import (
    invoke_repeater,
    exec_shell_command,
    exec_shell_command_async,
    FormattedString,
)
from widgets.helpers.formatted_exec import formatted_exec_shell_command
from fabric.core.service import Property

from fabric.widgets.box import Box
from fabric.widgets.circularprogressbar import CircularProgressBar
from fabric.widgets.label import Label
from fabric.widgets.overlay import Overlay


class BatteryWidget(Box):
    def __init__(self, *args, **kwargs):
        super().__init__(
            name="battery_widget",
            style_classes="bar_widget",
            *args,
            **kwargs,
        )
        self.warned_low_battery = False
        self.primary_previous_state = ""
        self.blocks = {}

        invoke_repeater(
            1000,
            self.update_battery_levels,
        )

    def update_battery_levels(self):
        output = exec_shell_command(
            configuration.try_get_property("battery_list_devices_command")
        )
        devices = list(
            filter(lambda x: "battery" in x or "headset" in x, output.splitlines())
        )

        processed_devices = {}
        for device in devices:
            info = formatted_exec_shell_command(
                configuration.try_get_property("battery_device_info_command"),
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

            if name == "Primary" and self.primary_previous_state != state:
                if (
                    state == "discharging" or state == "unknown"
                ) and not self.warned_low_battery:
                    if percentage_float * 100 < configuration.try_get_property(
                        "battery_warning_level"
                    ):
                        self.warned_low_battery = True
                        exec_shell_command_async(
                            f"fabric-cli execute {configuration.try_get_property('app_name')} \"urgent_osd.show_urgent_osd('battery')\""
                        )
                    elif percentage_float * 100 < configuration.try_get_property(
                        "battery_hibernate_level"
                    ):
                        # TODO
                        pass
                elif state != "discharging" and state != "unknown":
                    self.warned_low_battery = False
                    exec_shell_command_async(
                        f'fabric-cli execute {configuration.try_get_property("app_name")} "urgent_osd.hide_urgent_osd()"'
                    )

                self.primary_previous_state = state

            if "headset" in device:
                icon = configuration.try_get_property("battery_widget_headset_icon")
            elif "battery" in device:
                icon = (
                    configuration.try_get_property(
                        "battery_widget_battery_charging_icon"
                    )
                    if state in ("charging", "fully-charged")
                    else (
                        configuration.try_get_property(
                            "battery_widget_battery_full_icon"
                        )
                        if percentage_float >= 0.7
                        else configuration.try_get_property(
                            "battery_widget_battery_half_full_icon"
                        )
                        if percentage_float >= 0.3
                        else configuration.try_get_property(
                            "battery_widget_battery_empty_icon"
                        )
                    )
                )
            else:
                icon = configuration.try_get_property(
                    "battery_widget_battery_unknown_icon"
                )

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
                self.blocks[device][0].bulk_set(device, name, percentage, icon, state)

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
                new_block[0].bulk_set(device, name, percentage, icon, state)
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

                new_block = BatteryBlock()
                new_block.bulk_set(device, name, percentage, icon, state)

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


class BatteryBlock(Box):
    def __init__(
        self,
        percentage_display_processor=lambda v: f"{int(v * 100)} %",
        *args,
        **kwargs,
    ):
        super().__init__(
            style_classes="circular_progress_block",
            *args,
            **kwargs,
        )
        self._device = ""
        self._device_name = ""
        self._state = ""
        self._icon = ""
        self._percentage = ""
        self.percentage_display_processor = percentage_display_processor

        match configuration.try_get_property("circular_progress_empty_part"):
            case "bottom":
                circ_progress_empty_base_angle = 90
            case "right":
                circ_progress_empty_base_angle = 0
            case "top":
                circ_progress_empty_base_angle = 270
            case "left":
                circ_progress_empty_base_angle = 180
            case _:
                circ_progress_empty_base_angle = 0

        circ_progress_start_angle = circ_progress_empty_base_angle + (
            float(configuration.try_get_property("circular_progress_empty_angle")) / 2
        )
        circ_progress_end_angle = (
            360
            + circ_progress_empty_base_angle
            - (
                float(configuration.try_get_property("circular_progress_empty_angle"))
                / 2
            )
        )

        self.circ_progress = CircularProgressBar(
            name="battery_percentage",
            style_classes="circular_progress",
            value=0,
            h_expand=True,
            v_expand=True,
            start_angle=circ_progress_start_angle,
            end_angle=circ_progress_end_angle,
        )
        self.icon = Label()
        self.label = Label()

        self.children = [
            Overlay(
                child=Box(
                    style_classes="circular_progress_container",
                    children=[self.circ_progress],
                ),
                overlays=[
                    Box(
                        style_classes="circular_progress_overlay_icon",
                        children=[self.icon],
                        h_expand=True,
                        v_expand=True,
                        h_align="center",
                        v_align="center",
                    )
                ],
            ),
            self.label,
        ]

    def bulk_set(self, device, name, percentage, icon, state):
        self.set_percentage(percentage)
        self.set_icon(icon)
        self.set_state(state)
        self.set_device(device, name)

    def set_device(self, device, name):
        self._device = device
        self._device_name = name

        self.set_state(self._state)
        self.update_tooltip()

    def set_percentage(self, new_percentage: float):
        self._percentage = new_percentage

        self.label.set_markup(self.percentage_display_processor(self._percentage))
        self.circ_progress.value = self._percentage

    def set_state(self, new_state: str):
        self._state = new_state

        self.icon.add_style_class("charging") if new_state in (
            "charging",
            "fully-charged",
        ) and "headset" not in self._device else self.icon.remove_style_class(
            "charging"
        )

    def set_icon(self, new_icon: str):
        self._icon = new_icon
        self.icon.set_markup(self._icon)

    def update_tooltip(self):
        self.set_tooltip_markup(
            FormattedString(
                configuration.try_get_property("battery_widget_tooltip_markup")
            ).format(
                icon=self._icon,
                name=self._device_name,
                battery=self.percentage_display_processor(self._percentage),
                state=self._state,
            )
        )
