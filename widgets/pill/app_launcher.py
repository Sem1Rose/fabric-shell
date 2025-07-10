import json
import os
import gi
from loguru import logger
from xdg.DesktopEntry import DesktopEntry
from config import configuration

from widgets.grid import Grid
from widgets.pill.applet import Applet

from fabric.utils import exec_shell_command_async
from fabric.widgets.entry import Entry
from fabric.widgets.box import Box
from fabric.core.service import Signal
from fabric.utils.helpers import get_desktop_applications, DesktopApp


gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, GObject, Gio, GLib

class AppLauncher(Applet, Box):
    @Signal
    def on_launched(self): ...

    def __init__(self, *args, **kwargs):
        Box.__init__(
            self,
            name="pill_app_launcher",
            orientation="v",
            *args,
            **kwargs,
        )

        try:
            with open('app_launcher_history') as history_data:
                self.history = json.load(history_data)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"Error while reading app launcher history file: {e}")
            self.history: dict[str, int] = {}

        self.entry = Entry(placeholder="Search for apps", name="app_launcher_entry")
        self.entry.grab_focus_without_selecting()

        self.entry.connect("key-press-event", self.handle_key_press_event)
        self.entry.connect(
            "changed",
            lambda entry, *_: self.app_grid.filter_items(entry.get_text()),
        )
        self.entry.connect("activate", lambda *_: True)

        self.app_grid = Grid(
            columns=configuration.get_property("app_launcher_columns"),
            rows=configuration.get_property("app_launcher_rows"),
            items_fetcher=get_desktop_applications,
            item_sort_name_fetcher=lambda app: f"{app.name} {app.generic_name} {app.display_name} {app.description}",
            item_factory=lambda item: (
                item.display_name,
                item.get_icon_pixbuf(
                    size=configuration.get_property("app_launcher_icon_size")
                ),
            ),
            sort_function=lambda item: self.history[item.name] if self.history.__contains__(item.name) else 0,
        )

        self.app_grid.connect("on_item_clicked", lambda *_: self.select_app())

        self.children = [self.entry, self.app_grid]

    def handle_key_press_event(self, entry: Entry, event):
        match event.keyval:
            case 65363:  # right arrow
                # self.app_grid.inc_selection()
                return True
            case 65361:  # left arrow
                # self.app_grid.dec_selection()
                return True
            case 65362:  # up arrow
                # self.app_grid.dec_selection_row()
                return True
            case 65364:  # down arrow
                # self.app_grid.inc_selection_row()
                return True

        return False

    def handle_arrow_keys(self, event):
        match event.keyval:
            case 65363:  # right arrow
                self.app_grid.inc_selection()
            case 65361:  # left arrow
                self.app_grid.dec_selection()
            case 65362:  # up arrow
                self.app_grid.dec_selection_row()
            case 65364:  # down arrow
                self.app_grid.inc_selection_row()

        return False

    def select_app(self):
        app = self.app_grid.items[self.app_grid.selected_item]
        logger.error(app._app.get_executable())

        terminal = False
        desktop_app_properties = DesktopEntry(app._app.get_filename())
        if desktop_app_properties.getTerminal():
            terminal = True
            if (e:=desktop_app_properties.getTryExec()):
                logger.error(f"TryExec: {e}")
                exec = (
                    e
                    .replace("%u", "")
                    .replace("%U", "")
                    .replace("%f", "")
                    .replace("%F", "")
                    .replace("%i", "")
                    .replace("%c", "")
                    .replace("%k", "")
                    .strip()
                )
            else:
                logger.error(f"Exec: {desktop_app_properties.getExec()}")
                exec = (
                    desktop_app_properties.getExec()
                    .replace("%u", "")
                    .replace("%U", "")
                    .replace("%f", "")
                    .replace("%F", "")
                    .replace("%i", "")
                    .replace("%c", "")
                    .replace("%k", "")
                    .strip()
                )
        try:
            logger.info(f"Launching {app.name}...")
            if terminal:
                exec_shell_command_async(f"uwsm app -- kitty -d ~ --detach {exec}")
            else:
                app.launch()

            if self.history.__contains__(app.name):
                self.history[app.name] -= 1
            else:
                self.history[app.name] = -1

            with open('app_launcher_history', "w") as file:
                file.write(json.dumps(self.history))

            self.on_launched()
        except Exception as e:
            logger.error(f"Error while trying to launch {app.name}: {e}...")

    def unhide(self, *args):
        Applet.unhide(self, *args)

        self.app_grid.reset_items()
        self.entry.set_text("")
        self.entry.grab_focus()
