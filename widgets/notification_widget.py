import random
import gi
from time import sleep
import os.path

from loguru import logger
from widgets.buttons import MarkupButton
from widgets.rounded_image import RoundedImage
from widgets.revealer import Revealer

from config import configuration

from fabric.notifications import Notification
from fabric.widgets.eventbox import EventBox
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.core import Signal
from fabric.utils.helpers import idle_add

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GdkPixbuf, GLib  # noqa: E402

CUSTOM_HINTS = ["progress", "name", "custom-icon", "accent-color"]
URGENCY = {0: "low", 1: "normal", 2: "urgent"}
COLORS = ["accent", "green", "red", "yellow", "blue", "cyan", "magenta"]


class NotificationWidget(Revealer):
    @Signal
    def closed(self): ...

    def __init__(
        self, autohide: bool = True, notification: Notification | None = None, **kwargs
    ):
        super().__init__(**kwargs)

        self.main_container = Box(orientation="v", h_expand=True, style_classes="notification")

        self.autohide = autohide

        if not self.autohide:
            self.reveal()
        else:
            self.main_container.add_style_class("hidden")

        self.hidden = True
        self.hide_ticket = 0
        self.hovored = False
        self.do_hide = False

        if notification:
            self.build_from_notification(notification)

        self.event_box = EventBox(
            events=[
                "enter-notify",
                "leave-notify",
            ],
            child=self.main_container,
        )

        self.event_box.connect("enter-notify-event", lambda *_: self.on_hover())
        self.event_box.connect("leave-notify-event", lambda *_: self.on_unhover())

        self.add(self.event_box)

    def close(self):
        idle_add(self.reset)
        GLib.Thread.new(
            "notification_hide",
            lambda *_: sleep(0.2) or idle_add(self.notification.close),
        )

    def on_hover(self):
        if self.hovored:
            return

        if not self.hidden:
            self.hovored = True

    def on_unhover(self):
        if not self.hidden:
            self.hovored = False
            if self.do_hide:
                GLib.Thread.new(
                    "",
                    lambda *_: sleep(0.5)
                    or (not self.hovored and not self.hidden and idle_add(self.close)),
                )

    def reset(self):
        if self.autohide:
            self.hidden = True
            self.unreveal()
            self.main_container.add_style_class("hidden")

        self.hovored = False
        self.do_hide = False

    def rebuild(self):
        self.reset()

        timeout = self.notification.timeout
        if timeout == -1:
            timeout = configuration.get_property(
                f"notification_{URGENCY[self.notification.urgency]}_timeout"
            )

        if self.autohide and timeout > 0:
            self.start_hiding(timeout)

        self.hidden = False
        self.main_container.remove_style_class("hidden")
        self.reveal()

    def build_from_notification(self, notification: Notification):
        self.reset()

        self.notification = notification
        for i in URGENCY.values():
            self.main_container.remove_style_class(i)

        hints = {}
        for hint in CUSTOM_HINTS:
            hints[hint] = self.notification.do_get_hint_entry(f"fabric-shell-{hint}")

        progress = hints["progress"] is not None
        custom_icon = hints["custom-icon"]
        custom_icon_color = (
            hints["accent-color"] if hints["accent-color"] in COLORS else None
        )

        actions = self.notification.actions.__len__() > 0
        actions_overflow = self.notification.actions.__len__() > configuration.get_property(
            "notification_max_actions"
        )

        image = self.notification.image_pixbuf
        app_name = self.notification.app_name
        # logger.error(image)
        # logger.error(self.notification.app_name)
        # logger.error(self.notification.app_icon)
        try:
            if self.notification.app_icon and self.notification.app_icon != "":
                if os.path.isfile(self.notification.app_icon) and not image:
                    image = GdkPixbuf.Pixbuf.new_from_file(self.notification.app_icon)
                    pixbuf = (
                        Gtk.IconTheme()
                        .get_default()
                        .load_icon(
                            "error",
                            configuration.get_property("notification_app_icon_size"),
                            Gtk.IconLookupFlags.FORCE_SIZE,
                        )
                    )
                else:
                    pixbuf = (
                        Gtk.IconTheme()
                        .get_default()
                        .load_icon(
                            self.notification.app_icon,
                            configuration.get_property("notification_app_icon_size"),
                            Gtk.IconLookupFlags.FORCE_SIZE,
                        )
                    )
            else:
                pixbuf = (
                    Gtk.IconTheme()
                    .get_default()
                    .load_icon(
                        "error",
                        configuration.get_property("notification_app_icon_size"),
                        Gtk.IconLookupFlags.FORCE_SIZE,
                    )
                )
        except Exception as e:
            logger.error(f"Error while loading {self.notification.app_icon}: {e}")

            pixbuf = (
                Gtk.IconTheme()
                .get_default()
                .load_icon(
                    "error",
                    configuration.get_property("notification_app_icon_size"),
                    Gtk.IconLookupFlags.FORCE_SIZE,
                )
            )

        app_icon = RoundedImage(
            name="app_icon",
            pixbuf=pixbuf,
        )

        app_details = Box(
            children=[
                app_icon,
                Label(
                    label=app_name,
                    name="app_name",
                    h_expand=True,
                    justification="fill",
                    h_align="start",
                    ellipsization="end",
                    max_chars_width=10,
                    chars_width=1,
                ),
            ]
        )

        if self.autohide:
            dismiss_button = MarkupButton(
                name="dismiss_button",
                markup=configuration.get_property("notification_dismiss_icon"),
                vexpand=True,
            )
            dismiss_button.connect("button-release-event", lambda *_: self.close())
            dismiss_button.connect("enter-notify-event", lambda *_: self.on_hover())

        image_container = Box(orientation="v")
        if image:
            image_container.add(
                RoundedImage(
                    pixbuf=image.scale_simple(
                        int(
                            configuration.get_property(
                                "notification_image_size", "css_settings"
                            )[0:-2]
                        ),
                        int(
                            configuration.get_property(
                                "notification_image_size", "css_settings"
                            )[0:-2]
                        ),
                        GdkPixbuf.InterpType.BILINEAR,
                    ),
                    name="image",
                    h_expand=True,
                )
            )
        else:
            image_container.add(
                Box(
                    name="icon_container",
                    style_classes=custom_icon_color
                    if custom_icon_color
                    else configuration.get_property(
                        f"notification_{URGENCY[self.notification.urgency]}_icon_color"
                    ),
                    h_expand=True,
                    children=[
                        Label(
                            markup=custom_icon
                            if custom_icon
                            else configuration.get_property(
                                f"notification_{URGENCY[self.notification.urgency]}_icon"
                            ),
                            name="icon",
                            h_expand=True,
                            v_expand=True,
                            h_align="fill",
                            v_align="fill",
                            justification="fill",
                        )
                    ],
                )
            )

        image_container.add(Box(v_expand=True))

        summary = Label(
            self.notification.summary.splitlines()[0],
            # self.notification.summary,
            name="summary",
            justification="left",
            h_align="start",
            line_wrap="none" if self.autohide else "word-char",
            h_expand=True,
            max_chars_width=50,
            # chars_width=1,
            ellipsization="end" if self.autohide else "none",
        )
        body = Label(
            '\n'.join(self.notification.body.splitlines()[0:4]),
            name="body",
            justification="left",
            h_align="start",
            line_wrap="word-char",
            h_expand=True,
            # v_expand=True,
            # max_chars_width=10,
            # chars_width=1,
            ellipsization="end" if self.autohide else "none",
        )

        if self.autohide:
            body.set_lines(4)

        notification_body = Box(
            orientation="v",
            name="body_container",
            v_expand=True,
            h_expand=True,
            children=[
                summary,
                body,
                # Box(v_expand=True),
            ],
        )

        self.main_container.children = [
            Box(
                children=[
                    Box(orientation="v", children=[app_details, Box(v_expand=True)]),
                    Box(h_expand=True),
                    dismiss_button if self.autohide else (),
                ],
            ),
            Box(
                children=[
                    image_container,
                    notification_body,
                ]
            ),
        ]

        if progress:
            progress = hints["progress"]

            progress_bar = Gtk.ProgressBar()
            progress_bar.set_hexpand(True)
            progress_bar.get_style_context().add_class(
                custom_icon_color
                if custom_icon_color
                else configuration.get_property(
                    f"notification_{URGENCY[self.notification.urgency]}_icon_color"
                )
            )
            progress_bar.set_name("progress_bar")
            progress_bar.set_fraction(progress / 100.0)
            progress_bar.show()

            self.main_container.add_style_class("special")
            self.main_container.add(progress_bar)

        if actions:
            action_buttons = []
            actions_container = Box(
                name="actions_container",
                children=[Box(h_expand=True)],
                style_classes=custom_icon_color
                if custom_icon_color
                else configuration.get_property(
                    f"notification_{URGENCY[self.notification.urgency]}_icon_color"
                ),
            )
            for action in (
                self.notification.actions
                if not actions_overflow
                else self.notification.actions[
                    0 : (configuration.get_property("notification_max_actions") - 1)
                ]
            ):
                action_button = MarkupButton(
                    name="action_button",
                    markup=action.label,
                    v_expand=True,
                )
                action_button.connect(
                    "button-release-event",
                    lambda button, *_: not self.hidden
                    and self.notification.actions[
                        action_buttons.index(button)
                    ].invoke(),
                )
                action_button.connect("enter-notify-event", lambda *_: self.on_hover())

                action_buttons.append(action_button)
                actions_container.add(action_button)

            if action_buttons.__len__() > 0:
                self.main_container.add_style_class("special")

            if actions_overflow:
                overflow_actions_combo = Gtk.ComboBoxText()
                overflow_actions_combo.set_name("overflow_actions_combo")
                for action in self.notification.actions[
                    (configuration.get_property("notification_max_actions") - 1) :
                ]:
                    overflow_actions_combo.append(action.identifier, action.label)

                overflow_actions_combo.set_active(0)
                overflow_actions_combo.connect(
                    "changed",
                    lambda combo: self.notification.invoke_action(
                        combo.get_active_id()
                    ),
                )
                overflow_actions_combo.show()

                actions_container.add(overflow_actions_combo)

            self.main_container.add(actions_container)

        self.notification.connect("action-invoked", lambda *_: self.close())

        timeout = self.notification.timeout
        if timeout == -1:
            timeout = configuration.get_property(
                f"notification_{URGENCY[self.notification.urgency]}_timeout"
            )

        self.hide_ticket = random.getrandbits(32)
        if self.autohide and timeout > 0:
            self.start_hiding(timeout)

        self.hidden = False
        self.main_container.remove_style_class("hidden")
        self.main_container.remove_style_class("special")
        self.main_container.add_style_class(URGENCY[self.notification.urgency])
        self.reveal()

    def start_hiding(self, timeout):
        def hide(notif: NotificationWidget, timeout, ticket):
            sleep(timeout)

            if notif.hidden or notif.hide_ticket != ticket:
                return

            if notif.hovored:
                notif.do_hide = True
            else:
                def clear_children(container):
                    container.main_container.children = []

                idle_add(notif.reset)
                sleep(0.2)
                idle_add(clear_children, notif)
                idle_add(notif.notification.close)

        GLib.Thread.new("notification_hide", hide, self, timeout, self.hide_ticket)
