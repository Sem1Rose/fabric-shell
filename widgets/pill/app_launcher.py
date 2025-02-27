from loguru import logger

from config import configuration
from widgets.grid import Grid

from fabric.widgets.box import Box
from fabric.core.service import Signal
from fabric.utils.helpers import get_desktop_applications


class AppLauncher(Box):
    @Signal
    def on_launched(self): ...

    def __init__(self, *args, **kwargs):
        super().__init__(name="pill_app_launcher", orientation="v", *args, **kwargs)

        self.app_grid = Grid(
            columns=configuration.get_property("app_launcher_columns"),
            rows=configuration.get_property("app_launcher_rows"),
            items_fetcher=get_desktop_applications,
            item_sort_name_fetcher=lambda app: f"{app.name} {app.generic_name} {app.display_name} {app.description}",
            item_factory=lambda item: (
                item.display_name,
                item.get_icon_pixbuf(
                    size=configuration.get_property("app_launcher_icon_size")
                ),
            ),
        )

        self.app_grid.connect("on_item_clicked", lambda *_: self.select_app())

        self.children = [self.app_grid]

    def handle_arrow_keys(self, event):
        match event.keyval:
            case 65363:  # right arrow
                self.app_grid.inc_selection()
            case 65361:  # left arrow
                self.app_grid.dec_selection()
            case 65362:  # up arrow
                self.app_grid.dec_selection_row()
            case 65364:  # down arrow
                self.app_grid.inc_selection_row()
        return False

    def select_app(self):
        app = self.app_grid.items[self.app_grid.selected_item]
        logger.error(app._app.get_executable())
        try:
            app.launch()
            logger.info(f"Launching {app.name}...")
        except Exception as e:
            logger.error(f"Error while trying to launch {app.name}: {e}...")

        self.on_launched()

    def hide(self, *args):
        self.add_style_class("hidden")

    def unhide(self, *args):
        self.remove_style_class("hidden")
        self.app_grid.reset_items()
        # self.app_grid.init_items()
