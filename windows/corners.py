from loguru import logger
from config import configuration

from fabric.widgets.wayland import WaylandWindow as Window
from fabric.widgets.shapes.corner import Corner
from fabric.widgets.box import Box
from widgets.helpers.workspace_properties import get_workspace_properties_service


class CornersWindow(Window):
    def __init__(self, *args, **kwargs):
        super().__init__(
            name="corners_window",
            anchor="top right bottom left",
            exclusivity="none",
            layer="top",
            style="background-color: transparent;",
            margin=f"{configuration.get_property('pill_height', 'css_settings')} 0px 0px 0px",
            pass_through=True,
            visible=False,
            *args,
            **kwargs,
        )

        self.main_container = Box(
            name="main_container",
            orientation="v",
            style="background-color: transparent;",
        )
        self.corners: list[Corner] = []
        for vert in ["top", "bottom"]:
            for horiz in ["left", "right"]:
                self.corners.append(
                    Box(
                        name="corner_container",
                        style="background-color: transparent;",
                        children=Corner(
                            orientation=f"{vert}-{horiz}",
                            name="corner",
                            h_expand=True,
                            v_expand=True,
                        ),
                    )
                )

        self.main_container.add(
            Box(
                children=[
                    self.corners[0],
                    Box(h_expand=True, style="background-color: transparent;"),
                    self.corners[1],
                ],
                style="background-color: transparent;",
            )
        )
        self.main_container.add(
            Box(h_expand=True, v_expand=True, style="background-color: transparent;")
        )
        self.main_container.add(
            Box(
                children=[
                    self.corners[2],
                    Box(h_expand=True, style="background-color: transparent;"),
                    self.corners[3],
                ],
                style="background-color: transparent;",
            )
        )

        # self.service = get_workspace_properties_service()
        # self.service.connect(
        #     "on-fullscreen",
        #     lambda _, state: self.hide() if state > 0 else self.unhide(),
        # )

        # if self.service.fullscreen_state > 0:
        #     self.hide()

        self.add(self.main_container)
        self.show_all()

    def hide(self):
        for corner in self.corners:
            corner.add_style_class("hidden")

    def unhide(self):
        for corner in self.corners:
            corner.remove_style_class("hidden")
