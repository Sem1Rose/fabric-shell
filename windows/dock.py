from loguru import logger
import gi

gi.require_version("Glace", "0.1")
from gi.repository import Glace

global client
client = None

def assign(_client):
    global client
    if not client and _client.get_app_id() == "spotify":
        client = _client
        logger.error(
            f"[ID] {_client.get_id()} [APP ID] {_client.get_app_id()} [TITLE] {_client.get_title()}"
        )

def on_client_added(_, _client):
    _client.connect(
        "changed",
        lambda client: assign(client),
    )

manager = Glace.Manager()
manager.connect("client-added", on_client_added)