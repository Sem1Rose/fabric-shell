from os import name
import random
from time import sleep
from fabric.widgets.eventbox import EventBox
import gi
from typing import Any, Self
from loguru import logger
from config import configuration

from fabric.widgets.image import Image
from fabric.widgets.box import Box
from fabric.widgets.wayland import WaylandWindow as Window
from fabric.widgets.revealer import Revealer
from fabric.hyprland.widgets import get_hyprland_connection

from fabric.core import Signal
from fabric.utils import get_desktop_applications, DesktopApp, idle_add, invoke_repeater

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

        self.empty = False
        self.hovored = False
        self.hide_ticket = 0
        self.height = 0
        self.width = 0

        self.clients_service = get_clients_service()
        self.clients_service.connect("client-added", self.on_client_added)
        self.clients_service.connect("client-removed", self.on_client_removed)

        self.items_pos: list[DockItem] = []
        self.dock_items = {}

        self.main_container = Box(name="dock")

        self.add(
            Box(
                name="dock_window",
                style="min-width: 1px; min-height: 1px;",
                children=self.main_container,
            )
        )

        self.show_all()
        DockWindow.instances.append(self)

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

    def on_client_added(self, service):
        client = self.clients_service.clients[-1]

        item = DockItem(client)
        item.connect("enter-notify-event", self.handle_item_hovered)
        item.connect("leave-notify-event", self.handle_item_unhovered)

        self.dock_items[client._client] = item
        self.items_pos.append(item)
        self.main_container.add(item)

        item.add_style_class("shown")

        if configuration.get_property(
            "dock_visibility_rule"
        ) != "always visible" and configuration.get_property("dock_flash_on_app_added"):
            self.on_mouse_enter()
            self.on_mouse_leave()
        elif configuration.get_property("dock_visibility_rule") == "always visible":
            self.main_container.add_style_class("shown")

        self.empty = False

    def on_client_removed(self, service, client):
        if not self.dock_items.__contains__(client):
            logger.error(
                f"Client not managed:  [ID] {client.get_id()} [APP ID] {client.get_app_id()} [TITLE] {client.get_title()}"
            )
            return

        item = self.dock_items[client]

        def hide_item(self: Self, item):
            sleep(0.25)

            idle_add(self.main_container.remove, item)
            idle_add(self.items_pos.remove, item)
            idle_add(self.dock_items.pop, client)

        item.unreveal()
        if self.items_pos.__len__() == 1:
            self.main_container.remove_style_class("shown")
            self.empty = True

        GLib.Thread.new("item-hide", hide_item, self, item)

    def handle_item_hovered(self, item, *_):
        index = self.items_pos.index(item)
        if index > 0:
            self.items_pos[index - 1].add_style_class("semi_hovered")
        if index < self.items_pos.__len__() - 1:
            self.items_pos[index + 1].add_style_class("semi_hovered")

        self.on_mouse_enter()

    def handle_item_unhovered(self, item, *_):
        index = self.items_pos.index(item)
        if index > 0:
            self.items_pos[index - 1].remove_style_class("semi_hovered")
        if index < self.items_pos.__len__() - 1:
            self.items_pos[index + 1].remove_style_class("semi_hovered")

        self.on_mouse_leave()

    def on_mouse_enter(self):
        if self.empty or configuration.get_property("dock_visibility_rule") == "always visible":
            return

        self.hide_ticket = random.getrandbits(32)

        self.main_container.add_style_class("shown")

        self.hovored = True

    def on_mouse_leave(self):
        if configuration.get_property("dock_visibility_rule") == "always visible":
            return

        self.hide_ticket = random.getrandbits(32)

        def hide(self: Self, hide_ticket):
            sleep(configuration.get_property("dock_hide_delay"))

            if hide_ticket == self.hide_ticket:
                if configuration.get_property("dock_visibility_rule") == "auto hide":
                    self.main_container.remove_style_class("shown")
                self.hovored = False

        GLib.Thread.new("dock-hide", hide, self, self.hide_ticket)

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

        obstructed = self.workspace_props_service.get_clients_overlap_rect2(lx, ly, rx, ry)
        if obstructed:
            if not self.hovored:
                self.main_container.remove_style_class("shown")
        elif not self.empty:
            self.main_container.add_style_class("shown")

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

        # self.revealer = Revealer(
        #     child=Box(
        #         name="dock_item_main_container",
        #         orientation="v",
        #         children=[self.icon, self.indicator],
        #     ),
        #     transition_type="slide-up",
        #     transition_duration=250,
        #     child_revealed=False
        # )
        self.add(
            Box(
                name="dock_item_main_container",
                orientation="v",
                children=[self.icon, self.indicator],
            )
        )

        self.connect("clicked", self.on_clicked)

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
        self.set_tooltip_text(self.client._desktop_entry.display_name)
        self.set_image(
            self.client._desktop_entry.get_icon_pixbuf(
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

    def on_clicked(self, *_):
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

    def unreveal(self):
        self.remove_style_class("shown")
        # self.revealer.unreveal()
