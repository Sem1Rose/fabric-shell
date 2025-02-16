import gi
import cairo
import math
from enum import Enum
from typing import Literal
from collections.abc import Iterable
from fabric.core.service import Property
from fabric.widgets.widget import Widget
from fabric.utils.helpers import get_enum_member

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk  # noqa: E402


class CornerOrientation(Enum):
    TOP_LEFT = 1
    TOP_RIGHT = 2
    BOTTOM_LEFT = 3
    BOTTOM_RIGHT = 4
    LEFT_TOP = 5
    LEFT_BOTTOM = 6
    RIGHT_TOP = 7
    RIGHT_BOTTOM = 8


class Corner(Gtk.DrawingArea, Widget):
    @staticmethod
    def render_shape(
        cr: cairo.Context,
        width: float,
        height: float,
        angle: float,
        spacing: int,
        orientation: CornerOrientation = CornerOrientation.TOP_LEFT,
    ):
        # _this is fine_
        cr.save()
        match orientation:
            case CornerOrientation.TOP_LEFT:
                center = (width, height + spacing)

                cr.move_to(0, 0)
                cr.line_to(width, 0)
                cr.arc_negative(
                    center[0], center[1], center[1], math.pi * 3 / 2, math.pi + angle
                )
            case CornerOrientation.TOP_RIGHT:
                center = (0, height + spacing)

                cr.move_to(width, 0)
                cr.line_to(0, 0)
                cr.arc(center[0], center[1], center[1], math.pi * 3 / 2, -angle)
            case CornerOrientation.BOTTOM_LEFT:
                center = (width, -spacing)

                cr.move_to(0, height)
                cr.line_to(width, height)
                cr.arc(
                    center[0],
                    center[1],
                    height + spacing,
                    math.pi / 2,
                    math.pi - angle,
                )
            case CornerOrientation.BOTTOM_RIGHT:
                center = (0, -spacing)

                cr.move_to(width, height)
                cr.line_to(0, height)
                cr.arc_negative(
                    center[0],
                    center[1],
                    height + spacing,
                    math.pi / 2,
                    angle,
                )
            case CornerOrientation.LEFT_TOP:
                center = (width + spacing, height)

                cr.move_to(0, 0)
                cr.line_to(0, height)
                cr.arc(
                    center[0], center[1], center[0], math.pi, math.pi * 3 / 2 - angle
                )
            case CornerOrientation.LEFT_BOTTOM:
                center = (width + spacing, 0)

                cr.move_to(0, height)
                cr.line_to(0, 0)
                cr.arc_negative(
                    center[0], center[1], center[0], math.pi, math.pi / 2 + angle
                )
            case CornerOrientation.RIGHT_TOP:
                center = (-spacing, height)

                cr.move_to(width, 0)
                cr.line_to(width, height)
                cr.arc_negative(
                    center[0],
                    center[1],
                    width + spacing,
                    2 * math.pi,
                    math.pi * 3 / 2 + angle,
                )
            case CornerOrientation.RIGHT_BOTTOM:
                center = (-spacing, 0)

                cr.move_to(width, height)
                cr.line_to(width, 0)
                cr.arc(
                    center[0],
                    center[1],
                    width + spacing,
                    0,
                    math.pi / 2 - angle,
                )

        cr.close_path()
        cr.restore()
        return

    @Property(CornerOrientation, "read-write")
    def orientation(self) -> CornerOrientation:
        return self._orientation

    @orientation.setter
    def orientation(
        self,
        value: Literal[
            "top-left",
            "top-right",
            "bottom-left",
            "bottom-right",
            "left-top",
            "left-bottom",
            "right-top",
            "right-bottom",
        ]
        | CornerOrientation,
    ):
        self._orientation = get_enum_member(CornerOrientation, value)
        return self.queue_draw()

    @Property(int, "read-write")
    def spacing(self) -> int:
        return self._spacing

    @spacing.setter
    def spacing(
        self,
        value: int,
    ):
        self._spacing = value
        return self.queue_draw()

    def __init__(
        self,
        orientation: Literal[
            "top-left",
            "top-right",
            "bottom-left",
            "bottom-right",
            "left-top",
            "left-bottom",
            "right-top",
            "right-bottom",
        ]
        | CornerOrientation = CornerOrientation.TOP_RIGHT,
        spacing: int = 0,
        name: str | None = None,
        visible: bool = True,
        all_visible: bool = False,
        style: str | None = None,
        style_classes: Iterable[str] | str | None = None,
        tooltip_text: str | None = None,
        tooltip_markup: str | None = None,
        h_align: Literal["fill", "start", "end", "center", "baseline"]
        | Gtk.Align
        | None = None,
        v_align: Literal["fill", "start", "end", "center", "baseline"]
        | Gtk.Align
        | None = None,
        h_expand: bool = False,
        v_expand: bool = False,
        size: Iterable[int] | int | None = None,
        **kwargs,
    ):
        Gtk.DrawingArea.__init__(self)  # type: ignore
        Widget.__init__(
            self,
            name,
            visible,
            all_visible,
            style,
            style_classes,
            tooltip_text,
            tooltip_markup,
            h_align,
            v_align,
            h_expand,
            v_expand,
            size,
            **kwargs,
        )
        self._orientation = get_enum_member(CornerOrientation, orientation)
        self._spacing = spacing
        self.connect("draw", self.on_draw)

    def on_draw(self, _, cr: cairo.Context):
        aloc: cairo.Rectangle = self.get_allocation()  # type: ignore
        # ^ hear me out, Gtk.Allocation == Gdk.Rectangle == cairo.Rectangle
        width, height = aloc.width, aloc.height
        angle = math.atan2(width, self._spacing) * (math.pi / 180)

        context: Gtk.StyleContext = self.get_style_context()
        border_color: Gdk.RGBA = context.get_border_color(Gtk.StateFlags.NORMAL)  # type: ignore
        border_width = (
            max(
                (border := context.get_border(Gtk.StateFlags.NORMAL)).top,  # type: ignore
                border.bottom,  # type: ignore
                border.left,  # type: ignore
                border.right,  # type: ignore
            )
            * 2  # the power of two because half the size of the border is out the bounding box
        )

        cr.save()

        self.render_shape(cr, width, height, angle, self._spacing, self._orientation)
        cr.clip()
        Gtk.render_background(context, cr, 0, 0, width, height)

        if border_width:
            Gdk.cairo_set_source_rgba(cr, border_color)  # type: ignore
            cr.set_line_width(border_width)
            self.render_shape(
                cr, width, height, angle, self._spacing, self._orientation
            )
            cr.stroke()

        cr.restore()
        return
