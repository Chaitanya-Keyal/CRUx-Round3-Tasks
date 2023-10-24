import os
import pickle


ASSET = os.curdir + "/assets/theme"
THEME_FILE = os.curdir + "/settings/theme.bin"


class Theme:
    def __init__(self, root, theme="dark"):
        self.root = root
        self.root.tk.call("source", os.path.join(ASSET, "void.tcl"))

        for i in ["dark", "light"]:
            self.root.tk.call("init", i, os.path.join(ASSET, i))

        self.root.tk.call("set_theme", theme)

    def toggle_theme(self):
        if self.root.tk.call("ttk::style", "theme", "use") == "void-dark":
            t = "light"
        else:
            t = "dark"

        self.root.tk.call("set_theme", t)

        with open(THEME_FILE, "rb+") as f:
            pickle.dump(t, f)

    def curr_theme(self):
        return self.root.tk.call("ttk::style", "theme", "use")[5:]
