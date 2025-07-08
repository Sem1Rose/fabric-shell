from loguru import logger

from config import configuration
from widgets import notification_widget
from widgets.pill.pill import Pill, PillApplets
from widgets.pill.popup_notifications import NotificationsContainer
from widgets.buttons import MarkupButton

from fabric.widgets.box import Box
from fabric.widgets.wayland import WaylandWindow as Window
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.button import Button
# from fabric.widgets.eventbox import EventBox

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402


class PillWindow(Window):
    def __init__(self, *args, **kwargs):
        super().__init__(
            anchor="top",
            exclusivity="normal",
            layer="top",
            margin=f"-{configuration.get_property('pill_height', 'css_settings')} 0px 0px 0px",
            visible=False,
            *args,
            **kwargs,
        )

        def create_spacings(**args):
            def on_click():
                # if self.pill.dashboard.expanded or self.pill.dashboard.peeking:
                #     self.unpeek()
                #     return True
                # else:
                #     return False
                self.change_applet("dashboard", expand=False)

            box = Button(v_expand=True, h_expand=True, **args)
            box.set_can_focus(False)
            box.connect("clicked", lambda *_: on_click())
            return box

        self.pill = Pill()
        self.pill.connect("on_peeked", self.on_peeked)
        self.pill.connect("on_unpeeked", self.on_unpeeked)
        self.pill.connect("on_expanded", self.on_expanded)

        self.notifications_container = NotificationsContainer()

        # self.hover_listener = EventBox(
        #     name="hover_listener",
        #     child=self.pill,
        # )

        if self.pill.dashboard.quick_settings_widget.do_not_disturb:
            self.pill.dashboard.quick_settings_widget.do_not_disturb.connect(
                "on-toggled",
                lambda toggle, *_: (
                    self.notifications_container.do_not_disturb() if toggle.toggled else self.notifications_container.do_disturb(),
                    toggle.set_icon(
                        configuration.get_property(
                            "dnd_on_icon" if toggle.toggled else "dnd_off_icon"
                        )
                    ),
                ),
            )

        self.left_button = MarkupButton(
            style_classes="floating_buttons",
            markup=configuration.get_property("wallpaper_selector_icon"),
        )
        self.left_button.set_can_focus(False)
        self.left_button.set_focus_on_click(False)

        self.right_button = MarkupButton(
            style_classes="floating_buttons",
            markup=configuration.get_property("power_menu_icon"),
        )
        self.right_button.set_can_focus(False)
        self.right_button.set_focus_on_click(False)

        self.center_box = CenterBox(name="pill_window", orientation="h")
        self.center_box.center_container.set_orientation(Gtk.Orientation.VERTICAL)
        self.center_box.center_children = [
            self.pill,
            self.notifications_container,
            create_spacings(),
        ]
        self.center_box.start_children = [
            create_spacings(),
            Box(children=[self.left_button, create_spacings()], orientation="v"),
        ]
        self.center_box.end_children = [
            Box(children=[self.right_button, create_spacings()], orientation="v"),
            create_spacings(),
        ]

        self.pill_widgets = [self.left_button, self.right_button]

        self.left_button.connect("clicked", lambda *_: self.change_applet("wallpaper"))
        self.right_button.connect("clicked", lambda *_: self.change_applet("powermenu"))

        self.add_keybinding(
            "Escape",
            lambda _, event_key: self.handle_esc(event_key),
        )
        self.add_keybinding(
            "Return",
            lambda _, event_key: self.handle_enter(event_key),
        )
        self.add_keybinding(
            "Right",
            lambda _, event_key: self.handle_arrow_keys(event_key),
        )
        self.add_keybinding(
            "Left",
            lambda _, event_key: self.handle_arrow_keys(event_key),
        )
        self.add_keybinding(
            "Up",
            lambda _, event_key: self.handle_arrow_keys(event_key),
        )
        self.add_keybinding(
            "Down",
            lambda _, event_key: self.handle_arrow_keys(event_key),
        )

        self.add(self.center_box)
        self.show_all()

    def handle_esc(self, _):
        match self.pill.active_applet:
            case PillApplets.DASHBOARD:
                self.unpeek()
            case PillApplets.POWERMENU:
                if not self.pill.powermenu.handle_esc():
                    self.change_applet("dashboard", expand=False)
            case _:
                self.change_applet("dashboard", expand=False)

    def handle_enter(self, _):
        match self.pill.active_applet:
            case PillApplets.POWERMENU:
                self.pill.powermenu.handle_enter()
            case PillApplets.WALLPAPER:
                self.pill.wallpaper_selector.select_wallpaper()
            case PillApplets.LAUNCHER:
                self.pill.app_launcher.select_app()
            case _:
                pass

    def handle_arrow_keys(self, event_key):
        match self.pill.active_applet:
            case PillApplets.POWERMENU:
                self.pill.powermenu.navigate_actions(event_key)
            case PillApplets.WALLPAPER:
                self.pill.wallpaper_selector.handle_arrow_keys(event_key)
            case PillApplets.LAUNCHER:
                self.pill.app_launcher.handle_arrow_keys(event_key)
            case _:
                pass

    def on_expanded(self, _, applet):
        for child in self.pill_widgets:
            child.add_style_class("expanded")
            child.add_style_class("peeking")

        if applet != PillApplets.DASHBOARD:
            self.steal_input()
        else:
            self.return_input()

            self.notifications_container.hide()

    def on_peeked(self, _, applet):
        for child in self.pill_widgets:
            child.remove_style_class("expanded")
            child.add_style_class("peeking")

        self.notifications_container.unhide()

    def on_unpeeked(self, _, applet):
        for child in self.pill_widgets:
            child.remove_style_class("expanded")
            child.remove_style_class("peeking")

        self.return_input()

        self.notifications_container.unhide()

    def change_applet(self, applet, expand=True):
        if applet == "dashboard" or applet == PillApplets.DASHBOARD:
            applet = PillApplets.DASHBOARD
        elif applet == "powermenu" or applet == PillApplets.POWERMENU:
            applet = PillApplets.POWERMENU
        elif applet == "wallpaper" or applet == PillApplets.WALLPAPER:
            applet = PillApplets.WALLPAPER
        elif applet == "launcher" or applet == PillApplets.LAUNCHER:
            applet = PillApplets.LAUNCHER
        else:
            logger.error(f"Unknown applet {applet}")
            return

        self.pill.select_pill_applet(applet, expand)

    def toggle_dashboard_expand(self, peek=False):
        self.pill.toggle_dashboard_expand(peek)

    def expand(self):
        self.pill.expand()

    def peek(self):
        self.pill.peek()

    def unpeek(self):
        self.pill.unpeek()
