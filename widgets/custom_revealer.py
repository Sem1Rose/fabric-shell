import gi
import gi.overrides
import gi._signalhelper
import gi._propertyhelper
import gi.overrides.GObject
from gi.repository import Gtk, Gdk, GLib  # noqa: E402

from collections.abc import Callable
from typing import Literal
from fabric.widgets.revealer import Revealer

from loguru import logger

gi.require_version("Gtk", "3.0")


class CustomRevealer(Revealer):
    def __init__(
        self,
        reveal_transition_function: Literal[
            "none", "linear", "ease", "ease-in", "ease-out", "ease-in-out"
        ]
        | Callable[[float], float]
        | None = None,
        # hide_transition_function: Literal[
        #     "none", "linear", "ease", "ease-in", "ease-out", "ease-in-out"
        # ]
        # | Callable[float, float]
        # | None = None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        match reveal_transition_function:
            case "linear":
                self.reveal_transition_function = self.linear
            case "ease":
                self.reveal_transition_function = self.ease
            case "ease-in":
                self.reveal_transition_function = self.ease_in
            case "ease-out":
                self.reveal_transition_function = self.ease_out
            case "ease-in-out":
                self.reveal_transition_function = self.ease_in_out
            case "none":
                self.reveal_transition_function = self.linear
            case None:
                self.reveal_transition_function = self.linear
            case _:
                self.reveal_transition_function = reveal_transition_function

        # match hide_transition_function:
        #     case "linear":
        #         self.hide_transition_function = self.linear
        #     case "ease":
        #         self.hide_transition_function = self.ease
        #     case "ease-in":
        #         self.hide_transition_function = self.ease_in
        #     case "ease-out":
        #         self.hide_transition_function = self.ease_out
        #     case "ease-in-out":
        #         self.hide_transition_function = self.ease_in_out
        #     case None, "none":
        #         self.hide_transition_function = self.reveal_transition_function
        #     case _:
        #         self.hide_transition_function = hide_transition_function

        self.start_time = None
        self.is_revealed = False

        self.reveal() if self.is_revealed else self.unreveal()

        # print(self.reveal_transition_function)

    def reveal(self):
        if self.is_revealed:
            return
        self.child_visible = True
        self.is_revealed = True
        self.start_time = GLib.get_monotonic_time() / 1000
        self.queue_draw()

    def unreveal(self):
        if not self.is_revealed:
            return
        self.is_revealed = False
        self.start_time = GLib.get_monotonic_time() / 1000
        self.queue_draw()

    def do_draw(self, cr):
        current_time = GLib.get_monotonic_time() / 1000
        elapsed_time = current_time - self.start_time if self.start_time else 0
        progress = elapsed_time / self.transition_duration
        if progress > 1:
            return

        if self.is_revealed:
            progress = self.reveal_transition_function(progress)
            self.set_sensitive(True)
        else:
            progress = 1 - self.reveal_transition_function(progress)
            self.set_sensitive(False)

        match self.transition_type:
            case Gtk.RevealerTransitionType.CROSSFADE:
                cr_opacity = self.get_window().cairo_create()
                cr_opacity.set_source_rgba(0, 0, 0, progress)
                cr_opacity.paint()
            case Gtk.RevealerTransitionType.SLIDE_RIGHT:
                width = self.get_allocated_width() * progress
                self.set_size_request(int(width), -1)
            # case Gtk.RevealerTransitionType.SLIDE_LEFT:
            #     pass
            case Gtk.RevealerTransitionType.SLIDE_DOWN:
                height = self.get_allocated_height() * progress
                self.set_size_request(-1, int(height))
            # case Gtk.RevealerTransitionType.SLIDE_UP:
            #     height = self.get_allocated_height() * progress
            #     self.set_size_request(-1, int(height))
            case _:
                if self.is_revealed:
                    self.set_size_request(0, 0)
                else:
                    self.set_size_request(-1, -1)

        logger.debug(
            "{} {} {}".format(progress, self.is_revealed, self.transition_type)
        )

        if progress not in (0.0, 1.0):
            self.queue_draw()
        # Revealer.do_draw(self, cr)

    @staticmethod
    def linear(t):
        return t

    @staticmethod
    def ease(t):
        return t * t * (3 - 2 * t)

    @staticmethod
    def ease_in(t):
        return t * t

    @staticmethod
    def ease_out(t):
        return t * (2 - t)

    @staticmethod
    def ease_in_out(t):
        return 2 * t * t if t < 0.5 else -1 + (4 - 2 * t) * t

    @staticmethod
    def cubic_bezier(t, p0=0, p1=0.25, p2=0.25, p3=1):
        return (
            (1 - t) ** 3 * p0
            + 3 * (1 - t) ** 2 * t * p1
            + 3 * (1 - t) * t**2 * p2
            + t**3 * p3
        )


# import gi
# import math
# from gi.repository import Gtk, GLib
# from fabric.widgets.revealer import Revealer

# gi.require_version("Gtk", "3.0")


# class CustomRevealer(Revealer):
#     def __init__(
#         self,
#         transition_function=None,
#         transition_type=Gtk.RevealerTransitionType.SLIDE_DOWN,
#         transition_duration=500,
#         **args,
#     ):
#         """
#         Custom Revealer widget with support for custom transition functions.

#         :param transition_function: A function that takes progress (0.0 to 1.0) and returns a transformed progress value.
#                                     If None, the default Gtk.Revealer transition is used.
#         :param transition_type: The default Gtk.RevealerTransitionType to use if no custom function is provided.
#         :param duration: Duration of the transition in milliseconds.
#         """
#         super().__init__(**args)
#         self.set_transition_type(transition_type)
#         self.set_transition_duration(transition_duration)

#         # Store the custom transition function
#         self.transition_function = transition_function

#         # Internal state for animation
#         self._animation_progress = 0.0
#         self._animation_running = False
#         self._animation_direction = 1  # 1 for reveal, -1 for hide

#     def set_transition_function(self, func):
#         """
#         Set a custom transition function.

#         :param func: A function that takes progress (0.0 to 1.0) and returns a transformed progress value.
#         """
#         self.transition_function = func

#     def do_draw(self, cr):
#         """
#         Override the draw method to apply custom transition animations.
#         """
#         if self.transition_function:
#             # If a custom transition function is provided, animate manually
#             if not self._animation_running:
#                 self._start_animation()
#         else:
#             # Use the default Gtk.Revealer behavior
#             super().do_draw(cr)

#     def _start_animation(self):
#         """
#         Start the custom animation loop.
#         """
#         self._animation_running = True
#         self._animation_progress = 0.0 if self._animation_direction == 1 else 1.0

#         def update_animation():
#             # Update the animation progress
#             step = 1 / (self.get_transition_duration() / 16.67)  # Approx. 60 FPS
#             self._animation_progress += step * self._animation_direction

#             # Clamp progress between 0.0 and 1.0
#             self._animation_progress = max(0.0, min(1.0, self._animation_progress))

#             # Apply the custom transition function
#             if self.transition_function:
#                 t = self.transition_function(self._animation_progress)
#             else:
#                 t = self._animation_progress

#             # Set the reveal-child property based on progress
#             self.set_reveal_child(t > 0.5)

#             # Queue a redraw
#             self.queue_draw()

#             # Stop the animation if it's complete
#             if self._animation_progress in (0.0, 1.0):
#                 self._animation_running = False
#                 return False  # Stop the timeout

#             return True  # Continue the timeout

#         # Start the GLib timeout for the animation
#         GLib.timeout_add(16, update_animation)

#     def reveal(self):
#         """
#         Trigger the reveal animation.
#         """
#         self._animation_direction = 1
#         self._start_animation()

#     def unreveal(self):
#         """
#         Trigger the hide animation.
#         """
#         self._animation_direction = -1
#         self._start_animation()


# def ease_in(progress):
#     return progress**2


# def ease_out(progress):
#     return 1 - (1 - progress) ** 2


# def ease_in_out(progress):
#     return 0.5 * (math.sin((progress - 0.5) * math.pi) + 1)


# def cubic_bezier(p1x, p1y, p2x, p2y):
#     """
#     Generate a cubic bezier function for custom easing.
#     """

#     def bezier(t):
#         # Cubic bezier formula
#         cx = 3 * p1x
#         bx = 3 * (p2x - p1x) - cx
#         ax = 1 - cx - bx

#         cy = 3 * p1y
#         by = 3 * (p2y - p1y) - cy
#         ay = 1 - cy - by

#         x = ((ax * t + bx) * t + cx) * t
#         y = ((ay * t + by) * t + cy) * t

#         return y

#     return bezier


# # Example usage
# if __name__ == "__main__":

#     def on_button_clicked(button, revealer):
#         if revealer.get_child_revealed():
#             revealer.hide()
#         else:
#             revealer.reveal()

#     # Create a GTK application
#     win = Gtk.Window()
#     win.connect("destroy", Gtk.main_quit)

#     # Create a vertical box
#     vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
#     win.add(vbox)

#     # Create a custom revealer
#     revealer = CustomRevealer(transition_function=ease_in_out, duration=1000)
#     label = Gtk.Label(label="Hello, I am a revealed widget!")
#     revealer.add(label)
#     vbox.pack_start(revealer, True, True, 0)

#     # Create a button to toggle the revealer
#     button = Gtk.Button(label="Toggle Revealer")
#     button.connect("clicked", on_button_clicked, revealer)
#     vbox.pack_start(button, False, False, 0)

#     # Show the window
#     win.show_all()
#     Gtk.main()
