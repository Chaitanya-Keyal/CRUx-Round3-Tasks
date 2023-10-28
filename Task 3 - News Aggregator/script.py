import base64
import json
import os
import pickle
import random
import re
import sys
import threading
import tkinter as tk
import tkinter.ttk as ttk
import webbrowser
from functools import partial as lambda_func
from io import BytesIO
from tkinter import filedialog as fd
from tkinter import messagebox as msgb

import requests
from PIL import Image, ImageChops, ImageDraw, ImageTk

sys.path.append(os.curdir)
import util.db_handler as db
from util.theme import Theme
from util.xml_parser import get_articles_from_rss

ASSETS = os.path.join(os.curdir, "assets")

REMEMBER_ME_FILE = os.path.join(os.curdir, "settings", "remember_me.bin")

THEME_FILE = os.path.join(os.curdir, "settings", "theme.bin")

f = open(os.path.join(ASSETS, "rss_feeds.json"), "r")
RSS_FEEDS: dict = json.load(f)
f.close()

if not os.name == "nt":
    print("I don't like your Operating System. Install Windows.")


class ScrollableFrame(ttk.Frame):
    def __init__(self, parent, height, *args, **kwargs):
        ttk.Frame.__init__(
            self, parent, style="Card.TFrame", padding=4, *args, **kwargs
        )

        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(
            self,
            orient="vertical",
            command=self.canvas.yview,
            style="Vertical.TScrollbar",
        )
        self.scrollable_frame = tk.Frame(self.canvas)

        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        self.scrollbar.place(relx=1.0, rely=0, relheight=1.0, anchor="ne")
        self.canvas.place(relx=0, rely=0, relwidth=0.98, relheight=1.0)
        self.canvas.create_window(
            (0, 0),
            window=self.scrollable_frame,
            anchor="nw",
            tags="self.scrollable_frame",
            height=height,
        )

    def _on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig("self.scrollable_frame", width=event.width)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(-1 * int(event.delta / 120), "units")


class NewsAggregator(tk.Toplevel):
    def __init__(self):
        super().__init__()
        # GUI Initializing
        self.screen_width = int(0.9 * self.winfo_screenwidth())
        self.screen_height = int(self.screen_width / 1.9)
        self.x_coord = self.winfo_screenwidth() // 2 - self.screen_width // 2
        self.y_coord = (self.winfo_screenheight() - 70) // 2 - self.screen_height // 2

        self.title("News Aggregator")
        self.iconbitmap(os.path.join(ASSETS, "icon.ico"))
        self.geometry(
            f"{self.screen_width//2}x{self.screen_height}+{self.x_coord+self.screen_width//4}+{self.y_coord}"
        )
        self.protocol("WM_DELETE_WINDOW", self.exit)
        self.minsize(self.screen_width // 2, self.screen_height)

    def initialize(self, name):
        self.name = name
        self.tabs = {"favorites": None, "saved": None}
        self.tabs.update({i: None for i in RSS_FEEDS})
        self.feed_threads = {i: None for i in self.tabs}
        self.feed_frames = {i: None for i in self.tabs}
        self.loading_labels = {i: None for i in self.tabs}
        self.loaded_once = {i: False for i in self.tabs}
        self.logo_label.destroy()
        self.geometry(
            f"{self.screen_width}x{self.screen_height}+{self.x_coord}+{self.y_coord}"
        )
        self.minsize(self.screen_width, self.screen_height)

        self.notebook = ttk.Notebook(self, style="TNotebook")
        self.notebook.place(relx=0, rely=0, anchor="nw", relheight=1, relwidth=1)
        self.notebook.enable_traversal()

        self.queue = []

        def load_queue():
            while True:
                for topic in self.queue:
                    print(f"Loading {topic} Feed")
                    try:
                        self.queue.remove(topic)
                    except ValueError:
                        pass
                    self.loaded_once[topic] = True
                    self.show_feed(topic)
                    self.loading_labels[topic].destroy()

        def load_feed(topic, force=False):
            if not self.loaded_once[topic] or force:
                self.loading_labels[topic] = tk.Label(
                    self.tabs[topic],
                    text="Loading...",
                    font=("rockwell", 16),
                )
                self.loading_labels[topic].place(relx=0.5, rely=0.03, anchor="center")

                if topic == "saved":
                    print("Loading saved Feed")
                    self.feed_threads[topic] = threading.Thread(
                        target=self.show_feed, args=(topic,), daemon=True
                    )
                    self.feed_threads[topic].start()
                    self.loaded_once[topic] = True
                else:
                    if topic not in self.queue:
                        self.queue.append(topic)

            # rebind scroll wheel
            try:
                self.feed_frames[topic].canvas.bind_all(
                    "<MouseWheel>", self.feed_frames[topic]._on_mousewheel
                )
            except AttributeError:
                pass

        self.notebook.bind(
            "<<NotebookTabChanged>>",
            lambda a: load_feed(
                self.notebook.tab(self.notebook.select(), "text").lower()
            ),
        )

        threading.Thread(target=load_queue, daemon=True).start()

        for i in self.tabs:
            self.tabs[i] = tk.Frame(self.notebook)
            self.tabs[i].place(relx=0, rely=0, relheight=1, relwidth=1, anchor="nw")
            self.notebook.add(self.tabs[i], text=i.title())

            self.feed_frames[i] = ttk.Frame(
                self.tabs[i], style="Card.TFrame", padding=4
            )
            tk.Label(
                self.feed_frames[i],
                text="Wow, Such Empty...",
                font=("rockwell", 16),
            ).place(relx=0.5, rely=0.5, anchor="center")
            self.feed_frames[i].place(
                relx=0.01, rely=0.07, relheight=0.9, relwidth=0.98
            )
            ttk.Button(
                self.tabs[i],
                text="Refresh",
                style="12.TButton",
                command=lambda_func(load_feed, i, True),
            ).place(relx=0.01, rely=0.03, anchor="w")

        self.my_pfp = NewsAggregator.get_pfp(self.name, (40, 40))
        self.acc_button = tk.Button(
            self,
            image=self.my_pfp,
            text=f" {self.name} ▾",
            highlightthickness=0,
            cursor="hand2",
            border=0,
            font=("arial black", 14),
            compound="left",
            command=self.account_tab,
        )
        self.acc_button.place(relx=0.99, rely=0.09, anchor="e")
        self.acc_frame = ttk.Frame()
        self.acc_frame.destroy()

    def start_news(self):
        root.withdraw()
        self.logo = ImageTk.PhotoImage(
            Image.open(os.path.join(ASSETS, "logo.png")).resize(
                (self.screen_width // 4, self.screen_width // 4),
                Image.Resampling.LANCZOS,
            )
        )
        self.logo_label = tk.Label(self, image=self.logo, bg=self.cget("bg"))
        self.logo_label.place(
            relx=0.5, rely=0.3, anchor="center", relheight=0.8, relwidth=1
        )
        Login(
            self, self.initialize, remember_login=os.path.exists(REMEMBER_ME_FILE)
        ).place(relx=0.5, rely=0.6, relheight=0.4, relwidth=1, anchor="n")

    # region Account Tab

    def account_tab(self):
        if self.acc_frame.winfo_exists():
            self.unbind("<Button-1>")
            self.acc_frame.destroy()
        else:
            try:
                self.change_frame.destroy()
            except:
                pass

            def clicked(e):
                if self.acc_frame.winfo_containing(e.x_root, e.y_root) not in [
                    self.log_out_button,
                    self.change_pass_button,
                    self.change_pfp_button,
                    self.acc_frame,
                    self.acc_button,
                    self.theme_button,
                ]:
                    self.acc_frame.destroy()

            self.bind("<Button-1>", clicked, add="+")
            self.acc_frame = ttk.Frame(self, style="Card.TFrame", padding=4)
            self.acc_frame.place(relx=0.99, rely=0.12, anchor="ne")

            self.log_out_button = ttk.Button(
                self.acc_frame, text="Log Out", style="12.TButton", command=self.log_out
            )
            self.log_out_button.grid(
                row=0,
                column=0,
                columnspan=2,
                pady=2,
                sticky="nsew",
            )

            self.change_pass_button = ttk.Button(
                self.acc_frame,
                text="Change Password",
                style="12.TButton",
                command=self.change_password,
            )
            self.change_pass_button.grid(
                row=1, column=0, columnspan=2, sticky="nsew", pady=2
            )

            self.change_pfp_button = ttk.Button(
                self.acc_frame,
                text="Change Picture",
                style="12.TButton",
                command=self.change_pfp,
            )
            self.change_pfp_button.grid(
                row=2, column=0, columnspan=2, sticky="nsew", pady=2
            )

            theme_var = tk.StringVar(value=theme.curr_theme())

            tk.Label(self.acc_frame, text="Dark Mode", font=("rockwell", 14)).grid(
                row=4, column=0, sticky="e", pady=2, padx=6
            )
            self.theme_button = ttk.Checkbutton(
                self.acc_frame,
                style="Switch.TCheckbutton",
                variable=theme_var,
                onvalue="dark",
                offvalue="light",
                command=theme.toggle_theme,
            )
            self.theme_button.grid(row=4, column=1, sticky="e", pady=2)

    def change_password(self):
        self.acc_frame.destroy()
        self.change_frame = ttk.Frame(self, style="Card.TFrame", padding=4)
        self.change_frame.place(
            relx=0.99, rely=0.1, relheight=0.3, relwidth=0.25, anchor="ne"
        )
        self.pwd = tk.StringVar()
        self.confpwd = tk.StringVar()
        tk.Button(
            self.change_frame,
            text="← Cancel",
            highlightthickness=0,
            cursor="hand2",
            border=0,
            command=self.change_frame.destroy,
        ).place(relx=0.01, rely=0.01, anchor="nw")

        self.change_frame.bind("<Escape>", lambda a: self.change_frame.destroy())
        tk.Label(self.change_frame, text="New Password: ").place(
            relx=0.49, rely=0.25, anchor="e"
        )
        self.pwdentry = ttk.Entry(self.change_frame, textvariable=self.pwd, show="*")
        self.pass_hidden = True
        self.pwdentry.place(relx=0.5, rely=0.25, relwidth=0.275, anchor="w")
        self.pwdentry.focus_set()
        tk.Label(self.change_frame, text="Confirm Password: ").place(
            relx=0.49, rely=0.4, anchor="e"
        )
        self.confpwdentry = ttk.Entry(
            self.change_frame, textvariable=self.confpwd, show="*"
        )
        self.conf_pass_hidden = True
        self.confpwdentry.place(relx=0.5, rely=0.4, relwidth=0.275, anchor="w")

        self.pwdentry.bind("<Return>", lambda a: self.confpwdentry.focus_set())
        self.confpwdentry.bind("<Return>", lambda a: self.confpwdentry.focus_set())

        def chng_pass():
            pwd = self.pwd.get().strip()
            confpwd = self.confpwd.get().strip()

            self.confpwdentry.delete(0, tk.END)
            prompts = {
                "length": "Atleast 4 Characters in Total",
                "space": "No Spaces",
            }
            missing = Register.check_pass(pwd)

            msg = ""
            if not pwd:
                self.pwdentry.delete(0, tk.END)
                msg = "Enter Password"
                prompt(msg)
            elif pwd and not confpwd:
                msg = "Confirm Password"
                prompt(msg)
            elif missing:
                self.pwdentry.delete(0, tk.END)
                msg = "Password should have:"
                for i in missing:
                    msg += "\n" + prompts[i]
                prompt(msg)
            elif confpwd != pwd:
                msg = "Password does not match"
                prompt(msg)
            else:
                if db.change_password(self.name, pwd) == "Success":
                    msg = "Confirming and Logging you out..."
                    prompt(msg)
                    try:
                        os.remove(REMEMBER_ME_FILE)
                    except FileNotFoundError:
                        pass
                    self.after(2000, self.log_out)
                else:
                    self.pwdentry.delete(0, tk.END)
                    msg = "ERROR"
                    prompt(msg)

        def prompt(msg):
            try:
                destroyprompt()
                self.notifc += 1
                color = "red"
                if msg.startswith("Confirming"):
                    color = "green"
                self.notif = (
                    tk.Label(self.change_frame, text=msg, fg=color),
                    self.notifc,
                )
                self.notif[0].place(
                    relx=0.5, rely=0.55 if "\n" not in msg else 0.7, anchor="center"
                )
                self.after(5000, destroyprompt)

            except:
                pass

        def destroyprompt():
            if self.notif and self.notif[1] == self.notifc:
                self.notif[0].destroy()
                self.notif = None

        self.change_button = ttk.Button(
            self.change_frame,
            text="CHANGE",
            style="12.TButton",
            command=chng_pass,
        )
        self.change_button.place(relx=0.5, rely=0.7, anchor="center")

        self.show_password = ImageTk.PhotoImage(
            Image.open(os.path.join(ASSETS, "show_password.png")).resize(
                (20, 15), Image.Resampling.LANCZOS
            )
        )

        self.hide_password = ImageTk.PhotoImage(
            Image.open(os.path.join(ASSETS, "hide_password.png")).resize(
                (20, 15), Image.Resampling.LANCZOS
            )
        )

        self.show_hide_pass = tk.Button(
            self.change_frame,
            image=self.show_password,
            highlightthickness=0,
            cursor="hand2",
            border=0,
            command=lambda: toggle_hide_password(False),
        )
        self.show_hide_conf_pass = tk.Button(
            self.change_frame,
            image=self.show_password,
            highlightthickness=0,
            cursor="hand2",
            border=0,
            command=lambda: toggle_hide_password(True),
        )
        self.show_hide_pass.place(relx=0.8, rely=0.25, anchor="w")
        self.show_hide_conf_pass.place(relx=0.8, rely=0.4, anchor="w")

        def toggle_hide_password(conf):
            if conf:
                if self.conf_pass_hidden:
                    self.confpwdentry.config(show="")
                    self.show_hide_conf_pass.config(image=self.hide_password)
                else:
                    self.confpwdentry.config(show="*")
                    self.show_hide_conf_pass.config(image=self.show_password)
                self.conf_pass_hidden = not self.conf_pass_hidden
            else:
                if self.pass_hidden:
                    self.pwdentry.config(show="")
                    self.show_hide_pass.config(image=self.hide_password)
                else:
                    self.pwdentry.config(show="*")
                    self.show_hide_pass.config(image=self.show_password)
                self.pass_hidden = not self.pass_hidden

        self.confpwdentry.bind("<Return>", lambda a: chng_pass())

        self.notif = None
        self.notifc = 0

    def change_pfp(self):
        self.acc_frame.destroy()
        self.pfp_path = os.path.join(ASSETS, ".cache", self.name + ".png")
        self.change_frame = ttk.Frame(self, style="Card.TFrame", padding=4)
        self.change_frame.place(
            relx=0.99, rely=0.1, relheight=0.3, relwidth=0.25, anchor="ne"
        )
        tk.Button(
            self.change_frame,
            text="← Cancel",
            highlightthickness=0,
            cursor="hand2",
            border=0,
            command=self.change_frame.destroy,
        ).place(relx=0.01, rely=0.01, anchor="nw")
        self.select_pfp()

    def select_pfp(self):
        self.pfp_image = ImageTk.PhotoImage(
            NewsAggregator.circle_PIL_Image(Image.open(self.pfp_path), (100, 100))
        )
        tk.Label(self.change_frame, image=self.pfp_image).place(
            relx=0.5, rely=0.3, anchor="center"
        )
        self.remove_image = ImageTk.PhotoImage(
            Image.open(os.path.join(ASSETS, "remove.png")).resize(
                (32, 32),
                Image.Resampling.LANCZOS,
            )
        )

        def choose():
            n = fd.askopenfilename(
                title="Choose a Profile Picture",
                initialdir=r"%userprofile%",
                filetypes=(("Image Files", "*.jpg *.png *.webp *.gif *.jpeg"),),
            )
            self.pfp_path = n if n else self.pfp_path
            self.select_pfp()

        def set_default():
            self.pfp_path = os.path.join(ASSETS, "default_pfp.png")
            self.select_pfp()

        self.remove_button = tk.Button(
            self.change_frame,
            image=self.remove_image,
            cursor="hand2",
            border=0,
            highlightthickness=0,
            command=set_default,
        )
        if self.pfp_path == os.path.join(ASSETS, "default_pfp.png"):
            self.remove_button.destroy()
        else:
            self.remove_button.place(relx=0.8, rely=0.45, anchor="center")

        self.choose_button = ttk.Button(
            self.change_frame,
            text="Upload Picture",
            style="12.TButton",
            command=choose,
        )
        self.choose_button.place(relx=0.5, rely=0.625, anchor="center")

        def confirm_change():
            db.change_pfp(self.name, NewsAggregator.pfp_send(self.pfp_path))
            self.change_frame.destroy()
            self.my_pfp = NewsAggregator.get_pfp(self.name, force=True)
            self.acc_button.configure(image=self.my_pfp)

        self.confirm_button = ttk.Button(
            self.change_frame,
            text="Confirm",
            style="12.TButton",
            command=confirm_change,
        )

        if self.pfp_path == os.path.join(ASSETS, ".cache", self.name + ".png"):
            self.confirm_button.destroy()
        else:
            self.confirm_button.place(relx=0.5, rely=0.9, anchor="center")

    def log_out(self):
        try:
            os.remove(REMEMBER_ME_FILE)
        except FileNotFoundError:
            pass
        self.acc_button.destroy()
        self.acc_frame.destroy()
        try:
            self.change_frame.destroy()
        except:
            pass

        self.queue = []
        for i in self.feed_frames:
            self.feed_frames[i].destroy()

        self.feed_frames = {i: None for i in self.tabs}
        self.feed_threads = {i: None for i in self.tabs}

        self.screen_width = int(0.9 * self.winfo_screenwidth())
        self.screen_height = int(self.screen_width / 1.9)
        self.x_coord = self.winfo_screenwidth() // 2 - self.screen_width // 2
        self.y_coord = (self.winfo_screenheight() - 70) // 2 - self.screen_height // 2
        self.minsize(self.screen_width // 2, self.screen_height)
        self.geometry(
            f"{self.screen_width//2}x{self.screen_height}+{self.x_coord+self.screen_width//4}+{self.y_coord}"
        )
        self.protocol("WM_DELETE_WINDOW", self.exit)

        self.logo_label = tk.Label(self, image=self.logo, bg=self.cget("bg"))
        self.logo_label.place(
            relx=0.5, rely=0.3, anchor="center", relheight=0.8, relwidth=1
        )
        Login(
            self, self.initialize, remember_login=os.path.exists(REMEMBER_ME_FILE)
        ).place(relx=0.5, rely=0.6, relheight=0.4, relwidth=1, anchor="n")

    # endregion

    # region Profile Picture

    @staticmethod
    def pfp_send(path):
        im = Image.open(path)
        im = im.crop(
            (
                (im.size[0] - min(im.size)) // 2,
                (im.size[1] - min(im.size)) // 2,
                (im.size[0] + min(im.size)) // 2,
                (im.size[1] + min(im.size)) // 2,
            )
        ).resize((256, 256), Image.Resampling.LANCZOS)
        im.save(os.path.join(ASSETS, "temp.png"), optimize=True)
        with open(os.path.join(ASSETS, "temp.png"), "rb") as f:
            a = base64.b64encode(f.read()).decode("latin1")
        os.remove(os.path.join(ASSETS, "temp.png"))
        return a

    @staticmethod
    def pfp_make(img):
        try:
            b = base64.b64decode(img.encode("latin1"))
            c = Image.open(BytesIO(b))
            return c
        except Exception as e:
            print(f"Couldn't Access Profile Picture\n{e}")
            return Image.open(os.path.join(ASSETS, "default_pfp.png"))

    @staticmethod
    def get_pfp(name, resize=(32, 32), force=False):
        if not os.path.isfile(os.path.join(ASSETS, ".cache", name + ".png")) or force:
            NewsAggregator.circle_PIL_Image(
                NewsAggregator.pfp_make(db.fetch_pfp(name))
            ).save(os.path.join(ASSETS, ".cache", name + ".png"))
        return ImageTk.PhotoImage(
            Image.open(os.path.join(ASSETS, ".cache", name + ".png")).resize(
                resize, Image.Resampling.LANCZOS
            )
        )

    @staticmethod
    def circle_PIL_Image(pil_img: Image.Image, resize=(256, 256)):
        im = pil_img.convert("RGBA")
        im = im.crop(
            (
                (im.size[0] - min(im.size)) // 2,
                (im.size[1] - min(im.size)) // 2,
                (im.size[0] + min(im.size)) // 2,
                (im.size[1] + min(im.size)) // 2,
            )
        ).resize(resize, Image.Resampling.LANCZOS)
        bigsize = (im.size[0] * 10, im.size[1] * 10)

        mask = Image.new("L", bigsize, 0)
        ImageDraw.Draw(mask).ellipse((0, 0) + bigsize, fill=255)
        mask = mask.resize(im.size, Image.Resampling.LANCZOS)
        mask = ImageChops.darker(
            mask,
            im.split()[-1],
        )
        im.putalpha(mask)

        a = im.resize(bigsize)
        ImageDraw.Draw(a).ellipse((0, 0) + (bigsize), outline=(0, 0, 0), width=15)
        a = a.resize(im.size, Image.Resampling.LANCZOS)
        im.paste(a)

        return im

    # endregion

    def search_bar(self):  # TODO: Search Bar
        self.search_icon = ImageTk.PhotoImage(
            Image.open(os.path.join(ASSETS, "search.png")).resize(
                (20, 20), Image.Resampling.LANCZOS
            )
        )
        self.search_var = tk.StringVar(value="Search")
        self.search_entry = ttk.Entry(
            self, style="Search.TEntry", textvariable=self.search_var
        )
        self.search_entry.configure(xscrollcommand=self.search_entry.xview_moveto(1))
        self.search_entry.place(relx=0.01, rely=0.05, relwidth=0.4, relheight=0.05)
        self.search_button = tk.Button(
            self,
            border=0,
            highlightthickness=0,
            cursor="hand2",
            compound="left",
            image=self.search_icon,
            command=lambda: print(f"Searching for {self.search_var.get()}"),
        )
        self.search_button.place(relx=0.415, rely=0.05, relheight=0.05, anchor="nw")

        def clicked(e):
            if self.search_entry.winfo_containing(e.x_root, e.y_root) not in [
                self.search_entry,
            ]:
                self.focus_set()

        self.bind("<Button-1>", clicked, add="+")

        self.search_entry.bind("<Return>", lambda a: self.search_button.invoke())
        self.search_entry.bind("<Return>", lambda a: self.focus_set(), add="+")
        self.search_entry.bind(
            "<FocusIn>", lambda a: self.search_entry.select_range(0, tk.END)
        )
        self.search_entry.bind(
            "<FocusOut>", lambda a: self.search_entry.select_range(0, 0)
        )

    def show_feed(self, topic="favorites"):
        self.articles = Feed(topic, self.name).articles
        self.feed_frames[topic].destroy()
        self.feed_frames[topic] = ttk.Frame(
            self.tabs[topic], style="Card.TFrame", padding=4
        )
        tk.Label(
            self.feed_frames[topic],
            text="Wow, Such Empty...",
            font=("rockwell", 16),
        ).place(relx=0.5, rely=0.5, anchor="center")
        self.feed_frames[topic].place(
            relx=0.01, rely=0.07, relheight=0.9, relwidth=0.98
        )

        self.feed_frames[topic] = FeedFrame(self.tabs[topic], self.articles, self.name)
        self.feed_frames[topic].place(
            relx=0.01, rely=0.07, relheight=0.9, relwidth=0.98
        )

        self.loading_labels[topic].destroy()

        # rebind scroll wheel to active tab
        try:
            current_frame = self.feed_frames[
                self.notebook.tab(self.notebook.select(), "text").lower()
            ]
            current_frame.canvas.bind_all("<MouseWheel>", current_frame._on_mousewheel)
        except AttributeError:
            pass

    def exit(self):
        self.destroy()
        root.destroy()


class Article:
    def __init__(self, article_dict: dict):
        self.link = article_dict["link"]
        self.title = article_dict["title"]
        self.image = article_dict["image"]
        try:
            self.tk_image = ImageTk.PhotoImage(
                Image.open(
                    BytesIO(
                        requests.get(
                            self.image,
                            headers={
                                "Referer": "https://www.google.com/",
                                "User-Agent": "Mozilla/5.0",
                            },
                        ).content
                    )
                ).resize((250, 175), Image.Resampling.LANCZOS)
            )
        except:
            self.tk_image = ImageTk.PhotoImage(
                Image.open(os.path.join(ASSETS, "logo.png")).resize(
                    (250, 175), Image.Resampling.LANCZOS
                )
            )
            self.image = None


class Feed:
    def __init__(self, topic, username):
        self.articles = []
        if topic == "favorites":
            self.topics = db.get_fav_topics(username)
            if not self.topics:
                self.topics = RSS_FEEDS.keys()
        elif topic == "saved":
            articles = db.get_saved_articles(username)
            for i in articles:
                self.articles.append(Article(i))
            self.topics = []
        else:
            self.topics = [topic]

        self.articles_per_topic = (15 // len(self.topics)) if len(self.topics) else 15
        for i in self.topics:
            self.add_articles(i, self.articles_per_topic)
        if len(self.articles) > 15:
            self.articles = random.sample(self.articles, 15)
        else:
            random.shuffle(self.articles)

    def add_articles(self, topic, articles_per_topic):
        for i in RSS_FEEDS[topic]:
            articles_per_feed = articles_per_topic // len(RSS_FEEDS[topic]) + 1
            feed = get_articles_from_rss(i, articles_per_feed)
            for j in feed:
                self.articles.append(Article(j))


class ArticleFrame(ttk.Frame):
    def __init__(self, master, article: Article, username):
        super().__init__(master, style="Card.TFrame", padding=4)
        self.master = master
        self.username = username
        self.article = article

        self.title = self.remove_html_tags(self.article.title)
        self.title = (self.title[:69] + "...") if len(self.title) > 69 else self.title
        self.title = self.title.replace("&#8217;", "'")

        self.image = self.article.tk_image
        self.label = tk.Label(
            self,
            text=self.title,
            image=self.image,
            compound="top",
            font=("rockwell", 13),
            wraplength=250,
            justify="center",
            anchor="n",
            cursor="hand2",
        )
        self.label.place(relx=0.5, rely=0.5, relheight=1, relwidth=1, anchor="center")
        self.label.bind("<Button-1>", lambda a: webbrowser.open(self.article.link))
        self.save_unsave()

    def remove_html_tags(self, text):
        """Remove html tags from a string"""

        clean = re.compile("<.*?>")
        return re.sub(clean, "", text)

    def save_unsave(self):
        self.save_image = ImageTk.PhotoImage(
            Image.open(os.path.join(ASSETS, "save.png")).resize(
                (20, 20), Image.Resampling.LANCZOS
            )
        )
        self.unsave_image = ImageTk.PhotoImage(
            Image.open(os.path.join(ASSETS, "unsave.png")).resize(
                (20, 20), Image.Resampling.LANCZOS
            )
        )

        self.save_button = tk.Button(
            self,
            image=self.save_image,
            highlightthickness=0,
            cursor="hand2",
            border=0,
            command=self.save_article,
        )

        self.unsave_button = tk.Button(
            self,
            image=self.unsave_image,
            highlightthickness=0,
            cursor="hand2",
            border=0,
            command=self.unsave_article,
        )

        if db.is_saved(self.username, self.article.link):
            self.save_button.place_forget()
            self.unsave_button.place(relx=0.975, rely=0.025, anchor="ne")
        else:
            self.unsave_button.place_forget()
            self.save_button.place(relx=0.975, rely=0.025, anchor="ne")

    def save_article(self):
        db.save_article(
            self.username, self.article.title, self.article.link, self.article.image
        )
        self.save_button.place_forget()
        self.unsave_button.place(relx=0.975, rely=0.025, anchor="ne")

    def unsave_article(self):
        db.unsave_article(self.username, self.article.link)
        self.unsave_button.place_forget()
        self.save_button.place(relx=0.975, rely=0.025, anchor="ne")

        # Remove from Saved Tab
        notebook = self.master.master.master.master.master
        if notebook.tab(notebook.select(), "text") == "Saved":
            self.destroy()


class FeedFrame(ScrollableFrame):
    def __init__(self, master, articles: list[Article], username):
        scrollheight = len(articles) // 4 * 255 + (255 if len(articles) % 4 else 0)
        super().__init__(master, height=scrollheight)

        self.articles = articles
        self.article_frames = [
            ArticleFrame(self.scrollable_frame, i, username) for i in self.articles
        ]

        for i, j in enumerate(self.article_frames):
            j.place(
                height=250,
                relwidth=0.2475,
                relx=0.0025 + (i % 4) * 0.25,
                y=(i // 4) * 255,
                anchor="nw",
            )


class Login(tk.Frame):
    def __init__(self, master, complete, remember_login=False):
        super().__init__(master)
        self.notif = None
        self.notifc = 0
        self.complete = complete

        if remember_login:
            flag = True
            log_win = tk.Toplevel(self)
            log_win.geometry(
                f"{300}x{40}+{self.winfo_screenwidth()//2-150}+{self.winfo_screenheight()//2-20}"
            )
            master.withdraw()
            lbl = tk.Label(
                log_win, text="Logging in...", font=("rockwell", 13), fg="green"
            )
            lbl.pack()
            with open(REMEMBER_ME_FILE, "rb") as f:
                try:
                    uname, pwd = pickle.load(f)
                except:
                    uname = pwd = ""
            self.check_login = db.do_login(uname, pwd, remember_login=True)
            if self.check_login[0] == "Success":
                lbl.configure(text="Loading...")
                self.loading_thread = threading.Thread(
                    target=lambda: self.complete(uname), daemon=True
                )
                self.loading_thread.start()
            else:
                lbl.configure(text="Invalid Credentials! File Corrupted!", fg="red")
                flag = False
                try:
                    os.remove(REMEMBER_ME_FILE)
                except FileNotFoundError:
                    pass

            def thing():
                log_win.destroy()
                master.deiconify()
                if flag:
                    self.destroy()

            self.after(1500, thing)

        tk.Label(
            self,
            text="Welcome to the News Aggregator!\nPlease Enter your Credentials to Login:",
        ).place(relx=0.5, rely=0.1, anchor="center")
        self.uname = tk.StringVar()
        self.pwd = tk.StringVar()

        tk.Label(self, text="Username: ").place(relx=0.44, rely=0.3, anchor="e")

        def no_special(e):
            if not any(i in ["'", '"', ";", " ", "\\"] for i in e) and len(e) <= 32:
                return True
            else:
                return False

        self.uentry = ttk.Entry(
            self,
            textvariable=self.uname,
            validate="key",
            validatecommand=(
                self.register(no_special),
                "%P",
            ),
        )
        self.uentry.place(relx=0.45, rely=0.3, relwidth=0.2, anchor="w")
        self.uentry.focus_set()
        tk.Label(self, text="Password: ").place(relx=0.44, rely=0.4, anchor="e")
        self.pwdentry = ttk.Entry(self, textvariable=self.pwd, show="*")
        self.pass_hidden = True
        self.pwdentry.place(relx=0.45, rely=0.4, relwidth=0.2, anchor="w")
        self.uentry.bind("<Return>", lambda a: self.pwdentry.focus_set())

        self.login_button = ttk.Button(
            self,
            text="LOGIN",
            style="15.TButton",
            command=self.login,
        )
        self.login_button.place(relx=0.5, rely=0.8, anchor="center")

        def forget_reg():
            self.reg.destroy()

        def register():
            self.reg = Register(self, forget_reg)
            self.reg.place(relx=0.5, rely=0.5, relheight=1, relwidth=1, anchor="center")

        def toggle_hide_password():
            if self.pass_hidden:
                self.pwdentry.config(show="")
                self.show_hide_pass.config(image=self.hide_password)
            else:
                self.pwdentry.config(show="*")
                self.show_hide_pass.config(image=self.show_password)

            self.pass_hidden = not self.pass_hidden

        tk.Button(
            self,
            text="New User? Click Here To Sign Up",
            fg="#15a8cd",
            highlightthickness=0,
            cursor="hand2",
            border=0,
            command=register,
        ).place(relx=0.5, rely=0.6, anchor="center")

        self.show_password = ImageTk.PhotoImage(
            Image.open(os.path.join(ASSETS, "show_password.png")).resize(
                (20, 15), Image.Resampling.LANCZOS
            )
        )

        self.hide_password = ImageTk.PhotoImage(
            Image.open(os.path.join(ASSETS, "hide_password.png")).resize(
                (20, 15), Image.Resampling.LANCZOS
            )
        )

        self.show_hide_pass = tk.Button(
            self,
            image=self.show_password,
            highlightthickness=0,
            cursor="hand2",
            border=0,
            command=toggle_hide_password,
        )
        self.show_hide_pass.place(relx=0.66, rely=0.4, anchor="w")
        self.remember_me = tk.BooleanVar()
        remember_me_button = ttk.Checkbutton(
            self,
            text="Remember Me",
            variable=self.remember_me,
            offvalue=False,
            onvalue=True,
        )
        remember_me_button.place(relx=0.445, rely=0.5, anchor="w")

        self.pwdentry.bind("<Return>", lambda a: self.login())

    def login(self):
        uname = self.uentry.get().strip()
        pwd = self.pwd.get().strip()
        self.pwdentry.delete(0, tk.END)
        msg = ""
        if uname and not pwd:
            msg = "Enter Password"
            self.prompt(msg)
        elif not uname:
            msg = "Enter your Credentials"
            pwd = ""
            self.prompt(msg)
        else:
            try:
                self.check_login = db.do_login(
                    uname.strip(), pwd.strip(), remember_me=self.remember_me.get()
                )
            except Exception as e:
                print(e)
                self.destroy()
                msgb.showerror(
                    "Connection Error",
                    "Unable to connect to the Server at the moment, please try again later!\nThings you can do:\n1. Check your network connection\n2. Restart your system\n3. If this issue persists, wait for sometime. The server might be down, We are working on it!",
                    master=root,
                )
                quit()
            if self.check_login[0] == "Success":
                msg = "Logging in..."
                self.pwdentry.config(state="disabled")
                self.uentry.config(state="disabled")
                self.login_button.config(state="disabled")
                self.pwdentry.unbind("<Return>")
                self.uentry.unbind("<Return>")
                self.prompt(msg)
                if isinstance(self.check_login[1], str):
                    self.store_password(uname.strip(), self.check_login[1])
                self.after(1500, lambda: self.complete(uname))
            else:
                msg = "Incorrect Username or Password"
                self.prompt(msg)

    def store_password(self, uname, pwd):
        with open(
            REMEMBER_ME_FILE,
            "wb",
        ) as f:
            pickle.dump((uname, pwd), f)

    def prompt(self, msg):
        try:
            self.destroyprompt()
            self.notifc += 1
            color = "red"
            if msg == "Logging in...":
                color = "green"
            self.notif = (
                tk.Label(self, text=msg, fg=color),
                self.notifc,
            )
            self.notif[0].place(relx=0.5, rely=0.67, anchor="center")
            self.after(3000, self.destroyprompt)
        except:
            pass

    def destroyprompt(self):
        if self.notif and self.notif[1] == self.notifc:
            self.notif[0].destroy()
            self.notif = None


class Register(tk.Frame):
    def __init__(self, master, complete):
        super().__init__(master)
        tk.Label(
            self,
            text="Welcome to the News Aggregator!\nPlease Enter your Details to Create an Account:",
            font=("rockwell", 10),
        ).place(relx=0.5, rely=0.1, anchor="center")
        self.uname = tk.StringVar()
        self.pwd = tk.StringVar()
        self.confpwd = tk.StringVar()
        tk.Button(
            self,
            text="← Sign In",
            highlightthickness=0,
            cursor="hand2",
            border=0,
            command=self.destroy,
        ).place(relx=0.01, rely=0.01, anchor="nw")
        self.bind("<Escape>", lambda a: self.destroy())
        tk.Label(self, text="Create Username: ").place(relx=0.24, rely=0.3, anchor="e")

        def no_special(e):
            if not any(i in ["'", '"', ";", " ", "\\"] for i in e) and len(e) <= 32:
                return True
            else:
                return False

        self.uentry = ttk.Entry(
            self,
            textvariable=self.uname,
            validate="key",
            validatecommand=(
                self.register(no_special),
                "%P",
            ),
        )
        self.uentry.place(relx=0.25, rely=0.3, relwidth=0.2, anchor="w")
        self.uentry.focus_set()
        tk.Label(self, text="Create Password: ").place(relx=0.24, rely=0.4, anchor="e")
        self.pwdentry = ttk.Entry(self, textvariable=self.pwd, show="*")
        self.pass_hidden = True
        self.pwdentry.place(relx=0.25, rely=0.4, relwidth=0.2, anchor="w")
        tk.Label(self, text="Confirm Password: ").place(relx=0.24, rely=0.5, anchor="e")
        self.confpwdentry = ttk.Entry(self, textvariable=self.confpwd, show="*")
        self.conf_pass_hidden = True
        self.confpwdentry.place(relx=0.25, rely=0.5, relwidth=0.2, anchor="w")

        self.uentry.bind("<Return>", lambda a: self.pwdentry.focus_set())
        self.pwdentry.bind("<Return>", lambda a: self.confpwdentry.focus_set())

        self.reg_button = ttk.Button(
            self,
            text="REGISTER",
            style="15.TButton",
            command=self.reg_user,
        )
        self.reg_button.place(relx=0.5, rely=0.8, anchor="center")

        self.show_password = ImageTk.PhotoImage(
            Image.open(os.path.join(ASSETS, "show_password.png")).resize(
                (20, 15), Image.Resampling.LANCZOS
            )
        )

        self.hide_password = ImageTk.PhotoImage(
            Image.open(os.path.join(ASSETS, "hide_password.png")).resize(
                (20, 15), Image.Resampling.LANCZOS
            )
        )

        self.show_hide_pass = tk.Button(
            self,
            image=self.show_password,
            highlightthickness=0,
            cursor="hand2",
            border=0,
            command=lambda: toggle_hide_password(False),
        )
        self.show_hide_conf_pass = tk.Button(
            self,
            image=self.show_password,
            highlightthickness=0,
            cursor="hand2",
            border=0,
            command=lambda: toggle_hide_password(True),
        )
        self.show_hide_pass.place(relx=0.46, rely=0.4, anchor="w")
        self.show_hide_conf_pass.place(relx=0.46, rely=0.5, anchor="w")

        for i in self.winfo_children():
            i.bind("<Escape>", lambda a: self.destroy())

        def toggle_hide_password(conf):
            if conf:
                if self.conf_pass_hidden:
                    self.confpwdentry.config(show="")
                    self.show_hide_conf_pass.config(image=self.hide_password)
                else:
                    self.confpwdentry.config(show="*")
                    self.show_hide_conf_pass.config(image=self.show_password)
                self.conf_pass_hidden = not self.conf_pass_hidden
            else:
                if self.pass_hidden:
                    self.pwdentry.config(show="")
                    self.show_hide_pass.config(image=self.hide_password)
                else:
                    self.pwdentry.config(show="*")
                    self.show_hide_pass.config(image=self.show_password)
                self.pass_hidden = not self.pass_hidden

        self.confpwdentry.bind("<Return>", lambda a: self.reg_user())

        self.notif = None
        self.notifc = 0
        self.complete = complete
        self.pfp_path = os.path.join(ASSETS, "default_pfp.png")
        self.pfp_select()

    def pfp_select(self):
        self.pfp_image = ImageTk.PhotoImage(
            NewsAggregator.circle_PIL_Image(Image.open(self.pfp_path), (100, 100))
        )
        tk.Label(self, image=self.pfp_image).place(relx=0.8, rely=0.26, anchor="center")
        self.remove_image = ImageTk.PhotoImage(
            Image.open(os.path.join(ASSETS, "remove.png")).resize(
                (32, 32),
                Image.Resampling.LANCZOS,
            )
        )

        def choose():
            n = fd.askopenfilename(
                title="Choose a Profile Picture",
                initialdir=r"%userprofile%",
                filetypes=(("Image Files", "*.jpg *.png *.webp *.gif *.jpeg"),),
            )
            self.pfp_path = n if n else self.pfp_path
            self.pfp_select()

        def set_default():
            self.pfp_path = os.path.join(ASSETS, "default_pfp.png")
            self.pfp_select()

        self.remove_button = tk.Button(
            self,
            image=self.remove_image,
            cursor="hand2",
            border=0,
            highlightthickness=0,
            command=set_default,
        )
        if self.pfp_path == os.path.join(ASSETS, "default_pfp.png"):
            self.remove_button.destroy()
        else:
            self.remove_button.place(relx=0.9, rely=0.35, anchor="center")

        self.choose_button = ttk.Button(
            self,
            text="Upload Picture",
            style="15.TButton",
            command=choose,
        )
        self.choose_button.place(relx=0.8, rely=0.51, anchor="center")

    @staticmethod
    def check_pass(pwd):
        check = {
            "length": False,
            "space": True,
        }
        if len(pwd) >= 4:
            check["length"] = True
        if any(i.isspace() for i in pwd):
            check["space"] = False

        return [i for i, j in check.items() if not j]

    def reg_user(self):
        uname = self.uentry.get().strip()
        pwd = self.pwd.get().strip()
        confpwd = self.confpwd.get().strip()

        self.confpwdentry.delete(0, tk.END)
        prompts = {
            "length": "Atleast 4 Characters",
            "space": "No Spaces",
        }
        missing = Register.check_pass(pwd)

        msg = ""
        if uname in ["none", "Unknown"]:
            self.uentry.delete(0, tk.END)
            msg = "Illegal Username!"
            self.prompt(msg)
        elif uname and not pwd:
            self.pwdentry.delete(0, tk.END)
            msg = "Enter Password"
            self.prompt(msg)
        elif uname and pwd and not confpwd:
            msg = "Confirm Password"
            self.prompt(msg)
        elif not uname:
            msg = "Enter your Credentials"
            pwd = ""
            confpwd = ""
            self.pwdentry.delete(0, tk.END)
            self.prompt(msg)
        elif missing:
            self.pwdentry.delete(0, tk.END)
            msg = "Password should have:"
            for i in missing:
                msg += "\n" + prompts[i]
            self.prompt(msg)
        elif confpwd != pwd:
            msg = "Password does not match"
            self.prompt(msg)
        else:
            try:
                if db.register(
                    uname.strip(),
                    pwd.strip(),
                    NewsAggregator.pfp_send(self.pfp_path),
                ):
                    msg = "Registering..."
                    self.prompt(msg)
                    self.after(1000, self.complete)
                else:
                    self.uentry.delete(0, tk.END)
                    self.pwdentry.delete(0, tk.END)
                    msg = "User Already Registered"
                    self.prompt(msg)
            except Exception as e:
                print(e)
                self.destroy()
                msgb.showerror(
                    "Try Again Later",
                    "Unable to connect to the Server at the moment, please try again later!\nThings you can do:\n1. Check your network connection\n2. Restart your system\n3. If this issue persists, wait for sometime. The server might be down, We are working on it!",
                    master=root,
                )
                quit()

    def prompt(self, msg):
        try:
            self.destroyprompt()
            self.notifc += 1
            color = "red"
            if msg == "Registering...":
                color = "green"
            self.notif = (
                tk.Label(self, text=msg, fg=color),
                self.notifc,
            )
            self.notif[0].place(relx=0.25, rely=0.7, anchor="center")
            self.after(5000, self.destroyprompt)
        except:
            pass

    def destroyprompt(self):
        if self.notif and self.notif[1] == self.notifc:
            self.notif[0].destroy()
            self.notif = None


if __name__ == "__main__":
    root = tk.Tk()
    root.title("News Aggregator")

    if not os.path.exists(os.path.join(os.curdir, "settings")):
        os.mkdir(os.path.join(os.curdir, "settings"))
    if not os.path.exists(os.path.join(os.curdir, "assets", ".cache")):
        os.mkdir(os.path.join(os.curdir, "assets", ".cache"))

    if not os.path.exists(THEME_FILE):
        with open(THEME_FILE, "wb") as f:
            pickle.dump("dark", f)
            CURR_THEME = "dark"
    else:
        with open(THEME_FILE, "rb") as f:
            CURR_THEME = pickle.load(f)

    theme = Theme(root, CURR_THEME)
    app = NewsAggregator()
    app.start_news()
    root.mainloop()
