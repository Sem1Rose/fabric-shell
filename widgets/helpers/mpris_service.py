import gi
from loguru import logger

from fabric import Service, Signal, Property

gi.require_version("Playerctl", "2.0")
from gi.repository import Playerctl  # noqa: E402


class MPRISService(Service):
    @Signal
    def changed(self) -> None: ...

    @Signal
    def player_added(self, player: Playerctl.Player) -> None: ...

    @Signal
    def player_removed(self, player: Playerctl.Player) -> None: ...

    @Property(list[str], "readable")
    def player_names(self) -> list[str]:
        return self._player_names

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        self._manager = Playerctl.PlayerManager.new()
        self._player_names = []

        self._manager.connect(
            "name-appeared",
            lambda _, name: self.handle_manager_events(player_name=name),
        )

        self.find_connected_players()

    def find_connected_players(self):
        for player_name in self._manager.props.player_names:
            self.handle_manager_events(player_name=player_name)

    def handle_manager_events(self, player=None, player_name=None):
        # player_name != None -> adding a player
        # player != None -> removing a player
        if player is None and player_name is None:
            logger.error("Either player or name must not be none")
            return
        # elif player is not None and player_name is not None:
        #     logger.error("Either player or name must be none")
        #     return

        if player_name:
            name = player_name.name
            if name in self._player_names:
                logger.warning(f'"{name}" already added')
            else:
                logger.debug(f'Adding "{name}" to managed players')
                self._player_names.append(name)
                # return

            # if name in configuration.get_property("media_player_allowed_players"):
            #     logger.debug(f'Adding "{name}" to media players')

            _controller = Playerctl.Player.new_from_name(player_name)
            self._manager.manage_player(_controller)
            # self.player_manager.move_player_to_top(_controller)

            _controller.connect(
                "exit", lambda player: self.handle_manager_events(player=player)
            )
            self.emit("player-added", _controller)
            self.notifier("players")

            # else:
            #     logger.warning(f"Player {name} is available but won't be managed")
        elif player:
            self._player_names.remove(player.props.player_name)
            logger.debug(f'Removing "{player.props.player_name}" from media players')

            self.emit("player-removed", player)
            self.notifier("players")

            # self.remove_player(player)
        else:
            logger.error("THIS SHALL NOT BE REACHED")

    def notifier(self, name: str, *args):
        self.notify(name)
        self.emit("changed")
        return


mpris_service: MPRISService | None = None

def get_mpris_service() -> MPRISService:
    global mpris_service

    if not mpris_service:
        mpris_service = MPRISService()

    return mpris_service
