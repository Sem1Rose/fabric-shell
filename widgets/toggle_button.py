from fabric.widgets.button import Button
from fabric.core.service import Signal


class ToggleButton(Button):
    @Signal
    def on_toggled(self): ...

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.toggled = False

        self.connect("clicked", lambda *_: self.toggle())

    def toggle(self):
        self.set_state(not self.toggled)
        self.on_toggled()

    def set_state(self, state):
        self.toggled = state
        if state:
            self.add_style_class("toggled")
        else:
            self.remove_style_class("toggled")


class CycleToggleButton(Button):
    @Signal
    def on_cycled(self): ...

    def __init__(self, states, **kwargs):
        super().__init__(**kwargs)

        self.toggled = False
        self.states = states
        self.num_states = states.__len__()

        self.state = 0

        self.connect("clicked", lambda *_: self.cycle())

    def cycle(self):
        def cycle_val(v, max):
            if v < max:
                return v
            return 0

        self.set_state(index=cycle_val(self.state + 1, self.num_states))
        self.on_cycled()

    def set_state(self, state=None, index=None):
        if state is None and index is None:
            return
        if state is not None:
            self.state = self.states.index(state)
        elif index is not None:
            self.state = index

        self.toggled = self.state > 0

        if self.toggled:
            self.add_style_class("toggled")
        else:
            self.remove_style_class("toggled")

    def get_state(self):
        return self.states[self.state]
