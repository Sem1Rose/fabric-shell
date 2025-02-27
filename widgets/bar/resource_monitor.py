from loguru import logger
from config import configuration
import psutil

from fabric.core.fabricator import Fabricator

from fabric.widgets.box import Box
from fabric.widgets.circularprogressbar import CircularProgressBar
from fabric.widgets.label import Label


class ResourceMonitor(Box):
    def __init__(self, *args, **kwargs):
        super().__init__(
            name="resource_monitor_widget",
            style_classes="bar_widget",
            *args,
            **kwargs,
        )

        def progress_set_value(progress, value):
            progress.value = value

        self.cpu_usage_progress = CircularProgressBar(
            name="cpu_usage_progress",
            style_classes="circular_progress",
            line_style="butt",
            h_expand=True,
            v_expand=True,
            start_angle=90,
            end_angle=450,
        ).build(
            lambda progress, _: Fabricator(
                poll_from=lambda *_: psutil.cpu_percent(),
                interval=configuration.get_property("resource_monitor_poll_interval"),
                on_changed=lambda _, value: progress_set_value(
                    progress, float(value) / 100
                ),
            )
        )

        self.cpu_block = Box(
            name="cpu_usage_block",
            style_classes="circular_progress_block",
            children=[
                Box(
                    style_classes="circular_progress_container",
                    children=[self.cpu_usage_progress],
                ),
                Label(
                    style_classes="circular_progress_label",
                    label=configuration.get_property("resource_monitor_cpu_icon_"),
                ),
            ],
        )

        self.memory_usage_progress = CircularProgressBar(
            name="memory_usage_progress",
            style_classes="circular_progress",
            line_style="butt",
            h_expand=True,
            v_expand=True,
            start_angle=90,
            end_angle=450,
        ).build(
            lambda progress, _: Fabricator(
                poll_from=lambda *_: psutil.virtual_memory().percent,
                interval=configuration.get_property("resource_monitor_poll_interval"),
                on_changed=lambda _, value: progress_set_value(
                    progress, float(value) / 100
                ),
            )
        )

        self.memory_block = Box(
            name="memory_usage_block",
            style_classes="circular_progress_block",
            children=[
                Box(
                    style_classes="circular_progress_container",
                    children=[self.memory_usage_progress],
                ),
                Label(
                    style_classes="circular_progress_label",
                    label=configuration.get_property("resource_monitor_memory_icon_"),
                ),
            ],
        )

        self.children = [
            self.memory_block,
            Box(
                style_classes="circular_progress_block_spacer",
                v_expand=True,
            ),
            self.cpu_block,
        ]
