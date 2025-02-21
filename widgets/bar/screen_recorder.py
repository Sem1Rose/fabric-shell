from loguru import logger
from config import configuration
import signal
import time

from widgets.buttons import ToggleButton, CycleToggleButton

from fabric.utils.helpers import exec_shell_command, exec_shell_command_async

from fabric.widgets.box import Box
from fabric.widgets.revealer import Revealer


class ScreenRecorder(Box):
    def __init__(self, *args, **kwargs):
        super().__init__(
            name="screen_recorder_container",
            *args,
            **kwargs,
        )

        self.command_handle = None
        self.enable_audio = False
        self.use_mic = False
        self.recording = False

        self.record_toggle = ToggleButton(
            name="record_toggle",
            markup=configuration.get_property("screen_record_widget_record_icon"),
        )
        self.audio_toggle = CycleToggleButton(
            name="audio_toggle",
            states=["none", "speakers", "microphone"],
            markup=configuration.get_property("screen_record_widget_no_audio_icon"),
        )

        self.audio_toggle_revealer = Revealer(
            name="audio_toggle_revealer",
            child=self.audio_toggle,
            transition_type="slide-right",
            transition_duration=200,
        )

        self.record_toggle.connect(
            "on_toggled", lambda _, modifiers: self.toggle_recording(modifiers)
        )
        self.record_toggle.connect(
            "rmb_pressed",
            lambda *_: self.toggle_audio_toggle_revealer(),
        )
        self.record_toggle.connect(
            "mmb_pressed", lambda _, modifiers: self.toggle_recording(modifiers, True)
        )

        self.audio_toggle.connect("on_cycled", lambda *_: self.toggle_audio())

        self.children = [self.record_toggle, self.audio_toggle_revealer]

    def toggle_audio_toggle_revealer(self):
        if self.recording:
            return

        if self.audio_toggle_revealer.child_revealed:
            self.audio_toggle_revealer.unreveal()
            self.remove_style_class("toggle_revealed")
        else:
            self.audio_toggle_revealer.reveal()
            self.add_style_class("toggle_revealed")

    def toggle_audio(self):
        if self.recording:
            return

        self.enable_audio = self.audio_toggle.toggled
        self.use_mic = self.audio_toggle.get_state() == "microphone"

        self.audio_toggle.build(
            lambda toggle, _: toggle.set_markup(
                configuration.get_property("screen_record_widget_mic_icon")
                if self.enable_audio and self.use_mic
                else configuration.get_property("screen_record_widget_speakers_icon")
                if self.enable_audio
                else configuration.get_property("screen_record_widget_no_audio_icon")
            )
        )

    def toggle_recording(self, modifiers=0, portion=False):
        if self.audio_toggle_revealer.child_revealed:
            self.toggle_audio_toggle_revealer()

        if self.recording:
            self.recording = False

            self.record_toggle.set_state(self.recording)

            if self.command_handle is not None:
                self.command_handle.send_signal(signal.SIGINT)
                self.command_handle.wait()
                self.command_handle = None
        else:
            self.record_toggle.set_state(self.recording)

            # logger.warning(modifiers)
            # portion = modifiers & Gdk.ModifierType.SHIFT_MASK

            geometry = None
            if portion:
                geometry = exec_shell_command(
                    configuration.get_property("screen_record_portion_command")
                )
                logger.error(geometry)
                if not geometry or "selection cancelled" in geometry:
                    return

            self.recording_path = f"{configuration.get_property('screen_records_dir')}/{time.strftime(r'%y%m%d.%s', time.localtime())}.mp4"
            self.command = f"{configuration.get_property('screen_record_command')}"

            input_device = None
            output_device = None
            audio_devices = exec_shell_command("pactl info")
            for line in audio_devices.splitlines():
                if "Default Sink: " in line:
                    output_device = f"'{line.split(': ')[1]}.monitor'"
                elif "Default Source: " in line:
                    input_device = f"'{line.split(': ')[1]}.monitor'"

            if self.enable_audio and (input_device or output_device):
                self.command = " ".join(
                    [
                        self.command,
                        configuration.get_property("screen_record_audio_option"),
                    ]
                )

                if self.use_mic and not input_device:
                    self.audio_toggle.set_state("speakers")
                    self.toggle_audio()
                elif not self.use_mic and not output_device:
                    self.audio_toggle.set_state("microphone")
                    self.toggle_audio()

                if self.use_mic:
                    self.command = "".join(
                        [
                            self.command,
                            input_device,
                            # "'",
                            # configuration.get_property("screen_record_microphone_sink"),
                            # ".monitor'",
                        ]
                    )
                else:
                    self.command = "".join(
                        [
                            self.command,
                            output_device,
                            # "'",
                            # configuration.get_property("screen_record_speakers_sink"),
                            # ".monitor'",
                        ]
                    )

            if portion:
                self.command = " ".join(
                    [
                        self.command,
                        configuration.get_property("screen_record_portion_option"),
                        f'"{geometry}"',
                    ]
                )

            self.command = " ".join(
                [
                    self.command,
                    configuration.get_property("screen_record_output_option"),
                    self.recording_path,
                ]
            )

            # logger.warning(self.command)

            self.recording = True
            self.record_toggle.set_state(self.recording)
            (self.command_handle, _) = exec_shell_command_async(self.command)

        self.record_toggle.build(
            lambda toggle, _: toggle.set_markup(
                configuration.get_property("screen_record_widget_stop_icon")
                if self.recording
                else configuration.get_property("screen_record_widget_record_icon")
            )
        )
