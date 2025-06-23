from loguru import logger
from enum import IntEnum

from config import configuration
from widgets.buttons import MarkupButton
from widgets.pill.applet import Applet

from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.revealer import Revealer

from fabric.core.service import Signal
from fabric.utils.helpers import exec_shell_command, exec_shell_command_async

from gi.repository import GLib


class Actions(IntEnum):
    LOCK = 0
    SUSPEND = 1
    REBOOT = 2
    SHUT_DOWN = 3


class PowerMenu(Applet, Box):
    BUTTONS = [
        Actions.LOCK,
        Actions.SUSPEND,
        Actions.REBOOT,
        Actions.SHUT_DOWN,
    ]

    @Signal
    def on_action(self): ...

    def __init__(self, *args, **kwargs):
        Box.__init__(
            self,
            name="pill_power_menu",
            style_classes="pill_applet",
            orientation="v",
            *args,
            **kwargs,
        )

        self.selected_action = Actions.LOCK
        self.selected_popup_action = Actions.LOCK

        self.lock_button = MarkupButton(
            name="power_menu_lock",
            style_classes="power_menu_action",
            markup=configuration.get_property("power_menu_action_lock_icon"),
        )
        # self.lock_button.set_can_focus(False)
        # self.lock_button.set_focus_on_click(False)

        self.suspend_button = MarkupButton(
            name="power_menu_suspend",
            style_classes="power_menu_action",
            markup=configuration.get_property("power_menu_action_suspend_icon"),
        )
        # self.suspend_button.set_can_focus(False)
        # self.suspend_button.set_focus_on_click(False)

        self.reboot_button = MarkupButton(
            name="power_menu_reboot",
            style_classes="power_menu_action",
            markup=configuration.get_property("power_menu_action_reboot_icon"),
        )
        # self.reboot_button.set_can_focus(False)
        # self.reboot_button.set_focus_on_click(False)

        self.shut_down_button = MarkupButton(
            name="power_menu_shut_down",
            style_classes="power_menu_action",
            markup=configuration.get_property("power_menu_action_shut_down_icon"),
        )
        # self.shut_down_button.set_can_focus(False)
        # self.shut_down_button.set_focus_on_click(False)

        self.action_buttons = [
            self.lock_button,
            self.suspend_button,
            self.reboot_button,
            self.shut_down_button,
        ]

        for i, b in enumerate(self.action_buttons):
            # logger.error(f"{i}: {b} {PowerMenu.ACTIONS[i]}")
            b.set_can_focus(False)
            b.set_focus_on_click(False)

            b.connect(
                "clicked",
                lambda button: self.change_action(
                    PowerMenu.BUTTONS[self.action_buttons.index(button)]
                ),
            )
            if i == 0:
                b.connect(
                    "clicked",
                    lambda _: self.execute_action(),
                )
            else:
                b.connect(
                    "clicked",
                    lambda _: self.show_confirmation_popup(),
                )

        self.actions_container = Box(
            name="power_menu_actions",
            # v_expand=True,
            children=self.action_buttons,
        )
        self.actions_container.set_homogeneous(True)

        self.popup_window_action_confirm = MarkupButton(
            name="power_menu_confirm_button", markup="OK"
        )
        self.popup_window_action_confirm.set_can_focus(False)
        self.popup_window_action_confirm.connect(
            "clicked", lambda *_: self.execute_action()
        )

        self.popup_window_action_cancel = MarkupButton(
            name="power_menu_cancel_button", markup="Cancel"
        )
        self.popup_window_action_cancel.set_can_focus(False)
        self.popup_window_action_cancel.connect(
            "clicked", lambda *_: self.hide_confirmation_popup()
        )

        self.popup_actions = [
            self.popup_window_action_confirm,
            self.popup_window_action_cancel,
        ]

        self.confirmation_popup = Box(
            name="power_menu_confirmation_container",
            orientation="v",
            children=[
                Label(
                    name="power_menu_confirmation_label",
                    label="Are you sure?",
                    h_expand=True,
                    h_align="start",
                ),
                Box(v_expand=True),
                Box(
                    # orientation="h",
                    # h_expand=True,
                    children=[
                        Box(h_expand=True),
                        self.popup_window_action_confirm,
                        self.popup_window_action_cancel,
                    ],
                ),
            ],
        )

        self.confirmation_popup_revealer = Revealer(
            name="power_menu_confirmation_revealer",
            child=self.confirmation_popup,
            transition_type="slide-down",
            transition_duration=configuration.get_property(
                "pill_revealer_animation_duration"
            ),
        )

        self.children = [
            self.actions_container,
            self.confirmation_popup_revealer,
        ]

        self.select_action()

    def select_action(self, action_id=0):
        if self.confirmation_popup_revealer.get_reveal_child():
            if 0 > action_id:
                action_id = len(self.popup_actions) - 1
            elif action_id >= len(self.popup_actions):
                action_id = 0
        else:
            if 0 > action_id:
                action_id = len(self.action_buttons) - 1
            elif action_id >= len(self.action_buttons):
                action_id = 0

        for action in self.action_buttons:
            action.remove_style_class("focused")
        for popup_action in self.popup_actions:
            popup_action.remove_style_class("focused")

        if self.confirmation_popup_revealer.get_reveal_child():
            self.change_action(self.selected_action)

            self.popup_actions[action_id].add_style_class("focused")
            self.selected_popup_action = action_id
        else:
            self.change_action(action_id)

    def change_action(self, action_id=0):
        self.action_buttons[action_id].add_style_class("focused")
        self.selected_action = action_id

    def handle_enter(self):
        if self.confirmation_popup_revealer.get_reveal_child():
            self.popup_actions[self.selected_popup_action].clicked()
        else:
            self.action_buttons[self.selected_action].clicked()

    def navigate_actions(self, event_key):
        match event_key.keyval:
            case 65363:  # right arrow
                if self.confirmation_popup_revealer.get_reveal_child():
                    self.select_action(self.selected_popup_action + 1)
                else:
                    self.select_action(self.selected_action + 1)
            case 65361:  # left arrow
                if self.confirmation_popup_revealer.get_reveal_child():
                    self.select_action(self.selected_popup_action - 1)
                else:
                    self.select_action(self.selected_action - 1)
            case 65362:  # up arrow
                self.select_action(0)
            case 65364:  # down arrow
                self.select_action(-1)
            case _:
                return False
        return True

    def handle_esc(self):
        if self.confirmation_popup_revealer.get_reveal_child():
            self.hide_confirmation_popup()
            return True

        return False

    def show_confirmation_popup(self):
        self.confirmation_popup_revealer.reveal()
        self.select_action()

    def hide_confirmation_popup(self):
        self.confirmation_popup_revealer.unreveal()
        self.select_action(self.selected_action)

    def execute_action(self, action: Actions | None = None):
        action = action if action is not None else self.selected_action

        self.hide_confirmation_popup()
        match action:
            case Actions.LOCK:
                lock_commands = " ".join(
                    [
                        f"{command};"
                        for command in configuration.get_property(
                            "power_menu_lock_commands"
                        )
                    ]
                )

                logger.warning("LOCKING")
                exec_shell_command_async(f"sh -c 'sleep 0.5; {lock_commands}'")
            case Actions.SUSPEND:
                lock_commands = " ".join(
                    [
                        f"{command};"
                        for command in configuration.get_property(
                            "power_menu_lock_commands"
                        )
                    ]
                )
                suspend_commands = configuration.get_property(
                    "power_menu_suspend_commands"
                )

                def suspend():
                    exec_shell_command(f"sh -c 'sleep 0.5; {lock_commands}'")
                    exec_shell_command(suspend_commands)

                logger.warning("SUSPENDING")
                GLib.Thread.new("suspend", suspend)
            case Actions.REBOOT:
                pre_shutdown_commands = None

                if pre_shutdown_commands_raw := configuration.get_property(
                    "power_menu_pre_shutdown_commands"
                ):
                    pre_shutdown_commands = " ".join(
                        [f"{command};" for command in pre_shutdown_commands_raw]
                    )

                reboot_commands = " ".join(
                    [
                        f"{command};"
                        for command in configuration.get_property(
                            "power_menu_reboot_commands"
                        )
                    ]
                )

                def reboot():
                    if pre_shutdown_commands is not None:
                        exec_shell_command(f"timeout 3 sh -c '{pre_shutdown_commands}'")
                    exec_shell_command_async(f"sh -c 'sleep 0.5; {reboot_commands}'")

                logger.warning("REBOOTING")
                GLib.Thread.new("reboot", reboot)
            case Actions.SHUT_DOWN:
                pre_shutdown_commands = None

                if pre_shutdown_commands_raw := configuration.get_property(
                    "power_menu_pre_shutdown_commands"
                ):
                    pre_shutdown_commands = " ".join(
                        [f"{command};" for command in pre_shutdown_commands_raw]
                    )

                shutdown_commands = " ".join(
                    [
                        f"{command};"
                        for command in configuration.get_property(
                            "power_menu_shutdown_commands"
                        )
                    ]
                )

                def shutdown():
                    if pre_shutdown_commands is not None:
                        exec_shell_command(f"timeout 3 sh -c '{pre_shutdown_commands}'")
                    exec_shell_command_async(f"sh -c 'sleep 0.5; {shutdown_commands}'")

                logger.warning("SHUTTING DOWN")
                GLib.Thread.new("shutdown", shutdown)

        self.on_action()

    def unhide(self, *args):
        Applet.unhide(self, *args)

        self.confirmation_popup_revealer.unreveal()
        self.select_action()
