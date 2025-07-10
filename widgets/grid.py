import math
from fabric.utils import DesktopApp
from fabric.widgets.button import Button
from loguru import logger

from widgets.rounded_image import RoundedImage as Image
from fabric.widgets.eventbox import EventBox
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.core.service import Signal

from gi.repository import Gdk  # noqa: E402


class Grid(Box):
    @Signal
    def on_item_clicked(self): ...

    def __init__(
        self,
        columns,
        rows,
        items_fetcher,
        item_sort_name_fetcher,
        item_factory,
        sort_function,
        *args,
        **kwargs,
    ):
        super().__init__(h_expand=True, v_expand=True, orientation="v", *args, **kwargs)

        self.selected_item = 0
        self.row_offset = 0

        self.num_columns = columns
        self.get_items = items_fetcher
        self.get_item_name = item_sort_name_fetcher
        self.item_factory = item_factory
        self.sort_function = sort_function

        self.rows: list[Box] = []
        self.items = self.get_items()

        def row_factory():
            return Box(h_expand=True, v_expand=True)

        for i in range(rows):
            self.rows.append(row_factory())
            self.add(self.rows[-1])

        id = 0
        for row in self.rows:
            for i in range(self.num_columns):
                new_item = GridItem(id=id)
                new_item.connect("button-release-event", self.handle_item_click)

                row.add(new_item)

                id += 1

            row.set_homogeneous(True)

        self.set_homogeneous(True)

    def handle_item_click(self, item, *_):
        index = item.id + self.row_offset * self.num_columns

        self.selected_item = index
        self.redraw_items()

        self.on_item_clicked()

    def reset_items(self):
        for row in self.rows:
            children: list[GridItem] = row.children

            for child in children:
                child.clear()
                child.remove_style("active")

        self.filter_items()

    def filter_items(self, keyword: str | None = None):
        if keyword is None:
            self.items = self.get_items()
        else:
            self.items = [
                item
                for item in self.get_items()
                if keyword.casefold() in self.get_item_name(item).casefold()
            ]

        self.items.sort(key=lambda x: str.casefold(x.name))
        self.items.sort(key=self.sort_function)

        self.row_offset = 0
        self.selected_item = 0

        self.redraw_items(force_update=True)

    def redraw_items(self, force_update=False):
        if not force_update:
            update_items = False
            while (
                self.selected_item - self.row_offset * self.num_columns
                >= self.num_columns * len(self.rows)
            ):
                self.row_offset += 1
                update_items = True

            while self.selected_item - self.row_offset * self.num_columns < 0:
                self.row_offset -= 1
                update_items = True
        else:
            update_items = True

        if update_items:
            for i in range(self.num_columns * len(self.rows)):
                index = i + self.row_offset * self.num_columns

                row = math.floor(i / self.num_columns)
                column = i % self.num_columns

                grid_item = self.rows[row].children[column]

                if index >= len(self.items):
                    grid_item.clear()
                    grid_item.remove_style("active")

                    continue

                item = self.items[index]
                grid_item.update(*self.item_factory(item))

                if index == self.selected_item:
                    # logger.error(f"forced index: {i} {index}")
                    grid_item.add_style("active")
                else:
                    grid_item.remove_style("active")
        else:
            for i in range(self.num_columns * len(self.rows)):
                index = i + self.row_offset * self.num_columns

                row = math.floor(i / self.num_columns)
                column = i % self.num_columns

                grid_item = self.rows[row].children[column]

                if index >= len(self.items):
                    grid_item.clear()
                    grid_item.remove_style("active")

                    continue

                if index == self.selected_item:
                    # logger.error(f"index: {i} {index}")
                    grid_item.add_style("active")
                else:
                    grid_item.remove_style("active")

    def inc_selection(self):
        self.selected_item += 1

        if self.selected_item >= len(self.items):
            self.selected_item = 0

        self.redraw_items()

    def dec_selection(self):
        self.selected_item -= 1

        if self.selected_item < 0:
            self.selected_item = len(self.items) - 1

        self.redraw_items()

    def inc_selection_row(self):
        self.selected_item += self.num_columns

        if self.selected_item >= len(self.items):
            self.selected_item -= self.num_columns

            remaining_columns = len(self.items) % self.num_columns - 1
            column = self.selected_item % self.num_columns

            if column > remaining_columns:
                self.selected_item = len(self.items) - 1
            else:
                self.selected_item = min(remaining_columns, column)

        self.redraw_items()

    def dec_selection_row(self):
        self.selected_item -= self.num_columns

        if self.selected_item < 0:
            self.selected_item += self.num_columns

            full_rows = math.floor(len(self.items) / self.num_columns)
            remaining_columns = len(self.items) % self.num_columns - 1

            column = self.selected_item % self.num_columns

            self.selected_item = full_rows * self.num_columns + min(
                remaining_columns, column
            )

        self.redraw_items()


class GridItem(Button):
    def __init__(self, id, *args, **kwargs):
        super().__init__(name="grid_item", * args, **kwargs)

        self.id = id

        self.set_can_focus(False)
        self.set_focus_on_click(False)

        self.icon = Image(name="grid_item_icon", h_align="center")
        self.label = Label(
            name="grid_item_label",
            line_wrap="word-char",
            h_expand=True,
            v_expand=True,
            justification="center",
            ellipsization="end",
        )

        self.label.set_lines(2)

        self.main_container = Box(
            orientation="v",
            h_expand=True,
            v_expand=True,
            children=[self.icon, self.label],
            *args,
            **kwargs,
        )

        self.add(self.main_container)

        self.connect("enter-notify-event", lambda *_: self.cursor_enter())
        self.connect("leave-notify-event", lambda *_: self.cursor_leave())

    def cursor_enter(self):
        if not self.is_sensitive():
            return

        window = self.get_window()
        if window:
            window.set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))

    def cursor_leave(self):
        if not self.is_sensitive():
            return

        window = self.get_window()
        if window:
            window.set_cursor(None)

    def update(self, markup, image):
        self.set_label(markup)
        self.set_image(image)

        self.remove_style("empty")

    def clear(self):
        self.set_label("")
        self.icon.clear()

        self.add_style("empty")

    def set_label(self, markup):
        self.label.set_markup(markup)

    def set_image(self, image):
        if isinstance(image, str):
            self.icon.set_from_file(image)
        else:
            self.icon.set_from_pixbuf(image)

    def add_style(self, style):
        self.add_style_class(style)

    def remove_style(self, style):
        self.remove_style_class(style)
