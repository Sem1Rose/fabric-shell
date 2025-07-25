from curses import meta
from typing import Self
import gi
import random
from time import sleep
from fabric.widgets.label import Label
import os.path as path
from loguru import logger
from config import configuration

from fabric.widgets.box import Box
from fabric.core import Signal
from fabric.utils import idle_add
from fabric.utils import PixbufUtils

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
        self.ticket = 0
        self.artwork_rotating = False

        self.player_manager.connect(
            "player-added",
            lambda _, player: self.add_player(player),
        )
        self.player_manager.connect(
            "player-removed",
            lambda _, player: self.remove_player(player),
        )

        self.player_manager.find_connected_players()

        self.artwork_pixbuf = None
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

        if player.props.player_name not in configuration.get_property(
            "music_ticker_players"
        ):
            return

        player.connect(
            "metadata",
            lambda player, metadata: self.update_metadata(
                player.props.player_name, metadata
            ),
        )
        player.connect(
            "playback-status",
            lambda player, status: self.update_metadata(
                player.props.player_name, player.props.metadata
            )
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
                self.artwork_pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    filename=file_path,
                    width=28,
                    height=28,
                    preserve_aspect_ratio=False,
                )
                idle_add(self.artwork_image.set_from_pixbuf, self.artwork_pixbuf)

                return

            sleep(1)
            i += 1

    def update_artwork(self, data):
        self.artwork_pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            filename=f"{configuration.get_property('icons_dir')}/image-off.svg",
            width=28,
            height=28,
            preserve_aspect_ratio=False,
        )
        self.artwork_image.set_from_pixbuf(
            self.artwork_pixbuf
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
                self.artwork_pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    filename=file_path,
                    width=28,
                    height=28,
                    preserve_aspect_ratio=False,
                )
                self.artwork_image.set_from_pixbuf(
                    self.artwork_pixbuf
                )
            else:
                GLib.Thread.new(
                    "artwork-downloader",
                    self.wait_for_artwork,
                    file_path,
                )

        if not self.artwork_rotating:
            self.rotate_artwork()
            self.artwork_rotating = True

    def metadata_get(self, metadata, key, default):
        if key in metadata.keys():
            return metadata[key]
        else:
            return default

    def update_metadata(self, player, metadata):
        label = (
            f"{player} - {title}"
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
        def hide_thread(ticker: Self, ticket):
            sleep(configuration.get_property("music_ticker_timeout"))

            if ticker.ticket == ticket:
                self.do_hide()

        GLib.Thread.new("hide-music-ticker", hide_thread, self, self.ticket)

    def rotate_artwork(self):
        angle = 0.0
        angle_delta = configuration.get_property("music_ticker_artwork_rotation_speed") * 360.0 / 24.0

        def rotate():
            nonlocal angle
            angle += angle_delta

            self.artwork_image.set_style(f"-gtk-icon-transform: rotate({angle}deg);")

            return True

        GLib.timeout_add(1000 / 24, rotate)

        return True
