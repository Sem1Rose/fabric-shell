import os
import random
import gi

from loguru import logger
from PIL import Image
from config import configuration
from concurrent.futures import ThreadPoolExecutor

from widgets.buttons import MarkupButton
from widgets.cooldown import cooldown
from widgets.helpers.formatted_exec import formatted_exec_shell_command_async
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.core.service import Signal
from fabric.utils.helpers import idle_add
# from fabric.widgets.eventbox import EventBox
# from widgets.corner import Corner
# from fabric.widgets.shapes.corner import Corner

# from fabric.utils.helpers import idle_add

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib  # noqa: E402


class WallpaperSelector(Box):
    @Signal
    def on_selected(self): ...

    def __init__(self, *args, **kwargs):
        super().__init__(
            name="pill_wallpaper_selector", orientation="v", *args, **kwargs
        )

        self.matugen_scheme = "scheme-tonal-spot"
        self.selected_index = 0
        self.wallpaper_paths = []
        self.last_cycle_time = 0
        self.stop_goto = False
        self.goto_started = False
        self.thread_pool = ThreadPoolExecutor(
            max_workers=configuration.get_property("thumbnails_generator_max_workers")
        )
        self.wallpaper_processor_thread = None

        self.title = Label(
            name="title", label="Wallpaper selector", ellipsization="end"
        )

        self.schemes = {
            "scheme-tonal-spot": "Tonal Spot",
            "scheme-content": "Content",
            "scheme-expressive": "Expressive",
            "scheme-fidelity": "Fidelity",
            "scheme-fruit-salad": "Fruit Salad",
            "scheme-monochrome": "Monochrome",
            "scheme-neutral": "Neutral",
            "scheme-rainbow": "Rainbow",
        }

        def update_matugen_scheme():
            self.matugen_scheme = self.matugen_scheme_combo.get_active_id()

        self.matugen_scheme_combo = Gtk.ComboBoxText()
        self.matugen_scheme_combo.set_name("matugen_scheme_combo")
        for key, display_name in self.schemes.items():
            self.matugen_scheme_combo.append(key, display_name)
        self.matugen_scheme_combo.set_active_id(self.matugen_scheme)
        self.matugen_scheme_combo.connect("changed", lambda *_: update_matugen_scheme())
        self.matugen_scheme_combo.set_can_focus(False)

        self.Images = [MarkupButton(name="wallpaper_item") for _ in range(5)]
        self.wallpapers_container = Box(children=self.Images)

        for image in self.Images:
            image.connect("clicked", lambda button: self.handle_image_press(button))
            image.set_can_focus(False)

        self.wallpaper_view = Box(
            name="wallpaper_view",
            children=[
                Box(h_expand=True),
                self.wallpapers_container,
                Box(h_expand=True),
            ],
        )

        # self.scroll_button_left = MarkupButton(
        #     name="scroll_button", style_classes="left", h_expand=True, markup="A"
        # )
        # self.scroll_button_right = MarkupButton(
        #     name="scroll_button", style_classes="right", h_expand=True, markup="B"
        # )

        # # max(self.selected_index - 3, 0)
        # self.scroll_button_left.connect(
        #     "clicked",
        #     lambda *_: self.cycle_cooldown(False),
        # )
        # # min(self.selected_index + 3, len(self.wallpaper_paths) - 1)
        # self.scroll_button_right.connect(
        #     "clicked",
        #     lambda *_: self.cycle_cooldown(),
        # )
        # self.scroll_button_left.connect(
        #     "enter-notify-event", lambda *_: self.on_hover(0, True)
        # )
        # self.scroll_button_left.connect(
        #     "leave-notify-event", lambda *_: self.on_hover(0, False)
        # )
        # self.scroll_button_right.connect(
        #     "enter-notify-event", lambda *_: self.on_hover(1, True)
        # )
        # self.scroll_button_right.connect(
        #     "leave-notify-event", lambda *_: self.on_hover(1, False)
        # )

        # self.corner_parents = [
        #     Box(
        #         name="corners_parent",
        #         style_classes="left",
        #         orientation="v",
        #         children=[
        #             Box(
        #                 name="corner_container",
        #                 children=[
        #                     Corner(
        #                         name="corner",
        #                         orientation="left-top",
        #                         spacing=5,
        #                         h_expand=True,
        #                         v_expand=True,
        #                     )
        #                 ],
        #             ),
        #             Box(v_expand=True),
        #             Box(
        #                 name="corner_container",
        #                 children=[
        #                     Corner(
        #                         name="corner",
        #                         orientation="left-bottom",
        #                         spacing=5,
        #                         h_expand=True,
        #                         v_expand=True,
        #                     )
        #                 ],
        #             ),
        #         ],
        #     ),
        #     Box(
        #         name="corners_parent",
        #         style_classes="right",
        #         orientation="v",
        #         children=[
        #             Box(
        #                 name="corner_container",
        #                 children=[
        #                     Corner(
        #                         name="corner",
        #                         orientation="right-top",
        #                         spacing=5,
        #                         h_expand=True,
        #                         v_expand=True,
        #                     )
        #                 ],
        #             ),
        #             Box(v_expand=True),
        #             Box(
        #                 name="corner_container",
        #                 children=[
        #                     Corner(
        #                         name="corner",
        #                         orientation="right-bottom",
        #                         spacing=5,
        #                         h_expand=True,
        #                         v_expand=True,
        #                     )
        #                 ],
        #             ),
        #         ],
        #     ),
        # ]

        self.children = [
            Box(children=[self.title, Box(h_expand=True), self.matugen_scheme_combo]),
            Box(
                children=[
                    # self.scroll_button_left,
                    # Box(
                    #     h_expand=True,
                    #     children=[self.scroll_button_left, self.corner_parents[0]],
                    # ),
                    self.wallpaper_view,
                    # Box(
                    #     h_expand=True,
                    #     children=[self.corner_parents[1], self.scroll_button_right],
                    # ),
                    # self.scroll_button_right,
                ]
            ),
        ]

        self.format_view()

    # def on_hover(self, id, hover):
    #     self.corner_parents[id].add_style_class(
    #         "hovered"
    #     ) if hover else self.corner_parents[id].remove_style_class("hovered")

    # def update_scroll_buttons(self):
    #     left_enabled = self.selected_index > 0
    #     self.scroll_button_left.set_sensitive(left_enabled)
    #     self.corner_parents[0].remove_style_class(
    #         "disabled"
    #     ) if left_enabled else self.corner_parents[0].add_style_class("disabled")

    #     right_enabled = self.selected_index + 1 < len(self.wallpaper_paths)
    #     self.scroll_button_right.set_sensitive(right_enabled)
    #     self.corner_parents[1].remove_style_class(
    #         "disabled"
    #     ) if right_enabled else self.corner_parents[1].add_style_class("disabled")

    def update_style_classes(self):
        for i in [0, 4]:
            self.Images[i].remove_style_class("edge")
            self.Images[i].add_style_class("empty")
            self.Images[i].set_sensitive(False)

        for i in [1, 3]:
            self.Images[i].remove_style_class("empty")
            self.Images[i].add_style_class("edge")

            if 0 <= self.selected_index + i - 2 < len(self.wallpaper_paths):
                self.Images[i].set_sensitive(True)
            else:
                self.Images[i].set_sensitive(False)

        for i in [0, 1]:
            self.Images[i].remove_style_class("right")
            self.Images[i].add_style_class("left")

        for i in [3, 4]:
            self.Images[i].remove_style_class("left")
            self.Images[i].add_style_class("right")

        self.Images[2].remove_style_class("edge")
        # self.wallpapers[2].remove_style_class("empty")

        if 0 <= self.selected_index < len(self.wallpaper_paths):
            self.Images[2].set_sensitive(True)
        else:
            self.Images[2].set_sensitive(False)

        # self.update_scroll_buttons()

    def format_view(self):
        self.selected_index = 0
        self.wallpaper_paths = []
        self.stop_goto = False

        self.update_style_classes()
        for i in range(5):
            self.Images[i].set_style("background-image: none;")
            self.Images[i].set_sensitive(False)

    def append_wallpaper(self, thumbnail, path):
        if len(self.wallpaper_paths) - self.selected_index < 2:
            self.Images[len(self.wallpaper_paths) - self.selected_index + 2].set_style(
                f'background-image: url("{thumbnail}")'
            )
            self.Images[
                len(self.wallpaper_paths) - self.selected_index + 2
            ].set_sensitive(True)

        self.wallpaper_paths.append((thumbnail, path))
        # self.update_scroll_buttons()

    @cooldown(0.26, lambda *_: False, True)
    def cycle_cooldown(self, next=True):
        self.cycle(next)
        return True

    def cycle(self, next=True):
        if next:
            self.selected_index += 1
            self.wallpapers_container.reorder_child(self.Images[0], 4)

            first = self.Images[0]
            for i in range(0, 4):
                self.Images[i] = self.Images[i + 1]
            self.Images[4] = first
        else:
            self.selected_index -= 1
            self.wallpapers_container.reorder_child(self.Images[4], 0)

            last = self.Images[4]
            for i in range(4, 0, -1):
                self.Images[i] = self.Images[i - 1]
            self.Images[0] = last

        self.update_style_classes()

        self.Images[0].set_style("background-image: none;")
        self.Images[4].set_style("background-image: none;")

        if self.selected_index - 1 >= 0:
            self.Images[1].set_style(
                f'background-image: url("{self.wallpaper_paths[self.selected_index - 1][0]}")'
            )
        if self.selected_index + 1 < len(self.wallpaper_paths):
            self.Images[3].set_style(
                f'background-image: url("{self.wallpaper_paths[self.selected_index + 1][0]}")'
            )

    # @cooldown(0.3, lambda *_: False, True)
    def goto_index(self, index):
        if (
            index >= len(self.wallpaper_paths)
            or index < 0
            or index == self.selected_index
        ):
            return

        # if abs(index - self.selected_index) <= 2:
        def goto_thread():
            for _ in range(abs(index - self.selected_index)):
                if self.stop_goto:
                    break
                idle_add(self.cycle, index - self.selected_index > 0)

                GLib.usleep(170 * 1000)

            self.goto_started = False

        self.stop_goto = False
        self.goto_started = True
        GLib.Thread.new("goto_thread", goto_thread)
        # else:
        #     for i in range(1, 4):
        #         if 0 <= index + i - 2 < len(self.wallpaper_paths):
        #             self.wallpapers[i].set_style(
        #                 f'background-image: url("{self.wallpaper_paths[index + i - 2][0]}")'
        #             )
        #         else:
        #             self.wallpapers[i].set_style("background-image: none;")

        #     self.selected_index = index
        #     self.update_scroll_buttons()

        return True

    def handle_arrow_keys(self, event):
        match event.keyval:
            case 65363:  # right arrow
                if self.selected_index + 1 < len(self.wallpaper_paths):
                    self.stop_goto = True
                    return self.cycle_cooldown()
            case 65361:  # left arrow
                if self.selected_index > 0:
                    self.stop_goto = True
                    return self.cycle_cooldown(False)
            case 65362:  # up arrow
                self.stop_goto = True
                if not self.goto_started:
                    return self.goto_index(0)
            case 65364:  # down arrow
                self.stop_goto = True
                if not self.goto_started:
                    return self.goto_index(len(self.wallpaper_paths) - 1)
        return False

    def select_wallpaper(self):
        if not len(self.wallpaper_paths) == 0:
            wallpaper_path = self.wallpaper_paths[self.selected_index][1]
            # command = FormattedString(
            #     configuration.get_property("change_wallpaper_command")
            # ).format(
            #     path=wallpaper_path, scheme=self.matugen_scheme_combo.get_active_id()
            # )

            formatted_exec_shell_command_async(
                f'sh -c "sleep 0.5; {configuration.get_property("change_wallpaper_command")}"',
                path=wallpaper_path,
                scheme=self.matugen_scheme_combo.get_active_id(),
            )
            logger.info(
                f"Setting wallpaper: {wallpaper_path}, scheme: {self.matugen_scheme_combo.get_active_id()} ..."
            )

        self.on_selected()

    def handle_image_press(self, image):
        index = self.Images.index(image)
        if index in [0, 4]:
            return
        elif index in [1, 3]:
            self.cycle_cooldown(index == 3)
        elif index == 2:
            self.select_wallpaper()
        else:
            logger.error(f"unknown index: {index}")

    def start_thumbnails_thread(self):
        self.wallpaper_processor_thread = GLib.Thread.new(
            "wallpaper_processor", self.process_images
        )

    def process_images(self):
        files = [
            file
            for file in os.listdir(configuration.get_property("wallpapers_dir"))
            if file.lower().endswith(".png")
        ]
        random.shuffle(files)

        self.thread_pool.map(self.generate_thumbnail, files)

    def generate_thumbnail(self, image):
        thumbnail_path = os.path.join(
            configuration.get_property("wallpapers_thumbnails_cache_dir"), image
        )
        file_path = os.path.join(configuration.get_property("wallpapers_dir"), image)
        if os.path.exists(thumbnail_path):
            idle_add(self.append_wallpaper, thumbnail_path, file_path)
        else:
            try:
                with Image.open(file_path) as img:
                    img.thumbnail((256, 256), Image.Resampling.BILINEAR)
                    img.save(thumbnail_path, "PNG")
            except Exception as e:
                logger.error(f"error processing {file_path}: {e}")
                return False

            if not os.path.exists(thumbnail_path):
                logger.error(f"error processing {file_path}")
                return False

            idle_add(self.append_wallpaper, thumbnail_path, file_path)

        return True

    def hide(self, *args):
        self.add_style_class("hidden")
        self.stop_goto = True

        for i in range(5):
            # self.wallpapers[i].add_style_class("empty")
            self.Images[i].set_style("background-image: none;")

    def unhide(self, *args):
        self.remove_style_class("hidden")
        self.format_view()
        self.start_thumbnails_thread()
