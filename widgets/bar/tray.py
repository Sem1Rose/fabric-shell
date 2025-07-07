from typing import Literal
from config import configuration

from widgets.buttons import MarkupButton
from widgets.system_tray import SystemTray
from widgets.revealer import Revealer

from fabric.widgets.box import Box
from fabric.widgets.eventbox import EventBox


class Tray(EventBox):
    def __init__(self, dir: Literal["left", "right"] = "left", *args, **kwargs):
        super().__init__(
            *args,
            **kwargs,
        )

        self.dir = dir

        self.sys_tray = SystemTray(
            name="tray_widget",
            icon_size=configuration.get_property("tray_icon_size"),
        )
        self.revealer = Revealer(
            child=self.sys_tray,
            transition_type=f"slide_{self.dir}",
            transition_duration=configuration.get_property(
                "bar_revealer_animation_duration"
            ),
        )

        self.expander = MarkupButton(
            name="tray_container_expander",
            markup=configuration.get_property(f"chevron_{self.dir}"),
        )
        self.expander.connect(
            "clicked",
            lambda *_: self.on_expander_clicked(),
        )

        self.add(
            Box(
                name="tray_container",
                style_classes="bar_widget",
                children=[
                    self.revealer,
                    self.expander,
                ],
            )
        )

        # self.tray_hovered = False
        # self.tray_unreveal_handler = None
        # self.cancellable = Gio.Cancellable.new()

        # def change_tray_hovered(hovered):
        #     self.tray_hovered = hovered

        #     # if not hovered and self.tray_revealer.child_revealed:
        #     #     start_unreveal_thread()

        # def start_unreveal_thread():
        #     # if not self.tray_revealer.child_revealed:
        #     #     return
        #     if self.tray_unreveal_handler is not None:
        #         # self.tray_unreveal_handler.get_cancellable().cancel()
        #         # if cancellable := self.tray_unreveal_handler.get_cancellable():
        #         #     logger.error("cancelled")
        #         #     cancellable.cancel()
        #         self.cancellable.cancel()
        #         self.cancellable = Gio.Cancellable.new()
        #         self.tray_unreveal_handler = None

        #     def unreveal(*_):
        #         logger.warning("waiting")
        #         self.cancellable.set_error_if_cancelled()
        #         GLib.usleep(int(3 * 1e6))
        #         logger.warning("closing")

        #         if not self.tray_hovered and self.tray_revealer.child_revealed:
        #             logger.warning("closed")
        #             idle_add(on_tray_expander_clicked)

        #     # self.tray_unreveal_handler = Gio.Task.new()
        #     self.tray_unreveal_handler = Gio.Task.new()
        #     self.tray_unreveal_handler.set_return_on_cancel(True)
        #     self.tray_unreveal_handler.run_in_thread(unreveal)
        #     # self.tray_unreveal_handler = GLib.Thread.new("tray_unreveal", unreveal)

        # self.tray_expander.connect(
        #     "enter-notify-event", lambda *_: change_tray_hovered(True)
        # )
        # self.tray_expander.connect(
        #     "leave-notify-event", lambda *_: change_tray_hovered(False)
        # )

    def on_expander_clicked(self):
        if self.revealer.child_revealed:
            self.revealer.unreveal()
            self.expander.remove_style_class("revealed")
            self.expander.set_markup(configuration.get_property(f"chevron_{self.dir}"))
        else:
            self.revealer.reveal()
            self.expander.add_style_class("revealed")
            self.expander.set_markup(
                configuration.get_property(
                    f"chevron_{'left' if self.dir == 'right' else 'right'}"
                )
            )
