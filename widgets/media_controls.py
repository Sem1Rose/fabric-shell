import gi
import os.path as path
from loguru import logger
from config import configuration

from widgets.rounded_image import RoundedImage
from widgets.buttons import ToggleButton, CycleToggleButton, MarkupButton
from widgets.interactable_slider import Slider
from widgets.helpers.formatted_exec import formatted_exec_shell_command
from widgets.helpers.str import UpperToPascal

from fabric import Fabricator
from fabric.widgets.box import Box
from fabric.widgets.revealer import Revealer
from fabric.widgets.label import Label
from fabric.core.service import Signal
from fabric.utils import (
    # exec_shell_command_async,
    idle_add,
    get_enum_member,
    get_enum_member_name,
)

gi.require_version("Playerctl", "2.0")
from gi.repository import GdkPixbuf, GLib, Playerctl  # noqa: E402


class MediaControls(Revealer):
    @Signal
    def on_show_hide(self, shown: bool): ...

    def __init__(
        self, transition_type="slide-down", transition_duration=200, *args, **kwargs
    ):
        super().__init__(
            transition_type=transition_type, transition_duration=transition_duration
        )

        self.player_manager = Playerctl.PlayerManager.new()
        self.player_controller = None
        self.playing = False
        self.seeking = False
        self.length = 0

        def set_length(value):
            if value != "":
                self.length = value
            else:
                self.length = None

        # Fabricator(
        #     poll_from=configuration.get_property("playerctl_command")
        #     + r" metadata --follow -f '{{ mpris:length }}'",
        #     interval=0,
        #     stream=True,
        #     on_changed=lambda _, v: set_length(v),
        # )
        self.media_previous = MarkupButton(
            name="media_previous",
            markup=configuration.get_property("media_player_previous_icon"),
            h_align="start",
        )
        self.media_previous.connect(
            "clicked",
            lambda *_: self.player_controller.previous(),
            # lambda *_: exec_shell_command_async(
            #     f"{configuration.get_property('playerctl_command')} previous"
            # ),
        )

        self.media_next = MarkupButton(
            name="media_next",
            markup=configuration.get_property("media_player_next_icon"),
            h_align="end",
        )
        self.media_next.connect(
            "clicked",
            lambda *_: self.player_controller.next(),
            # lambda *_: exec_shell_command_async(
            #     f"{configuration.get_property('playerctl_command')} next"
            # ),
        )

        self.media_play_pause = ToggleButton(
            name="media_play_pause",
            h_align="end",
            # ).build(
            #     lambda button, _: Fabricator(  # process
            #         poll_from=f"{configuration.get_property('playerctl_command')} status -F",
            #         interval=0,
            #         stream=True,
            #         default_value="",
            #         on_changed=lambda _, value: (
            #             button.set_markup(
            #                 configuration.get_property("media_player_pause_icon")
            #                 if value == "Playing"
            #                 else configuration.get_property("media_player_play_icon")
            #             ),
            #             button.set_state(value == "Playing"),
            #         ),
            #     )
        )
        self.media_play_pause.connect(
            "on_toggled",
            lambda *_: self.player_controller.play_pause(),
            # lambda *_: exec_shell_command_async(
            #     f"{configuration.get_property('playerctl_command')} play-pause"
            # ),
        )

        self.media_shuffle = ToggleButton(
            name="media_shuffle",
            markup=configuration.get_property("media_player_shuffle_icon"),
            # ).build(
            #     lambda toggle, _: Fabricator(  # process
            #         poll_from=f"{configuration.get_property('playerctl_command')} shuffle -F",
            #         interval=0,
            #         stream=True,
            #         default_value="",
            #         on_changed=lambda _, value: toggle.set_state(value == "On"),
            #     )
        )
        self.media_shuffle.connect(
            "on_toggled",
            lambda toggle, *_: self.player_controller.set_shuffle(toggle.toggled),
            # lambda *_: exec_shell_command_async(
            #     f"{configuration.get_property('playerctl_command')} shuffle Toggle"
            # ),
        )

        self.media_loop = CycleToggleButton(
            name="media_loop",
            states=["None", "Playlist", "Track"],
            # ).build(
            #     lambda cycle_toggle, _: Fabricator(  # process
            #         poll_from=f"{configuration.get_property('playerctl_command')} loop -F",
            #         interval=0,
            #         stream=True,
            #         default_value="",
            #         on_changed=lambda _, value: (
            #             cycle_toggle.set_markup(
            #                 configuration.get_property("media_player_repeat_none_icon")
            #                 if value == "None"
            #                 else configuration.get_property(
            #                     "media_player_repeat_playlist_icon"
            #                 )
            #                 if value == "Playlist"
            #                 else configuration.get_property(
            #                     "media_player_repeat_track_icon"
            #                 )
            #             ),
            #             cycle_toggle.set_state(state=value),
            #         ),
            #     )
        )
        self.media_loop.connect(
            "on_cycled",
            lambda cycle_toggle, *_: self.player_controller.set_loop_status(
                get_enum_member(Playerctl.LoopStatus, cycle_toggle.get_state())
            ),
            # lambda cycle_toggle, *_: exec_shell_command_async(
            #     f"{configuration.get_property('playerctl_command')} loop {cycle_toggle.get_state()}"
            # ),
        )

        def seek_playback(value):
            if self.player_controller and self.length:
                self.player_controller.set_position(int(value * self.length))
                # exec_shell_command_async(
                #     f"{configuration.get_property('playerctl_command')} position {value * self.length}"
                # )

        def try_get_position(*_):
            if not self.player_controller:
                return 0

            try:
                return self.player_controller.get_position()
            except Exception:
                return 0

        self.media_progress = Slider(
            name="media_progress",
            h_expand=True,
            draw_value=False,
            orientation="h",
            # poll=False,
            poll_command=try_get_position,
            # poll_command=f"{configuration.get_property('playerctl_command')} position",
            poll_value_processor=lambda v: (
                (v / self.length)
                # (float(v) / self.length)
                if self.length is not None and self.length != 0
                else 0
            ),
            poll_interval=500,
            poll_stream=False,
            animation_duration=0.5,
        )
        self.media_progress.connect(
            "on_interacted",
            lambda _, value: seek_playback(value),
        )
        # Fabricator(
        #     poll_from=lambda *_: self.player_controller.get_position(),
        #     interval=500,
        #     on_changed=lambda _, v: logger.error(
        #         f"ass is: {(float(v / 1e6) / self.length)}, {self.length}"
        #     ),
        #     # on_changed=lambda _, v: self.media_progress.change_value(
        #     #     (float(v / 1e6) / self.length)
        #     #     if self.length is not None and self.length != 0
        #     #     else 0
        #     # ),
        # )

        # progress_box = Box(h_expand=True, children=[self.media_progress])

        self.title_label = Label(
            name="media_title_label",
            h_expand=True,
            h_align="start",
            ellipsization="end",
            # ).build(
            #     lambda label, _: Fabricator(  # process
            #         poll_from=configuration.get_property("playerctl_command")
            #         + r" metadata -F -f '{{ title }}'",
            #         interval=0,
            #         stream=True,
            #         on_changed=lambda _, v: (label.set_label(v), label.set_tooltip_text(v)),
            #     )
        )

        self.artist_album_label = Label(
            name="media_artist_album_label",
            h_expand=False,
            h_align="start",
            justification="start",
            # line_wrap="word",
            ellipsization="end",
            # ).build(
            #     lambda label, _: Fabricator(  # process
            #         poll_from=configuration.get_property("playerctl_command")
            #         + r" metadata -F -f '{{ artist }} 🞄 {{ album }}'",
            #         interval=0,
            #         stream=True,
            #         on_changed=lambda _, v: (label.set_label(v), label.set_tooltip_text(v)),
            #     )
        )

        self.artwork_image = RoundedImage(
            name="media_artwork",
            image_file=f"{configuration.get_property('icons_dir')}/image-off.svg",
            size=configuration.get_property("media_player_no_artwork_icon_size"),
            h_expand=True,
            # ).build(
            #     lambda image, _: Fabricator(  # process
            #         poll_from=configuration.get_property("playerctl_command")
            #         + r" metadata -F -f '{{ mpris:artUrl }}'",
            #         interval=0,
            #         stream=True,
            #         on_changed=lambda _, v: update_artwork(image, v),
            #     )
        )

        self.artwork_box = Box(
            name="media_artwork_box",
            orientation="h",
            size=configuration.get_property("media_player_artwork_size"),
            children=[self.artwork_image],
        )

        self.main_container = Box(
            name="media_controls_widget",
            orientation="v",
            children=[
                Box(
                    orientation="h",
                    h_expand=True,
                    v_expand=True,
                    children=[
                        self.artwork_box,
                        Box(
                            h_expand=True,
                            orientation="v",
                            children=[
                                Box(v_expand=True),
                                self.title_label,
                                self.artist_album_label,
                                Box(v_expand=True),
                            ],
                        ),
                        Box(
                            v_expand=True,
                            h_expand=True,
                            orientation="v",
                            children=[
                                Box(v_expand=True),
                                self.media_play_pause,
                                Box(v_expand=True),
                            ],
                        ),
                    ],
                ),
                Box(
                    orientation="h",
                    h_expand=True,
                    children=[
                        self.media_previous,
                        self.media_shuffle,
                        self.media_progress,
                        # progress_box,
                        self.media_loop,
                        self.media_next,
                    ],
                ),
            ],
            *args,
            **kwargs,
        )
        self.children = self.main_container

        # self.update_metadata()

        self.player_manager.connect(
            "name-appeared",
            # lambda _, name: self.handle_manager_events(name, True),
            lambda _, name: self.handle_manager_events(player_name=name),
        )
        # self.player_manager.connect(
        #     "player-vanished",
        #     # "name-vanished",
        #     # lambda _, name: self.handle_manager_events(name, False),
        #     lambda _, player: self.handle_manager_events(player=player),
        # )

        # self.player_controller = Playerctl.Player.new(
        #     configuration.get_property("playerctl_player_name")
        # )
        # self.connect_player_controller()

        # self.show_hide()
        player_names = [
            player
            for player in self.player_manager.props.player_names
            if player.name == configuration.get_property("playerctl_player_name")
        ]
        if len(player_names) > 0:
            self.handle_manager_events(player_name=player_names[0])

        # Fabricator(
        #     poll_from=configuration.get_property("playerctl_command")
        #     + r" metadata --follow -f '{{ title }}'",
        #     interval=0,
        #     stream=True,
        #     on_changed=lambda _, value: show_hide(value != ""),
        # )

    def handle_manager_events(self, player=None, player_name=None):
        # logger.error("benis")

        if player is None and player_name is None:
            logger.error("Either player or name must not be none")
            return
        elif player is not None and player_name is not None:
            logger.error("Either player or name must be none")
            return

        # logger.warning(
        #     f"{self.player_controller}: {'added' if player_name else 'removed'} {player.props.player_name if player else player_name.name}"
        # )

        if player_name and self.player_controller:
            logger.warning("Already added")
            return
        elif player and not self.player_controller:
            logger.warning("Nothing to remove")
            return

        # if added and self.player_controller:
        #     return
        # elif not added and not self.player_controller:
        #     return

        # name = player.name
        # logger.error("caulk")
        if player_name:
            name = player_name.name
            # logger.error(f"bewbs {name}")
            if configuration.get_property("playerctl_player_name") == name:
                # logger.error("bussy")
                self.player_controller = Playerctl.Player.new_from_name(player_name)
                self.player_manager.manage_player(self.player_controller)
                # self.player_controller = Playerctl.Player.new(
                #     configuration.get_property("playerctl_player_name")
                # )
                self.connect_player_controller()

                self.player_controller.connect(
                    "exit", lambda player: self.handle_manager_events(player=player)
                )

                self.show_hide()
        # else:
        elif player:
            name = player.props.player_name
            # logger.error(f"logos {name}")
            if configuration.get_property("playerctl_player_name") == name:
                # logger.error("vachina")

                self.player_controller = None
                self.show_hide()
        else:
            logger.error("THIS SHALL NOT BE REACHED")

        # logger.error(
        #     f"{self.player_manager.props.players}, {self.player_manager.props.player_names} \n {self.player_controller}: {'added' if player_name else 'removed'} {player.props.player_name if player else player_name.name}"
        # )

    def connect_player_controller(self):
        self.player_controller.connect(
            "metadata", lambda _, metadata: self.update_metadata(metadata)
        )
        self.player_controller.connect(
            "loop-status",
            lambda _, status: (
                self.media_loop.set_markup(
                    configuration.get_property("media_player_repeat_none_icon")
                    if status == Playerctl.LoopStatus.NONE
                    else configuration.get_property("media_player_repeat_playlist_icon")
                    if status == Playerctl.LoopStatus.PLAYLIST
                    else configuration.get_property("media_player_repeat_track_icon")
                ),
                self.media_loop.set_state(
                    state=UpperToPascal(get_enum_member_name(status, default="None"))
                ),
            ),
        )
        self.player_controller.connect(
            "shuffle",
            lambda _, status: self.media_shuffle.set_state(status),
        )
        self.player_controller.connect(
            "playback-status",
            lambda _, status: (
                self.media_play_pause.set_markup(
                    configuration.get_property("media_player_pause_icon")
                    if status == Playerctl.PlaybackStatus.PLAYING
                    else configuration.get_property("media_player_play_icon")
                ),
                self.media_play_pause.set_state(
                    status == Playerctl.PlaybackStatus.PLAYING
                ),
            ),
        )

    def show_hide(self):
        # logger.error("showhide")
        # if self.player_controller:
        #     # show = self.player_controller.props.can_play
        #     show = True
        #     # logger.error(f"anas {show}")
        # else:
        #     show = False
        #     # logger.warning(f"dicktionary {show}")
        show = self.player_controller is not None

        if show:
            # logger.warning("niggativity")
            if not self.playing:
                logger.debug("Player found!")
                self.on_show_hide(True)

            # self.children = self.media_controls
            self.reveal()
            self.main_container.remove_style_class("empty")
            self.playing = True

            self.update_metadata()
        else:
            if self.playing:
                logger.warning("No media is playing!")
                self.on_show_hide(False)

            # self.children = []
            self.unreveal()
            self.main_container.add_style_class("empty")
            self.playing = False

    def download_artwork(self, art_url, file_path):
        logger.debug(f"Caching artwork {file_path}")

        formatted_exec_shell_command(
            configuration.get_property("media_player_artwork_download_command"),
            url=art_url,
            path=file_path,
        )
        if path.exists(file_path):
            logger.debug("Applying artwork...")

            idle_add(
                self.artwork_image.set_from_pixbuf,
                GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    filename=file_path,
                    width=configuration.get_property("media_player_artwork_size"),
                    height=configuration.get_property("media_player_artwork_size"),
                    preserve_aspect_ratio=True,
                ),
            )
        else:
            logger.error("Failed to fetch artwork: {}", file_path)

    def update_artwork(self, art_url):
        self.artwork_image.set_from_pixbuf(
            GdkPixbuf.Pixbuf.new_from_file_at_scale(
                filename=f"{configuration.get_property('icons_dir')}/image-off.svg",
                width=configuration.get_property("media_player_no_artwork_icon_size"),
                height=configuration.get_property("media_player_no_artwork_icon_size"),
                preserve_aspect_ratio=True,
            )
        )

        if art_url != "":
            file_path = path.join(
                configuration.get_property("artwork_cache_dir"),
                art_url.split("/")[-1],
            )

            if path.exists(file_path):
                self.artwork_image.set_from_pixbuf(
                    GdkPixbuf.Pixbuf.new_from_file_at_scale(
                        filename=file_path,
                        width=configuration.get_property("media_player_artwork_size"),
                        height=configuration.get_property("media_player_artwork_size"),
                        preserve_aspect_ratio=True,
                    )
                )
                logger.debug(f"Applying cached artwork {file_path}")
            else:
                GLib.Thread.new(
                    "artwork-downloader",
                    self.download_artwork,
                    art_url,
                    file_path,
                )

    def metadata_get(self, metadata, key, default):
        if key in metadata.keys():
            return metadata[key]
        else:
            return default

    def update_metadata(self, metadata=None):
        if not self.player_controller:
            return
        elif not metadata:
            metadata = self.player_controller.props.metadata

        # for i in metadata.keys():
        #     logger.error(f"{i}: {metadata[i]}")

        if length := self.metadata_get(metadata, "mpris:length", None):
            self.length = length
        else:
            self.length = None

        if self.player_controller.props.can_go_next:
            self.media_next.set_sensitive(True)
        else:
            self.media_next.set_sensitive(False)

        if self.player_controller.props.can_go_previous:
            self.media_previous.set_sensitive(True)
        else:
            self.media_previous.set_sensitive(False)

        self.media_play_pause.set_markup(
            configuration.get_property("media_player_pause_icon")
            if self.player_controller.props.playback_status
            == Playerctl.PlaybackStatus.PLAYING
            else configuration.get_property("media_player_play_icon")
        )
        self.media_play_pause.set_state(
            self.player_controller.props.playback_status
            == Playerctl.PlaybackStatus.PLAYING
        )

        self.media_shuffle.set_state(self.player_controller.props.shuffle)

        self.media_loop.set_markup(
            configuration.get_property("media_player_repeat_none_icon")
            if self.player_controller.props.loop_status == Playerctl.LoopStatus.NONE
            else configuration.get_property("media_player_repeat_playlist_icon")
            if self.player_controller.props.loop_status == Playerctl.LoopStatus.PLAYLIST
            else configuration.get_property("media_player_repeat_track_icon")
        )
        self.media_loop.set_state(
            state=UpperToPascal(
                get_enum_member_name(
                    self.player_controller.props.loop_status, default="None"
                )
            )
        )

        self.title_label.set_label(
            title if (title := self.player_controller.get_title()) else "Unknown"
        )
        self.title_label.set_tooltip_text(
            title if (title := self.player_controller.get_title()) else "Unknown"
        )

        self.artist_album_label.set_label(
            f"{artist if (artist := self.player_controller.get_artist()) else 'Unknown'} 🞄 {album if (album := self.player_controller.get_album()) else 'Unknown'}"
        )
        self.artist_album_label.set_tooltip_text(
            f"{artist if (artist := self.player_controller.get_artist()) else 'Unknown'} 🞄 {album if (album := self.player_controller.get_album()) else 'Unknown'}"
        )

        self.update_artwork(self.metadata_get(metadata, "mpris:artUrl", ""))

    def add_style(self, style):
        self.main_container.add_style_class(style)

    def remove_style(self, style):
        self.main_container.remove_style_class(style)
