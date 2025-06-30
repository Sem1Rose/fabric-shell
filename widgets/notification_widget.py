from time import sleep
import gi

from loguru import logger
from widgets.buttons import MarkupButton

from config import configuration

from fabric.notifications import Notification
from fabric.widgets.eventbox import EventBox
from fabric.widgets.box import Box
from fabric.widgets.revealer import Revealer
from fabric.widgets.label import Label
from fabric.core import Signal
from fabric.utils.helpers import exec_shell_command_async

from gi.repository import GLib


class NotificationWidget(Revealer):
    @Signal
    def closed(self): ...

    def __init__(self, autohide: bool = True, notification: Notification | None = None, **kwargs):
        super().__init__(**kwargs)

        self.main_contianer = Box()
        self.main_contianer.add_style_class("notification")

        self.autohide = autohide

        if not self.autohide:
            self.reveal()
        else:
            self.main_contianer.add_style_class("hidden")

        self.hidden = True
        self.hovored = False
        self.timeout = -1
        self.do_hide = False

        if notification:
            self.build_from_notification(notification)

        self.event_box = EventBox(
            events=[
                "enter-notify",
                "leave-notify",
            ],
            child=self.main_contianer,
        )

        self.event_box.connect("enter-notify-event", lambda *_: self.on_hover())
        self.event_box.connect("leave-notify-event", lambda *_: self.on_unhover())

        self.add(self.event_box)

    def close(self):
        self.reset()
        GLib.Thread.new("notification_hide", lambda *_: sleep(0.2) or self.notification.close())

    def on_hover(self):
        if self.hovored:
            return

        logger.error("hovered")
        if not self.hidden:
            self.hovored = True

    def on_unhover(self):
        logger.error("unhovered")
        if not self.hidden:
            self.hovored = False
            if self.do_hide:
                GLib.Thread.new("", lambda *_: sleep(0.5) or (not self.hovored and not self.hidden and self.close()))

    def reset(self):
        if self.autohide:
            self.unreveal()
            self.hidden = True
            self.main_contianer.add_style_class("hidden")

        self.hovored = False
        self.do_hide = False
        self.timeout = -1


    def build_from_notification(self, notification: Notification):
        self.reset()

        self.notification = notification

        summary = Label(self.notification.summary, name="notification_summary", justification="fill", h_align="start", line_wrap="`word", h_expand=True, max_chars_width=10, chars_width=1,)
        body = Label(
            self.notification.body,
            name="notification_body",
            justification="fill", h_align="start",
            line_wrap="word",
            h_expand=True,
            max_chars_width=100,
            chars_width=1,
        )
        dismiss = MarkupButton(name="notification_dismiss_button", markup="D", hexpand=True)
        dismiss.connect("button-release-event", lambda *_: self.close())
        dismiss.connect("enter-notify-event", lambda *_: self.on_hover())

        self.timeout = self.notification.timeout
        if self.timeout == -1:
            self.timeout = configuration.get_property(f"notification_{"low" if self.notification.urgency == 0 else "normal" if self.notification.urgency == 1 else "urgent"}_timeout")

        self.main_contianer.remove_style_class("hidden")
        self.main_contianer.children =  [Box(orientation="v", v_expand=True, h_expand=True, children=[summary, body, dismiss])]

        if self.autohide and self.timeout > 0:
            self.reveal()
            self.hidden = False

            self.start_hiding()

    def start_hiding(self):
        def hide(self):
            sleep(self.timeout)
            if self.hidden:
                return

            if self.hovored:
                self.do_hide = True
            else:
                self.reset()
                sleep(0.2)
                self.notification.close()

        GLib.Thread.new("notification_hide", hide, self)
