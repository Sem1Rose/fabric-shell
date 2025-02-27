from enum import Enum
from loguru import logger

from fabric.widgets.wayland import WaylandWindow as Window
from fabric.widgets.label import Label
from fabric.widgets.box import Box
from fabric.widgets.revealer import Revealer
from fabric.widgets.stack import Stack
from fabric.widgets.eventbox import EventBox
from fabric.widgets.shapes.corner import Corner
from fabric.core.fabricator import Fabricator
from fabric.utils.helpers import (
    exec_shell_command_async,
    exec_shell_command,
    cooldown,
    FormattedString,
)

from config import configuration
from widgets.interactable_slider import Slider
from widgets.buttons import ToggleButton, MarkupButton
from widgets.helpers.formatted_exec import formatted_exec_shell_command_async
from fabric.audio import Audio


class OSDWindow(Window):
    def __init__(self, *args, **kwargs):
        super().__init__(
            name="osd_window",
            anchor="top right",
            exclusivity="normal",
            layer="overlay",
            visible=False,
            *args,
            **kwargs,
        )

        self.hovered = False
        self.revealed = False
        self.brightness_handle = None
        self.volume_handle = None

        self.audio_controller = Audio()

        self.backlight_device = ""
        if backlight_device := configuration.get_property("backlight_device"):
            self.backlight_device = backlight_device
        else:
            devices = exec_shell_command(
                configuration.get_property("brightness_list_devices_command")
            )
            for device in devices.splitlines():
                if "backlight" in device:
                    self.backlight_device = device.split(",")[0]
                    logger.info(f"Found brightness device {self.backlight_device}")
                    break
            else:
                logger.error("Counldn't find a controllable brightness device.")

        def update_brightness_icon(value):
            self.brightness_icon.set_markup(
                configuration.get_property("brightness_high_icon")
                if self.brightness_slider.value
                > configuration.get_property("qs_brightness_high_threshold")
                else configuration.get_property("brightness_low_icon")
            )

        self.brightness_icon = Label(
            name="osd_brightness_icon", h_expand=True, v_expand=True
        )

        self.brightness_slider = Slider(
            name="osd_brightness_slider",
            style_classes="osd_slider",
            orientation="v",
            v_expand=True,
            inverted=True,
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
            name="osd_volume_slider",
            style_classes="osd_slider",
            orientation="v",
            v_expand=True,
            poll=False,
            inverted=True,
        )

        def update_volume_slider(*_):
            self.volume_slider.change_value(
                float(self.audio_controller.speaker.volume) / 100.0
            )

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
                    if self.audio_controller.speaker.volume > 0
                    else configuration.get_property("volume_off_icon")
                )
            )

        self.volume_toggle = ToggleButton(
            name="osd_volume_toggle",
            h_expand=True,
            v_expand=True,
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
        )

        self.brightness_revealer = Revealer(
            Box(
                name="osd_brightness_container",
                orientation="v",
                children=[
                    self.brightness_slider,
                    Box(
                        name="osd_icon_container",
                        children=self.brightness_icon,
                        h_expand=True,
                        v_expand=True,
                    ),
                ],
            ),
            transition_type="slide-left",
            transition_duration=configuration.get_property(
                "osd_revealer_animation_duration"
            ),
            child_revealed=True,
        )

        self.volume_revealer = Revealer(
            Box(
                name="osd_volume_container",
                orientation="v",
                children=[
                    self.volume_slider,
                    Box(
                        name="osd_icon_container",
                        children=self.volume_toggle,
                        h_expand=True,
                        v_expand=True,
                    ),
                ],
            ),
            transition_type="slide-left",
            transition_duration=configuration.get_property(
                "osd_revealer_animation_duration"
            ),
            child_revealed=True,
        )

        self.main_container = Box(
            name="osd_container",
            children=[self.volume_revealer, self.brightness_revealer],
        )
        #     name="osd_main_box",
        #     orientation="v",
        #     children=[
        #         Box(
        #             children=[
        #                 Box(h_expand=True),
        #                 Box(
        #                     name="osd_corner_container",
        #                     children=Corner(
        #                         name="corner",
        #                         h_expand=True,
        #                         v_expand=True,
        #                         orientation="bottom-right",
        #                     ),
        #                 ),
        #             ]
        #         ),
        #         Box(
        #             name="osd_container",
        #             children=[self.volume_revealer, self.brightness_revealer],
        #         ),
        #         Box(
        #             children=[
        #                 Box(h_expand=True),
        #                 Box(
        #                     name="osd_corner_container",
        #                     children=Corner(
        #                         name="corner",
        #                         h_expand=True,
        #                         v_expand=True,
        #                         orientation="top-right",
        #                     ),
        #                 ),
        #             ]
        #         ),
        #     ],
        # )

        self.volume_slider.connect(
            "enter-notify-event", lambda *_: self.on_mouse_enter()
        )
        self.volume_slider.connect(
            "leave-notify-event", lambda *_: self.on_mouse_leave()
        )
        self.volume_toggle.connect(
            "enter-notify-event", lambda *_: self.on_mouse_enter()
        )
        self.volume_toggle.connect(
            "leave-notify-event", lambda *_: self.on_mouse_leave()
        )

        self.brightness_slider.connect(
            "enter-notify-event", lambda *_: self.on_mouse_enter()
        )
        self.brightness_slider.connect(
            "leave-notify-event", lambda *_: self.on_mouse_leave()
        )
        self.brightness_icon.connect(
            "enter-notify-event", lambda *_: self.on_mouse_enter()
        )
        self.brightness_icon.connect(
            "leave-notify-event", lambda *_: self.on_mouse_leave()
        )

        self.add(self.main_container)
        self.show_all()

        self.hide_brightness_slider()
        self.hide_volume_slider()

    def on_mouse_enter(self):
        if self.brightness_handle:
            self.brightness_handle.force_exit()
        if self.volume_handle:
            self.volume_handle.force_exit()

    def on_mouse_leave(self):
        if self.brightness_revealer.child_revealed:
            (self.brightness_handle, _) = exec_shell_command_async(
                f"sh -c 'sleep {configuration.get_property('osd_timeout')}; fabric-cli execute {configuration.get_property('app_name')} \"osd_window.hide_brightness_slider()\"'"
            )

        if self.volume_revealer.child_revealed:
            (self.volume_handle, _) = exec_shell_command_async(
                f"sh -c 'sleep {configuration.get_property('osd_timeout')}; fabric-cli execute {configuration.get_property('app_name')} \"osd_window.hide_volume_slider()\"'"
            )

    def show_brightness_slider(self):
        logger.debug("Showing brightness OSD")
        self.brightness_revealer.reveal()
        self.on_show_hide()

        if self.brightness_handle is not None:
            self.brightness_handle.force_exit()

        if not self.hovered:
            (self.brightness_handle, _) = exec_shell_command_async(
                f"sh -c 'sleep {configuration.get_property('osd_timeout')}; fabric-cli execute {configuration.get_property('app_name')} \"osd_window.hide_brightness_slider()\"'"
            )

    def show_volume_slider(self):
        logger.debug("Showing volume OSD")
        self.volume_revealer.reveal()
        self.on_show_hide()

        if self.volume_handle is not None:
            self.volume_handle.force_exit()

        if not self.hovered:
            (self.volume_handle, _) = exec_shell_command_async(
                f"sh -c 'sleep {configuration.get_property('osd_timeout')}; fabric-cli execute {configuration.get_property('app_name')} \"osd_window.hide_volume_slider()\"'"
            )

    def hide_brightness_slider(self):
        logger.debug("Hiding brightness OSD")
        self.brightness_revealer.unreveal()
        self.brightness_handle = None
        self.on_show_hide()

    def hide_volume_slider(self):
        logger.debug("Hiding volume OSD")
        self.volume_revealer.unreveal()
        self.volume_handle = None
        self.on_show_hide()

    def on_show_hide(self):
        if (
            not self.volume_revealer.child_revealed
            and not self.brightness_revealer.child_revealed
        ):
            if self.revealed:
                self.revealed = False
                self.main_container.remove_style_class("revealed")
                logger.debug("Hiding OSD window")
        else:
            if not self.revealed:
                self.revealed = True
                self.main_container.add_style_class("revealed")
                logger.debug("Showing OSD window")

    @cooldown(0.1, lambda *_: logger.error("cooldown reached"))
    def inc_volume(self):
        self.audio_controller.speaker.volume += configuration.get_property(
            "osd_volume_delta"
        )
        self.show_volume_slider()

    @cooldown(0.1, lambda *_: logger.error("cooldown reached"))
    def dec_volume(self):
        self.audio_controller.speaker.volume -= configuration.get_property(
            "osd_volume_delta"
        )
        self.show_volume_slider()

    @cooldown(0.1, lambda *_: logger.error("cooldown reached"))
    def volume_mute_toggle(self):
        self.audio_controller.speaker.muted = not self.audio_controller.speaker.muted
        self.show_volume_slider()

    @cooldown(0.1, lambda *_: logger.error("cooldown reached"))
    def inc_brightness(self):
        formatted_exec_shell_command_async(
            configuration.get_property("brightness_inc_command"),
            device=self.backlight_device,
            delta=f"{configuration.get_property('osd_brightness_delta')}%",
        )
        self.show_brightness_slider()

    @cooldown(0.1, lambda *_: logger.error("cooldown reached"))
    def dec_brightness(self):
        formatted_exec_shell_command_async(
            configuration.get_property("brightness_dec_command"),
            device=self.backlight_device,
            delta=f"{configuration.get_property('osd_brightness_delta')}%",
        )
        self.show_brightness_slider()


class UrgentOSDs(Enum):
    BATTERY = 0


class UrgentOSDWindow(Window):
    def __init__(self, *args, **kwargs):
        super().__init__(
            name="urgent_osd_window",
            anchor="top right bottom left",
            exclusivity="normal",
            layer="overlay",
            visible=False,
            margin="-100px 0px 0px 0px",
            *args,
            **kwargs,
        )
        self.osd_shown = False
        self.active_osd = None

        self.battery_osd = UrgentBatteryOSD()

        self.battery_osd.confirm_button.connect(
            "clicked", lambda *_: self.hide_urgent_osd()
        )

        self.osds = {
            UrgentOSDs.BATTERY: self.battery_osd,
        }

        self.stack = Stack(
            transition_type="none",
            children=[self.battery_osd],
            h_align="center",
            v_align="center",
        )

        self.add(self.stack)

        self.add_keybinding(
            "Escape",
            lambda *_: self.handle_esc(),
        )

        self.add_keybinding(
            "Return",
            lambda *_: self.handle_enter(),
        )

        self.add_keybinding(
            "Right",
            lambda _, event_key: self.handle_arrow_keys(event_key),
        )
        self.add_keybinding(
            "Left",
            lambda _, event_key: self.handle_arrow_keys(event_key),
        )
        self.add_keybinding(
            "Up",
            lambda _, event_key: self.handle_arrow_keys(event_key),
        )
        self.add_keybinding(
            "Down",
            lambda _, event_key: self.handle_arrow_keys(event_key),
        )

    def handle_esc(self):
        match self.active_osd:
            case _:
                return False

    def handle_enter(self):
        match self.active_osd:
            case UrgentOSDs.BATTERY:
                self.battery_osd.confirm_button.clicked()
            case _:
                return False

        return True

    def handle_arrow_keys(self, event_key):
        match event_key.keyval:
            case 65363:  # right arrow
                pass
            case 65361:  # left arrow
                pass
            case 65362:  # up arrow
                pass
            case 65364:  # down arrow
                pass

        return False

    def show_urgent_osd(self, osd):
        if self.osd_shown:
            return False

        if osd == "battery" or osd == UrgentOSDs.BATTERY:
            osd = UrgentOSDs.BATTERY
        else:
            return False

        self.remove_style_class("empty")
        self.add_style_class(osd.name.lower())
        self.stack.set_visible_child(self.osds[osd])

        self.osd_shown = True
        self.active_osd = osd
        self.show_all()
        self.steal_input()

        logger.info(f"Showing {osd.name.lower()} urgent osd!")

        return True

    def hide_urgent_osd(self):
        if not self.osd_shown:
            return False

        for osd in self.osds.keys():
            self.remove_style_class(osd.name.lower())
        self.add_style_class("empty")

        self.osd_shown = False
        self.hide()
        self.return_input()

        logger.info("Hiding urgent osd!")

        return True


class UrgentBatteryOSD(Box):
    def __init__(self, *args, **kwargs):
        super().__init__(
            name="urgent_battery_osd",
            orientation="v",
            h_align="center",
            v_align="center",
            *args,
            **kwargs,
        )

        self.title = Label(
            name="battery_osd_title",
            label="Low Battery",
            h_align="start",
            h_expand=True,
        )
        self.description = Label(
            name="battery_osd_description",
            label=f"Battery level is below {configuration.get_property('battery_warning_level')}%",
            h_align="start",
            h_expand=True,
        )
        self.confirm_button = MarkupButton(
            name="battery_osd_confirm",
            markup=configuration.get_property("confirm_icon"),
        )
        self.confirm_button.set_can_focus(False)

        self.children = [
            self.title,
            self.description,
            Box(v_expand=True),
            Box(
                children=[
                    Box(h_expand=True),
                    self.confirm_button,
                ]
            ),
        ]
