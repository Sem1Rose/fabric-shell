import json
import gi
import random
from time import sleep
from typing import Any, Self
from loguru import logger
from xdg.DesktopEntry import DesktopEntry
from config import configuration

from fabric.widgets.image import Image
from fabric.widgets.box import Box
from fabric.widgets.wayland import WaylandWindow as Window

from fabric.utils import DesktopApp, exec_shell_command_async, idle_add

from widgets.buttons import Button
from widgets.helpers.clients import get_clients_service, Client
from widgets.helpers.workspace_properties import get_workspace_properties_service

gi.require_version("Glace", "0.1")
from gi.repository import GLib  # noqa: E402


class DockWindow(Window):
    instances: list[Self] = []

    def __init__(self, *args, **kwargs):
        super().__init__(
            anchor="bottom",
            exclusivity="none",
            layer="top",
            style="background-color: transparent;",
            visible=False,
            *args,
            **kwargs,
        )

        self.hovored = False
        self.hide_ticket = 0
        self.height = 0
        self.width = 0

        self.dock_items_pos: list[DockItem] = []
        self.dock_items: dict[Any, DockItem] = {}
        self.pinned_items_pos: list[PinnedDockItem] = []
        self.pinned_items: dict[str, PinnedDockItem] = {}
        self.loaded_pinned_desktop_apps: list[DesktopApp] = []

        self.main_container_empty = True
        self.main_container = Box(name="dock_container")
        self.pinned_separator = Box(
            name="dock_pinned_separator", v_align="center", style_classes="hidden"
        )
        self.pinned_container_empty = True
        self.pinned_container = Box(name="dock_pinned_container")

        self.dock = Box(
            name="dock",
            children=[
                self.pinned_container,
                self.pinned_separator,
                self.main_container,
            ],
        )

        self.add(Box(style="min-width: 1px; min-height: 1px;", children=self.dock))

        self.show_all()
        DockWindow.instances.append(self)

        self.clients_service = get_clients_service()
        self.clients_service.connect("client-added", self.on_client_added)
        self.clients_service.connect("client-removed", self.on_client_removed)

        self.load_pinned_items()

        if configuration.get_property("dock_visibility_rule") == "hide when obstructed":
            self.workspace_props_service = get_workspace_properties_service()

            # get_hyprland_connection().connect("event", lambda *_: self.check_obstructed())
            # self.workspace_props_service.connect(
            #     "props-recalculated", lambda *_: self.check_obstructed()
            # )
            GLib.timeout_add(100, self.check_obstructed)
            self.check_obstructed()

        self.connect("enter-notify-event", lambda *_: self.on_mouse_enter())
        self.connect("leave-notify-event", lambda *_: self.on_mouse_leave())

    def load_pinned_items(self):
        try:
            with open("dock_pinned_items") as pinned_identifiers:
                pinned_identifiers = json.load(pinned_identifiers)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"Error while reading pinned dock apps file: {e}")

            with open("dock_pinned_items", "w") as file:
                file.write("")

            return

        for identifier in list(set(pinned_identifiers)):
            app = self.clients_service.find_app_by_identifier(identifier)
            if app:
                self.add_pinned_item(identifier, app)

        with open("dock_pinned_items", "w") as file:
            file.write(json.dumps(list(self.pinned_items.keys())))

    def add_pinned_item(self, identifier, item: DesktopApp):
        if item in self.loaded_pinned_desktop_apps:
            logger.error(f"Item already pinned: {identifier}")
            return

        self.loaded_pinned_desktop_apps.append(item)

        item = PinnedDockItem(item)
        item.connect(
            "enter-notify-event", lambda item, *_: self.handle_item_hovered(item, True)
        )
        item.connect(
            "leave-notify-event",
            lambda item, *_: self.handle_item_unhovered(item, True),
        )

        self.pinned_items[identifier] = item
        self.pinned_items_pos.append(item)
        self.pinned_container.add(item)

        item.add_style_class("shown")

        if configuration.get_property(
            "dock_visibility_rule"
        ) != "always visible" and configuration.get_property("dock_flash_on_app_added"):
            self.on_mouse_enter()
            self.on_mouse_leave()
        elif configuration.get_property("dock_visibility_rule") == "always visible":
            self.dock.add_style_class("shown")

        self.pinned_container_empty = False
        if self.main_container_empty:
            self.pinned_separator.add_style_class("hidden")
        else:
            self.pinned_separator.remove_style_class("hidden")

        with open("dock_pinned_items", "w") as file:
            file.write(json.dumps(list(self.pinned_items.keys())))

    def remove_pinned_item(self, item):
        if isinstance(item, str):
            if not self.pinned_items.__contains__(item):
                logger.error(f"Item not pinned: {item}")
                return

            identifier = item
            item = self.pinned_items[item]
        elif isinstance(item, PinnedDockItem):
            if item not in self.pinned_items.values():
                logger.error(f"Item not pinned: {item.desktop_app.display_name}")
                return

            identifier = list(self.pinned_items.keys())[
                list(self.pinned_items.values()).index(item)
            ]

        if item.desktop_app in self.loaded_pinned_desktop_apps:
            self.loaded_pinned_desktop_apps.remove(item.desktop_app)
        else:
            logger.error("Item not loaded???")

        def hide_item(self: Self, item, identifier):
            sleep(0.25)

            self.pinned_container.remove(item)
            self.pinned_items_pos.remove(item)
            self.pinned_items.pop(identifier)

            with open("dock_pinned_items", "w") as file:
                file.write(json.dumps(list(self.pinned_items.keys())))

        item.unreveal()
        if self.pinned_items_pos.__len__() <= 1:
            self.pinned_container_empty = True

            if self.main_container_empty:
                self.dock.remove_style_class("shown")

            self.pinned_separator.add_style_class("hidden")

        GLib.Thread.new("item-hide", hide_item, self, item, identifier)

    def on_client_added(self, service):
        client = self.clients_service.clients[-1]

        item = DockItem(client)
        item.connect(
            "enter-notify-event", lambda item, *_: self.handle_item_hovered(item, False)
        )
        item.connect(
            "leave-notify-event",
            lambda item, *_: self.handle_item_unhovered(item, False),
        )

        self.dock_items[client._client] = item
        self.dock_items_pos.append(item)
        self.main_container.add(item)

        item.add_style_class("shown")

        if configuration.get_property(
            "dock_visibility_rule"
        ) != "always visible" and configuration.get_property("dock_flash_on_app_added"):
            self.on_mouse_enter()
            self.on_mouse_leave()
        elif configuration.get_property("dock_visibility_rule") == "always visible":
            self.dock.add_style_class("shown")

        self.main_container_empty = False
        if self.pinned_container_empty:
            self.pinned_separator.add_style_class("hidden")
        else:
            self.pinned_separator.remove_style_class("hidden")

    def on_client_removed(self, service, client):
        if not self.dock_items.__contains__(client):
            logger.error(
                f"Client not managed:  [ID] {client.get_id()} [APP ID] {client.get_app_id()} [TITLE] {client.get_title()}"
            )
            return

        item = self.dock_items[client]

        def hide_item(self: Self, item):
            sleep(0.25)

            self.dock_items_pos.remove(item)
            self.main_container.remove(item)
            self.dock_items.pop(client)

        item.unreveal()
        if self.dock_items_pos.__len__() <= 1:
            self.main_container_empty = True

            if self.pinned_container_empty:
                self.dock.remove_style_class("shown")

            self.pinned_separator.add_style_class("hidden")

        GLib.Thread.new("item-hide", hide_item, self, item)

    def handle_item_hovered(self, item, pinned=False):
        if pinned:
            index = self.pinned_items_pos.index(item)
            if index > 0:
                self.pinned_items_pos[index - 1].add_style_class("semi_hovered")
            if index < self.pinned_items_pos.__len__() - 1:
                self.pinned_items_pos[index + 1].add_style_class("semi_hovered")
        else:
            index = self.dock_items_pos.index(item)
            if index > 0:
                self.dock_items_pos[index - 1].add_style_class("semi_hovered")
            if index < self.dock_items_pos.__len__() - 1:
                self.dock_items_pos[index + 1].add_style_class("semi_hovered")

        self.on_mouse_enter()

    def handle_item_unhovered(self, item, pinned=False):
        if pinned:
            index = self.pinned_items_pos.index(item)
            if index > 0:
                self.pinned_items_pos[index - 1].remove_style_class("semi_hovered")
            if index < self.pinned_items_pos.__len__() - 1:
                self.pinned_items_pos[index + 1].remove_style_class("semi_hovered")
        else:
            index = self.dock_items_pos.index(item)
            if index > 0:
                self.dock_items_pos[index - 1].remove_style_class("semi_hovered")
            if index < self.dock_items_pos.__len__() - 1:
                self.dock_items_pos[index + 1].remove_style_class("semi_hovered")

        self.on_mouse_leave()

    def on_mouse_enter(self):
        if (
            self.main_container_empty and self.pinned_container_empty
        ) or configuration.get_property("dock_visibility_rule") == "always visible":
            return

        self.hide_ticket = random.getrandbits(32)

        self.dock.add_style_class("shown")

        self.hovored = True

    def on_mouse_leave(self):
        if configuration.get_property("dock_visibility_rule") == "always visible":
            return

        self.hide_ticket = random.getrandbits(32)

        def hide(self: Self, hide_ticket):
            sleep(configuration.get_property("dock_hide_delay"))

            if hide_ticket == self.hide_ticket:
                if configuration.get_property("dock_visibility_rule") == "auto hide":
                    self.dock.remove_style_class("shown")
                self.hovored = False

        GLib.Thread.new("dock-hide", hide, self, self.hide_ticket)

    # @cooldown(0.1, lambda *_: logger.error("cooldown reached"))
    def check_obstructed(self):
        root = [960, 1080]
        size = self.get_size()
        if not self.height or size.height > self.height:
            self.height = size.height - 8
        self.width = size.width

        lx = root[0] - self.width / 2
        ly = root[1] - self.height

        rx = root[0] + self.width / 2
        ry = root[1]

        obstructed = self.workspace_props_service.get_clients_overlap_rect2(
            lx, ly, rx, ry
        )
        if obstructed:
            if not self.hovored:
                self.dock.remove_style_class("shown")
        elif not self.main_container_empty:
            self.dock.add_style_class("shown")

        return True


class DockItem(Button):
    def __init__(self, client: Client, **kwargs):
        super().__init__(
            name="dock_item",
            h_align="center",
            v_align="center",
            v_expand=False,
            **kwargs,
        )

        self.icon = Image(name="dock_item_icon", h_align="center")
        self.indicator = Box(name="dock_item_indicator", h_align="center")

        self.client = None
        self.build_from_client(client)

        self.add(
            Box(
                name="dock_item_main_container",
                orientation="v",
                children=[self.icon, self.indicator],
            )
        )

        self.connect("button-release-event", self.on_clicked)

    def build_from_client(self, client: Client):
        if self.client:
            self.client._client.disconnect_by_func(self.update_state)

        self.client = client

        self.client.connect("updated", self.update)
        self.client._client.connect("notify::activated", self.update_state)
        self.client._client.connect("notify::maximized", self.update_state)
        self.client._client.connect("notify::minimized", self.update_state)

        self.update()

    def update(self, *_):
        self.set_tooltip_text(self.client._desktop_app.display_name)
        self.set_image(
            self.client._desktop_app.get_icon_pixbuf(
                size=configuration.get_property("dock_icon_size")
            )
        )

        self.update_state()

    def set_image(self, image):
        if isinstance(image, str):
            self.icon.set_from_file(image)
        else:
            self.icon.set_from_pixbuf(image)

    def update_state(self, *_):
        if self.client._client.get_closed():
            return

        activated = self.client._client.get_activated()
        if activated:
            self.add_style_class("activated")
        else:
            self.remove_style_class("activated")

        maximized = self.client._client.get_maximized()
        if maximized:
            self.add_style_class("maximized")
        else:
            self.remove_style_class("maximized")

        minimized = self.client._client.get_minimized()
        if minimized:
            self.add_style_class("minimized")
        else:
            self.remove_style_class("minimized")

    def on_clicked(self, button, event):
        if event.button == 1:
            if self.client._client.get_closed():
                return

            if not self.client._client.get_activated():
                self.client._client.activate()
            elif self.client._client.get_minimized():
                self.client._client.unminimize()
            elif self.client._client.get_maximized():
                self.client._client.unmaximize()
            elif not self.client._client.get_maximized():
                self.client._client.maximize()

            return True
        elif event.button == 2:
            DockWindow.instances[0].add_pinned_item(
                self.client._desktop_app.name.lower(), self.client._desktop_app
            )

            return True
        else:
            return False

    def unreveal(self):
        self.remove_style_class("shown")


class PinnedDockItem(Button):
    def __init__(self, desktop_app: DesktopApp, **kwargs):
        super().__init__(
            name="dock_item",
            h_align="center",
            v_align="center",
            v_expand=False,
            **kwargs,
        )

        self.icon = Image(name="dock_item_icon", h_align="center")

        self.desktop_app = desktop_app
        self.build_from_app(desktop_app)

        self.add(
            Box(
                name="dock_item_main_container",
                orientation="v",
                children=[self.icon],
            )
        )

        self.connect("button-release-event", self.on_clicked)

    def build_from_app(self, desktop_app: DesktopApp):
        self.set_tooltip_text(desktop_app.display_name)
        self.set_image(
            desktop_app.get_icon_pixbuf(
                size=configuration.get_property("dock_icon_size")
            )
        )

    def set_image(self, image):
        if isinstance(image, str):
            self.icon.set_from_file(image)
        else:
            self.icon.set_from_pixbuf(image)

    def on_clicked(self, button, event):
        if event.button == 1:
            terminal = False
            desktop_app_properties = DesktopEntry(
                filename=self.desktop_app._app.get_filename()
            )
            if desktop_app_properties.getTerminal():
                terminal = True
                if e := desktop_app_properties.getTryExec():
                    exec = (
                        e.replace("%u", "")
                        .replace("%U", "")
                        .replace("%f", "")
                        .replace("%F", "")
                        .replace("%i", "")
                        .replace("%c", "")
                        .replace("%k", "")
                        .strip()
                    )
                else:
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
                # logger.info(f"Launching {self.desktop_app.name}...")
                # logger.debug(
                #     f"[NAME] {self.desktop_app.name} [GENERIC NAME] {self.desktop_app.generic_name} [DISPLAY NAME] {self.desktop_app.display_name} [EXECUTABLE] {self.desktop_app.executable} [COMMAND LINE] {self.desktop_app.command_line} [WINDOW CLASS] {self.desktop_app.window_class}"
                # )
                if terminal:
                    exec_shell_command_async(f"uwsm app -- kitty -d ~ --detach {exec}")
                else:
                    self.desktop_app.launch()

            except Exception as e:
                logger.error(
                    f"Error while trying to launch pinned app {self.desktop_app.name}: {e}..."
                )

            return True
        elif event.button == 2:
            DockWindow.instances[0].remove_pinned_item(self)

            return True
        else:
            return False

    def unreveal(self):
        self.remove_style_class("shown")
