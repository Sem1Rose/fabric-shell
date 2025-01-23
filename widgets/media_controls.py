from config import configuration
import os.path as path

from loguru import logger
from widgets.rounded_image import RoundedImage
from widgets.toggle_button import ToggleButton, CycleToggleButton

from gi.repository import GdkPixbuf
from fabric import Fabricator
from fabric.widgets.box import Box
from fabric.widgets.image import Image
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.widgets.scale import Scale
from fabric.utils import exec_shell_command, exec_shell_command_async

playerctl = "playerctl -p spotify"


class MediaControls(Box):
    def __init__(self, **kwargs):
        super().__init__(
            spacing=configuration.get_setting("spacing"),
            orientation="v",
            name="media_controls_widget",
            **kwargs,
        )

        self.playing = True
        self.seeking = False
        self.length = 0

        def set_length(value):
            if value != "":
                self.length = float(value) / 10e5
            else:
                self.length = None

        Fabricator(
            poll_from=playerctl + r" metadata -F -f '{{ mpris:length }}'",
            interval=0,
            stream=True,
            on_changed=lambda _, v: set_length(v),
        )

        media_previous = Button(
            name="media_previous",
            label="",
            # image=Image(
            #     image_file=f"{configuration.icons_dir}/backward.svg",
            #     size=configuration.icon_size,
            # ),
            h_align="end",
        )
        media_previous.connect(
            "clicked",
            lambda *_: exec_shell_command_async(f"{playerctl} previous"),
        )

        media_next = Button(
            name="media_next",
            label="",
            # image=Image(
            #     image_file=f"{configuration.icons_dir}/forward.svg",
            #     size=configuration.icon_size,
            # ),
            h_align="end",
        )
        media_next.connect(
            "clicked",
            lambda *_: exec_shell_command_async(f"{playerctl} next"),
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
                on_changed=lambda _, value: button.set_label(
                    "" if value == "Playing" else ""
                ),
            )
        )
        media_play_pause.connect(
            "clicked",
            lambda *_: exec_shell_command_async(f"{playerctl} play-pause"),
        )

        media_shuffle = ToggleButton(name="media_shuffle", label="")
        media_shuffle.connect(
            "on_toggled",
            lambda *_: exec_shell_command_async(f"{playerctl} shuffle Toggle"),
        )

        media_loop = CycleToggleButton(
            name="media_loop",
            states=["None", "Playlist", "Track"],
        ).build(
            lambda cycle_toggle, _: Fabricator(
                poll_from=f"{playerctl} loop -F",
                interval=0,
                stream=True,
                default_value="",
                on_changed=lambda _, value: (
                    cycle_toggle.set_label(
                        "A" if value == "None" else "B" if value == "Playlist" else "C"
                    ),
                    cycle_toggle.set_state(state=value),
                ),
            )
        )
        media_loop.connect(
            "on_cycled",
            lambda cycle_toggle: exec_shell_command_async(
                f"{playerctl} loop {cycle_toggle.get_state()}"
            ),
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
            lambda scale, *_: seek_playback(scale),
        )

        def update_progress_box(box, visible):
            box.children = [media_progress] if visible else []

        progress_box = Box(h_expand=True).build(
            lambda box, _: Fabricator(
                poll_from=playerctl + r" -F -f '{{ mpris:length }}'",
                interval=0,
                stream=True,
                on_changed=lambda _, value: update_progress_box(box, value == ""),
            )
        )

        title_label = Label(
            name="media_title_label",
            h_expand=True,
            h_align="start",
            ellipsization="end",
        ).build(
            lambda label, _: Fabricator(
                poll_from=playerctl + r" metadata -F -f '{{ title }}'",
                interval=0,
                stream=True,
                on_changed=lambda _, v: label.set_label(v),
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
            lambda label, _: Fabricator(
                poll_from=playerctl + r" metadata -F -f '{{ artist }} 🞄 {{ album }}'",
                interval=0,
                stream=True,
                on_changed=lambda _, v: label.set_label(v),
            )
        )

        def download_artwork(button, art_url, file_path):
            exec_shell_command(f'curl -s "{art_url}" -o "{file_path}"')
            button.set_image(
                Image(
                    image_file=file_path, size=configuration.get_setting("artwork_size")
                )
            )

        def update_artwork(image, art_url):
            image.set_from_pixbuf(
                GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    filename=f"{configuration.get_setting('icons_dir')}/image-off.svg",
                    width=configuration.get_setting("no_artwork_icon_size"),
                    height=configuration.get_setting("no_artwork_icon_size"),
                    preserve_aspect_ratio=True,
                )
            )

            if art_url != "":
                file_path = path.join(
                    configuration.get_setting("artwork_cache_dir"),
                    art_url.split("/")[-1],
                )

                if path.exists(file_path):
                    image.set_from_pixbuf(
                        GdkPixbuf.Pixbuf.new_from_file_at_scale(
                            filename=file_path,
                            width=configuration.get_setting("artwork_size"),
                            height=configuration.get_setting("artwork_size"),
                            preserve_aspect_ratio=True,
                        )
                    )
                    logger.debug(f"Applying cached artwork {file_path}")
                else:
                    # TODO: find a way for this multithreading shit to work
                    # thread = GLib.Thread.new(
                    #     "artwork-downloader",
                    #     download_artwork,
                    #     image,
                    #     art_url,
                    #     file_path,
                    # )

                    # exec_shell_command_async(
                    #     f'curl -s "{art_url}" -o "{file_path}"',
                    #     lambda _: image.set_from_pixbuf(
                    #         GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    #             filename=file_path,
                    #             width=configuration.get_setting("artwork_size"),
                    #             height=configuration.get_setting("artwork_size"),
                    #             preserve_aspect_ratio=True,
                    #         )
                    #     ),
                    # )

                    logger.debug(f"Caching artwork {file_path}")
                    if (
                        exec_shell_command(f'curl -s "{art_url}" -o "{file_path}"')
                        is not False
                    ):
                        logger.debug("Applying artwork...")
                        image.set_from_pixbuf(
                            GdkPixbuf.Pixbuf.new_from_file_at_scale(
                                filename=file_path,
                                width=configuration.get_setting("artwork_size"),
                                height=configuration.get_setting("artwork_size"),
                                preserve_aspect_ratio=True,
                            )
                        )

        artwork_image = RoundedImage(
            name="media_artwork",
            image_file=f"{configuration.get_setting('icons_dir')}/image-off.svg",
            size=configuration.get_setting("no_artwork_icon_size"),
            h_expand=True,
        ).build(
            lambda image, _: Fabricator(
                poll_from=playerctl + r" metadata -F -f '{{ mpris:artUrl }}'",
                interval=0,
                stream=True,
                on_changed=lambda _, v: update_artwork(image, v),
            )
        )

        artwork_box = Box(
            name="media_artwork_box",
            orientation="h",
            size=configuration.get_setting("artwork_size"),
            children=[artwork_image],
        )

        self.widgets = [
            Box(
                # spacing=configuration.get_setting("spacing"),
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
                # spacing=configuration.get_setting("spacing"),
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
        ]

        def show_hide(show):
            if show:
                self.children = self.widgets
                self.remove_style_class("empty")
                self.playing = True
            else:
                self.children = []
                self.add_style_class("empty")
                self.playing = False

        Fabricator(
            poll_from=playerctl + r" metadata -F -f '{{ title }}'",
            interval=0,
            stream=True,
            default_value="",
            on_changed=lambda _, value: show_hide(value != ""),
        )
