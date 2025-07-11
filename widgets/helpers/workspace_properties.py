import json
from loguru import logger

from fabric import Service
from fabric.core import Signal
from fabric.hyprland.widgets import get_hyprland_connection
from fabric.utils.helpers import bulk_connect


class WorkspaceProperties(Service):
    @Signal
    def on_fullscreen(self, state: int): ...

    @Signal
    def on_empty(self, empty: bool): ...

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.hyprland = get_hyprland_connection()

        self.current_workspace = -1
        # self.fullscreen: bool = False
        self.fullscreen_state: int = 0
        self.empty: bool = False

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
            if client["workspace"]["id"] == self.current_workspace
            and not client["pinned"]
            and not client["hidden"]
        ]

    def recalculate_props(self, *_):
        self.current_workspace = json.loads(
            self.hyprland.send_command("j/activeworkspace").reply
        )["id"]

        clients = self.get_workspace_clients()
        count = clients.__len__()
        if count == 0:
            # logger.error("no windows")
            if not self.empty:
                self.empty = True
                # logger.error("empty")
                self.on_empty(self.empty)

            if self.fullscreen_state != 0:
                self.fullscreen_state = 0
                # logger.error(f"no fullscreen {self.fullscreen_state}")
                self.on_fullscreen(self.fullscreen_state)
                # self.fullscreen = False
        else:
            floating_count: int = 0
            fullscreen_state: int = 0
            for client in clients:
                if client["floating"] and client["fullscreen"] != 2:
                    floating_count += 1
                elif client["fullscreen"] > 0:
                    fullscreen_state = client["fullscreen"]

            non_floating = count - floating_count

            if non_floating == 0:
                # logger.error("all floating")
                if not self.empty:
                    self.empty = True
                    # logger.error("empty")
                    self.on_empty(self.empty)

                if self.fullscreen_state != fullscreen_state:
                    self.fullscreen_state = fullscreen_state
                    # logger.error(f"no fullscreen {self.fullscreen_state}")
                    self.on_fullscreen(0)
                    # self.fullscreen = False
            else:
                if self.empty:
                    self.empty = False
                    # logger.error("no empty")
                    self.on_empty(self.empty)

                logger.warning(fullscreen_state)
                if non_floating == 1:
                    # logger.error("only one window")
                    if fullscreen_state == 0:
                        fullscreen_state = 1
                    if self.fullscreen_state != fullscreen_state:
                        self.fullscreen_state =fullscreen_state
                        # logger.warning(f"fullscreen {self.fullscreen_state}")
                        self.on_fullscreen(self.fullscreen_state)
                        # self.fullscreen = True
                else:
                    # if fullscreen_state > 0:
                    #     logger.error("at lease one fullscreen")
                    #     if not self.fullscreen:
                    #         self.fullscreen = True
                    #         # logger.error("fullscreen")
                    #         self.on_fullscreen(self.fullscreen, fullscreen_state)
                    if self.fullscreen_state != fullscreen_state:
                        self.fullscreen_state = fullscreen_state
                        # logger.error(f"no fullscreen {self.fullscreen_state}")
                        self.on_fullscreen(self.fullscreen_state)

                        # if fullscreen_state > 0:
                        #     logger.error("at lease one fullscreen")
                        # else:
                        #     logger.error("none fullscreen")

                        # self.fullscreen = False

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
