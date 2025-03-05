class Applet:
    def hide(self, *args):
        self.add_style_class("hidden")

    def unhide(self, *args):
        self.remove_style_class("hidden")
