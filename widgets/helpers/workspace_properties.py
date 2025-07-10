import json
from loguru import logger

from fabric import Service
from fabric.core import Signal
from fabric.hyprland.widgets import get_hyprland_connection
from fabric.utils.helpers import bulk_connect


class WorkspaceProperties(Service):
    @Signal
    def on_fullscreen(self, state: bool): ...

    @Signal
    def on_empty(self, state: bool): ...

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.hyprland = get_hyprland_connection()

        self._current_workspace = -1
        self._fullscreen: bool = False
        self._empty: bool = False

        bulk_connect(
            self.hyprland,
            {
                "event::workspace": self.recalculate_props,
                "event::fullscreen": self.recalculate_props,
                "event::openwindow": self.recalculate_props,
                "event::closewindow": self.recalculate_props,
                "event::movewindow": self.recalculate_props,
                "event::changefloatingmode": self.recalculate_props,
            },
        )

        self.recalculate_props()

    def get_workspace_clients(self):
        clients = json.loads(self.hyprland.send_command("j/clients").reply)
        return [
            client
            for client in clients
            if client["workspace"]["id"] == self._current_workspace
            and not client["pinned"]
            and not client["hidden"]
        ]

    def recalculate_props(self, *_):
        self._current_workspace = json.loads(
            self.hyprland.send_command("j/activeworkspace").reply
        )["id"]

        clients = self.get_workspace_clients()
        count = clients.__len__()
        if count == 0:
            if not self._empty:
                self._empty = True
                logger.error("empty")
                self.on_empty(self._empty)

            if self._fullscreen:
                self._fullscreen = False
                logger.error("no fullscreen")
                self.on_fullscreen(self._fullscreen)
        else:
            floating = 0
            fullscreen = 0
            for client in clients:
                if client["floating"] and client["fullscreen"] != 2:
                    floating += 1
                elif client["fullscreen"] > 0:
                    fullscreen += 1

            non_floating = count - floating

            if non_floating == 0:
                if not self._empty:
                    self._empty = True
                    logger.error("empty")
                    self.on_empty(self._empty)

                if self._fullscreen:
                    self._fullscreen = False
                    logger.error("no fullscreen")
                    self.on_fullscreen(self._fullscreen)
            else:
                if self._empty:
                    self._empty = False
                    logger.error("no empty")
                    self.on_empty(self._empty)

                if non_floating == 1:
                    if not self._fullscreen:
                        self._fullscreen = True
                        logger.error("fullscreen")
                        self.on_fullscreen(self._fullscreen)
                else:
                    if fullscreen > 0:
                        if not self._fullscreen:
                            self._fullscreen = True
                            logger.error("fullscreen")
                            self.on_fullscreen(self._fullscreen)
                    elif self._fullscreen:
                        self._fullscreen = False
                        logger.error("no fullscreen")
                        self.on_fullscreen(self._fullscreen)

    def get_clients_overlap_rect(self, rect) -> bool:
        rectl = [rect.x, rect.y]
        rectr = [rect.x + rect.width, rect.y + rect.height]
        clients = self.get_workspace_clients()
        for client in clients:
            clientl = client["at"]
            clientr = [
                client["at"][0] + client["size"][0],
                client["at"][1] + client["size"][1],
            ]
            if clientl[0] > rectr[0] or rectl[0] > clientr[0]:
                return False
            elif clientl[1] > rectr[1] or rectl[1] > clientr[1]:
                return False

        return True


service: WorkspaceProperties | None = None


def get_service() -> WorkspaceProperties:
    global service
    if not service:
        service = WorkspaceProperties()

    return service
