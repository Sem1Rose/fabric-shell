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

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk  # noqa: E402


class PillWindow(Window):
    def __init__(self, *args, **kwargs):
        super().__init__(
            name="pill_window",
            anchor="top",
            exclusivity="normal",
            layer="top",
            visible=False,
            *args,
            **kwargs,
        )

        self.pointer = self.get_display().get_default_seat().get_pointer()
        logger.debug(self.pointer)

        def create_spacings(**args):
            def on_click():
                if self.pill.dashboard.expanded:
                    self.pill.dashboard.unpeek()
                    return True
                else:
                    return False

            box = Button(v_expand=True, h_expand=True, **args)
            box.connect("clicked", lambda *_: on_click())
            return box

        self.pill = Pill()
        self.hover_listener = EventBox(
            name="hover_listener",
            child=self.pill,
        )

        self.b = Button(name="show_hide_pill")
        self.b2 = Button(name="show_hide_pill")

        self.center_box = CenterBox(name="pill_main_container", orientation="h")
        self.center_box.center_children = Box(
            children=[self.hover_listener, create_spacings()],
            spacing=10,
            orientation="v",
        )
        self.center_box.start_children = [
            create_spacings(),
            Box(children=[self.b, create_spacings()], orientation="v"),
        ]
        self.center_box.end_children = [
            Box(children=[self.b2, create_spacings()], orientation="v"),
            create_spacings(),
        ]

        self.hover_listener.connect("enter-notify-event", self.mouse_enter)
        self.hover_listener.connect("leave-notify-event", self.mouse_leave)
        self.pill.dashboard.date_time_widget.connect(
            "clicked", lambda *_: self.toggle_expand(True)
        )

        self.add(self.center_box)
        self.show_all()

    def mouse_enter(self, eventbox, event_crossing):
        self.pill.dashboard.try_peek(eventbox, event_crossing)

    def mouse_leave(self, eventbox, event_crossing):
        self.pill.dashboard.try_unpeek(eventbox, event_crossing)

    def toggle_expand(self, peak=False):
        self.pill.dashboard.toggle_expand(peak)
        # if self.pill.dashboard.toggle_expand(peak):
        #     for i in self.spacings:
        #         i.set_style("min-width: 00px;")
        # else:
        #     for i in self.spacings:
        #         i.set_style("")

    def expand(self):
        self.pill.dashboard.expand()

    def peek(self):
        self.pill.dashboard.peek()

    def unpeek(self):
        self.pill.dashboard.unpeek()


class Pill(Box):
    def __init__(self, *args, **kwargs):
        super().__init__(name="pill_box", *args, **kwargs)

        # self.idle = Dashboard()
        self.dashboard = Dashboard()

        # self.widgets = {"idle": self.idle, "dashboard": self.dashboard}

        self.stack = Stack(
            name="pill_stack",
            transition_type="crossfade",
            transition_duration=200,
            children=[self.dashboard],
            h_expand=True,
        )
        # self.select_pill_widget("idle")

        self.add(self.stack)

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
    def __init__(self, *args, **kwargs):
        super().__init__(
            name="pill_dashboard", orientation="v", h_expand=True, *args, **kwargs
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
            transition_duration=configuration.get_property("reveal_animation_duration"),
        )
        self.media_controls_revealer = Revealer(
            name="media_controls_revealer",
            child=self.media_controls_widget,
            transition_type="slide-down",
            transition_duration=configuration.get_property("reveal_animation_duration"),
        )
        self.calendar_revealer = Revealer(
            name="calendar_revealer",
            child=self.calendar_widget,
            transition_type="slide-down",
            transition_duration=configuration.get_property("reveal_animation_duration"),
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

    def try_peek(self, eventbox, event_crossing):
        if not self.expanded and not self.peaking:
            self.peek()

    def try_unpeek(self, eventbox, event_crossing):
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
            return False
        else:
            self.expand()
            return True

    def expand(self):
        logger.debug("Expanding")
        self.peaking = False
        self.expanded = True

        self.quick_settings_revealer.reveal()
        self.media_controls_revealer.reveal()
        self.calendar_revealer.reveal()

        self.quick_settings_widget.add_style_class("revealed")
        self.media_controls_widget.add_style_class("revealed")
        self.calendar_widget.add_style_class("revealed")

    def peek(self):
        self.peaking = True
        self.expanded = False

        self.quick_settings_revealer.unreveal()
        self.media_controls_revealer.reveal()
        self.calendar_revealer.unreveal()

        self.quick_settings_widget.remove_style_class("revealed")
        self.media_controls_widget.add_style_class("revealed")
        self.calendar_widget.remove_style_class("revealed")

        logger.debug("Peaking")

    def unpeek(self):
        self.peaking = False
        self.expanded = False

        self.quick_settings_revealer.unreveal()
        self.media_controls_revealer.unreveal()
        self.calendar_revealer.unreveal()

        self.quick_settings_widget.remove_style_class("revealed")
        self.calendar_widget.remove_style_class("revealed")
        self.media_controls_widget.remove_style_class("revealed")

        logger.debug("Shrinking")
