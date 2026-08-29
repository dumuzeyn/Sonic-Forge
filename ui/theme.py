from tkinter import ttk


APP_BACKGROUND = "#F9F9FB"

COLORS = {
    "bg": APP_BACKGROUND,
    "surface": APP_BACKGROUND,
    "surface_alt": "#F0F1F3",
    "elevated": "#E8EAED",
    "field": "#FBFBFC",
    "text": "#17191D",
    "secondary": "#60656D",
    "disabled": "#989DA5",
    "border": "#D5D8DD",
    "border_active": "#A5AAB2",
    "accent": "#24272D",
    "accent_hover": "#34383F",
    "accent_pressed": "#15171A",
    "danger": "#A94F56",
    "danger_hover": "#8F4047",
    "log": "#F7F8F9",
    "white": "#FFFFFF",
}

SPACING = {"xs": 4, "sm": 8, "md": 12, "lg": 18, "xl": 24}
SIZES = {
    "control_height": 36,
    "button_width": 11,
    "language_width": 12,
    "primary_width": 18,
    "check_size": 16,
    "header_height": 70,
    "tab_height": 42,
    "tooltip_width": 380,
    "window_width_reserve": 6,
    "window_height_reserve": 4,
    "minimum_window_aspect": 4 / 3,
}
FONTS = {
    "body": ("Segoe UI", 10),
    "label": ("Segoe UI", 9),
    "section": ("Segoe UI Semibold", 11),
    "title": ("Segoe UI Semibold", 15),
    "small": ("Segoe UI", 9),
    "mono": ("Cascadia Mono", 9),
}


def configure_styles(root):
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(
        ".",
        background=COLORS["bg"],
        foreground=COLORS["text"],
        fieldbackground=COLORS["field"],
        bordercolor=COLORS["border"],
        lightcolor=COLORS["border"],
        darkcolor=COLORS["border"],
        font=FONTS["body"],
    )
    style.configure("TFrame", background=COLORS["bg"])
    style.configure("Surface.TFrame", background=COLORS["surface"])
    style.configure("Elevated.TFrame", background=COLORS["elevated"])
    style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"])
    style.configure("Surface.TLabel", background=COLORS["surface"], foreground=COLORS["text"])
    style.configure(
        "Secondary.TLabel",
        background=COLORS["bg"],
        foreground=COLORS["secondary"],
        font=FONTS["small"],
    )
    style.configure(
        "SurfaceSecondary.TLabel",
        background=COLORS["surface"],
        foreground=COLORS["secondary"],
        font=FONTS["small"],
    )
    style.configure("Title.TLabel", font=FONTS["title"])
    style.configure("Section.TLabel", font=FONTS["section"])
    style.configure(
        "Surface.TLabelframe",
        background=COLORS["surface"],
        bordercolor=COLORS["border"],
        borderwidth=1,
        relief="solid",
    )
    style.configure(
        "Surface.TLabelframe.Label",
        background=COLORS["surface"],
        foreground=COLORS["text"],
        font=FONTS["section"],
    )

    style.configure(
        "TButton",
        background=COLORS["elevated"],
        foreground=COLORS["text"],
        bordercolor=COLORS["border"],
        borderwidth=1,
        focusthickness=1,
        focuscolor=COLORS["accent"],
        padding=(12, 7),
        relief="flat",
    )
    style.map(
        "TButton",
        background=[("pressed", "#D9DCE1"), ("active", "#E0E2E6")],
        bordercolor=[("focus", COLORS["accent"]), ("active", COLORS["border_active"])],
        foreground=[("disabled", COLORS["disabled"])],
    )
    style.configure(
        "TMenubutton",
        background=COLORS["elevated"],
        foreground=COLORS["text"],
        bordercolor=COLORS["border"],
        borderwidth=1,
        padding=(12, 7),
        arrowcolor=COLORS["secondary"],
    )
    style.map(
        "TMenubutton",
        background=[("pressed", "#D9DCE1"), ("active", "#E0E2E6")],
        bordercolor=[("focus", COLORS["accent"]), ("active", COLORS["border_active"])],
    )
    style.configure(
        "Primary.TButton",
        background=COLORS["accent"],
        foreground=COLORS["white"],
        bordercolor=COLORS["accent"],
        font=("Segoe UI Semibold", 10),
        padding=(14, 7),
    )
    style.map(
        "Primary.TButton",
        background=[("pressed", COLORS["accent_pressed"]), ("active", COLORS["accent_hover"])],
        bordercolor=[("pressed", COLORS["accent_pressed"]), ("active", COLORS["accent_hover"])],
        foreground=[("disabled", "#D2D4D8")],
    )
    style.configure("Danger.TButton", background=COLORS["elevated"], foreground=COLORS["danger"])
    style.map(
        "Danger.TButton",
        background=[("pressed", "#E4D0D2"), ("active", "#F0DFE1")],
        bordercolor=[("focus", COLORS["danger"]), ("active", COLORS["danger_hover"])],
    )

    for name in ("TEntry", "TSpinbox", "TCombobox"):
        style.configure(
            name,
            fieldbackground=COLORS["field"],
            foreground=COLORS["text"],
            insertcolor=COLORS["text"],
            bordercolor=COLORS["border"],
            arrowcolor=COLORS["secondary"],
            borderwidth=1,
            padding=(8, 6),
        )
        style.map(
            name,
            bordercolor=[("focus", COLORS["accent"]), ("disabled", COLORS["border"])],
            fieldbackground=[("disabled", COLORS["surface_alt"]), ("readonly", COLORS["field"])],
            foreground=[("disabled", COLORS["disabled"]), ("readonly", COLORS["text"])],
        )
    style.map(
        "TCombobox",
        selectbackground=[("readonly", COLORS["field"])],
        selectforeground=[("readonly", COLORS["text"])],
    )
    style.configure(
        "Thin.Horizontal.TProgressbar",
        background=COLORS["accent"],
        troughcolor=COLORS["surface_alt"],
        bordercolor=COLORS["surface_alt"],
        lightcolor=COLORS["accent"],
        darkcolor=COLORS["accent"],
        thickness=6,
    )
    style.configure(
        "Vertical.TScrollbar",
        background=COLORS["elevated"],
        troughcolor=COLORS["log"],
        bordercolor=COLORS["border"],
        arrowcolor=COLORS["secondary"],
    )
    style.configure("TSeparator", background=COLORS["border"])
    style.configure("TabBar.TFrame", background=COLORS["border"])
    style.configure(
        "Tab.TButton",
        background=COLORS["surface_alt"],
        foreground=COLORS["secondary"],
        bordercolor=COLORS["border"],
        borderwidth=1,
        padding=(12, 8),
        font=FONTS["body"],
    )
    style.map(
        "Tab.TButton",
        background=[("pressed", COLORS["elevated"]), ("active", COLORS["elevated"])],
        foreground=[("active", COLORS["text"])],
    )
    style.configure(
        "Selected.Tab.TButton",
        background=COLORS["surface"],
        foreground=COLORS["text"],
        bordercolor=COLORS["accent"],
        borderwidth=1,
        padding=(12, 8),
        font=("Segoe UI Semibold", 10),
    )
    style.map(
        "Selected.Tab.TButton",
        background=[("pressed", COLORS["surface"]), ("active", COLORS["surface"])],
        foreground=[("disabled", COLORS["disabled"])],
    )
    return style
