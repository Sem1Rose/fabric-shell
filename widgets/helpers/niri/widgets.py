import gi
import re
import json

from loguru import logger
from collections.abc import Iterable, Callable
from typing import Literal

from fabric.core.service import Property
from fabric.hyprland.widgets import WorkspaceButton
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.eventbox import EventBox
from fabric.utils.helpers import bulk_connect

from widgets.helpers.niri.service import Niri, NiriEvent

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk

connection: Niri | None = None

def get_niri_connection() -> Niri:
    global connection
    if not connection:
        connection = Niri()

    return connection

class Workspaces(EventBox):
    @staticmethod
    def default_buttons_factory(workspace_id: int):
        return WorkspaceButton(id=workspace_id, label=str(workspace_id))

    def __init__(
        self,
        buttons: Iterable[WorkspaceButton] | None = None,
        buttons_factory: Callable[[int], WorkspaceButton | None]
        | None = default_buttons_factory,
        invert_scroll: bool = False,
        empty_scroll: bool = False,
        static_workspace_buttons: bool = False,
        **kwargs,
    ):
        super().__init__(events="scroll")
        self.connection = get_niri_connection()
        self._container = Box(**kwargs)
        self.children = self._container

        self._static_workspace_buttons = static_workspace_buttons
        self._active_workspace: int | None = None
        self._buttons: dict[int, WorkspaceButton] = {}
        self._buttons_preset: list[WorkspaceButton] = list(buttons or [])
        self._buttons_factory = buttons_factory
        self._invert_scroll = invert_scroll
        self._empty_scroll = empty_scroll

        bulk_connect(
            self.connection,
            {
                "event::WorkspaceActivated": self.on_workspace,
                "event::WorkspacesChanged": self.on_workspace,
                "event::WorkspaceUrgencyChanged": self.on_workspace_urgent,
            },
        )

        if self.connection.ready:
            self.on_ready(None)
        else:
            self.connection.connect("event::ready", self.on_ready)

        self.connect("scroll-event", self.scroll_handler)

    def on_ready(self, _):
        response = self.connection.send_command("Workspaces").reply
        json_data = self.parse_niri_response(response)
        if not json_data:
            return

        workspaces = json_data.get("Workspaces", [])

        if self._static_workspace_buttons:
            for btn in self._buttons_preset:
                self.insert_button(btn)

        self.sync_workspaces(workspaces)

        active = self.check_active_workspace_niri(json_data)
        if active:
            self._active_workspace = active["idx" if self._static_workspace_buttons else "id"]
            if (btn := self._buttons.get(self._active_workspace)):
                btn.active = True

    def on_workspace(self, _, event: NiriEvent):
        logger.debug(f"[EVENT] on_workspace: {event.data}")

        response = self.connection.send_command("Workspaces").reply
        json_data = self.parse_niri_response(response)
        if not json_data:
            return

        workspaces = json_data.get("Workspaces", [])
        self.sync_workspaces(workspaces)

        active_ws = self.check_active_workspace_niri(json_data)
        if not active_ws:
            return

        new_active_id = active_ws["idx" if self._static_workspace_buttons else "id"]
        if new_active_id == self._active_workspace:
            return

        if (old := self._buttons.get(self._active_workspace)):
            old.active = False

        self._active_workspace = new_active_id

        if (new := self._buttons.get(new_active_id)):
            new.active = True
            new.urgent = False

    def on_workspace_urgent(self, _, event: NiriEvent):
        urgent_ws = self.check_urgent_workspace_niri(event.data)
        ws_id = urgent_ws.get("idx" if self._static_workspace_buttons else "id")
        if not ws_id:
            return

        if (btn := self._buttons.get(ws_id)):
            btn.urgent = True
            logger.info(f"[Workspaces] workspace {ws_id} is now urgent")

    def scroll_handler(self, _, event: Gdk.EventScroll):
        direction = event.direction

        if direction == Gdk.ScrollDirection.UP:
            cmd = {
                "Action": {
                    "FocusWorkspaceUp": {},
                },
            }

            self.connection.send_command(cmd)
            logger.info("[Workspaces] Moving to the workspace above")
        elif direction == Gdk.ScrollDirection.DOWN:
            cmd = {
                "Action": {
                    "FocusWorkspaceDown": {},
                },
            }

            logger.info("[Workspaces] Moving to the workspace below")
            self.connection.send_command(cmd)
        else:
            logger.warning(f"[Workspaces] Unknown sLayoutSwitchTargetcroll direction ({direction})")
            return

    def sync_workspaces(self, fresh_data: list[dict]) -> None:
        """
        Sync internal workspace buttons with the latest workspace data.
        Adds new buttons, updates existing ones, and removes stale ones.
        """
        key = "idx" if self._static_workspace_buttons else "id"
        fresh_ids = {ws[key] for ws in fresh_data if key in ws}

        # Add/update buttons
        for ws in fresh_data:
            btn = self.lookup_or_bake_button(ws[key])
            if not btn:
                continue

            btn.empty = False
            btn.active = ws.get("is_active", False)

            if btn not in self._buttons:
                self.insert_button(btn)

        # Remove old buttons
        for id_, btn in list(self._buttons.items()):
            if id_ not in fresh_ids:
                if self._static_workspace_buttons and btn in self._buttons_preset:
                    btn.active = False
                    btn.empty = True
                else:
                    self.remove_button(btn)

    def insert_button(self, button: WorkspaceButton) -> None:
        self._buttons[button.id] = button
        self._container.add(button)
        button.connect("clicked", self.on_workspace_button_clicked)
        self.reorder_buttons()

    def remove_button(self, button: WorkspaceButton) -> None:
        if self._buttons.pop(button.id, None):
            self._container.remove(button)
        button.destroy()

    def reorder_buttons(self):
        for pos, btn in enumerate(sorted(self._buttons.values(), key=lambda b: b.id)):
            self._container.reorder_child(btn, pos)

    def lookup_or_bake_button(self, workspace_id: int) -> WorkspaceButton | None:
        return self._buttons.get(workspace_id) or (
            self._buttons_factory(workspace_id) if self._buttons_factory else None
        )

    def on_workspace_button_clicked(self, button: WorkspaceButton):
        key = "Index" if self._static_workspace_buttons else "Id"
        cmd = {"Action": {"FocusWorkspace": {"reference": {key: button.id}}}}
        self.connection.send_command(cmd)
        logger.info(f"[Workspaces] Moved to workspace {button.id}")

    def parse_niri_response(self, json_data: dict) -> dict | None:
        if "Err" in json_data:
            logger.warning(f"[Niri] Error: {json_data['Err']}")
            return

        ok_data = json_data.get("Ok")
        if not isinstance(ok_data, dict) or len(ok_data) != 1:
            logger.warning(f"[Niri] Unexpected response: {json_data}")
            return

        return ok_data

    def check_active_workspace_niri(self, json_data: dict) -> dict | None:
        for key in ("Workspaces", "workspaces"):
            for ws in json_data.get(key, []):
                if ws.get("is_active"):
                    return ws
        return None

    def check_urgent_workspace_niri(self, json_data: dict) -> dict:
        return json_data.get("WorkspaceUrgencyChanged", {})

class Language(Button):
    def __init__(
        self,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.connection = get_niri_connection()
        self._keyboard_layouts = []

        bulk_connect(
            self.connection,
            {
                "event::KeyboardLayoutsChanged": self.on_layout_changed,
                "event::KeyboardLayoutSwitched": self.on_layout_switched,
            },
        )

        if self.connection.ready:
            self.on_ready(None)
        else:
            self.connection.connect("event::ready", self.on_ready)

        self.connect("scroll-event", self.scroll_handler)

    def on_ready(self, _):
        return self.do_initialize(), logger.info(
            "[Language] Connected to the Niri socket"
        )

    def on_layout_changed(self, _, event: NiriEvent):
        logger.error(event.data)

        data = event.data["keyboard_layouts"]
        names = data["names"]
        current_idx = data["current_idx"]
        current_layout = names[current_idx]

        logger.debug(current_layout)
        return self.set_label(current_layout)

    def on_layout_switched(self, _, event: NiriEvent):
        logger.error(event.data)

        current_idx = event.data.get("idx", None)

        if current_idx is None:
            return self.do_initialize()

        return self.set_label(self._keyboard_layouts[current_idx])

    def do_initialize(self):
        keyboard_layouts = self.parse_niri_response(self.connection.send_command("KeyboardLayouts").reply)["KeyboardLayouts"]
        logger.error(keyboard_layouts)

        names = keyboard_layouts["names"]
        current_idx = keyboard_layouts["current_idx"]

        self._keyboard_layouts = names

        current_layout = names[current_idx]
        return self.set_label(current_layout)

    def scroll_handler(self, _, event: Gdk.EventScroll):
        direction = event.direction

        if direction == Gdk.ScrollDirection.UP:
            cmd = {
                "Action": {
                    "SwitchLayout": {
                        "layout": "Next",
                    },
                },
            }

            self.connection.send_command(cmd)
            logger.info("[Language] Changing to the next language")
        elif direction == Gdk.ScrollDirection.DOWN:
            cmd = {
                "Action": {
                    "SwitchLayout": {
                        "layout": "Prev",
                    },
                },
            }

            logger.info("[Language] Changing to the previous language")
            self.connection.send_command(cmd)
        else:
            logger.warning(f"[Language] Unknown scroll direction ({direction})")
            return

    def parse_niri_response(self, json_data: dict) -> dict | None:
        if "Err" in json_data:
            logger.warning(f"[Niri] Error: {json_data['Err']}")
            return

        ok_data = json_data.get("Ok")
        if not isinstance(ok_data, dict) or len(ok_data) != 1:
            logger.warning(f"[Niri] Unexpected response: {json_data}")
            return

        return ok_data
