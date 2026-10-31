import json
from pathlib import Path
import re
import threading
import tkinter as tk
from tkinter import ttk
import pymupdf

from coach import generate_question_coaching, clean_key
from scoring import score_attempt
from ui_theme import COLORS, configure_styles

# Load the validated catalogue created in Step 2.
papers = json.loads(Path("data/papers.json").read_text(encoding="utf-8"))
paper = papers[0]
answers = {int(row["number"]): row for row in paper["answers"]}
document = pymupdf.open(paper["paper"])
responses = {}
marked = set()
current = 1
remaining = 180 * 60
response_vars = []
palette_buttons = []

Path("cache").mkdir(exist_ok=True)


def render_question():
    page_number = int(paper["question_pages"][str(current)])
    cache_name = f"{paper['session']}-{page_number}.png"
    cache_path = Path("cache") / cache_name
    if not cache_path.exists():
        pixmap = document[page_number].get_pixmap(dpi=120, alpha=False)
        pixmap.save(cache_path)

    image = tk.PhotoImage(file=cache_path)
    page_canvas.delete("all")
    page_canvas.create_image(0, 0, anchor="nw", image=image)
    page_canvas.image = image
    page_canvas.configure(scrollregion=(0, 0, image.width(), image.height()))
    page_canvas.yview_moveto(0)


def show_response_controls():
    global response_vars
    for child in response_frame.winfo_children():
        child.destroy()

    metadata = answers[current]
    kind = metadata["type"]
    saved = responses.get(current, "")
    question_label.config(text=f"Question {current} of 65")
    type_label.config(text=f"{kind} | {metadata['marks']} mark(s)")
    response_vars = []

    options = {
        "bg": COLORS["panel"],
        "fg": COLORS["text"],
        "activebackground": COLORS["surface"],
        "activeforeground": COLORS["text"],
        "selectcolor": COLORS["surface"],
        "font": ("Segoe UI", 10),
        "padx": 8,
        "pady": 4,
        "anchor": "w",
        "highlightthickness": 0,
    }

    if kind == "MCQ":
        variable = tk.StringVar(value=saved)
        response_vars.append(variable)
        for option in "ABCD":
            tk.Radiobutton(
                response_frame,
                text=f"Option {option}",
                variable=variable,
                value=option,
                **options,
            ).pack(fill="x", pady=1)
    elif kind == "MSQ":
        selected = set(saved.split(";"))
        for option in "ABCD":
            variable = tk.BooleanVar(value=option in selected)
            response_vars.append(variable)
            tk.Checkbutton(
                response_frame,
                text=f"Option {option}",
                variable=variable,
                **options,
            ).pack(fill="x", pady=1)
    else:
        variable = tk.StringVar(value=saved)
        response_vars.append(variable)
        tk.Entry(
            response_frame,
            textvariable=variable,
            bg=COLORS["surface"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            font=("Segoe UI", 11),
            relief="flat",
        ).pack(fill="x", ipady=7)


def save_response():
    kind = answers[current]["type"]
    if kind == "MSQ":
        value = ";".join(
            option for option, variable in zip("ABCD", response_vars) if variable.get()
        )
    else:
        value = response_vars[0].get().strip()

    if value:
        responses[current] = value
    else:
        responses.pop(current, None)
    update_palette()


def go_to(number):
    global current
    save_response()
    current = max(1, min(65, number))
    refresh()


def save_and_next():
    save_response()
    marked.discard(current)
    update_palette()
    if current < 65:
        go_to(current + 1)


def toggle_mark():
    if current in marked:
        marked.remove(current)
    else:
        marked.add(current)
    update_palette()


def update_palette():
    for number, button in enumerate(palette_buttons, start=1):
        state = (
            "current"
            if number == current
            else "review"
            if number in marked
            else "answered"
            if number in responses
            else "unseen"
        )
        color = COLORS[state]
        button.configure(bg=color, activebackground=color, fg="white")
    progress_label.config(
        text=f"{len(responses)} answered  |  {len(marked)} for review"
    )
    progress_bar.configure(value=len(responses))


def refresh():
    render_question()
    show_response_controls()
    update_palette()


def load_session(session):
    global paper, answers, document, current, remaining
    document.close()
    paper = next(item for item in papers if item["session"] == session)
    answers = {int(row["number"]): row for row in paper["answers"]}
    document = pymupdf.open(paper["paper"])
    responses.clear()
    marked.clear()
    current = 1
    remaining = 180 * 60
    refresh()


def tick():
    global remaining
    hours, remainder = divmod(max(remaining, 0), 3600)
    minutes, seconds = divmod(remainder, 60)
    timer_label.config(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
    if remaining > 0:
        remaining -= 1
        root.after(1000, tick)


def show_report(report):
    window = tk.Toplevel(root)
    window.title("Attempt Review")
    window.geometry("1440x900")
    window.minsize(1120, 720)
    window.configure(bg=COLORS["app"])
    configure_styles(window)

    report_paper = paper
    review_document = pymupdf.open(report_paper["paper"])
    rows = {int(row["number"]): row for row in report["questions"]}
    selected = {"number": 1}
    running = {"number": None}
    coach_cache = {}
    review_buttons = []

    # 1. Top Header Bar
    topbar = tk.Frame(
        window,
        bg=COLORS["panel"],
        highlightbackground=COLORS["border"],
        highlightthickness=1,
    )
    topbar.pack(fill="x", padx=16, pady=(14, 10))

    identity = tk.Frame(topbar, bg=COLORS["panel"])
    identity.pack(side="left", padx=16, pady=10)
    tk.Label(
        identity,
        text="ATTEMPT REVIEW",
        bg=COLORS["panel"],
        fg=COLORS["text"],
        font=("Segoe UI", 16, "bold"),
    ).pack(anchor="w")
    tk.Label(
        identity,
        text=f"GATE CS Offline Mock | {report['session']}",
        bg=COLORS["panel"],
        fg=COLORS["muted"],
        font=("Segoe UI", 9),
    ).pack(anchor="w", pady=(1, 0))

    summary = tk.Frame(topbar, bg=COLORS["panel"])
    summary.pack(side="right", padx=14, pady=8)
    tk.Label(
        summary,
        text=f"Score: {report['score']:.2f} / 100",
        bg=COLORS["surface_alt"],
        fg=COLORS["text"],
        font=("Segoe UI", 12, "bold"),
        padx=12,
        pady=6,
    ).pack(side="left", padx=4)

    for label, key, color in (
        ("Correct", "correct", COLORS["correct"]),
        ("Incorrect", "incorrect", COLORS["incorrect"]),
        ("Unattempted", "unattempted", COLORS["muted"]),
    ):
        tk.Label(
            summary,
            text=f"{label}: {report[key]}",
            bg=COLORS["surface"],
            fg=color,
            font=("Segoe UI", 10, "bold"),
            padx=10,
            pady=6,
        ).pack(side="left", padx=4)

    # 2. Main Workspace Split
    review_body = tk.Frame(window, bg=COLORS["app"])
    review_body.pack(fill="both", expand=True, padx=16, pady=(0, 14))
    review_body.grid_rowconfigure(0, weight=1)
    review_body.grid_columnconfigure(0, weight=15, uniform="rev")
    review_body.grid_columnconfigure(1, weight=5, uniform="rev")

    left = tk.Frame(review_body, bg=COLORS["app"])
    left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
    left.grid_rowconfigure(0, weight=1)
    left.grid_columnconfigure(0, weight=1)

    viewer = tk.Frame(
        left,
        bg=COLORS["paper"],
        highlightbackground=COLORS["border"],
        highlightthickness=1,
    )
    viewer.grid(row=0, column=0, sticky="nsew")

    review_canvas = tk.Canvas(viewer, bg=COLORS["paper"], highlightthickness=0)
    review_y = ttk.Scrollbar(viewer, orient="vertical", command=review_canvas.yview)
    review_canvas.configure(yscrollcommand=review_y.set)
    review_y.pack(side="right", fill="y")
    review_canvas.pack(side="left", fill="both", expand=True)

    # Horizontal Evaluation Strip
    evaluation = tk.Frame(
        left,
        bg=COLORS["panel"],
        highlightbackground=COLORS["border"],
        highlightthickness=1,
        padx=12,
        pady=8,
    )
    evaluation.grid(row=1, column=0, sticky="ew", pady=(8, 0))

    review_question = tk.Label(
        evaluation,
        bg=COLORS["panel"],
        fg=COLORS["text"],
        font=("Segoe UI", 11, "bold"),
    )
    review_question.pack(side="left", padx=(4, 16))

    answer_line = tk.Label(
        evaluation,
        bg=COLORS["surface"],
        fg=COLORS["text"],
        font=("Segoe UI", 9, "bold"),
        padx=8,
        pady=4,
    )
    answer_line.pack(side="left", padx=4)

    key_line = tk.Label(
        evaluation,
        bg=COLORS["surface"],
        fg="#38bdf8",
        font=("Segoe UI", 9, "bold"),
        padx=8,
        pady=4,
    )
    key_line.pack(side="left", padx=4)

    verdict_line = tk.Label(
        evaluation, bg=COLORS["panel"], font=("Segoe UI", 10, "bold")
    )
    verdict_line.pack(side="right", padx=8)

    # Right Column: Question Palette
    right = tk.Frame(
        review_body,
        bg=COLORS["panel"],
        highlightbackground=COLORS["border"],
        highlightthickness=1,
    )
    right.grid(row=0, column=1, sticky="nsew")

    tk.Label(
        right,
        text="QUESTION REVIEW",
        bg=COLORS["panel"],
        fg=COLORS["text"],
        font=("Segoe UI", 11, "bold"),
    ).pack(anchor="w", padx=12, pady=(12, 2))

    tk.Label(
        right,
        text="Green: correct  Red: incorrect  Slate: blank",
        bg=COLORS["panel"],
        fg=COLORS["muted"],
        font=("Segoe UI", 8),
    ).pack(anchor="w", padx=12, pady=(0, 6))

    review_palette = tk.Frame(right, bg=COLORS["panel"])
    review_palette.pack(fill="x", padx=10, pady=(4, 10))

    for number in range(1, 66):
        row = rows[number]
        color = COLORS[row["verdict"]]
        button = tk.Button(
            review_palette,
            text=str(number),
            width=3,
            height=1,
            bg=color,
            fg="white",
            activebackground=color,
            activeforeground="white",
            relief="flat",
            bd=0,
            font=("Segoe UI", 8, "bold"),
            cursor="hand2",
            command=lambda n=number: show_review_question(n),
        )
        button.grid(
            row=(number - 1) // 7, column=(number - 1) % 7, padx=2, pady=2
        )
        review_buttons.append(button)

    # ==========================================
    # ENLARGED HIGH-READABILITY CHATBOT DRAWER
    # ==========================================
    drawer = tk.Frame(
        window,
        bg=COLORS["surface_alt"],
        highlightbackground=COLORS["coach_border"],
        highlightthickness=2,
    )
    drawer_open = [False]

    drawer_header = tk.Frame(drawer, bg=COLORS["panel"], padx=18, pady=12)
    drawer_header.pack(fill="x")

    drawer_title = tk.Label(
        drawer_header,
        text="✨ Gemma Problem Coach (Q.1)",
        bg=COLORS["panel"],
        fg=COLORS["text"],
        font=("Segoe UI", 13, "bold"),
    )
    drawer_title.pack(side="left")

    close_btn = tk.Button(
        drawer_header,
        text="✕",
        bg=COLORS["panel"],
        fg=COLORS["muted"],
        activebackground=COLORS["panel"],
        activeforeground=COLORS["text"],
        bd=0,
        font=("Segoe UI", 13, "bold"),
        cursor="hand2",
        command=lambda: toggle_drawer(False),
    )
    close_btn.pack(side="right")

    drawer_controls = tk.Frame(drawer, bg=COLORS["surface_alt"], padx=18, pady=10)
    drawer_controls.pack(fill="x")

    coach_btn = ttk.Button(
        drawer_controls, text="Explain Solution & Method", style="Primary.TButton"
    )
    coach_btn.pack(fill="x", pady=(2, 6))

    coach_status = tk.Label(
        drawer_controls,
        text="Ready for analysis.",
        bg=COLORS["surface_alt"],
        fg=COLORS["muted"],
        font=("Segoe UI", 10),
    )
    coach_status.pack(anchor="w")

    coach_progress = ttk.Progressbar(
        drawer, mode="indeterminate", style="Review.Horizontal.TProgressbar"
    )

    # Large-print chat viewport
    chat_box = tk.Text(
        drawer,
        wrap="word",
        bg=COLORS["coach_bubble"],
        fg=COLORS["text"],
        relief="flat",
        bd=0,
        padx=18,
        pady=16,
        font=("Segoe UI", 11),
        spacing1=5,
        spacing2=3,
        spacing3=8,
        state="disabled",
    )
    chat_scroll = ttk.Scrollbar(drawer, orient="vertical", command=chat_box.yview)
    chat_box.configure(yscrollcommand=chat_scroll.set)
    chat_scroll.pack(side="right", fill="y", pady=(0, 8))
    chat_box.pack(side="left", fill="both", expand=True, padx=(14, 0), pady=(0, 8))

    chat_box.tag_configure("bold", font=("Segoe UI", 11, "bold"), foreground=COLORS["text"])
    chat_box.tag_configure("bullet", lmargin1=10, lmargin2=28, foreground=COLORS["text"])
    chat_box.tag_configure(
        "head_sol", font=("Segoe UI", 12, "bold"), foreground=COLORS["heading_solution"], spacing1=10, spacing3=4
    )
    chat_box.tag_configure(
        "head_trap", font=("Segoe UI", 12, "bold"), foreground=COLORS["heading_trap"], spacing1=10, spacing3=4
    )
    chat_box.tag_configure(
        "head_short", font=("Segoe UI", 12, "bold"), foreground=COLORS["heading_shortcut"], spacing1=10, spacing3=4
    )

    header_map = {
        "Syllabus Topic Classification": "head_sol",
        "Likely Misconception": "head_trap",
        "3-Step Revision Advice": "head_short",
    }

    def render_coaching_text(raw_text):
        chat_box.configure(state="normal")
        chat_box.delete("1.0", "end")

        for line in raw_text.splitlines():
            line_str = line.strip()
            if not line_str:
                chat_box.insert("end", "\n")
                continue

            bullet = line_str.startswith(("* ", "- ", "• "))
            if bullet:
                line_str = line_str[2:].strip()

            handled = False
            for heading, tag_name in header_map.items():
                for pat in (f"**{heading}:**", f"**{heading}**", f"{heading}:"):
                    if line_str.startswith(pat):
                        chat_box.insert("end", f"{heading}\n", tag_name)
                        rem = line_str[len(pat) :].lstrip(" :")
                        if rem:
                            chat_box.insert("end", f"{rem}\n")
                        handled = True
                        break
                if handled:
                    break

            if handled:
                continue

            parts = line_str.split("**")
            if bullet:
                chat_box.insert("end", "• ", "bullet")
            for i, part in enumerate(parts):
                tags = ("bullet",) if bullet else ()
                if i % 2:
                    tags += ("bold",)
                chat_box.insert("end", part, tags)
            chat_box.insert("end", "\n")

        chat_box.see("1.0")
        chat_box.configure(state="disabled")

    def toggle_drawer(state=None):
        if state is None:
            state = not drawer_open[0]
        drawer_open[0] = state
        if drawer_open[0]:
            drawer.place(relx=0.985, rely=0.97, anchor="se", width=620, height=700)
            fab.place_forget()
        else:
            drawer.place_forget()
            fab.place(relx=0.985, rely=0.97, anchor="se")

    # Enlarged High-Visibility Floating Action Button
    fab = tk.Button(
        window,
        text="✨ Ask Gemma Coach",
        bg=COLORS["primary"],
        fg="white",
        activebackground="#658cff",
        activeforeground="white",
        font=("Segoe UI", 13, "bold"),
        relief="flat",
        cursor="hand2",
        bd=0,
        padx=26,
        pady=14,
        highlightthickness=2,
        highlightbackground="#60a5fa",
        command=lambda: toggle_drawer(True),
    )
    fab.place(relx=0.985, rely=0.97, anchor="se")

    def show_coach_state(number):
        drawer_title.config(text=f"✨ Gemma CS Coach (Q.{number})")
        if number <= 10:
            chat_box.configure(state="normal")
            chat_box.delete("1.0", "end")
            chat_box.insert(
                "end",
                "General Aptitude Question (Q.1 - Q.10).\n\n"
                "AI Study Coaching is enabled for Core Computer Science questions (Q.11 - Q.65).\n"
                f"Official Answer Key: {clean_key(rows[number]['key'])}"
            )
            chat_box.configure(state="disabled")
            coach_status.config(text="General Aptitude Section.", fg=COLORS["muted"])
            coach_btn.configure(state="disabled")
        elif number in coach_cache:
            render_coaching_text(coach_cache[number])
            coach_status.config(text="Analysis loaded.", fg=COLORS["success"])
            coach_btn.configure(state="normal")
        elif running["number"]:
            chat_box.configure(state="normal")
            chat_box.delete("1.0", "end")
            chat_box.insert("end", f"Analyzing Question {running['number']}...")
            chat_box.configure(state="disabled")
            coach_status.config(text="Analysis in progress...", fg=COLORS["muted"])
            coach_btn.configure(state="disabled")
        else:
            chat_box.configure(state="normal")
            chat_box.delete("1.0", "end")
            chat_box.insert("end", "Click 'Explain Solution & Method' to analyze this CS question.")
            chat_box.configure(state="disabled")
            coach_status.config(text="Ready for CS analysis.", fg=COLORS["muted"])
            coach_btn.configure(state="normal")

    def show_review_question(number):
        selected["number"] = number
        row = rows[number]
        page_number = int(report_paper["question_pages"][str(number)])
        cache_path = Path("cache") / f"{report_paper['session']}-{page_number}.png"
        if not cache_path.exists():
            pixmap = review_document[page_number].get_pixmap(dpi=120, alpha=False)
            pixmap.save(cache_path)

        image = tk.PhotoImage(file=cache_path)
        review_canvas.delete("all")
        review_canvas.create_image(0, 0, anchor="nw", image=image)
        review_canvas.image = image
        review_canvas.configure(scrollregion=(0, 0, image.width(), image.height()))
        review_canvas.yview_moveto(0)

        response = row["response"] or "Unattempted"
        points = f"{row['points']:+.2f}" if row["points"] else "0.00"

        review_question.config(
            text=f"Question {number} | {row['type']} | {row['marks']} mark(s)"
        )
        answer_line.config(text=f"Your Answer: {response}")
        key_line.config(text=f"Official Key: {row['key']}")
        verdict_line.config(
            text=f"Verdict: {row['verdict'].title()} ({points})",
            fg=COLORS[row["verdict"]],
        )

        show_coach_state(number)
        for i, btn in enumerate(review_buttons, start=1):
            chosen = i == number
            btn.configure(
                relief="solid" if chosen else "flat",
                bd=2 if chosen else 0,
                highlightthickness=2 if chosen else 0,
                highlightbackground=COLORS["current"],
                highlightcolor=COLORS["current"],
            )

    def finish_coach(number, text, failed=False):
        running["number"] = None
        coach_progress.stop()
        coach_progress.pack_forget()
        if not failed:
            coach_cache[number] = text
        if selected["number"] == number:
            render_coaching_text(text)
            coach_status.config(
                text="Failed to reach Ollama." if failed else "Complete.",
                fg=COLORS["error"] if failed else COLORS["success"],
            )
        else:
            show_coach_state(selected["number"])
        coach_btn.configure(state="normal")

    def coach_worker(number, row):
        try:
            guidance = generate_question_coaching(row, report_paper)
            window.after(0, finish_coach, number, guidance, False)
        except Exception as error:
            window.after(
                0, finish_coach, number, f"Study coach unavailable: {error}", True
            )

    def start_coach():
        number = selected["number"]
        running["number"] = number
        coach_btn.configure(state="disabled")
        coach_status.config(text=f"Analyzing Q.{number}...", fg=COLORS["muted"])
        chat_box.configure(state="normal")
        chat_box.delete("1.0", "end")
        chat_box.insert("end", "Consulting local Gemma model...")
        chat_box.configure(state="disabled")
        coach_progress.pack(fill="x", padx=14, pady=(2, 6), before=chat_box)
        coach_progress.start(12)
        threading.Thread(
            target=coach_worker, args=(number, rows[number]), daemon=True
        ).start()

    coach_btn.configure(command=start_coach)

    def close_report():
        review_document.close()
        window.destroy()

    review_canvas.bind("<Enter>", lambda _: review_canvas.focus_set())
    review_canvas.bind(
        "<MouseWheel>",
        lambda event: review_canvas.yview_scroll(
            -1 if event.delta > 0 else 1, "units"
        ),
    )
    window.protocol("WM_DELETE_WINDOW", close_report)
    show_review_question(1)


def submit_attempt():
    save_response()
    report = score_attempt(list(answers.values()), responses)
    report["session"] = paper["session"]
    Path("data/last_attempt.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    show_report(report)


# ==========================================
# ROOT WINDOW & INTERFACE ASSEMBLY
# ==========================================
root = tk.Tk()
root.title("Offline GATE Mock Test App")
root.geometry("1360x860")
root.minsize(1080, 720)
root.configure(bg=COLORS["app"])
configure_styles(root)

header = tk.Frame(
    root,
    bg=COLORS["panel"],
    highlightbackground=COLORS["border"],
    highlightthickness=1,
)
header.pack(fill="x", padx=20, pady=(18, 14))

brand = tk.Frame(header, bg=COLORS["panel"])
brand.pack(side="left", padx=18, pady=14)
tk.Label(
    brand,
    text="GATE CS OFFLINE MOCK",
    bg=COLORS["panel"],
    fg=COLORS["text"],
    font=("Segoe UI", 18, "bold"),
).pack(anchor="w")
tk.Label(
    brand,
    text="Official paper view with local attempt tracking",
    bg=COLORS["panel"],
    fg=COLORS["muted"],
    font=("Segoe UI", 10),
).pack(anchor="w", pady=(3, 0))

header_controls = tk.Frame(header, bg=COLORS["panel"])
header_controls.pack(side="right", padx=18, pady=12)

tk.Label(
    header_controls,
    text="SESSION",
    bg=COLORS["panel"],
    fg=COLORS["muted"],
    font=("Segoe UI", 9, "bold"),
).grid(row=0, column=0, sticky="w")

session_var = tk.StringVar(value=paper["session"])
session_menu = ttk.Combobox(
    header_controls,
    textvariable=session_var,
    values=[item["session"] for item in papers],
    state="readonly",
    width=12,
)
session_menu.grid(row=1, column=0, padx=(0, 24), pady=(4, 0))
session_menu.bind("<<ComboboxSelected>>", lambda _: load_session(session_var.get()))

tk.Label(
    header_controls,
    text="TIME REMAINING",
    bg=COLORS["panel"],
    fg=COLORS["muted"],
    font=("Segoe UI", 9, "bold"),
).grid(row=0, column=1, sticky="e")

timer_label = tk.Label(
    header_controls,
    text="03:00:00",
    bg=COLORS["panel"],
    fg=COLORS["clock"],
    font=("Consolas", 20, "bold"),
)
timer_label.grid(row=1, column=1, sticky="e")

body = tk.Frame(root, bg=COLORS["app"])
body.pack(fill="both", expand=True, padx=20, pady=(0, 18))

viewer_card = tk.Frame(body, bg=COLORS["border"])
viewer_card.pack(side="left", fill="both", expand=True)

viewer = tk.Frame(viewer_card, bg=COLORS["paper"])
viewer.pack(fill="both", expand=True, padx=1, pady=1)

page_canvas = tk.Canvas(viewer, bg=COLORS["paper"], highlightthickness=0)
page_scroll = ttk.Scrollbar(viewer, orient="vertical", command=page_canvas.yview)
page_canvas.configure(yscrollcommand=page_scroll.set)
page_scroll.pack(side="right", fill="y")
page_canvas.pack(side="left", fill="both", expand=True)

page_canvas.bind("<Enter>", lambda _: page_canvas.focus_set())
page_canvas.bind(
    "<MouseWheel>",
    lambda event: page_canvas.yview_scroll(-1 if event.delta > 0 else 1, "units"),
)

sidebar_shell = tk.Frame(
    body,
    width=350,
    bg=COLORS["panel"],
    highlightbackground=COLORS["border"],
    highlightthickness=1,
)
sidebar_shell.pack(side="right", fill="y", padx=(14, 0))
sidebar_shell.pack_propagate(False)

sidebar_canvas = tk.Canvas(sidebar_shell, bg=COLORS["panel"], highlightthickness=0)
sidebar_scroll = ttk.Scrollbar(
    sidebar_shell, orient="vertical", command=sidebar_canvas.yview
)
sidebar_canvas.configure(yscrollcommand=sidebar_scroll.set)
sidebar_scroll.pack(side="right", fill="y")
sidebar_canvas.pack(side="left", fill="both", expand=True)

sidebar_body = tk.Frame(sidebar_canvas, bg=COLORS["panel"])
sidebar_window = sidebar_canvas.create_window((0, 0), window=sidebar_body, anchor="nw")

sidebar_body.bind(
    "<Configure>",
    lambda _: sidebar_canvas.configure(scrollregion=sidebar_canvas.bbox("all")),
)
sidebar_canvas.bind(
    "<Configure>",
    lambda event: sidebar_canvas.itemconfigure(sidebar_window, width=event.width),
)

sidebar_canvas.bind(
    "<Enter>",
    lambda _: sidebar_canvas.bind_all(
        "<MouseWheel>",
        lambda event: sidebar_canvas.yview_scroll(
            -1 if event.delta > 0 else 1, "units"
        ),
    ),
)
sidebar_canvas.bind("<Leave>", lambda _: sidebar_canvas.unbind_all("<MouseWheel>"))

question_label = tk.Label(
    sidebar_body,
    bg=COLORS["panel"],
    fg=COLORS["text"],
    font=("Segoe UI", 15, "bold"),
)
question_label.pack(anchor="w", padx=14, pady=(12, 2))

type_label = tk.Label(
    sidebar_body, bg=COLORS["panel"], fg="#93c5fd", font=("Segoe UI", 9, "bold")
)
type_label.pack(anchor="w", padx=14, pady=(0, 7))

progress_label = tk.Label(
    sidebar_body,
    text="0 answered  |  0 for review",
    bg=COLORS["panel"],
    fg=COLORS["muted"],
    font=("Segoe UI", 9),
)
progress_label.pack(anchor="w", padx=14)

progress_bar = ttk.Progressbar(
    sidebar_body,
    maximum=65,
    mode="determinate",
    style="Exam.Horizontal.TProgressbar",
)
progress_bar.pack(fill="x", padx=14, pady=(5, 5))

palette = tk.Frame(sidebar_body, bg=COLORS["panel"])
palette.pack(fill="x", padx=12, pady=(6, 6))

for number in range(1, 66):
    button = tk.Button(
        palette,
        text=str(number),
        width=3,
        height=1,
        fg="white",
        font=("Segoe UI", 8, "bold"),
        relief="flat",
        bd=0,
        padx=1,
        pady=1,
        cursor="hand2",
        command=lambda n=number: go_to(n),
    )
    button.grid(
        row=(number - 1) // 9,
        column=(number - 1) % 9,
        padx=1,
        pady=1,
    )
    palette_buttons.append(button)

response_frame = tk.LabelFrame(
    sidebar_body,
    text="  Your response  ",
    bg=COLORS["panel"],
    fg=COLORS["text"],
    font=("Segoe UI", 9, "bold"),
    bd=1,
    relief="solid",
    padx=9,
    pady=7,
)
response_frame.pack(fill="x", padx=14, pady=(9, 8))

actions = tk.Frame(sidebar_body, bg=COLORS["panel"])
actions.pack(fill="x", padx=14, pady=(0, 14))

ttk.Button(
    actions,
    text="Save & Next",
    command=save_and_next,
    style="Primary.TButton",
).pack(fill="x", pady=(0, 4))

ttk.Button(
    actions,
    text="Mark for Review",
    command=toggle_mark,
    style="Secondary.TButton",
).pack(fill="x", pady=3)

ttk.Button(
    actions,
    text="Previous",
    command=lambda: go_to(current - 1),
    style="Secondary.TButton",
).pack(fill="x", pady=3)

ttk.Button(
    actions,
    text="Submit Attempt",
    command=submit_attempt,
    style="Danger.TButton",
).pack(fill="x", pady=(4, 0))


def close_app():
    document.close()
    root.destroy()


root.protocol("WM_DELETE_WINDOW", close_app)
refresh()
tick()
root.mainloop()