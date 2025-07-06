import gi
from time import sleep

from loguru import logger
from widgets.buttons import MarkupButton
from widgets.rounded_image import RoundedImage

from config import configuration

from fabric.notifications import Notification
from fabric.widgets.eventbox import EventBox
from fabric.widgets.box import Box
from fabric.widgets.revealer import Revealer
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

        self.main_contianer = Box(orientation="v", style_classes="notification")

        self.autohide = autohide

        if not self.autohide:
            self.reveal()
        else:
            self.main_contianer.add_style_class("hidden")

        self.hidden = True
        self.hovored = False
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
            self.unreveal()
            self.hidden = True
            self.main_contianer.add_style_class("hidden")

        self.hovored = False
        self.do_hide = False

    def rebuild(self):
        self.reset()
        self.main_contianer.remove_style_class("hidden")

        timeout = self.notification.timeout
        if timeout == -1:
            timeout = configuration.get_property(
                f"notification_{URGENCY[self.notification.urgency]}_timeout"
            )

        self.reveal()
        self.hidden = False

        if self.autohide and timeout > 0:
            self.start_hiding(timeout)

    def build_from_notification(self, notification: Notification):
        self.reset()

        self.notification = notification

        self.main_contianer.remove_style_class("hidden")
        self.main_contianer.remove_style_class("special")
        for i in URGENCY.values():
            self.main_contianer.remove_style_class(i)
        self.main_contianer.add_style_class(URGENCY[self.notification.urgency])

        hints = {}
        for hint in CUSTOM_HINTS:
            hints[hint] = notification.do_get_hint_entry(f"fabric-shell-{hint}")

        progress = hints["progress"] is not None
        custom_icon = hints["custom-icon"]
        custom_icon_color = (
            hints["accent-color"] if hints["accent-color"] in COLORS else None
        )

        actions = notification.actions.__len__() > 0
        actions_overflow = notification.actions.__len__() > configuration.get_property(
            "notification_max_actions"
        )

        image = notification.image_pixbuf
        app_name = notification.app_name
        app_icon = RoundedImage(
            name="app_icon",
            pixbuf=Gtk.IconTheme().load_icon(
                self.notification.app_icon,
                configuration.get_property("notification_app_icon_size"),
                Gtk.IconLookupFlags.FORCE_SIZE,
            )
            if self.notification.app_icon
            else Gtk.IconTheme()
            .get_default()
            .load_icon(
                "image-missing",
                configuration.get_property("notification_app_icon_size"),
                Gtk.IconLookupFlags.FORCE_SIZE,
            ),
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

        notification_body = Box(
            orientation="v",
            name="body_container",
            v_expand=True,
            h_expand=True,
            children=[
                Label(
                    self.notification.summary,
                    name="summary",
                    justification="fill",
                    h_align="start",
                    line_wrap="`word",
                    h_expand=True,
                    max_chars_width=50,
                    chars_width=1,
                ),
                Label(
                    self.notification.body,
                    name="body",
                    justification="fill",
                    h_align="start",
                    line_wrap="word",
                    h_expand=True,
                    max_chars_width=300,
                    chars_width=1,
                ),
                Box(v_expand=True),
            ],
        )

        self.main_contianer.children = [
            Box(
                children=[
                    Box(orientation="v", children=[app_details, Box(v_expand=True)]),
                    Box(h_expand=True),
                    dismiss_button,
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

            self.main_contianer.add_style_class("special")
            self.main_contianer.add(progress_bar)

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
                self.main_contianer.add_style_class("special")

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

            self.main_contianer.add(actions_container)

        timeout = self.notification.timeout
        if timeout == -1:
            timeout = configuration.get_property(
                f"notification_{URGENCY[self.notification.urgency]}_timeout"
            )

        self.notification.connect("action-invoked", lambda *_: self.close())

        self.reveal()
        self.hidden = False

        if self.autohide and timeout > 0:
            self.start_hiding(timeout)

    def start_hiding(self, timeout):
        def hide(self, timeout):
            sleep(timeout)
            if self.hidden:
                return

            if self.hovored:
                self.do_hide = True
            else:
                idle_add(self.reset)
                sleep(0.2)
                idle_add(self.notification.close)

        GLib.Thread.new("notification_hide", hide, self, timeout)
