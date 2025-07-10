from enum import Enum
from fabric.utils import idle_add
from loguru import logger
from config import configuration

from widgets.revealer import Revealer
from widgets.brightness_slider import BrightnessSlider
from widgets.volume_slider import VolumeSlider
from widgets.buttons import MarkupButton

from fabric.widgets.wayland import WaylandWindow as Window
from fabric.widgets.label import Label
from fabric.widgets.box import Box
from fabric.widgets.stack import Stack
from fabric.utils.helpers import exec_shell_command_async, cooldown
# from fabric.widgets.eventbox import EventBox
# from fabric.widgets.shapes.corner import Corner

# from widgets.helpers.brightness import get_brightness_service

from gi.repository import GLib


class OSDWindow(Window):
    def __init__(self, *args, **kwargs):
        super().__init__(
            name="osd_window",
            anchor="top right",
            exclusivity="normal",
            layer="overlay",
            visible=False,
            style="background-color: transparent;",
            *args,
            **kwargs,
        )

        # self.hovered = False
        self.revealed = False
        # self.brightness_handle = None
        self.volume_handle = None

        # self.brightness_slider = BrightnessSlider(True, True, orientation="vertical")

        # self.brightness_revealer = Revealer(
        #     self.brightness_slider,
        #     # Box(
        #     #     name="osd_brightness_container",
        #     #     orientation="v",
        #     #     # children=[
        #     #     #     self.brightness_slider,
        #     #     #     Box(
        #     #     #         name="osd_icon_container",
        #     #     #         children=self.auto_brightness_toggle,
        #     #     #         h_expand=True,
        #     #     #         v_expand=True,
        #     #     #     ),
        #     #     # ],
        #     # ),
        #     transition_type="slide-left",
        #     transition_duration=configuration.get_property(
        #         "osd_revealer_animation_duration"
        #     ),
        #     child_revealed=True,
        # )

        self.volume_slider = VolumeSlider(inverted=True, orientation="vertical")
        self.volume_revealer = Revealer(
            self.volume_slider,
            # Box(
            #     style_classes="osd_slider_container",
            #     orientation="v",
            #     children=[
            #         self.volume_slider,
            #         Box(
            #             name="osd_icon_container",
            #             children=self.volume_toggle,
            #             h_expand=True,
            #             v_expand=True,
            #         ),
            #     ],
            # ),
            transition_type="slide-left",
            transition_duration=configuration.get_property(
                "osd_revealer_animation_duration"
            ),
            child_revealed=True,
        )

        self.main_container = Box(
            name="osd_container",
            children=[
                self.volume_revealer,
                # self.brightness_revealer,
            ],
        )

        self.volume_slider.slider.connect(
            "enter-notify-event", lambda *_: self.on_mouse_enter()
        )
        self.volume_slider.slider.connect(
            "leave-notify-event", lambda *_: self.on_mouse_leave()
        )
        self.volume_slider.toggle.connect(
            "enter-notify-event", lambda *_: self.on_mouse_enter()
        )
        self.volume_slider.toggle.connect(
            "leave-notify-event", lambda *_: self.on_mouse_leave()
        )

        # self.brightness_slider.connect(
        #     "enter-notify-event", lambda *_: self.on_mouse_enter()
        # )
        # self.brightness_slider.connect(
        #     "leave-notify-event", lambda *_: self.on_mouse_leave()
        # )
        # self.auto_brightness_toggle.connect(
        #     "enter-notify-event", lambda *_: self.on_mouse_enter()
        # )
        # self.auto_brightness_toggle.connect(
        #     "leave-notify-event", lambda *_: self.on_mouse_leave()
        # )

        self.add(self.main_container)
        self.show_all()

        # self.hide_brightness_slider()
        self.hide_volume_slider()
        # self.on_show_hide()

    def on_mouse_enter(self):
        # if self.brightness_handle:
        #     self.brightness_handle.force_exit()
        if self.volume_handle:
            self.volume_handle.force_exit()

    def on_mouse_leave(self):
        # if self.brightness_revealer.child_revealed:
        #     (self.brightness_handle, _) = exec_shell_command_async(
        #         f"sh -c 'sleep {configuration.get_property('osd_timeout')}; fabric-cli execute {configuration.get_property('app_name')} \"osd_window.hide_brightness_slider()\"'"
        #     )

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

        # if not self.hovered:
        (self.brightness_handle, _) = exec_shell_command_async(
            f"sh -c 'sleep {configuration.get_property('osd_timeout')}; fabric-cli execute {configuration.get_property('app_name')} \"osd_window.hide_brightness_slider()\"'"
        )

    # def hide_volume_slider_timeout(self):
    #     sleep(configuration.get_property("osd_timeout"))
    #     idle_add(self.hide_volume_slider)

    def show_volume_slider(self):
        logger.debug("Showing volume OSD")
        self.volume_revealer.reveal()
        self.on_show_hide()

        if self.volume_handle is not None:
            self.volume_handle.force_exit()

        # if not self.hovered:
            # Doestn't work because "attempt to g_thread_exit() a thread not created by GLib"
            # self.volume_handle = GLib.Thread.new(
            #     "hide_volume_slider", self.hide_volume_slider_timeout
            # )
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
            # and not self.brightness_revealer.child_revealed
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
        if not self.volume_slider.controller.speaker:
            return

        self.volume_slider.controller.speaker.volume += configuration.get_property(
            "osd_volume_delta"
        )
        self.show_volume_slider()

    @cooldown(0.1, lambda *_: logger.error("cooldown reached"))
    def dec_volume(self):
        if not self.volume_slider.controller.speaker:
            return

        self.volume_slider.controller.speaker.volume -= configuration.get_property(
            "osd_volume_delta"
        )
        self.show_volume_slider()

    @cooldown(0.1, lambda *_: logger.error("cooldown reached"))
    def volume_mute_toggle(self):
        if not self.volume_slider.controller.speaker:
            return

        self.volume_slider.controller.speaker.muted = (
            not self.volume_slider.controller.speaker.muted
        )
        self.show_volume_slider()

    @cooldown(0.1, lambda *_: logger.error("cooldown reached"))
    def inc_brightness(self):
        # formatted_exec_shell_command_async(
        #     configuration.get_property("brightness_inc_command"),
        #     device=self.backlight_device,
        #     delta=f"{configuration.get_property('osd_brightness_delta')}%",
        # )
        return

        if not self.brightness_slider.service.active:
            return

        # self.brightness_slider.inc_brightness(
        #     configuration.get_property("osd_brightness_delta")
        # )

        self.brightness_slider.service.screen_brightness += configuration.get_property(
            "osd_brightness_delta"
        )

        self.show_brightness_slider()

    @cooldown(0.1, lambda *_: logger.error("cooldown reached"))
    def dec_brightness(self):
        # formatted_exec_shell_command_async(
        #     configuration.get_property("brightness_dec_command"),
        #     device=self.backlight_device,
        #     delta=f"{configuration.get_property('osd_brightness_delta')}%",
        # )
        return

        if not self.brightness_slider.service.active:
            return

        # self.brightness_slider.dec_brightness(
        #     configuration.get_property("osd_brightness_delta")
        # )

        self.brightness_slider.service.screen_brightness -= configuration.get_property(
            "osd_brightness_delta"
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
