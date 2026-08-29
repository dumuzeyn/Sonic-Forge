import tkinter as tk
import tkinter.font as tkfont

from .theme import COLORS, FONTS, SIZES


class ToolTip:
    def __init__(self, widget, text_provider, delay=450):
        self.widget = widget
        self.text_provider = text_provider
        self.delay = delay
        self.window = None
        self.after_id = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")
        widget.bind("<Destroy>", self._hide, add="+")

    def _schedule(self, _event=None):
        self._cancel()
        self.after_id = self.widget.after(self.delay, self._show)

    def _cancel(self):
        if self.after_id is not None:
            try:
                self.widget.after_cancel(self.after_id)
            except tk.TclError:
                pass
            self.after_id = None

    def _show(self):
        self.after_id = None
        text = self.text_provider()
        if not text or self.window is not None:
            return
        self.window = tk.Toplevel(self.widget)
        self.window.overrideredirect(True)
        label = tk.Label(
            self.window,
            text=text,
            justify="left",
            wraplength=SIZES["tooltip_width"],
            bg=COLORS["elevated"],
            fg=COLORS["text"],
            font=FONTS["body"],
            relief="solid",
            borderwidth=1,
            padx=11,
            pady=9,
        )
        label.pack()
        self.window.update_idletasks()
        x = self.widget.winfo_rootx()
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        max_x = self.widget.winfo_screenwidth() - self.window.winfo_reqwidth() - 8
        max_y = self.widget.winfo_screenheight() - self.window.winfo_reqheight() - 8
        if y > max_y:
            y = self.widget.winfo_rooty() - self.window.winfo_reqheight() - 8
        self.window.geometry(f"+{max(8, min(x, max_x))}+{max(8, y)}")

    def _hide(self, _event=None):
        self._cancel()
        if self.window is not None:
            try:
                self.window.destroy()
            except tk.TclError:
                pass
            self.window = None


class ModernScale(tk.Canvas):
    def __init__(
        self,
        parent,
        *,
        from_=0,
        to=100,
        variable=None,
        command=None,
        width=120,
        height=30,
        surface=True,
    ):
        self.minimum = float(from_)
        self.maximum = float(to)
        self.variable = variable if variable is not None else tk.DoubleVar(value=self.minimum)
        self.command = command
        self.hovered = False
        background = COLORS["surface"] if surface else COLORS["bg"]
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=background,
            highlightthickness=0,
            borderwidth=0,
            takefocus=True,
            cursor="hand2",
        )
        self.bind("<Configure>", self._redraw)
        self.bind("<Button-1>", self._move)
        self.bind("<B1-Motion>", self._move)
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<FocusIn>", self._redraw)
        self.bind("<FocusOut>", self._redraw)
        self.bind("<Left>", lambda _event: self._step(-1))
        self.bind("<Right>", lambda _event: self._step(1))
        self.bind("<Home>", lambda _event: self._set_value(self.minimum))
        self.bind("<End>", lambda _event: self._set_value(self.maximum))
        self.variable.trace_add("write", self._redraw)

    def _geometry(self):
        radius = 12 if self.hovered or self.focus_get() is self else 11
        start = radius + 3
        end = max(start + 1, self.winfo_width() - radius - 3)
        return start, end, self.winfo_height() / 2, radius

    def _redraw(self, *_args):
        if not self.winfo_exists():
            return
        self.delete("all")
        start, end, center_y, radius = self._geometry()
        span = self.maximum - self.minimum
        fraction = 0.0 if span == 0 else (float(self.variable.get()) - self.minimum) / span
        fraction = max(0.0, min(1.0, fraction))
        thumb_x = start + (end - start) * fraction
        self.create_line(
            start,
            center_y,
            end,
            center_y,
            fill=COLORS["accent"],
            width=4,
            capstyle=tk.ROUND,
        )
        self.create_oval(
            thumb_x - radius,
            center_y - radius,
            thumb_x + radius,
            center_y + radius,
            fill=COLORS["accent_hover"] if self.hovered else COLORS["text"],
            outline=COLORS["surface"],
            width=2,
        )

    def _set_value(self, value):
        value = max(self.minimum, min(self.maximum, float(value)))
        self.variable.set(value)
        if self.command is not None:
            self.command(str(value))
        return "break"

    def _move(self, event):
        self.focus_set()
        start, end, _center_y, _radius = self._geometry()
        fraction = (event.x - start) / max(1, end - start)
        return self._set_value(self.minimum + max(0.0, min(1.0, fraction)) * (self.maximum - self.minimum))

    def _step(self, direction):
        step = (self.maximum - self.minimum) / 100.0
        return self._set_value(float(self.variable.get()) + direction * step)

    def _enter(self, _event=None):
        self.hovered = True
        self._redraw()

    def _leave(self, _event=None):
        self.hovered = False
        self._redraw()


class SquareCheckbutton(tk.Frame):
    def __init__(
        self,
        parent,
        variable,
        text="",
        command=None,
        surface=True,
        fixed_width=None,
    ):
        self.background = COLORS["surface"] if surface else COLORS["bg"]
        super().__init__(
            parent,
            bg=self.background,
            height=26,
            takefocus=True,
            highlightthickness=1,
            highlightbackground=self.background,
            highlightcolor=COLORS["accent"],
            cursor="hand2",
        )
        self.variable = variable
        self.command = command
        self.enabled = True
        self.minimum_width = fixed_width
        if fixed_width is not None:
            self.configure(width=fixed_width)
            self.pack_propagate(False)
        self.canvas = tk.Canvas(
            self,
            width=20,
            height=20,
            bg=self.background,
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        self.label = tk.Label(
            self,
            text=text,
            bg=self.background,
            fg=COLORS["text"],
            font=FONTS["body"],
            cursor="hand2",
            anchor="w",
        )
        self.canvas.pack(side=tk.LEFT, padx=(1, 7))
        self.label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        for widget in (self, self.canvas, self.label):
            widget.bind("<Button-1>", self._toggle, add="+")
        self.bind("<space>", self._toggle, add="+")
        self.bind("<Return>", self._toggle, add="+")
        self.variable.trace_add("write", self._redraw)
        self._fit_text()
        self._redraw()

    def configure(self, cnf=None, **kwargs):
        text = kwargs.pop("text", None)
        state = kwargs.pop("state", None)
        if text is not None:
            self.label.configure(text=text)
            self._fit_text()
        if state is not None:
            self.enabled = str(state) != "disabled"
            self.configure_cursor()
            self._redraw()
        if kwargs:
            super().configure(cnf, **kwargs)

    config = configure

    def _fit_text(self):
        if self.minimum_width is None:
            return
        font = tkfont.Font(font=self.label.cget("font"))
        required = font.measure(self.label.cget("text")) + 38
        super().configure(width=max(self.minimum_width, required))

    def configure_cursor(self):
        cursor = "hand2" if self.enabled else "arrow"
        for widget in (self, self.canvas, self.label):
            widget.configure(cursor=cursor)

    def _toggle(self, _event=None):
        if not self.enabled:
            return "break"
        self.focus_set()
        self.variable.set(not bool(self.variable.get()))
        if self.command:
            self.command()
        return "break"

    def _redraw(self, *_args):
        selected = bool(self.variable.get())
        self.canvas.delete("all")
        if not self.enabled:
            border = COLORS["border"]
            fill = COLORS["surface_alt"]
            label_color = COLORS["disabled"]
        else:
            border = COLORS["accent"] if selected else COLORS["border_active"]
            fill = COLORS["accent"] if selected else COLORS["field"]
            label_color = COLORS["text"]
        self.canvas.create_rectangle(2, 2, 18, 18, outline=border, fill=fill, width=1)
        self.label.configure(fg=label_color)
