from loguru import logger
from enum import Enum

from config import configuration
from widgets.buttons import MarkupButton

from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.revealer import Revealer

from fabric.core.service import Signal
from fabric.utils.helpers import exec_shell_command, exec_shell_command_async

from gi.repository import GLib


class Actions(Enum):
    LOCK = 0
    SUSPEND = 1
    REBOOT = 2
    SHUT_DOWN = 3


class PowerMenu(Box):
    @Signal
    def on_action(self): ...

    def __init__(self, *args, **kwargs):
        super().__init__(name="pill_power_menu", orientation="v", *args, **kwargs)

        self.selected_action = 0
        self.selected_popup_action = 0

        self.lock_button = MarkupButton(
            name="power_menu_lock",
            style_classes="power_menu_action",
            markup=configuration.get_property("power_menu_action_lock_icon"),
        )
        self.lock_button.set_can_focus(False)
        self.lock_button.connect(
            "clicked",
            lambda _: (self.change_action(0), self.execute_action()),
        )

        self.suspend_button = MarkupButton(
            name="power_menu_suspend",
            style_classes="power_menu_action",
            markup=configuration.get_property("power_menu_action_suspend_icon"),
        )
        self.suspend_button.set_can_focus(False)
        self.suspend_button.connect(
            "clicked",
            lambda _: (self.change_action(1), self.show_confirmation_popup()),
        )

        self.reboot_button = MarkupButton(
            name="power_menu_reboot",
            style_classes="power_menu_action",
            markup=configuration.get_property("power_menu_action_reboot_icon"),
        )
        self.reboot_button.set_can_focus(False)
        self.reboot_button.connect(
            "clicked",
            lambda _: (self.change_action(2), self.show_confirmation_popup()),
        )

        self.shut_down_button = MarkupButton(
            name="power_menu_shut_down",
            style_classes="power_menu_action",
            markup=configuration.get_property("power_menu_action_shut_down_icon"),
        )
        self.shut_down_button.set_can_focus(False)
        self.shut_down_button.connect(
            "clicked",
            lambda _: (self.change_action(3), self.show_confirmation_popup()),
        )

        self.actions_enum = [
            Actions.LOCK,
            Actions.SUSPEND,
            Actions.REBOOT,
            Actions.SHUT_DOWN,
        ]
        self.actions = [
            self.lock_button,
            self.suspend_button,
            self.reboot_button,
            self.shut_down_button,
        ]

        self.actions_container = Box(
            name="power_menu_actions",
            # v_expand=True,
            children=self.actions,
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
                action_id = len(self.actions) - 1
            elif action_id >= len(self.actions):
                action_id = 0

        for action in self.actions:
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
        self.actions[action_id].add_style_class("focused")
        self.selected_action = action_id

    def handle_enter(self):
        if self.confirmation_popup_revealer.get_reveal_child():
            self.popup_actions[self.selected_popup_action].clicked()
        else:
            self.actions[self.selected_action].clicked()

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

    def execute_action(self):
        self.hide_confirmation_popup()
        match self.actions_enum[self.selected_action]:
            case Actions.LOCK:
                commands = " ".join(
                    [
                        f"{command};"
                        for command in configuration.get_property(
                            "power_menu_lock_commands"
                        )
                    ]
                )

                logger.warning("LOCKING")
                exec_shell_command_async(f"sh -c 'sleep 0.5; {commands}'")
            case Actions.SUSPEND:
                pre_suspend_commands = " ".join(
                    [
                        f"{command};"
                        for command in configuration.get_property(
                            "power_menu_suspend_commands"
                        )[:-1]
                    ]
                )
                suspend_command = configuration.get_property(
                    "power_menu_suspend_commands"
                )[-1]

                def suspend():
                    logger.warning("SUSPENDING")
                    exec_shell_command(f"sh -c 'sleep 0.5; {pre_suspend_commands}'")
                    exec_shell_command_async(suspend_command)

                GLib.Thread.new("suspend", suspend)
            case Actions.REBOOT:
                commands = " ".join(
                    [
                        f"{command};"
                        for command in configuration.get_property(
                            "power_menu_reboot_commands"
                        )
                    ]
                )

                logger.warning("REBOOTING")
                exec_shell_command_async(f"sh -c 'sleep 0.5; {commands}'")
            case Actions.SHUT_DOWN:
                commands = " ".join(
                    [
                        f"{command};"
                        for command in configuration.get_property(
                            "power_menu_shutdown_commands"
                        )
                    ]
                )

                logger.warning("SHUTTING DOWN")
                exec_shell_command_async(f"sh -c 'sleep 0.5; {commands}'")

        self.on_action()

    def hide(self, *args):
        self.add_style_class("hidden")

    def unhide(self, *args):
        self.remove_style_class("hidden")
        self.confirmation_popup_revealer.unreveal()
        self.select_action()
