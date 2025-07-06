import random
from time import sleep
from fabric.widgets.label import Label
import gi
import os.path as path
from loguru import logger
from config import configuration

from fabric.widgets.box import Box
from fabric.core import Signal
from fabric.utils import idle_add

from widgets.helpers.mpris_service import get_mpris_service
from widgets.rounded_image import RoundedImage

gi.require_version("Playerctl", "2.0")
from gi.repository import GdkPixbuf, GLib, Playerctl  # noqa: E402


class MusicTicker(Box):
    @Signal
    def music_tick(self): ...

    @Signal
    def do_hide(self): ...

    def __init__(self, *args, **kwargs):
        super().__init__(name="music_ticker_widget", *args, **kwargs)

        self.add_style_class("quick_glance_widget")

        self.player_manager = get_mpris_service()
        self.player_controllers = []
        self.ticket = None

        self.player_manager.connect(
            "player-added",
            lambda _, player: self.add_player(player),
        )
        self.player_manager.connect(
            "player-removed",
            lambda _, player: self.remove_player(player),
        )

        self.player_manager.find_connected_players()

        self.artwork_image = RoundedImage(
            name="media_artwork",
            h_expand=True,
            v_expand=True,
        )
        self.artwork_box = Box(
            name="media_artwork_box",
            children=[self.artwork_image],
            v_align="center",
            h_align="start",
        )
        self.title = Label(
            h_expand=True,
            ellipsization="end",
        )

        self.add(self.artwork_box)
        self.add(self.title)

    def add_player(self, player):
        player = player

        if player.props.player_name not in ["spotify"]:
            return

        player.connect("metadata", lambda _, metadata: self.update_metadata(metadata))
        player.connect(
            "playback-status",
            lambda _, status: (self.music_tick() or self.hide_music_ticker())
            if status == Playerctl.PlaybackStatus.PLAYING
            else (),
        )

        self.player_controllers.append(player)

    def remove_player(self, player):
        player = player
        if player not in self.player_controllers:
            return

        self.player_controllers.remove(player)

    # this depends on the MediaPlayer widget to download the artwork
    def wait_for_artwork(self, file_path):
        i = 0
        while i < 4:
            if path.exists(file_path):
                idle_add(
                    self.artwork_image.set_from_pixbuf,
                    GdkPixbuf.Pixbuf.new_from_file_at_scale(
                        filename=file_path,
                        width=28,
                        height=28,
                        preserve_aspect_ratio=False,
                    ),
                )

                return

            sleep(1)
            i += 1

    def update_artwork(self, data):
        self.artwork_image.set_from_pixbuf(
            GdkPixbuf.Pixbuf.new_from_file_at_scale(
                filename=f"{configuration.get_property('icons_dir')}/image-off.svg",
                width=28,
                height=28,
                preserve_aspect_ratio=False,
            )
        )

        if data != "":
            if data.startswith("file://"):
                file_path = data.replace("file://", "")
            elif data.startswith("http"):
                file_path = path.join(
                    configuration.get_property("artwork_cache_dir"),
                    data.split("/")[-1],
                )
            else:
                return

            if path.exists(file_path):
                self.artwork_image.set_from_pixbuf(
                    GdkPixbuf.Pixbuf.new_from_file_at_scale(
                        filename=file_path,
                        width=28,
                        height=28,
                        preserve_aspect_ratio=False,
                    )
                )
            else:
                GLib.Thread.new(
                    "artwork-downloader",
                    self.wait_for_artwork,
                    file_path,
                )

    def metadata_get(self, metadata, key, default):
        if key in metadata.keys():
            return metadata[key]
        else:
            return default

    def update_metadata(self, metadata):
        label = (
            f"spotify - {title}"
            if (title := self.metadata_get(metadata, "xesam:title", ""))
            else "unknown"
        )
        self.title.set_label(label)
        self.title.set_tooltip_text(label)

        self.update_artwork(self.metadata_get(metadata, "mpris:artUrl", ""))

        self.ticket = random.getrandbits(32)

        self.music_tick()
        self.hide_music_ticker()

    def hide_music_ticker(self):
        def hide_thread(ticker, ticket):
            sleep(4)

            if ticker.ticket == ticket:
                self.do_hide()

        GLib.Thread.new("hide-music-ticker", hide_thread, self, self.ticket)
