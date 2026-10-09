import os
import threading
import tkinter as tk
from tkinter import filedialog, ttk

from locker import EXT, MAGIC, decrypt_file, encrypt_file

# FXP tokens
FACE = "#ece9d8"
WINDOW = "#ffffff"
INK = "#000000"
INK_MUTED = "#7f7c70"
INK_DISABLED = "#a19f94"
SELECTION = "#316ac5"
PANE = "#6f8cde"
PANEL = "#d6dff7"
PANEL_TITLE = "#215dc6"
PANEL_HEAD_END = "#c6d3f7"
FIELD_LINE = "#7f9db9"
BUTTON_LINE = "#003c74"
BUTTON_FILL_END = "#e6e3d3"
BUTTON_PRESSED_TOP = "#e2e1d9"
BUTTON_PRESSED_END = "#f7f6f2"
BUTTON_DISABLED = "#f5f4ea"
BUTTON_DISABLED_LINE = "#c9c7ba"
HOVER_GLOW = "#fac55e"
FOCUS_GLOW = "#98b4eb"
ARROW_INK = "#4d6185"
SCROLL_THUMB = "#c1d3fb"
SCROLL_THUMB_HOVER = "#d7e3fe"
SCROLL_TROUGH = "#f7f6f0"
SCROLL_LINE = "#98b1e6"
SCROLL_LIGHT = "#e1eafe"
SCROLL_DARK = "#a8bef5"

UI = ("Tahoma", 8)
UI_BOLD = ("Tahoma", 8, "bold")
LOG = ("Lucida Console", 8)

PANE_WIDTH = 220
CONTROL_HEIGHT = 21
BUTTON_WIDTH = 75
SCALE = 1.0


def px(n):
    return round(n * SCALE)


def mix(a, b, t):
    a, b = int(a[1:], 16), int(b[1:], 16)
    return "#" + "".join(
        f"{round(((a >> s) & 255) * (1 - t) + ((b >> s) & 255) * t):02x}" for s in (16, 8, 0)
    )


def button_image(bg, line, top, bottom, ring=None):
    size = px(CONTROL_HEIGHT)
    # corners are chamfered 2px to approximate radius-control; bg fills the cut-off pixels
    img = tk.PhotoImage(width=size, height=size)
    rows = []
    for y in range(size):
        row = []
        for x in range(size):
            dx, dy = min(x, size - 1 - x), min(y, size - 1 - y)
            if dx + dy < 2:
                c = bg
            elif dx == 0 or dy == 0 or dx + dy == 2:
                c = line
            elif ring and (dx <= px(2) or dy <= px(2)):
                c = ring
            else:
                c = mix(top, bottom, y / (size - 1))
            row.append(c)
        rows.append("{" + " ".join(row) + "}")
    img.put(" ".join(rows))
    return img


def setup_style(root):
    global SCALE
    SCALE = root.winfo_fpixels("1i") / 96
    style = ttk.Style(root)
    style.theme_use("clam")
    root.images = []
    for name, bg in (("Face", FACE), ("Pane", PANE)):
        imgs = [
            button_image(bg, BUTTON_LINE, WINDOW, BUTTON_FILL_END),
            button_image(bg, BUTTON_DISABLED_LINE, BUTTON_DISABLED, BUTTON_DISABLED),
            button_image(bg, BUTTON_LINE, BUTTON_PRESSED_TOP, BUTTON_PRESSED_END),
            button_image(bg, BUTTON_LINE, WINDOW, BUTTON_FILL_END, HOVER_GLOW),
            button_image(bg, BUTTON_LINE, WINDOW, BUTTON_FILL_END, FOCUS_GLOW),
        ]
        root.images += imgs
        normal, disabled, pressed, hover, focus = imgs
        style.element_create(
            f"{name}.border", "image", normal,
            ("disabled", disabled), ("pressed", pressed), ("active", hover), ("focus", focus),
            border=px(4), padding=px(2), sticky="nsew",
        )
        style.layout(f"{name}.TButton", [(f"{name}.border", {"sticky": "nsew", "children": [
            ("Button.padding", {"sticky": "nsew", "children": [("Button.label", {"sticky": "nsew"})]}),
        ]})])
        style.configure(f"{name}.TButton", font=UI, foreground=INK, padding=(px(4), 0), anchor="center")
        style.map(f"{name}.TButton", foreground=[("disabled", INK_DISABLED)])

    style.configure(
        "TEntry", font=UI, padding=(2, 1), foreground=INK, fieldbackground=WINDOW,
        bordercolor=FIELD_LINE, lightcolor=WINDOW, darkcolor=WINDOW,
        selectbackground=SELECTION, selectforeground=WINDOW, insertcolor=INK,
    )
    style.map("TEntry", bordercolor=[("focus", FIELD_LINE)], lightcolor=[("focus", WINDOW)])

    style.configure(
        "Vertical.TScrollbar", background=SCROLL_THUMB, troughcolor=SCROLL_TROUGH,
        bordercolor=SCROLL_LINE, lightcolor=SCROLL_LIGHT, darkcolor=SCROLL_DARK,
        arrowcolor=ARROW_INK, arrowsize=px(15), gripcount=0,
    )
    style.map("Vertical.TScrollbar", background=[("pressed", SCROLL_DARK), ("active", SCROLL_THUMB_HOVER)])


def button(parent, text, command, on="Face"):
    box = tk.Frame(parent, width=px(BUTTON_WIDTH), height=px(CONTROL_HEIGHT), bg=PANE if on == "Pane" else FACE)
    box.pack_propagate(False)
    b = ttk.Button(box, text=text, command=command, style=f"{on}.TButton")
    b.pack(fill="both", expand=True)
    return box, b


def panel(parent, title):
    width, head = px(PANE_WIDTH - 20), px(23)
    outer = tk.Frame(parent, bg=PANE)
    c = tk.Canvas(outer, width=width, height=head, bg=PANE, highlightthickness=0, bd=0)
    for x in range(width):
        top = max(0, 2 - min(x, width - 1 - x))
        c.create_line(x, top, x, head, fill=mix(WINDOW, PANEL_HEAD_END, x / (width - 1)))
    c.create_text(px(12), head // 2, text=title, anchor="w", font=UI_BOLD, fill=PANEL_TITLE)
    c.pack(fill="x")
    edge = tk.Frame(outer, bg=WINDOW, padx=1)
    edge.pack(fill="x")
    body = tk.Frame(edge, bg=PANEL, padx=px(8), pady=px(4))
    body.pack(fill="x", pady=(0, 1))
    body.columnconfigure(1, weight=1)
    return outer, body


def detect(path):
    try:
        with open(path, "rb") as f:
            return "decrypt" if f.read(len(MAGIC)) == MAGIC else "encrypt"
    except OSError:
        return None


class App:
    def __init__(self, root):
        self.root = root
        self.mode = None
        self.result = None
        root.title("Locker")
        root.configure(bg=FACE)
        setup_style(root)
        root.geometry(f"{px(640)}x{px(360)}")
        root.minsize(px(480), px(280))

        bar = tk.Frame(root, bg=FACE, padx=px(4), pady=px(4))
        bar.pack(fill="x")
        tk.Label(bar, text="File", font=UI, fg=INK_MUTED, bg=FACE).pack(side="left")
        self.path = tk.StringVar()
        self.path.trace_add("write", lambda *_: self.refresh())
        ttk.Entry(bar, textvariable=self.path).pack(side="left", fill="x", expand=True, padx=px(4))
        button(bar, "Browse", self.browse)[0].pack(side="left")

        status = tk.Frame(root, bg=FACE, padx=2, pady=2)
        status.pack(side="bottom", fill="x")
        self.state = tk.Label(status, text="idle", width=12, anchor="w", font=UI, bg=FACE, fg=INK, relief="sunken", bd=1, padx=4)
        self.state.pack(side="left", padx=(0, 2))
        self.hint = tk.Label(status, anchor="w", font=UI, bg=FACE, fg=INK, relief="sunken", bd=1, padx=4)
        self.hint.pack(side="left", fill="x", expand=True)

        pane = tk.Frame(root, bg=PANE, width=px(PANE_WIDTH), padx=px(10), pady=px(10))
        pane.pack(side="left", fill="y")
        pane.pack_propagate(False)
        box, body = panel(pane, "Password")
        box.pack(fill="x")
        self.pw = tk.StringVar()
        self.confirm = tk.StringVar()
        tk.Label(body, text="Password:", font=UI, bg=PANEL, fg=INK).grid(row=0, column=0, sticky="w", pady=(0, 1))
        self.pw_entry = ttk.Entry(body, textvariable=self.pw, show="●", width=1)
        self.pw_entry.grid(row=0, column=1, sticky="ew", padx=(px(8), 0), pady=(0, 1))
        self.confirm_label = tk.Label(body, text="Confirm:", font=UI, bg=PANEL, fg=INK)
        self.confirm_label.grid(row=1, column=0, sticky="w")
        self.confirm_entry = ttk.Entry(body, textvariable=self.confirm, show="●", width=1)
        self.confirm_entry.grid(row=1, column=1, sticky="ew", padx=(px(8), 0))
        for e in (self.pw_entry, self.confirm_entry):
            e.bind("<Return>", lambda _: self.run())
        run_box, self.run_btn = button(pane, "Encrypt", self.run, on="Pane")
        run_box.pack(side="bottom", anchor="w")

        content = tk.Frame(root, bg=FACE, padx=px(8), pady=px(8))
        content.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(content, orient="vertical")
        scroll.pack(side="right", fill="y")
        self.log_box = tk.Text(
            content, font=LOG, bg=WINDOW, fg=INK, relief="flat", bd=0, padx=4, pady=2,
            highlightthickness=1, highlightbackground=FIELD_LINE, highlightcolor=FIELD_LINE,
            selectbackground=SELECTION, selectforeground=WINDOW, wrap="none",
            state="disabled", yscrollcommand=scroll.set,
        )
        self.log_box.pack(side="left", fill="both", expand=True)
        scroll.configure(command=self.log_box.yview)

        self.refresh()

    def browse(self):
        path = filedialog.askopenfilename(parent=self.root)
        if path:
            self.path.set(os.path.normpath(path))

    def refresh(self):
        path = self.path.get().strip()
        self.mode = detect(path) if path else None
        name = os.path.basename(path)
        if self.mode == "decrypt":
            self.run_btn.configure(text="Decrypt", state="normal")
            self.confirm_label.grid_remove()
            self.confirm_entry.grid_remove()
            self.hint.configure(text=f"locked file, writes {name.removesuffix(EXT)}")
        else:
            self.run_btn.configure(text="Encrypt", state="normal" if self.mode else "disabled")
            self.confirm_label.grid()
            self.confirm_entry.grid()
            if self.mode:
                self.hint.configure(text=f"plain file, writes {name}{EXT}")
            else:
                self.hint.configure(text="no such file" if path else "choose a file to lock or unlock")

    def log(self, line):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", line + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def run(self):
        if not self.mode or str(self.run_btn["state"]) == "disabled":
            return
        path, pw = self.path.get().strip(), self.pw.get()
        if not pw:
            self.hint.configure(text="enter a password")
            return
        if self.mode == "encrypt" and pw != self.confirm.get():
            self.hint.configure(text="passwords don't match")
            return
        fn = encrypt_file if self.mode == "encrypt" else decrypt_file
        self.state.configure(text="running")
        self.run_btn.configure(state="disabled")
        self.log(f"{self.mode} {path}")

        def work():
            try:
                self.result = ("ok", f"wrote {fn(path, pw)}")
            except SystemExit as e:
                self.result = ("error", str(e))
            except FileExistsError as e:
                self.result = ("error", f"output file already exists: {e.filename}")
            except OSError as e:
                self.result = ("error", str(e))

        self.result = None
        threading.Thread(target=work, daemon=True).start()
        self.poll()

    def poll(self):
        if self.result is None:
            self.root.after(50, self.poll)
            return
        kind, msg = self.result
        self.log(f"[{kind}] {msg}")
        self.state.configure(text="done" if kind == "ok" else "failed")
        self.pw.set("")
        self.confirm.set("")
        self.refresh()


if __name__ == "__main__":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass
    root = tk.Tk()
    App(root)
    root.mainloop()
