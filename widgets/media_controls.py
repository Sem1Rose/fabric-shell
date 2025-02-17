import os.path as path
from loguru import logger
from config import configuration

from widgets.rounded_image import RoundedImage
from widgets.buttons import ToggleButton, CycleToggleButton, MarkupButton
from widgets.interactable_slider import Slider
from widgets.helpers.formatted_exec import formatted_exec_shell_command

from gi.repository import GdkPixbuf, GLib
from fabric import Fabricator
from fabric.widgets.box import Box
from fabric.widgets.revealer import Revealer
from fabric.widgets.label import Label
from fabric.core.service import Signal
from fabric.utils import exec_shell_command_async, idle_add


class MediaControls(Revealer):
    @Signal
    def on_show_hide(self, shown: bool): ...

    def __init__(
        self, transition_type="slide-down", transition_duration=200, *args, **kwargs
    ):
        super().__init__(
            transition_type=transition_type, transition_duration=transition_duration
        )

        self.playing = False
        self.seeking = False
        self.length = 0

        def set_length(value):
            if value != "":
                self.length = float(value) / 10e5
            else:
                self.length = None

        Fabricator(
            poll_from=configuration.get_property("playerctl_command")
            + r" metadata --follow -f '{{ mpris:length }}'",
            interval=0,
            stream=True,
            on_changed=lambda _, v: set_length(v),
        )

        media_previous = MarkupButton(
            name="media_previous",
            markup=configuration.get_property("media_player_previous_icon"),
            h_align="start",
        )
        media_previous.connect(
            "clicked",
            lambda *_: exec_shell_command_async(
                f"{configuration.get_property('playerctl_command')} previous"
            ),
        )

        media_next = MarkupButton(
            name="media_next",
            markup=configuration.get_property("media_player_next_icon"),
            h_align="end",
        )
        media_next.connect(
            "clicked",
            lambda *_: exec_shell_command_async(
                f"{configuration.get_property('playerctl_command')} next"
            ),
        )

        media_play_pause = ToggleButton(
            name="media_play_pause",
            h_align="end",
        ).build(
            lambda button, _: Fabricator(  # process
                poll_from=f"{configuration.get_property('playerctl_command')} status -F",
                interval=0,
                stream=True,
                default_value="",
                on_changed=lambda _, value: (
                    button.set_markup(
                        configuration.get_property("media_player_pause_icon")
                        if value == "Playing"
                        else configuration.get_property("media_player_play_icon")
                    ),
                    button.set_state(value == "Playing"),
                ),
            )
        )
        media_play_pause.connect(
            "on_toggled",
            lambda *_: exec_shell_command_async(
                f"{configuration.get_property('playerctl_command')} play-pause"
            ),
        )

        media_shuffle = ToggleButton(
            name="media_shuffle",
            markup=configuration.get_property("media_player_shuffle_icon"),
        ).build(
            lambda toggle, _: Fabricator(  # process
                poll_from=f"{configuration.get_property('playerctl_command')} shuffle -F",
                interval=0,
                stream=True,
                default_value="",
                on_changed=lambda _, value: toggle.set_state(value == "On"),
            )
        )
        media_shuffle.connect(
            "on_toggled",
            lambda *_: exec_shell_command_async(
                f"{configuration.get_property('playerctl_command')} shuffle Toggle"
            ),
        )

        media_loop = CycleToggleButton(
            name="media_loop",
            states=["None", "Playlist", "Track"],
        ).build(
            lambda cycle_toggle, _: Fabricator(  # process
                poll_from=f"{configuration.get_property('playerctl_command')} loop -F",
                interval=0,
                stream=True,
                default_value="",
                on_changed=lambda _, value: (
                    cycle_toggle.set_markup(
                        configuration.get_property("media_player_repeat_none_icon")
                        if value == "None"
                        else configuration.get_property(
                            "media_player_repeat_playlist_icon"
                        )
                        if value == "Playlist"
                        else configuration.get_property(
                            "media_player_repeat_track_icon"
                        )
                    ),
                    cycle_toggle.set_state(state=value),
                ),
            )
        )
        media_loop.connect(
            "on_cycled",
            lambda cycle_toggle, *_: exec_shell_command_async(
                f"{configuration.get_property('playerctl_command')} loop {cycle_toggle.get_state()}"
            ),
        )

        def seek_playback(value):
            if self.length is not None:
                exec_shell_command_async(
                    f"{configuration.get_property('playerctl_command')} position {value * self.length}"
                )

        media_progress = Slider(
            name="media_progress",
            h_expand=True,
            draw_value=False,
            orientation="h",
            poll_command=f"{configuration.get_property('playerctl_command')} position",
            poll_value_processor=lambda v: (
                float(v) / self.length if self.length is not None else 0
            ),
            poll_interval=500,
            poll_stream=False,
            animation_duration=0.5,
        )
        media_progress.connect(
            "on_interacted",
            lambda _, value: seek_playback(value),
        )

        progress_box = Box(h_expand=True, children=[media_progress])

        title_label = Label(
            name="media_title_label",
            h_expand=True,
            h_align="start",
            ellipsization="end",
        ).build(
            lambda label, _: Fabricator(  # process
                poll_from=configuration.get_property("playerctl_command")
                + r" metadata -F -f '{{ title }}'",
                interval=0,
                stream=True,
                on_changed=lambda _, v: (label.set_label(v), label.set_tooltip_text(v)),
            )
        )

        artist_album_label = Label(
            name="media_artist_album_label",
            h_expand=False,
            h_align="start",
            justification="start",
            # line_wrap="word",
            ellipsization="end",
        ).build(
            lambda label, _: Fabricator(  # process
                poll_from=configuration.get_property("playerctl_command")
                + r" metadata -F -f '{{ artist }} 🞄 {{ album }}'",
                interval=0,
                stream=True,
                on_changed=lambda _, v: (label.set_label(v), label.set_tooltip_text(v)),
            )
        )

        def download_artwork(image, art_url, file_path):
            logger.debug(f"Caching artwork {file_path}")

            formatted_exec_shell_command(
                configuration.get_property("media_player_artwork_download_command"),
                url=art_url,
                path=file_path,
            )
            if path.exists(file_path):
                logger.debug("Applying artwork...")

                idle_add(
                    image.set_from_pixbuf,
                    GdkPixbuf.Pixbuf.new_from_file_at_scale(
                        filename=file_path,
                        width=configuration.get_property("media_player_artwork_size"),
                        height=configuration.get_property("media_player_artwork_size"),
                        preserve_aspect_ratio=True,
                    ),
                )
            else:
                logger.error("Failed to fetch artwork: {}", file_path)

        def update_artwork(image, art_url):
            image.set_from_pixbuf(
                GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    filename=f"{configuration.get_property('icons_dir')}/image-off.svg",
                    width=configuration.get_property(
                        "media_player_no_artwork_icon_size"
                    ),
                    height=configuration.get_property(
                        "media_player_no_artwork_icon_size"
                    ),
                    preserve_aspect_ratio=True,
                )
            )

            if art_url != "":
                file_path = path.join(
                    configuration.get_property("artwork_cache_dir"),
                    art_url.split("/")[-1],
                )

                if path.exists(file_path):
                    image.set_from_pixbuf(
                        GdkPixbuf.Pixbuf.new_from_file_at_scale(
                            filename=file_path,
                            width=configuration.get_property(
                                "media_player_artwork_size"
                            ),
                            height=configuration.get_property(
                                "media_player_artwork_size"
                            ),
                            preserve_aspect_ratio=True,
                        )
                    )
                    logger.debug(f"Applying cached artwork {file_path}")
                else:
                    GLib.Thread.new(
                        "artwork-downloader",
                        download_artwork,
                        image,
                        art_url,
                        file_path,
                    )

        artwork_image = RoundedImage(
            name="media_artwork",
            image_file=f"{configuration.get_property('icons_dir')}/image-off.svg",
            size=configuration.get_property("media_player_no_artwork_icon_size"),
            h_expand=True,
        ).build(
            lambda image, _: Fabricator(  # process
                poll_from=configuration.get_property("playerctl_command")
                + r" metadata -F -f '{{ mpris:artUrl }}'",
                interval=0,
                stream=True,
                on_changed=lambda _, v: update_artwork(image, v),
            )
        )

        artwork_box = Box(
            name="media_artwork_box",
            orientation="h",
            size=configuration.get_property("media_player_artwork_size"),
            children=[artwork_image],
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
                        artwork_box,
                        Box(
                            h_expand=True,
                            orientation="v",
                            children=[
                                Box(v_expand=True),
                                title_label,
                                artist_album_label,
                                Box(v_expand=True),
                            ],
                        ),
                        Box(
                            v_expand=True,
                            h_expand=True,
                            orientation="v",
                            children=[
                                Box(v_expand=True),
                                media_play_pause,
                                Box(v_expand=True),
                            ],
                        ),
                    ],
                ),
                Box(
                    orientation="h",
                    h_expand=True,
                    children=[
                        media_previous,
                        media_shuffle,
                        progress_box,
                        media_loop,
                        media_next,
                    ],
                ),
            ],
            *args,
            **kwargs,
        )
        self.children = self.main_container

        def show_hide(show):
            if show:
                if not self.playing:
                    logger.debug("Player found!")
                    self.on_show_hide(True)

                # self.children = self.media_controls
                self.reveal()
                self.main_container.remove_style_class("empty")
                self.playing = True
            else:
                if self.playing:
                    logger.warning("No media is playing!")
                    self.on_show_hide(False)

                # self.children = []
                self.unreveal()
                self.main_container.add_style_class("empty")
                self.playing = False

        show_hide(False)

        Fabricator(
            poll_from=configuration.get_property("playerctl_command")
            + r" metadata --follow -f '{{ title }}'",
            interval=0,
            stream=True,
            on_changed=lambda _, value: show_hide(value != ""),
        )

    def add_style(self, style):
        self.main_container.add_style_class(style)

    def remove_style(self, style):
        self.main_container.remove_style_class(style)
