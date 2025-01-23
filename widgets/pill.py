from loguru import logger

from config import configuration
from widgets.date_time import DateTimeWidget, Calendar
from widgets.media_controls import MediaControls
from widgets.quick_settings import QuickSettings

from fabric.widgets.box import Box
from fabric.widgets.wayland import WaylandWindow as Window
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.stack import Stack
from fabric.widgets.button import Button
from fabric.widgets.eventbox import EventBox
from fabric.widgets.revealer import Revealer
# from fabric.core.fabricator import Fabricator

# import gi

# gi.require_version("Gtk", "3.0")
# from gi.repository import Gtk, Gdk  # noqa: E402


class PillWindow(Window):
    def __init__(self, **kwargs):
        super().__init__(
            name="pill_window",
            anchor="top",
            exclusivity="none",
            layer="top",
            visible=False,
            **kwargs,
        )

        def create_spacings(**args):
            box = Button(v_expand=True, h_expand=True, **args)
            box.connect("clicked", lambda *_: self.pill.dashboard.unpeek())
            return box

        self.pill = Pill()
        self.hover_listener = EventBox(
            name="hover_listener",
            child=self.pill,
        )

        self.b = Button(name="show_hide_pill")
        self.b2 = Button(name="show_hide_pill")

        self.center_box = CenterBox(name="pill_center_box", orientation="h")
        self.center_box.center_children = Box(
            children=[self.hover_listener, create_spacings()],
            spacing=10,
            orientation="v",
        )
        self.center_box.start_children = [
            create_spacings(style="min-width: 900px;"),
            Box(children=[self.b, create_spacings()], orientation="v"),
        ]
        self.center_box.end_children = [
            Box(children=[self.b2, create_spacings()], orientation="v"),
            create_spacings(style="min-width: 900px;"),
        ]

        self.hover_listener.connect(
            "enter-notify-event", self.pill.dashboard.cursor_try_peek
        )
        self.hover_listener.connect(
            "leave-notify-event", self.pill.dashboard.cursor_try_unpeek
        )

        self.add(self.center_box)
        self.show_all()


class Pill(Box):
    def __init__(self, **kwargs):
        super().__init__(name="pill_box")

        # self.idle = Dashboard()
        self.dashboard = Dashboard()

        # self.widgets = {"idle": self.idle, "dashboard": self.dashboard}

        self.stack = Stack(
            name="pill_stack",
            transition_type="crossfade",
            transition_duration=200,
            children=[self.dashboard],
            h_expand=True,
            **kwargs,
        )
        # self.select_pill_widget("idle")

        self.add(self.stack)

        self.dashboard.date_time_widget.connect(
            "clicked", lambda *_: self.dashboard.toggle_expand(True)
        )

        # self.dashboard.date_time_widget.connect(
        #     "clicked", lambda *_: self.select_pill_widget("idle", True)
        # )

    # def select_pill_widget(self, name, expand=False):
    #     # logger.debug("pressed")

    #     for id, widget in self.widgets.items():
    #         self.remove_style_class(id)
    #         widget.add_style_class("hidden")
    #         widget.hide()

    #     self.widgets[name].remove_style_class("hidden")
    #     self.widgets[name].unhide(expand)
    #     self.add_style_class(name)
    #     self.stack.set_visible_child(self.widgets[name])


class Dashboard(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="pill_dashboard", orientation="v", h_expand=True, **kwargs
        )

        self.expanded = False
        self.peaking = False

        self.date_time_widget = DateTimeWidget()
        self.quick_settings_widget = QuickSettings()
        self.media_controls_widget = MediaControls()
        self.calendar_widget = Box(
            name="calendar_container",
            orientation="h",
            children=[
                Box(h_expand=True),
                Calendar(),
                Box(h_expand=True),
            ],
        )

        self.quick_settings_revealer = Revealer(
            name="quick_settings_revealer",
            child=self.quick_settings_widget,
            transition_type="slide-down",
            transition_duration=configuration.get_setting("reveal_animation_duration"),
        )
        self.media_controls_revealer = Revealer(
            name="media_controls_revealer",
            child=self.media_controls_widget,
            transition_type="slide-down",
            transition_duration=configuration.get_setting("reveal_animation_duration"),
        )
        self.calendar_revealer = Revealer(
            name="calendar_revealer",
            child=self.calendar_widget,
            transition_type="slide-down",
            transition_duration=configuration.get_setting("reveal_animation_duration"),
        )

        self.children = [
            self.date_time_widget,
            self.quick_settings_revealer,
            self.media_controls_revealer,
            self.calendar_revealer,
        ]

    #     Fabricator(
    #         poll_from=lambda *_: pyautogui.position(),
    #         interval=500,
    #         on_changed=lambda _, v: self.check_pointer_in_bounds(
    #             self.get_allocation(), v
    #         ),
    #     )

    # def check_pointer_in_bounds(self, allocation, mouse_pos):
    #     def in_range(v, a, b, threshold=10):
    #         return (a + threshold) < v < (b - threshold)

    #     origin = (
    #         pyautogui.size().x / 2 - allocation.width / 2,
    #         pyautogui.size().y / 2 - allocation.height / 2,
    #     )

    #     if in_range(mouse_pos.x, origin.x, origin.x + allocation.width) and in_range(
    #         mouse_pos.y, origin.y, origin.y + allocation.height
    #     ):
    #         print("in_range")
    #     else:
    #         print("not_in_range")

    def cursor_try_peek(self, eventbox, event_crossing):
        if not self.expanded and not self.peaking:
            self.peek()

    def cursor_try_unpeek(self, eventbox, event_crossing):
        if not self.peaking:
            return

        def in_range(v, a, b, threshold=10):
            # logger.debug(f"{v=}, {a=}, {b=}")
            return (a + threshold) < v < (b - threshold)

        geometry = event_crossing.window.get_geometry()
        if not in_range(
            event_crossing.x_root - geometry.x, 0, geometry.width
        ) or not in_range(event_crossing.y_root - geometry.y, 0, geometry.height):
            self.unpeek()

    def toggle_expand(self, peak=False):
        if self.expanded:
            if peak:
                self.peek()
            else:
                self.unpeek()
        else:
            self.expand()

    def expand(self):
        logger.debug("Expanding")
        self.peaking = False
        self.expanded = True

        self.quick_settings_revealer.child_revealed = True
        self.media_controls_revealer.child_revealed = True
        self.calendar_revealer.child_revealed = True

        self.quick_settings_widget.add_style_class("revealed")
        self.media_controls_widget.add_style_class("revealed")
        self.calendar_widget.add_style_class("revealed")

    def peek(self):
        self.peaking = True
        self.expanded = False

        self.quick_settings_revealer.child_revealed = False
        self.media_controls_revealer.child_revealed = True
        self.calendar_revealer.child_revealed = False

        self.quick_settings_widget.remove_style_class("revealed")
        self.media_controls_widget.add_style_class("revealed")
        self.calendar_widget.remove_style_class("revealed")

        logger.debug("Peaking")

    def unpeek(self):
        self.peaking = False
        self.expanded = False

        self.quick_settings_revealer.child_revealed = False
        self.media_controls_revealer.child_revealed = False
        self.calendar_revealer.child_revealed = False

        self.quick_settings_widget.remove_style_class("revealed")
        self.calendar_widget.remove_style_class("revealed")
        self.media_controls_widget.remove_style_class("revealed")

        logger.debug("Shrinking")
