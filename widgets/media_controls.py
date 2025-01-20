from config import configuration
import os.path as path
import threading

from fabric import Fabricator
from fabric.widgets.box import Box
from fabric.widgets.image import Image
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.widgets.scale import Scale
from fabric.utils import exec_shell_command, exec_shell_command_async
# from gi.repository import GLib

playerctl = "playerctl -p spotify"


class MediaControls(Box):
    # def progress(self) -> float:
    #     return self._progress

    # def progress(self, value: float):
    #     self._progress = value
    #     # self.progress_changed(value)

    def __init__(self, **kwargs):
        super().__init__(
            spacing=configuration.spacing,
            orientation="v",
            name="media_player",
            **kwargs,
        )

        # self.playing = False
        # self.poll_progress = False
        # self.polls = 0
        self.seeking = False
        # self.max_polls = 10
        # self.progress = 0
        # self.length = 1000000

        # exec_shell_command_async(r'playerctl metadata -f "{{mpris:length}}"', self.set_length)

        # def set_progress(progress):
        #     self.progress = float(progress)

        # Fabricator(
        #     poll_from=r"playerctl position",
        #     interval=500,
        #     default_value=0,
        #     on_changed=lambda _, value: set_progress(value),
        # )

        # Fabricator(
        #     poll_from=r"playerctl status -F",
        #     interval=0,
        #     stream=True,
        #     default_value="",
        #     on_changed=lambda _, value: self.set_playing(value == "Playing"),
        # )

        Fabricator(
            poll_from=f"{playerctl}" + r" metadata -F -f '{{ title }}'",
            interval=0,
            stream=True,
            default_value="",
            on_changed=lambda _, value: self.process_media(value),
        )

    # def poll_progress(self, value):
    #     print(self.progress)
    #     if self.poll_progress:
    #         self.poll_progress = False
    #         self.progress = float(value)
    #     else:
    #         self.polls += 1
    #         self.progress = self.progress + 0.5
    #         if self.polls == self.max_polls:
    #             self.polls = 0
    #             self.poll_progress = True

    # def set_length(self, length):
    #     self.length = float(length) / 1000000.0
    #     # self.process_media(" ")

    def process_media(self, media):
        if media == "":
            self.clear_children()
        else:
            self.remove_style_class("empty")
            [art_url, artist, album, title, length, _] = exec_shell_command(
                f"{playerctl}"
                + r" metadata -f '{{ mpris:artUrl }}|{{ artist }}|{{ album }}|{{ title }}|{{ mpris:length }}|'"
            ).split("|")

            artwork_box = Button(
                name="artwork_box",
                orientation="h",
                size=configuration.artwork_size,
            )

            artwork_box.set_image(
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
                    artwork_box.set_image(
                        Image(image_file=file_path, size=configuration.artwork_size)
                    )
                else:
                    threading.Thread(
                        target=self.download_artwork, args=(art_url, file_path)
                    ).start()

            media_play_pause = Button(
                name="media_play_pause",
                h_align="end",
            )
            media_play_pause.connect(
                "button-release-event",
                lambda _, value: exec_shell_command_async(f"{playerctl} play-pause"),
            )
            media_play_pause.build(
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

            # print(length)
            if length != "":
                self.seeking = False
                length = float(length) / 10e5

                def change_value(fabricator, scale, value):
                    # pass
                    if not self.seeking:
                        scale.set_value(value)

                def seek():
                    self.seeking = True

                media_progress = Scale(
                    name="media_progress",
                    h_expand=True,
                    draw_value=False,
                    orientation="h",
                    # value=self.progress / length,
                )
                media_progress.connect("button-press-event", lambda *_: seek())
                media_progress.connect(
                    "button-release-event",
                    lambda scale, _: self.seek_playback(scale, length),
                )

                media_progress.build(
                    lambda scale, _: Fabricator(
                        poll_from=f"{playerctl} position",
                        interval=500,
                        default_value=0,
                        on_changed=lambda fabricator, value: change_value(
                            fabricator, scale, float(value) / length
                        ),
                    )
                )
            else:
                self.seeking = True
                media_progress = Box(h_expand=True)

            artist_album = Box(
                name="media_artist_album",
                spacing=configuration.spacing,
                orientation="h",
                children=[
                    Label(artist),
                ],
                h_align="start",
            )

            if album != "":
                artist_album.add(Label("·"))
                artist_album.add(Label(album))

            self.children = [
                Box(
                    spacing=configuration.spacing,
                    orientation="h",
                    h_expand=True,
                    v_expand=True,
                    children=[
                        artwork_box,
                        # Box(
                        #     spacing=configuration.spacing,
                        #     orientation="v",
                        #     children=[
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
                                        Label(
                                            name="media_title",
                                            label=title,
                                            h_align="start",
                                        ),
                                        Box(v_expand=True),
                                        artist_album,
                                    ],
                                ),
                            ],
                        ),
                        # ],
                        # ),
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
                        media_progress,
                        media_next,
                    ],
                ),
            ]

    def clear_children(self):
        self.children = []
        self.add_style_class("empty")

    def download_artwork(self, art_url, file_path):
        exec_shell_command(f'curl -s "{art_url}" -o "{file_path}"')
        exec_shell_command(
            f"fabric-cli execute {configuration.app_name} 'bar.pill.media_controls_widget.process_media(\" \")'"
        )

    def seek_playback(self, scale, length):
        self.seeking = False
        exec_shell_command_async(f"{playerctl} position {scale.value * length}")
