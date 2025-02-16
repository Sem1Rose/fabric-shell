import gi

from widgets.buttons import MarkupButton as Button

gi.require_version("Gray", "0.1")
gi.require_version("Gtk", "3.0")
from gi.repository import Gray, Gtk, Gdk, GdkPixbuf, GLib  # noqa: E402


# Special thanks to Axenide (https://github.com/Axenide) 🙏🙏🙏
class SystemTray(Gtk.Box):
    def __init__(self, icon_size: int = 20, **kwargs) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, **kwargs)
        self.icon_size = icon_size
        self.watcher = Gray.Watcher()
        self.watcher.connect("item-added", self.on_item_added)

    def on_item_added(self, _, identifier: str):
        item = self.watcher.get_item_for_identifier(identifier)
        item_button = self.do_bake_item_button(item)
        item.connect("removed", lambda *args: item_button.destroy())
        item_button.show_all()
        self.add(item_button)

    def do_bake_item_button(self, item: Gray.Item) -> Gtk.Button:
        button = Button()

        button.connect(
            "button-press-event",
            lambda button, event: self.on_button_click(button, item, event),
        )

        pixmap = Gray.get_pixmap_for_pixmaps(item.get_icon_pixmaps(), self.icon_size)

        try:
            if pixmap is not None:
                pixbuf = pixmap.as_pixbuf(self.icon_size, GdkPixbuf.InterpType.HYPER)
            elif item.get_icon_name():
                pixbuf = Gtk.IconTheme().load_icon(
                    item.get_icon_name(),
                    self.icon_size,
                    Gtk.IconLookupFlags.FORCE_SIZE,
                )
            else:
                pixbuf = (
                    Gtk.IconTheme()
                    .get_default()
                    .load_icon(
                        "image-missing",
                        self.icon_size,
                        Gtk.IconLookupFlags.FORCE_SIZE,
                    )
                )
        except GLib.Error:
            pixbuf = (
                Gtk.IconTheme()
                .get_default()
                .load_icon(
                    "image-missing",
                    self.icon_size,
                    Gtk.IconLookupFlags.FORCE_SIZE,
                )
            )

        button.set_image(Gtk.Image.new_from_pixbuf(pixbuf))
        return button

    def on_button_click(self, button, item: Gray.Item, event):
        if event.button == Gdk.BUTTON_PRIMARY:
            try:
                item.activate(event.x, event.y)
            except Exception as e:
                print(f"Error activating the item: {e}")
        elif event.button == Gdk.BUTTON_SECONDARY:
            menu = item.get_menu()
            if menu:
                menu.set_name("system-tray-menu")
                menu.popup_at_widget(
                    button,
                    Gdk.Gravity.SOUTH,
                    Gdk.Gravity.NORTH,
                    event,
                )
            else:
                item.context_menu(event.x, event.y)
