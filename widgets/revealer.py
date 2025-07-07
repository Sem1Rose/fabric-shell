from fabric.core import Signal
from fabric.widgets.revealer import Revealer as GTKRevealer

class Revealer(GTKRevealer):
    @Signal
    def on_revealed(self): ...

    @Signal
    def on_unrevealed(self): ...

    def reveal(self):
        super().reveal()
        self.on_revealed()

    def unreveal(self):
        super().unreveal()
        self.on_unrevealed()