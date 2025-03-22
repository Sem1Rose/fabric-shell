import psutil
from loguru import logger
from config import configuration

from widgets.circular_progress_icon import CircularProgressIcon

from fabric.core.service import Property
from fabric.core.fabricator import Fabricator
from fabric.widgets.box import Box


class ResourceMonitor(Box):
    def __init__(self, *args, **kwargs):
        super().__init__(
            name="resource_monitor_widget",
            style_classes="bar_widget",
            *args,
            **kwargs,
        )

        # def progress_set_value(progress, value):
        #     progress.value = value

        # self.cpu_usage_progress = CircularProgressBar(
        #     name="cpu_usage_progress",
        #     style_classes="circular_progress",
        #     line_style="butt",
        #     h_expand=True,
        #     v_expand=True,
        #     start_angle=90,
        #     end_angle=450,
        # ).build(
        #     lambda progress, _: Fabricator(
        #         poll_from=lambda *_: psutil.cpu_percent(),
        #         interval=configuration.get_property("resource_monitor_poll_interval"),
        #         on_changed=lambda _, value: progress_set_value(
        #             progress, float(value) / 100
        #         ),
        #     )
        # )

        # self.cpu_block = Box(
        #     name="cpu_usage_block",
        #     style_classes="circular_progress_block",
        #     children=[
        #         Box(
        #             style_classes="circular_progress_container",
        #             children=[self.cpu_usage_progress],
        #         ),
        #         Label(
        #             style_classes="circular_progress_label",
        #             label=configuration.get_property("resource_monitor_cpu_icon_"),
        #         ),
        #     ],
        # )

        # self.memory_usage_progress = CircularProgressBar(
        #     name="memory_usage_progress",
        #     style_classes="circular_progress",
        #     line_style="butt",
        #     h_expand=True,
        #     v_expand=True,
        #     start_angle=90,
        #     end_angle=450,
        # ).build(
        #     lambda progress, _: Fabricator(
        #         poll_from=lambda *_: psutil.virtual_memory().percent,
        #         interval=configuration.get_property("resource_monitor_poll_interval"),
        #         on_changed=lambda _, value: progress_set_value(
        #             progress, float(value) / 100
        #         ),
        #     )
        # )

        # self.memory_block = Box(
        #     name="memory_usage_block",
        #     style_classes="circular_progress_block",
        #     children=[
        #         Box(
        #             style_classes="circular_progress_container",
        #             children=[self.memory_usage_progress],
        #         ),
        #         Label(
        #             style_classes="circular_progress_label",
        #             label=configuration.get_property("resource_monitor_memory_icon_"),
        #         ),
        #     ],
        # )

        self.cpu_block = ResourceBlock().build(
            lambda block, _: block.bulk_set(
                name="CPU Usage",
                icon=configuration.get_property("resource_monitor_cpu_icon"),
                percentage=0.0,
            )
        )
        self.memory_block = ResourceBlock().build(
            lambda block, _: block.bulk_set(
                name="Memory Usage",
                icon=configuration.get_property("resource_monitor_memory_icon"),
                percentage=0.0,
            )
        )

        Fabricator(
            poll_from=lambda *_: psutil.cpu_percent(),
            interval=configuration.get_property("resource_monitor_poll_interval"),
            on_changed=lambda _, value: self.cpu_block.bulk_set(
                percentage=float(value) / 100
            ),
        )

        Fabricator(
            poll_from=lambda *_: psutil.virtual_memory().percent,
            interval=configuration.get_property("resource_monitor_poll_interval"),
            on_changed=lambda _, value: self.memory_block.bulk_set(
                percentage=float(value) / 100
            ),
        )

        self.children = [
            self.memory_block,
            Box(
                style_classes="circular_progress_block_spacer",
                v_expand=True,
            ),
            self.cpu_block,
        ]


class ResourceBlock(CircularProgressIcon):
    @Property(str, "rw", default_value="")
    def resource_name(self) -> str:
        return self._resource_name

    @resource_name.setter
    def resource_name(self, value: str):
        self._resource_name = value
        # self.update_tooltip()

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(
            tooltip_markup=configuration.get_property(
                "resource_monitor_tooltip_markup"
            ),
            *args,
            **kwargs,
        )
        self._resource_name = ""

    def bulk_set(self, name: str | None = None, **kwargs):
        if name is not None:
            self.resource_name = name
        super().bulk_set(**kwargs)

    def update_tooltip(self):
        super().update_tooltip(name=self._resource_name)
