from tkinter import ttk

COLORS = {
    "app": "#0b1120",
    "panel": "#111827",
    "surface": "#172033",
    "surface_alt": "#1e293b",
    "border": "#2c3b55",
    "text": "#f8fafc",
    "muted": "#94a3b8",
    "primary": "#4f7cff",
    "current": "#4f7cff",
    "answered": "#15803d",
    "review": "#b45309",
    "unseen": "#334155",
    "correct": "#16a34a",
    "incorrect": "#dc2626",
    "unattempted": "#475569",
    "danger": "#dc2626",
    "success": "#22c55e",
    "error": "#f87171",
    "clock": "#fbbf24",
    "paper": "#e8edf5",
    "coach_bubble": "#0f172a",
    "coach_border": "#3b82f6",
    "heading_solution": "#60a5fa",
    "heading_trap": "#f87171",
    "heading_shortcut": "#fbbf24",
    "heading_drill": "#a78bfa",
    "drill_box": "#131d31",
}


def configure_styles(root):
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(
        "Primary.TButton",
        background=COLORS["primary"],
        foreground="white",
        padding=(12, 8),
        font=("Segoe UI", 9, "bold"),
        borderwidth=0,
    )
    style.map(
        "Primary.TButton",
        background=[("active", "#658cff"), ("disabled", COLORS["unseen"])],
    )

    style.configure(
        "Secondary.TButton",
        background=COLORS["surface"],
        foreground=COLORS["text"],
        padding=(12, 7),
        borderwidth=0,
    )
    style.map("Secondary.TButton", background=[("active", COLORS["border"])])

    style.configure(
        "Danger.TButton",
        background=COLORS["danger"],
        foreground="white",
        padding=(12, 8),
        font=("Segoe UI", 9, "bold"),
        borderwidth=0,
    )

    style.configure(
        "Exam.Horizontal.TProgressbar",
        troughcolor=COLORS["surface"],
        background=COLORS["primary"],
        borderwidth=0,
    )

    style.configure(
        "Review.Horizontal.TProgressbar",
        troughcolor=COLORS["surface"],
        background=COLORS["current"],
        borderwidth=0,
    )

    style.configure(
        "Vertical.TScrollbar",
        background=COLORS["surface"],
        troughcolor=COLORS["app"],
        bordercolor=COLORS["app"],
        arrowcolor=COLORS["muted"],
    )

    style.configure(
        "Horizontal.TScrollbar",
        background=COLORS["surface"],
        troughcolor=COLORS["app"],
        bordercolor=COLORS["app"],
        arrowcolor=COLORS["muted"],
    )