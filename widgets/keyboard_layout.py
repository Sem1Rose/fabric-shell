import json
import re
from loguru import logger
from collections.abc import Callable
from config import configuration

from fabric.hyprland.widgets import get_hyprland_connection
from fabric.hyprland.widgets import Language
from fabric.hyprland.service import HyprlandEvent

from gi.repository import Gdk


class KeyboardLayout(Language):
    def __init__(
        self, language_formatter: Callable[[str], str] = lambda x: x, *args, **kwargs
    ):
        self.language_formatter = language_formatter
        super().__init__(style_classes="bar_widget", *args, **kwargs)

        self.connect("enter-notify-event", lambda *_: self.cursor_enter())
        self.connect("leave-notify-event", lambda *_: self.cursor_leave())
        self.connect(
            "button-release-event",
            lambda *_: get_hyprland_connection().send_command(
                f"switchxkblayout {configuration.get_property('switchxkblayout_keyboard_name')} next"
            ),
        )

    def on_activelayout(self, _, event: HyprlandEvent):
        if len(event.data) < 2:
            return logger.warning(
                f"[Language] got invalid event data from hyprland, raw data is\n{event.raw_data}"
            )
        keyboard, language = event.data
        matched: bool = False

        if re.match(self.keyboard, keyboard) and (matched := True):
            self.set_label(
                self.language_formatter(self.formatter.format(language=language))
            )

        return logger.debug(
            f"[Language] Keyboard: {keyboard}, Language: {language}, Match: {matched}"
        )

    def do_initialize(self):
        devices: dict[str, list[dict[str, str]]] = json.loads(
            str(self.connection.send_command("j/devices").reply.decode())
        )
        if not devices or not (keyboards := devices.get("keyboards")):
            return logger.warning(
                f"[Language] cound't get devices from hyprctl, gotten data\n{devices}"
            )

        language: str | None = None
        for kb in keyboards:
            if (
                not (kb_name := kb.get("name"))
                or not re.match(self.keyboard, kb_name)
                or not (language := kb.get("active_keymap"))
            ):
                continue

            self.set_label(
                self.language_formatter(self.formatter.format(language=language))
            )
            logger.debug(
                f"[Language] found language: {language} for keyboard {kb_name}"
            )
            break

        return (
            logger.info(
                f"[Language] Could not find language for keyboard: {self.keyboard}, gotten keyboards: {keyboards}"
            )
            if not language
            else logger.info(
                f"[Language] Set language: {language} for keyboard: {self.keyboard}"
            )
        )

    def cursor_enter(self):
        if not self.is_sensitive():
            return

        window = self.get_window()
        if window:
            window.set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))

    def cursor_leave(self):
        if not self.is_sensitive():
            return

        window = self.get_window()
        if window:
            window.set_cursor(None)
