from config import configuration

from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.widgets.eventbox import EventBox
from fabric.widgets.box import Box
from fabric.core.service import Signal
from fabric.hyprland.widgets import WorkspaceButton

from loguru import logger
from typing import Literal

# import gi
# gi.require_version("Gtk", "3.0")
from gi.repository import Gdk  # noqa: E402


class MarkupButton(Button):
    def __init__(self, markup: str | None = None, *args, **kwargs):
        self.label = Label(h_expand=True, h_align="fill")
        super().__init__(child=self.label, *args, **kwargs)

        self.set_markup(markup) if markup else None

        self.connect("enter-notify-event", lambda *_: self.cursor_enter())
        self.connect("leave-notify-event", lambda *_: self.cursor_leave())

    def set_label(self, new_label):
        self.label.set_label(new_label)

    def set_markup(self, new_markup):
        self.label.set_markup(new_markup)

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


class ToggleButton(MarkupButton):
    @Signal
    def on_toggled(self, modifiers: int): ...

    @Signal
    def rmb_pressed(self, modifiers: int): ...

    @Signal
    def mmb_pressed(self, modifiers: int): ...

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.toggled = False

        self.connect("button-release-event", self.handle_button_release)

        self.set_state(self.toggled)

    def handle_button_release(self, button, event):
        # logger.error(
        #     f"{event.type}, {event.send_event}, {event.state}, {event.time}, {event.button}, {event.device}"
        # )
        if event.button == 1:
            self.toggle(event.get_state())
        elif event.button == 2:
            self.mmb_pressed(event.get_state())
        elif event.button == 3:
            self.rmb_pressed(event.get_state())
        else:
            return False

        return True

    def toggle(self, modifiers):
        self.set_state(not self.toggled)
        self.on_toggled(modifiers)

    def set_state(self, state):
        self.toggled = state
        if state:
            self.add_style_class("toggled")
        else:
            self.remove_style_class("toggled")


class ChevronButton(ToggleButton):
    def __init__(
        self,
        orientation: Literal["h", "v"] = "h",
        flipped: bool = False,
        *args,
        **kwargs,
    ):
        self.flipped = flipped
        self.orientation = orientation
        super().__init__(*args, **kwargs)

        self.connect("button-release-event", lambda *_: self.toggle())
        self.disconnect_by_func(self.handle_button_release)

    def toggle(self):
        self.set_state(not self.toggled)
        self.on_toggled(0)

        return True

    def set_state(self, state):
        self.toggled = state

        if state:
            self.add_style_class("toggled")
            self.set_markup(
                (
                    configuration.get_property("chevron_right")
                    if self.flipped
                    else configuration.get_property("chevron_left")
                )
                if self.orientation == "h"
                else (
                    configuration.get_property("chevron_down")
                    if self.flipped
                    else configuration.get_property("chevron_up")
                )
            )
        else:
            self.remove_style_class("toggled")
            self.set_markup(
                (
                    configuration.get_property("chevron_left")
                    if self.flipped
                    else configuration.get_property("chevron_right")
                )
                if self.orientation == "h"
                else (
                    configuration.get_property("chevron_up")
                    if self.flipped
                    else configuration.get_property("chevron_down")
                )
            )


class QSToggleButton(EventBox):
    @Signal
    def on_toggled(self, modifiers: int): ...

    @Signal
    def rmb_pressed(self, modifiers: int): ...

    def __init__(
        self,
        markup: str | None = None,
        icon: str | None = None,
        add_chevron=False,
        *args,
        **kwargs,
    ):
        super().__init__()

        self.chevron_button = None
        self.label = Label(
            name="qs_tile_label",
            h_expand=not add_chevron,
            h_align="start" if add_chevron else "fill",
            ellipsization="end",
        )
        self.icon = Label(name="qs_tile_icon", h_expand=False, h_align="start")

        self.main_container = Box(*args, **kwargs)
        self.main_container.add_style_class("qs_toggle")

        if add_chevron:
            self.chevron_button = ChevronButton(
                style_classes="qs_tile_chevron_button",
                # markup=configuration.get_property("chevron_right"),
            )
            # self.chevron_button.connect(
            #     "button-release-event", lambda *_: self.chevron_toggle()
            # )

            # self.chevron_toggled = False

            container = Box(h_expand=True, v_expand=True)
            container.pack_start(Box(children=[self.icon, self.label]), False, False, 0)
            container.pack_end(self.chevron_button, False, False, 0)

            self.main_container.add(container)
        else:
            self.main_container.add(Box(children=[self.icon, self.label]))

        self.toggled = False

        self.set_label(markup) if markup else None
        self.set_icon(icon) if icon else None

        self.connect("button-release-event", self.handle_button_release)
        self.connect("enter-notify-event", lambda *_: self.cursor_enter())
        self.connect("leave-notify-event", lambda *_: self.cursor_leave())

        self.set_state(self.toggled)

        self.add(self.main_container)

    def set_label(self, new_markup):
        self.label.set_markup(new_markup)

    def set_icon(self, new_icon):
        self.icon.set_markup(new_icon)

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

    def handle_button_release(self, button, event):
        if event.button == 1:
            self.toggle(event.get_state())
        elif event.button == 3:
            self.rmb_pressed(event.get_state())

    def toggle(self, modifiers):
        self.set_state(not self.toggled)
        self.on_toggled(modifiers)

    def set_state(self, state):
        self.toggled = state

        if state:
            self.main_container.add_style_class("toggled")
        else:
            self.main_container.remove_style_class("toggled")

        if self.chevron_button:
            self.chevron_button.set_sensitive(state)
            self.chevron_button.toggle() if self.chevron_button.toggled else None


class QSTileButton(Button):
    def __init__(
        self,
        markup: str | None = None,
        icon: str | None = None,
        centered: bool = True,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.label = Label(
            name="qs_tile_label",
            h_expand=True,
            h_align="fill",
            ellipsization="end",
        )
        self.icon = Label(name="qs_tile_icon", h_expand=False, h_align="start")

        if centered:
            self.add(Box(children=[self.icon, self.label]))
        else:
            container = Box()
            container.pack_start(Box(children=[self.icon, self.label]), False, False, 0)
            self.add(container)

        self.add_style_class("qs_tile")

        self.set_label(markup) if markup else None
        self.set_icon(icon) if icon else None

        self.connect("enter-notify-event", lambda *_: self.cursor_enter())
        self.connect("leave-notify-event", lambda *_: self.cursor_leave())

    def set_label(self, new_markup):
        self.label.set_markup(new_markup)

    def set_icon(self, new_icon):
        self.icon.set_markup(new_icon)

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


class CycleToggleButton(MarkupButton):
    @Signal
    def on_cycled(self, modifiers: int): ...

    @Signal
    def rmb_pressed(self, modifiers: int): ...

    @Signal
    def mmb_pressed(self, modifiers: int): ...

    def __init__(self, states, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.toggled = False
        self.states = states
        self.num_states = len(states)

        self.state = 0

        self.connect(
            "button-release-event", lambda _, event: self.handle_button_press(event)
        )

        self.set_state(index=self.state)

    def handle_button_press(self, event):
        if event.button == 1:
            self.cycle(event.get_state())
        elif event.button == 2:
            self.mmb_pressed(event.get_state())
        elif event.button == 3:
            self.rmb_pressed(event.get_state())
        else:
            return False

        return True

    def cycle(self, modifiers):
        def cycle_val(v, max):
            if v < max:
                return v
            return 0

        self.set_state(index=cycle_val(self.state + 1, self.num_states))
        self.on_cycled(modifiers)

    def set_state(self, state=None, index=None):
        if state is None and index is None:
            return
        if state is not None:
            self.state = self.states.index(state)
        elif index is not None:
            self.state = index

        self.toggled = self.state > 0

        for i in range(len(self.states)):
            self.remove_style_class(f"state{i}")
        self.add_style_class(f"state{self.state}")

        if self.toggled:
            self.add_style_class("toggled")
        else:
            self.remove_style_class("toggled")

    def get_state(self):
        return self.states[self.state]


class WorkspaceMarkupButton(WorkspaceButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.connect("enter-notify-event", lambda *_: self.cursor_enter())
        self.connect("leave-notify-event", lambda *_: self.cursor_leave())

    def cursor_enter(self):
        window = self.get_window()
        if window:
            window.set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))

    def cursor_leave(self):
        window = self.get_window()
        if window:
            window.set_cursor(None)
