from config import configuration
import os.path as path

from loguru import logger

from gi.repository import GLib
from fabric import Fabricator
from fabric.widgets.box import Box
from fabric.widgets.image import Image
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.widgets.scale import Scale, ScaleMark
from fabric.utils import exec_shell_command, exec_shell_command_async

playerctl = "playerctl -p spotify"


class MediaControls(Box):
    def __init__(self, **kwargs):
        super().__init__(
            spacing=configuration.spacing,
            orientation="v",
            name="media_player",
            **kwargs,
        )

        self.seeking = False
        self.length = 0

        def set_length(value):
            if value != "":
                self.length = float(value) / 10e5
            else:
                self.length = None

        Fabricator(
            poll_from=f"{playerctl}" + r" metadata -F -f '{{ mpris:length }}'",
            interval=0,
            stream=True,
            on_changed=lambda _, v: set_length(v),
        )

        media_previous = Button(
            name="media_previous",
            image=Image(
                image_file=f"{configuration.icons_dir}/backward.svg",
                size=configuration.icon_size,
            ),
            h_align="end",
        )
        media_previous.connect(
            "button-release-event",
            lambda *_: exec_shell_command_async(f"{playerctl} previous"),
        )

        media_next = Button(
            name="media_next",
            image=Image(
                image_file=f"{configuration.icons_dir}/forward.svg",
                size=configuration.icon_size,
            ),
            h_align="end",
        )
        media_next.connect(
            "button-release-event",
            lambda _, value: exec_shell_command_async(f"{playerctl} next"),
        )

        media_play_pause = Button(
            name="media_play_pause",
            h_align="end",
        ).build(
            lambda button, _: Fabricator(
                poll_from=f"{playerctl} status -F",
                interval=0,
                stream=True,
                default_value="",
                on_changed=lambda _, value: button.set_image(
                    Image(
                        f"{configuration.icons_dir}/pause.svg"
                        if value == "Playing"
                        else f"{configuration.icons_dir}/play.svg",
                        size=configuration.icon_size,
                    )
                ),
            )
        )
        media_play_pause.connect(
            "button-release-event",
            lambda _, value: exec_shell_command_async(f"{playerctl} play-pause"),
        )

        def change_value(value):
            if not self.seeking and value is not None:
                media_progress.set_value(value)

        def seek():
            self.seeking = True
            media_progress.draw_value = True

        def seek_playback(scale):
            if self.length is not None:
                self.seeking = False
                exec_shell_command_async(
                    f"{playerctl} position {scale.value * self.length}"
                )

        media_progress = Scale(
            name="media_progress",
            h_expand=True,
            draw_value=False,
            orientation="h",
        ).build(
            lambda scale, _: Fabricator(
                poll_from=f"{playerctl} position",
                interval=500,
                default_value=0,
                on_changed=lambda _, value: change_value(float(value) / self.length),
            )
        )
        media_progress.connect("button-press-event", lambda *_: seek())
        media_progress.connect(
            "button-release-event",
            lambda scale, _: seek_playback(scale),
        )

        def update_progress_box(box, visible):
            box.children = [media_progress] if visible else []

        progress_box = Box(h_expand=True).build(
            lambda box, _: Fabricator(
                poll_from=f"{playerctl}" + r" -F -f '{{ mpris:length }}'",
                interval=0,
                stream=True,
                on_changed=lambda _, value: update_progress_box(box, value == ""),
            )
        )

        title_label = Button(label="", name="media_title_label", h_align="start").build(
            lambda button, _: Fabricator(
                poll_from=f"{playerctl}" + r" metadata -F -f '{{ title }}'",
                interval=0,
                stream=True,
                on_changed=lambda _, v: button.set_label(v),
            )
        )

        artist_label = Button(label="", name="media_artist_label").build(
            lambda button, _: Fabricator(
                poll_from=f"{playerctl}" + r" metadata -F -f '{{ artist }}'",
                interval=0,
                stream=True,
                on_changed=lambda _, v: button.set_label(v),
            )
        )

        album_label = Button(label="", name="media_album_label").build(
            lambda button, _: Fabricator(
                poll_from=f"{playerctl}" + r" metadata -F -f '{{ album }}'",
                interval=0,
                stream=True,
                on_changed=lambda _, v: button.set_label(v),
            )
        )

        def download_artwork(button, art_url, file_path):
            exec_shell_command(f'curl -s "{art_url}" -o "{file_path}"')
            button.set_image(
                Image(image_file=file_path, size=configuration.artwork_size)
            )

        def update_artwork(button, art_url):
            button.set_image(
                Image(
                    image_file=f"{configuration.icons_dir}/image-off.svg",
                    size=configuration.no_artwork_icon_size,
                )
            )

            if art_url != "":
                file_path = path.join(
                    configuration.artwork_cache_dir, art_url.split("/")[-1]
                )

                # print(file_path)

                if path.exists(file_path):
                    button.set_image(
                        Image(image_file=file_path, size=configuration.artwork_size)
                    )
                else:
                    # TODO: find a way for this multithreading shit to work
                    # thread = GLib.Thread.new(
                    #     "artwork-downloader",
                    #     download_artwork,
                    #     button,
                    #     art_url,
                    #     file_path,
                    # )
                    # exec_shell_command_async(
                    #     f'curl -s "{art_url}" -o "{file_path}"',
                    #     lambda _: self.artwork_box.set_image(
                    #         Image(
                    #             image_file=f"{configuration.icons_dir}/image-off.svg",
                    #             size=configuration.no_artwork_icon_size,
                    #         )
                    #     ),
                    # )
                    if (
                        exec_shell_command(f'curl -s "{art_url}" -o "{file_path}"')
                        is not False
                    ):
                        button.set_image(
                            Image(image_file=file_path, size=configuration.artwork_size)
                        )

        artwork_box = Button(
            name="artwork_box",
            orientation="h",
            size=configuration.artwork_size,
        ).build(
            lambda button, _: Fabricator(
                poll_from=f"{playerctl}" + r" metadata -F -f '{{ mpris:artUrl }}'",
                interval=0,
                stream=True,
                on_changed=lambda _, v: update_artwork(button, v),
            )
        )
        artwork_box.set_image(
            Image(
                image_file=f"{configuration.icons_dir}/image-off.svg",
                size=configuration.no_artwork_icon_size,
            )
        )

        self.widgets = [
            Box(
                spacing=configuration.spacing,
                orientation="h",
                h_expand=True,
                v_expand=True,
                children=[
                    artwork_box,
                    Box(
                        v_expand=True,
                        h_expand=True,
                        orientation="h",
                        spacing=configuration.spacing,
                        children=[
                            Box(
                                h_expand=True,
                                orientation="v",
                                children=[
                                    Box(v_expand=True),
                                    title_label,
                                    Box(v_expand=True),
                                    Box(
                                        name="media_artist_album",
                                        spacing=configuration.spacing,
                                        orientation="h",
                                        children=[
                                            artist_label,
                                            Label("·"),
                                            album_label,
                                        ],
                                        h_align="start",
                                    ),
                                ],
                            ),
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
                spacing=configuration.spacing,
                orientation="h",
                h_expand=True,
                children=[
                    media_previous,
                    progress_box,
                    media_next,
                ],
            ),
        ]

        def show_hide(show):
            if show:
                self.children = self.widgets
                self.remove_style_class("empty")
            else:
                self.children = []
                self.add_style_class("empty")

        Fabricator(
            poll_from=f"{playerctl}" + r" metadata -F -f '{{ title }}'",
            interval=0,
            stream=True,
            default_value="",
            on_changed=lambda _, value: show_hide(value != ""),
        )
