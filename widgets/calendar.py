import gi
import calendar
from datetime import datetime, date, timedelta
from email.policy import default
from loguru import logger
from config import configuration

from fabric.core import Signal
from fabric.widgets.box import Box
from fabric.widgets.shapes import Corner
from fabric.widgets.stack import Stack
from fabric.widgets.label import Label
from fabric.utils.helpers import get_enum_member

from widgets.buttons import MarkupButton

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402


class CalendarDay(MarkupButton):
    def __init__(self, **kwargs) -> None:
        super().__init__(name="calendar_day", h_expand=True, **kwargs)
        self.date = date.today()

    def change_date(self, d: date):
        self.date = d
        self.set_label(self.date.strftime("%d"))

        self.remove_style_class("outsider")
        self.remove_style_class("active")
        self.remove_style_class("today")


class CalendarMonth(Box):
    @Signal
    def on_day_clicked(self, day: CalendarDay): ...

    def __init__(self, year, month, **kwargs) -> None:
        super().__init__(
            name="calendar_month", orientation="v", h_expand=True, **kwargs
        )

        self.calendar = calendar.Calendar(5)

        self.weeks = [[CalendarDay() for _ in range(7)] for _ in range(6)]
        for week in self.weeks:
            for day in week:
                day.connect(
                    "clicked",
                    lambda button, *_: self.on_day_clicked(button),
                )

        for week in self.weeks:
            self.add(Box(name="calendar_week", children=week, h_expand=True))

        self.update_month(year, month)

    def update_month(self, year, month, highlight_date: date | None = None):
        self.year = year
        self.month = month

        d = self.calendar.monthdatescalendar(year, month)[0][0]
        for week in self.weeks:
            for day in week:
                day.change_date(d)
                if d.month != month:
                    day.add_style_class("outsider")

                if d == date.today():
                    day.add_style_class("today")

                if highlight_date:
                    if d == highlight_date:
                        day.add_style_class("active")
                elif d == date.today():
                    day.add_style_class("active")

                d = d + timedelta(days=1)

    def highlight_date(self, d):
        for week in self.weeks:
            for day in week:
                if day.date == d:
                    day.add_style_class("active")
                else:
                    day.remove_style_class("active")


class Calendar(Box):
    def __init__(self, orientation = "v", **kwargs) -> None:
        super().__init__(
            name="calendar_widget", orientation=orientation, h_expand=True, **kwargs
        )

        self.orientation = orientation
        self.add_style_class("horizontal" if orientation == "h" else "vertical")

        calendar.setfirstweekday(calendar.SATURDAY)
        self.calendar = calendar.Calendar(5)
        self.selected_date = date.today()


        if orientation == "v":
            self.year_label = Label(
                name="calendar_year_label",
                label=self.selected_date.strftime("%Y"),
                h_align="start",
            )

            self.date_label = Label(
                name="calendar_date_label",
                label=self.selected_date.strftime("%a, %b %d"),
                h_align="start",
            )

            self.corners_container = Box(
                name="calendar_corners_container",
                children=[
                    Box(
                        name="calendar_corner_container",
                        children=Corner(
                            name="calendar_corner",
                            orientation="top-left",
                            h_expand=True,
                            v_expand=True,
                        ),
                    ),
                    Box(h_expand=True),
                    Box(
                        name="calendar_corner_container",
                        children=Corner(
                            name="calendar_corner",
                            orientation="top-right",
                            h_expand=True,
                            v_expand=True,
                        ),
                    ),
                ],
            )
        else:
            self.year_label = Label(
                name="calendar_year_label",
                label=self.selected_date.strftime("%Y"),
                h_align="start",
            )

            self.day_label = Label(
                name="calendar_day_label",
                label=self.selected_date.strftime("%a"),
                h_align="start",
            )
            self.date_label = Label(
                name="calendar_date_label",
                label=self.selected_date.strftime("%b %d"),
                h_align="start",
            )

            self.corners_container = Box(
                name="calendar_corners_container",
                orientation="v",
                children=[
                    Box(
                        name="calendar_corner_container",
                        children=Corner(
                            name="calendar_corner",
                            orientation="top-right",
                            h_expand=True,
                            v_expand=True,
                        ),
                    ),
                    Box(v_expand=True),
                    Box(
                        name="calendar_corner_container",
                        children=Corner(
                            name="calendar_corner",
                            orientation="bottom-right",
                            h_expand=True,
                            v_expand=True,
                        ),
                    ),
                ],
            )

        self.dec_month_button = MarkupButton(
            name="calendar_navigation_buttons",
            markup=configuration.get_property("chevron_left"),
        )
        self.month_label = Label(
            name="calendar_month_label",
            h_expand=True,
            label=self.selected_date.strftime("%B"),
        )
        self.inc_month_button = MarkupButton(
            name="calendar_navigation_buttons",
            markup=configuration.get_property("chevron_right"),
        )

        self.dec_month_button.connect(
            "button-release-event", lambda *_: self.dec_month()
        )
        self.inc_month_button.connect(
            "button-release-event", lambda *_: self.inc_month()
        )

        self.day_labels_contianer = Box(
            name="calendar_day_labels",
            h_expand=True,
            children=[
                Label(name="calendar_day_label", h_expand=True, label=name)
                for name in ["Sat", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri"]
            ],
        )

        self.calendar_months: list[CalendarMonth] = []
        if self.selected_date.month == 1:
            self.calendar_months.append(CalendarMonth(self.selected_date.year - 1, 12))
        else:
            self.calendar_months.append(
                CalendarMonth(self.selected_date.year, self.selected_date.month - 1)
            )
        self.calendar_months.append(
            CalendarMonth(self.selected_date.year, self.selected_date.month)
        )
        if self.selected_date.month == 12:
            self.calendar_months.append(CalendarMonth(self.selected_date.year + 1, 1))
        else:
            self.calendar_months.append(
                CalendarMonth(self.selected_date.year, self.selected_date.month + 1)
            )

        for month in self.calendar_months:
            month.connect("on-day-clicked", lambda _, day: self.handle_day_clicked(day))

        self.calendar_months_stack = Stack(
            transition_type="slide-left-right",
            transition_duration=400,
            children=self.calendar_months,
        )
        self.calendar_months_stack.set_visible_child(self.calendar_months[1])

        if orientation == "v":
            self.padded_container = Box(
                name="calendar_padded_container",
                orientation="v",
                children=[
                    self.year_label,
                    self.date_label,
                ],
            )
            self.calendar_container = Box(
                name="calendar_unpadded_container",
                orientation="v",
                children=[
                    # self.corners_container,
                    Box(
                        h_expand=True,
                        children=[
                            self.dec_month_button,
                            self.month_label,
                            self.inc_month_button,
                        ],
                    ),
                    self.day_labels_contianer,
                    self.calendar_months_stack,
                ],
            )

            self.add(self.padded_container)
            self.add(self.calendar_container)
        else:
            self.calendar_container = Box(
                name="calendar_unpadded_container",
                orientation="v",
                children=[
                    Box(
                        h_expand=True,
                        children=[
                            self.dec_month_button,
                            self.month_label,
                            self.inc_month_button,
                        ],
                    ),
                    self.day_labels_contianer,
                    self.calendar_months_stack,
                ],
            )
            self.padded_container = Box(
                name="calendar_padded_container",
                h_expand=True,
                orientation="v",
                children=[
                    self.year_label,
                    self.date_label,
                    self.day_label,
                ],
            )

            self.add(self.padded_container)
            self.add(self.calendar_container)
            # self.add(self.corners_container)


    def handle_day_clicked(self, day: CalendarDay):
        if (
            self.selected_date.month == day.date.month
            and self.selected_date.year == day.date.year
        ):
            offset = 0
        elif self.selected_date.month == 12:
            if day.date.year == self.selected_date.year + 1 and day.date.month == 1:
                offset = 1
        elif day.date.month == self.selected_date.month + 1:
            offset = 1
        elif self.selected_date.month == 1:
            if day.date.year == self.selected_date.year - 1 and day.date.month == 12:
                offset = -1
        elif day.date.month == self.selected_date.month - 1:
            offset = -1
        else:
            logger.error("YOU SHALL NOT PASS")
            return

        self.selected_date = day.date
        match offset:
            case 0:
                self.calendar_months[1].highlight_date(self.selected_date)
                self.update_labels()
            case 1:
                self.inc_month(False)
            case -1:
                self.dec_month(False)
            case _:
                pass

    def inc_month(self, update_selected_date=True):
        month = self.calendar_months[2].month
        year = self.calendar_months[2].year

        cycle = self.calendar_months.pop(0)
        self.calendar_months.insert(2, cycle)

        self.calendar_months_stack.set_transition_type(
            get_enum_member(Gtk.StackTransitionType, "slide-left")
        )
        self.calendar_months_stack.remove(cycle)
        self.calendar_months_stack.add(cycle)
        self.calendar_months_stack.set_visible_child(self.calendar_months[1])

        if month == 12:
            cycle.update_month(year + 1, 1)
        else:
            cycle.update_month(year, month + 1)

        if update_selected_date:
            month = self.calendar_months[1].month
            year = self.calendar_months[1].year
            if month == (d := date.today()).month and year == d.year:
                self.selected_date = d
            else:
                self.selected_date = date(year, month, 1)
        self.calendar_months[1].highlight_date(self.selected_date)

        self.calendar_months_stack.set_visible_child(self.calendar_months[1])

        self.update_labels()

    def dec_month(self, update_selected_date=True):
        month = self.calendar_months[0].month
        year = self.calendar_months[0].year

        cycle = self.calendar_months.pop()
        self.calendar_months.insert(0, cycle)
        self.calendar_months_stack.remove(self.calendar_months[-1])

        self.calendar_months_stack.children = self.calendar_months
        self.calendar_months_stack.set_transition_type(
            get_enum_member(Gtk.StackTransitionType, member="none")
        )
        self.calendar_months_stack.set_visible_child(self.calendar_months[-1])
        self.calendar_months_stack.set_transition_type(
            get_enum_member(Gtk.StackTransitionType, member="slide-right")
        )
        self.calendar_months_stack.set_visible_child(self.calendar_months[1])

        if month == 1:
            cycle.update_month(year - 1, 12)
        else:
            cycle.update_month(year, month - 1)

        if update_selected_date:
            month = self.calendar_months[1].month
            year = self.calendar_months[1].year
            if month == (d := date.today()).month and year == d.year:
                self.selected_date = d
            else:
                self.selected_date = date(year, month, 1)
        self.calendar_months[1].highlight_date(self.selected_date)

        self.calendar_months_stack.set_visible_child(self.calendar_months[1])

        self.update_labels()

    def update_labels(self):
        self.year_label.set_label(self.selected_date.strftime("%Y"))
        self.month_label.set_label(self.selected_date.strftime("%B"))

        if self.orientation == "v":
            self.date_label.set_label(self.selected_date.strftime("%a, %b %d"))
        else:
            self.day_label.set_label(self.selected_date.strftime("%a"))
            self.date_label.set_label(self.selected_date.strftime("%b %d"))

    def add_style(self, style):
        self.add_style_class(style)

    def remove_style(self, style):
        self.remove_style_class(style)
