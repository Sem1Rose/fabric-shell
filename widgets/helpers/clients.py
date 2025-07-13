import gi
from os import name
from loguru import logger

from fabric.utils import get_desktop_applications, DesktopApp
from fabric.core import Service, Signal, Property

gi.require_version("Glace", "0.1")
from gi.repository import Glace  # noqa: E402


class Client(Service):
    @Signal
    def updated(self): ...

    def __init__(self, glace_client: Glace.Client, desktop_entry: DesktopApp, **kwargs):
        super().__init__(**kwargs)
        self._client: Glace.Client = glace_client
        self._desktop_entry: DesktopApp = desktop_entry

    def update_desktop_entry(self, desktop_entry: DesktopApp):
        self._desktop_entry = desktop_entry
        self.updated()


class ClientsService(Service):
    @Signal
    def client_added(self): ...

    @Signal
    def client_removed(self, client: Glace.Client): ...

    @Property(list[Client], "r")
    def clients(self) -> list[Client]:
        return self._clients

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.build_app_identifiers()
        self._clients: list[Client] = []

        self.manager = Glace.Manager()
        self.manager.connect("client-added", self.on_client_appear)
        self.manager.connect("client-removed", self.on_client_disappear)

    def on_client_appear(self, manager, client):
        client.connect("changed", self.add_client)

    def get_app_identifiers(self, app: Glace.Client) -> list[str]:
        identifiers = []

        if app.get_app_id() == "kitty":
            identifiers.append(
                "".join(char for char in app.get_title().split()[0].lower() if char.isalnum()).strip()
            )
        identifiers.append(self.normalize_app_id(app.get_app_id().lower()))
        identifiers.append(self.normalize_app_title(app.get_title().lower()))

        return identifiers

    def normalize_app_id(self, app_id: str) -> str:
        if "." in app_id:
            return app_id.split(".")[1]

        return app_id

    def normalize_app_title(self, app_title: str) -> str:
        if " " in app_title:
            return app_title.split()[0]

        return app_title

    def add_client(self, client):
        client.disconnect_by_func(self.add_client)

        if desktop_app := self.find_app(client):
            logger.warning(
                f"Managing app: [ID] {client.get_id()} [APP ID] {client.get_app_id()} [TITLE] {client.get_title()}"
            )

            item = Client(client, desktop_app)
            item._client.connect(
                "notify::title",
                lambda client, *_: item.update_desktop_entry(entry)
                if (entry := self.find_app(client))
                else (),
            )

            self._clients.append(item)

            self.client_added()
        else:
            logger.error(
                f"Couldn't find the desktop app for: [ID] {client.get_id()} [APP ID] {client.get_app_id()} [TITLE] {client.get_title()}"
            )

    def on_client_disappear(self, manager, client):
        matches = [x for x in self._clients if x._client == client]
        if matches.__len__() == 0:
            logger.error(
                f"App not managed: [ID] {client.get_id()} [APP ID] {client.get_app_id()} [TITLE] {client.get_title()}"
            )
            return

        self._clients.remove(matches[0])
        self.client_removed(matches[0]._client)

    def build_app_identifiers(self):
        self.identifiers = {}
        for app in get_desktop_applications():
            if app.name:
                self.identifiers[app.name.lower()] = app
            if app.display_name:
                self.identifiers[app.display_name.lower()] = app
            if app.window_class:
                self.identifiers[app.window_class.lower()] = app
            if app.executable:
                self.identifiers[app.executable.split("/")[-1].lower()] = app
            if app.command_line:
                self.identifiers[app.command_line.split()[0].split("/")[-1].lower()] = (
                    app
                )

    # def find_app(self, app_identifier):
    #     if isinstance(app_identifier, dict):
    #         for key in [
    #             "window_class",
    #             "executable",
    #             "command_line",
    #             "name",
    #             "display_name",
    #         ]:
    #             if key in app_identifier and app_identifier[key]:
    #                 app = self.find_app_by_key(app_identifier[key])
    #                 if app:
    #                     return app
    # return None
    #     return self.find_app_by_key(app_identifier)

    def find_app(self, app: Glace.Client):
        for identifier in self.get_app_identifiers(app):
            if app := self.find_app_by_identifier(identifier):
                return app
        else:
            return None

    def find_app_by_identifier(self, identifier) -> DesktopApp | None:
        identifier = identifier.lower()

        if identifier in self.identifiers:
            return self.identifiers[identifier]

        for app in self.identifiers.keys():
            if identifier in app:
                return self.identifiers[app]
        return None


service: ClientsService | None = None


def get_clients_service() -> ClientsService:
    global service
    if not service:
        service = ClientsService()

    return service
