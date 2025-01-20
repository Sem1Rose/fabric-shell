from config import configuration
import os.path as path
# import threading

from loguru import logger

from gi.repository import GLib
from fabric import Fabricator
from fabric.widgets.box import Box
from fabric.widgets.image import Image
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.widgets.scale import Scale
from fabric.utils import exec_shell_command, exec_shell_command_async
# from fabric.core.service import Service, Signal, Property
# from gi.repository import GLib

playerctl = "playerctl -p spotify"


# class MetadataService(Service):
#     @Signal
#     def metadata_changed(self, new_metadata: str): ...

#     @Property(str, flags="read-write")
#     def metadata(self) -> str:
#         return self._metadata

#     @metadata.setter
#     def metadata(self, value: str):
#         self._metadata = value
#         self.metadata_changed(value)

#     def update_metadata(self, value):
#         # [art_url, artist, album, title, length, _] = value.split('|')
#         self.metadata = value

#     def __init__(self):
#         super().__init__()
#         self._name = []

#         Fabricator(
#             poll_from=f"{playerctl}"
#             + r" metadata -f '{{ mpris:artUrl }}|{{ artist }}|{{ album }}|{{ title }}|{{ mpris:length }}|'",
#             interval=0,
#             stream=True,
#             on_changed=lambda _, v: self.update_metadata(v),
#         )


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
        media_progress.connect(
            "button-release-event",
            lambda scale, _: self.seek_playback(scale),
        )
        media_progress.connect("button-press-event", lambda *_: seek())

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
            # x = exec_shell_command(f'curl -s "{art_url}" -o "{file_path}"')
            exec_shell_command(f'curl -s "{art_url}" -o "{file_path}"')
            # if exec_shell_command(f'curl -s "{art_url}" -o "{file_path}"') is not False:
            # if x == "":
            # time.sleep(1)
            # while not path.exists(file_path):
            #     pass
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
                    # media_progress if length != "" else Box(h_expand=True),
                    progress_box,
                    media_next,
                ],
            ),
        ]

        # self.playing = False
        # self.poll_progress = False
        # self.polls = 0
        # self.seeking = False
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

    # def setup_widgets(self):

    # self.metadata_service = MetadataService()

    # self.metadata_service.connect(
    #     "metadata-changed",
    #     lambda md, _: self.media_play_pause.set_image(
    #         Image(
    #             f"{configuration.icons_dir}/pause.svg"
    #             if md.metadata.split("|")[0] == "Playing"
    #             else f"{configuration.icons_dir}/play.svg",
    #             size=configuration.icon_size,
    #         )
    #     ),
    # )

    # def process_media(self, title):

    #     else:
    #         self.remove_style_class("empty")
    # [art_url, artist, album, title, length, _] = exec_shell_command(
    #     f"{playerctl}"
    #     + r" metadata -f '{{ mpris:artUrl }}|{{ artist }}|{{ album }}|{{ title }}|{{ mpris:length }}|'"
    # ).split("|")

    # # print(length)
    # if length != "":
    #     self.seeking = False
    #     self.length = float(length) / 10e5
    # else:
    #     self.seeking = True

    # if album != "":
    #     artist_album.add(Label("·"))
    #     artist_album.add(Label(album))

    # def clear_children(self):
    #     self.children = []
    #     self.add_style_class("empty")

    def seek_playback(self, scale):
        if self.length is not None:
            self.seeking = False
            exec_shell_command_async(
                f"{playerctl} position {scale.value * self.length}"
            )
