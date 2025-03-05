import gi
import math
import os.path as path
from loguru import logger
from config import configuration

from widgets.rounded_image import RoundedImage
from widgets.buttons import ToggleButton, CycleToggleButton, MarkupButton
from widgets.interactable_slider import Slider
from widgets.helpers.formatted_exec import formatted_exec_shell_command
from widgets.helpers.str import UpperToPascal

# from fabric import Fabricator
from fabric.widgets.box import Box
from fabric.widgets.stack import Stack
from fabric.widgets.revealer import Revealer
from fabric.widgets.label import Label
from fabric.core.service import Signal
from fabric.utils import idle_add, get_enum_member, get_enum_member_name

gi.require_version("Playerctl", "2.0")
from gi.repository import GdkPixbuf, GLib, Playerctl  # noqa: E402


class MediaPlayer(Revealer):
    @Signal
    def on_show_hide(self, shown: bool): ...

    def __init__(
        self, transition_type="slide-down", transition_duration=200, *args, **kwargs
    ):
        super().__init__(
            transition_type=transition_type, transition_duration=transition_duration
        )

        self.player_manager = Playerctl.PlayerManager.new()
        self.can_reveal = False
        self.player_controllers = {}
        self.selected_player = 0
        self.max_num_tabs = 7

        self.media_controls_stack = Stack(
            transition_type="slide-left-right", transition_duration=200
        )
        self.tabs = [
            MarkupButton(style_classes="tab_button") for _ in range(self.max_num_tabs)
        ]
        self.tab_holder = Box(name="tabs_holder", children=self.tabs)
        self.main_container = Box(
            name="media_player_widget",
            orientation="v",
            children=[
                self.media_controls_stack,
                Box(
                    children=[
                        Box(h_expand=True),
                        self.tab_holder,
                        Box(h_expand=True),
                    ]
                ),
            ],
            *args,
            **kwargs,
        )

        for tab in self.tabs:
            tab.set_sensitive(False)
            tab.add_style_class("empty")

            tab.connect("clicked", lambda tab: self.handle_tab_press(tab))
        for tab in [0, self.max_num_tabs - 1]:
            self.tabs[tab].add_style_class("hidden")

        self.add(self.main_container)

        self.player_manager.connect(
            "name-appeared",
            lambda _, name: self.handle_manager_events(player_name=name),
        )

        for player_name in [
            name
            for name in self.player_manager.props.player_names
            if name.name in configuration.get_property("media_player_allowed_players")
        ]:
            self.handle_manager_events(player_name=player_name)

        self.show_hide()

    def handle_manager_events(self, player=None, player_name=None):
        # player_name != None -> adding a player
        # player != None -> removing a player
        if player is None and player_name is None:
            logger.error("Either player or name must not be none")
            return
        elif player is not None and player_name is not None:
            logger.error("Either player or name must be none")
            return

        if player_name:
            name = player_name.name
            if name in self.player_controllers:
                logger.warning("Already added")
                return

            if name in configuration.get_property("media_player_allowed_players"):
                logger.debug(f'Adding "{name}" to media players')

                player_controller = Playerctl.Player.new_from_name(player_name)
                self.player_manager.manage_player(player_controller)
                # self.player_manager.move_player_to_top(player_controller)

                player_controller.connect(
                    "exit", lambda player: self.handle_manager_events(player=player)
                )

                self.add_player(player_controller)
                self.show_hide()
            else:
                logger.warning(f"Player {name} is available but won't be managed")
        elif player:
            logger.debug(f'Removing "{player.props.player_name}" from media players')

            self.remove_player(player)
            self.show_hide()
        else:
            logger.error("THIS SHALL NOT BE REACHED")

        # logger.error(
        #     f"{self.player_manager.props.players}, {self.player_manager.props.player_names} \n {self.player_controller}: {'added' if player_name else 'removed'} {player.props.player_name if player else player_name.name}"
        # )

    def show_hide(self):
        # show = self.player_controller is not None
        show = len(self.player_controllers) != 0

        if show:
            if not self.can_reveal:
                logger.debug("Player found!")
                self.on_show_hide(True)
                self.can_reveal = True

            # self.reveal()
            self.main_container.remove_style_class("empty")

            # self.update_metadata()
        else:
            if self.can_reveal:
                logger.warning("No media is playing!")
                self.on_show_hide(False)
                self.can_reveal = False

            # self.unreveal()
            self.main_container.add_style_class("empty")

    def add_player(self, player):
        name = player.props.player_name

        media_controls = MediaControls(player)
        media_controls.update_metadata()

        if len(self.player_controllers) == 0:
            self.media_controls_stack.children = []

        self.media_controls_stack.add(media_controls)
        self.player_controllers[name] = (player, media_controls)

        mid = math.floor(self.max_num_tabs / 2.0)
        if len(self.player_controllers) - self.selected_player <= mid:
            id = len(self.player_controllers) - 1 - self.selected_player + mid

            if id != 0 and id != self.max_num_tabs - 1:
                self.tabs[id].set_sensitive(True)
                self.tabs[id].remove_style_class("hidden")

            if id == mid:
                self.tabs[id].add_style_class("active")

            self.tabs[id].remove_style_class("empty")
            self.tabs[id].set_markup(
                configuration.get_property("media_player_allowed_players")[name]
            )
            self.tabs[id].set_tooltip_markup(name)

    def remove_player(self, player):
        name = player.props.player_name
        if name not in self.player_controllers:
            return

        index = list(self.player_controllers).index(name)
        _, media_controls = self.player_controllers.pop(name)

        if len(self.player_controllers) > 0:
            if index == self.selected_player:
                new_index = (
                    index
                    if index + 1 <= len(self.player_controllers)
                    else index - 1
                    if index > 0
                    else 0
                )
                self.media_controls_stack.set_visible_child(
                    list(self.player_controllers.values())[new_index][1],
                )
            self.media_controls_stack.remove(media_controls)

        if (
            length := len(self.player_controllers)
        ) > 0 and self.selected_player >= length:
            self.selected_player = len(self.player_controllers) - 1

        for i in range(1, self.max_num_tabs - 1):
            pos = i - math.floor(self.max_num_tabs / 2.0)

            if self.selected_player + pos < 0 or self.selected_player + pos >= len(
                self.player_controllers
            ):
                self.tabs[i].set_sensitive(False)
                self.tabs[i].set_markup("")
                self.tabs[i].set_tooltip_markup("")
                self.tabs[i].add_style_class("empty")
            else:
                self.tabs[i].set_sensitive(True)
                self.tabs[i].set_markup(
                    configuration.get_property("media_player_allowed_players")[
                        list(self.player_controllers)[self.selected_player + pos]
                    ]
                )
                self.tabs[i].set_tooltip_markup(
                    list(self.player_controllers)[self.selected_player + pos]
                )
                self.tabs[i].remove_style_class("empty")

    def handle_tab_press(self, tab):
        index = self.tabs.index(tab)
        mid = math.floor(self.max_num_tabs / 2.0)

        if index in [0, self.max_num_tabs - 1, mid]:
            return
        else:
            self.cycle_active_player(index - mid)

    def cycle_active_player(self, amount=1):
        if amount == 0:
            return

        forward = amount > 0
        if forward:
            if self.selected_player + amount >= len(self.player_controllers):
                amount = len(self.player_controllers) - self.selected_player - 1
        else:
            if self.selected_player - amount < 0:
                amount = self.selected_player
        forward = amount > 0

        def goto_thread():
            for _ in range(abs(amount)):
                idle_add(self.cycle, forward)

                GLib.usleep(100 * 1000)

        GLib.Thread.new("goto_thread", goto_thread)

    def cycle(self, forward=True):
        mid = math.floor(self.max_num_tabs / 2.0)
        if forward:
            self.selected_player += 1
            self.tab_holder.reorder_child(self.tabs[0], self.max_num_tabs - 1)

            first = self.tabs[0]
            for i in range(self.max_num_tabs - 1):
                self.tabs[i] = self.tabs[i + 1]
            self.tabs[-1] = first

            new = self.selected_player + math.floor(self.max_num_tabs / 2.0) - 1
            if new < len(self.player_controllers):
                self.tabs[-2].set_markup(
                    configuration.get_property("media_player_allowed_players")[
                        list(self.player_controllers)[new]
                    ]
                )
                self.tabs[-2].set_tooltip_markup(list(self.player_controllers)[new])
                self.tabs[-2].set_sensitive(True)
                self.tabs[-2].remove_style_class("empty")

            self.tabs[mid].add_style_class("active")
            self.tabs[mid - 1].remove_style_class("active")
        else:
            self.selected_player -= 1
            self.tab_holder.reorder_child(self.tabs[-1], 0)

            last = self.tabs[-1]
            for i in range(self.max_num_tabs - 1, 0, -1):
                self.tabs[i] = self.tabs[i - 1]
            self.tabs[0] = last

            new = self.selected_player - math.floor(self.max_num_tabs / 2.0) + 1
            if new >= 0:
                self.tabs[1].set_markup(
                    configuration.get_property("media_player_allowed_players")[
                        list(self.player_controllers)[new]
                    ]
                )
                self.tabs[1].set_tooltip_markup(list(self.player_controllers)[new])
                self.tabs[1].set_sensitive(True)
                self.tabs[1].remove_style_class("empty")

            self.tabs[mid].add_style_class("active")
            self.tabs[mid + 1].remove_style_class("active")

        for i in [0, self.max_num_tabs - 1]:
            self.tabs[i].set_sensitive(False)
            self.tabs[i].add_style_class("hidden")
            self.tabs[i].add_style_class("empty")
        for i in [1, self.max_num_tabs - 2]:
            self.tabs[i].remove_style_class("hidden")

        self.media_controls_stack.set_visible_child(
            list(self.player_controllers.values())[self.selected_player][1]
        )

    def add_style(self, style):
        self.main_container.add_style_class(style)

    def remove_style(self, style):
        self.main_container.remove_style_class(style)


class MediaControls(Box):
    def __init__(self, player_controller, *args, **kwargs):
        super().__init__(orientation="v", *args, **kwargs)
        self.add_style_class("media_controls")

        self.player_controller = player_controller
        self.playing = False
        self.length = 0

        self.media_previous = MarkupButton(
            name="media_previous",
            markup=configuration.get_property("media_player_previous_icon"),
            h_align="start",
        )
        self.media_previous.connect(
            "clicked",
            lambda *_: self.player_controller.previous(),
        )

        self.media_next = MarkupButton(
            name="media_next",
            markup=configuration.get_property("media_player_next_icon"),
            h_align="end",
        )
        self.media_next.connect(
            "clicked",
            lambda *_: self.player_controller.next(),
        )

        self.media_play_pause = ToggleButton(
            name="media_play_pause",
            h_align="end",
        )
        self.media_play_pause.connect(
            "on_toggled",
            lambda *_: self.player_controller.play_pause(),
        )

        self.media_shuffle = ToggleButton(
            name="media_shuffle",
            # markup=configuration.get_property("media_player_shuffle_icon"),
        )
        self.media_shuffle.connect(
            "on_toggled",
            lambda toggle, *_: self.player_controller.set_shuffle(toggle.toggled),
        )

        self.media_loop = CycleToggleButton(
            name="media_loop",
            states=["None", "Playlist", "Track"],
        )
        self.media_loop.connect(
            "on_cycled",
            lambda cycle_toggle, *_: self.player_controller.set_loop_status(
                get_enum_member(Playerctl.LoopStatus, cycle_toggle.get_state())
            ),
        )

        def seek_playback(value):
            if self.player_controller and self.length:
                self.player_controller.set_position(int(value * self.length))

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
            poll_command=try_get_position,
            poll_value_processor=lambda v: (
                (v / self.length) if self.length != 0 else 0
            ),
            poll_interval=500,
            poll_stream=False,
            animation_duration=0.5,
        )
        self.media_progress.connect(
            "on_interacted",
            lambda _, value: seek_playback(value),
        )

        self.title_label = Label(
            name="media_title_label",
            h_expand=True,
            h_align="start",
            ellipsization="end",
        )

        self.artist_album_label = Label(
            name="media_artist_album_label",
            h_expand=False,
            h_align="start",
            justification="start",
            # line_wrap="word",
            ellipsization="end",
        )

        self.artwork_image = RoundedImage(
            name="media_artwork",
            image_file=f"{configuration.get_property('icons_dir')}/image-off.svg",
            size=configuration.get_property("media_player_no_artwork_icon_size"),
            h_expand=True,
        )

        self.artwork_box = Box(
            name="media_artwork_box",
            orientation="h",
            size=configuration.get_property("media_player_artwork_size"),
            children=[self.artwork_image],
        )

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
            lambda _, status: (
                self.media_shuffle.set_markup(
                    configuration.get_property("media_player_shuffle_icon")
                    if status
                    else configuration.get_property("media_player_no_shuffle_icon")
                ),
                self.media_shuffle.set_state(status),
            ),
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

        self.children = [
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
                    self.media_loop,
                    self.media_next,
                ],
            ),
        ]

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

    def update_artwork(self, data):
        self.artwork_image.set_from_pixbuf(
            GdkPixbuf.Pixbuf.new_from_file_at_scale(
                filename=f"{configuration.get_property('icons_dir')}/image-off.svg",
                width=configuration.get_property("media_player_no_artwork_icon_size"),
                height=configuration.get_property("media_player_no_artwork_icon_size"),
                preserve_aspect_ratio=True,
            )
        )

        if data != "":
            if data.startswith("file://"):
                file_path = data.replace("file://", "")
            else:
                file_path = path.join(
                    configuration.get_property("artwork_cache_dir"),
                    data.split("/")[-1],
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
                    data,
                    file_path,
                )

    def metadata_get(self, metadata, key, default):
        if key in metadata.keys():
            return metadata[key]
        else:
            return default

    def update_metadata(self, metadata=None):
        if not metadata:
            metadata = self.player_controller.props.metadata

        # for i in metadata.keys():
        #     logger.error(f"{i}: {metadata[i]}")

        if length := self.metadata_get(metadata, "mpris:length", None):
            self.length = length
        else:
            self.length = 0

        # logger.warning(
        #     f"control:{self.player_controller.props.can_control} next:{self.player_controller.props.can_go_next} previous:{self.player_controller.props.can_go_previous} pause:{self.player_controller.props.can_pause} play:{self.player_controller.props.can_play} seek:{self.player_controller.props.can_seek}"
        # )

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

        self.media_shuffle.set_markup(
            configuration.get_property("media_player_shuffle_icon")
            if self.player_controller.props.shuffle
            else configuration.get_property("media_player_no_shuffle_icon")
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
            f"{', '.join(artists) if (artists := self.metadata_get(metadata, 'xesam:artist', None)) else artist if (artist := self.player_controller.get_artist()) else 'Unknown'} 🞄 {album if (album := self.player_controller.get_album()) else 'Unknown'}"
        )

        self.update_artwork(self.metadata_get(metadata, "mpris:artUrl", ""))
