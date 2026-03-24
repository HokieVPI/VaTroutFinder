import os
import threading
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import ttk

import pandas as pd

from va_trout_scraper import CSV_FILE, update

COLUMNS = ("Date", "County", "Waterbody", "Category", "Species")

BG = "#1e1e2e"
SURFACE = "#2a2a3d"
ACCENT = "#7c8aff"
ACCENT_HOVER = "#9aa4ff"
TEXT = "#e0e0e8"
TEXT_DIM = "#8888a0"
ENTRY_BG = "#33334a"
TABLE_BG = "#242438"
TABLE_ALT = "#2c2c42"
TABLE_SELECT = "#3d3d6b"
BORDER = "#3a3a52"
SUCCESS = "#6bcf7f"
ERROR = "#ff6b6b"


def apply_theme(root: tk.Tk):
    root.configure(bg=BG)
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(".", background=BG, foreground=TEXT, font=("Segoe UI", 10))
    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG, foreground=TEXT)
    style.configure("Title.TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 16, "bold"))
    style.configure("Dim.TLabel", background=BG, foreground=TEXT_DIM, font=("Segoe UI", 9))
    style.configure("Status.TLabel", background=SURFACE, foreground=TEXT_DIM, font=("Segoe UI", 9), padding=(12, 6))
    style.configure("TRadiobutton", background=BG, foreground=TEXT, font=("Segoe UI", 10))
    style.map("TRadiobutton", background=[("active", BG)])

    style.configure("Accent.TButton",
                     background=ACCENT, foreground="#ffffff",
                     font=("Segoe UI", 10, "bold"), padding=(16, 6), borderwidth=0)
    style.map("Accent.TButton",
              background=[("active", ACCENT_HOVER), ("disabled", BORDER)],
              foreground=[("disabled", TEXT_DIM)])

    style.configure("Flat.TButton",
                     background=SURFACE, foreground=TEXT,
                     font=("Segoe UI", 10), padding=(14, 6), borderwidth=0)
    style.map("Flat.TButton", background=[("active", BORDER)])

    style.configure("TEntry", fieldbackground=ENTRY_BG, foreground=TEXT,
                     insertcolor=TEXT, borderwidth=0, padding=(8, 6))

    style.configure("Treeview",
                     background=TABLE_BG, foreground=TEXT, fieldbackground=TABLE_BG,
                     rowheight=28, borderwidth=0, font=("Segoe UI", 10))
    style.configure("Treeview.Heading",
                     background=SURFACE, foreground=TEXT,
                     font=("Segoe UI", 10, "bold"), borderwidth=0, padding=(8, 4))
    style.map("Treeview",
              background=[("selected", TABLE_SELECT)],
              foreground=[("selected", TEXT)])
    style.map("Treeview.Heading", background=[("active", BORDER)])

    style.configure("TScrollbar", background=SURFACE, troughcolor=BG,
                     borderwidth=0, arrowsize=0)
    style.map("TScrollbar", background=[("active", BORDER)])


class TroutFinderApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("VA Trout Stocking Finder")
        self.root.geometry("1020x640")
        self.root.minsize(780, 440)
        self.df: pd.DataFrame | None = None

        apply_theme(root)

        self._build_header()
        self._build_search_bar()
        self._build_table()
        self._build_status_bar()

        self._load_csv()

    def _build_header(self):
        header = ttk.Frame(self.root, padding=(16, 12, 16, 4))
        header.pack(fill=tk.X)

        left = ttk.Frame(header)
        left.pack(side=tk.LEFT)
        ttk.Label(left, text="VA Trout Stocking Finder", style="Title.TLabel").pack(anchor=tk.W)
        ttk.Label(left, text="Search Virginia DWR stocking records", style="Dim.TLabel").pack(anchor=tk.W)

        self.update_btn = ttk.Button(header, text="Update Data", style="Accent.TButton", command=self._on_update)
        self.update_btn.pack(side=tk.RIGHT, pady=(2, 0))

    def _build_search_bar(self):
        outer = ttk.Frame(self.root, padding=(16, 8, 16, 4))
        outer.pack(fill=tk.X)

        card = tk.Frame(outer, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill=tk.X)
        inner = ttk.Frame(card, padding=(12, 10))
        inner.pack(fill=tk.X)
        inner.configure(style="Card.TFrame")
        ttk.Style(self.root).configure("Card.TFrame", background=SURFACE)

        mode_frame = ttk.Frame(inner)
        mode_frame.pack(side=tk.LEFT, padx=(0, 12))
        ttk.Label(mode_frame, text="Search by", style="Dim.TLabel").pack(anchor=tk.W)

        radio_frame = ttk.Frame(mode_frame)
        radio_frame.pack(anchor=tk.W)
        self.search_mode = tk.StringVar(value="Waterbody")
        ttk.Radiobutton(radio_frame, text="Waterbody", variable=self.search_mode, value="Waterbody").pack(side=tk.LEFT)
        ttk.Radiobutton(radio_frame, text="County", variable=self.search_mode, value="County").pack(side=tk.LEFT, padx=(8, 0))

        sep = tk.Frame(inner, bg=BORDER, width=1)
        sep.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12), pady=2)

        entry_frame = ttk.Frame(inner)
        entry_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.search_var = tk.StringVar()
        self.entry = tk.Entry(
            entry_frame, textvariable=self.search_var, font=("Segoe UI", 11),
            bg=ENTRY_BG, fg=TEXT, insertbackground=TEXT, relief=tk.FLAT,
            highlightbackground=BORDER, highlightthickness=1, highlightcolor=ACCENT,
        )
        self.entry.pack(fill=tk.X, ipady=4)
        self.entry.bind("<Return>", lambda _: self._on_search())

        ttk.Button(inner, text="Search", style="Flat.TButton", command=self._on_search).pack(side=tk.LEFT)

    def _build_table(self):
        container = ttk.Frame(self.root, padding=(16, 8, 16, 0))
        container.pack(fill=tk.BOTH, expand=True)

        table_frame = tk.Frame(container, bg=BORDER, highlightbackground=BORDER, highlightthickness=1)
        table_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL)
        scrollbar_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL)

        self.tree = ttk.Treeview(
            table_frame, columns=COLUMNS, show="headings",
            yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set,
        )
        scrollbar_y.config(command=self.tree.yview)
        scrollbar_x.config(command=self.tree.xview)

        col_widths = {"Date": 100, "County": 160, "Waterbody": 300, "Category": 70, "Species": 240}
        for col in COLUMNS:
            self.tree.heading(col, text=col, command=lambda c=col: self._sort_column(c))
            self.tree.column(col, width=col_widths.get(col, 120), minwidth=60)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")

        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        self.tree.tag_configure("oddrow", background=TABLE_ALT)
        self._sort_reverse: dict[str, bool] = {c: False for c in COLUMNS}

    def _build_status_bar(self):
        self.status_var = tk.StringVar(value="Ready")
        status = ttk.Label(self.root, textvariable=self.status_var, style="Status.TLabel")
        status.pack(fill=tk.X, side=tk.BOTTOM)

    def _load_csv(self):
        if not os.path.exists(CSV_FILE):
            self.df = None
            self.status_var.set("No data file found. Click 'Update Data' to download stocking records.")
            return
        self.df = pd.read_csv(CSV_FILE)
        self.df["Date"] = pd.to_datetime(self.df["Date"])
        self._show_recent()

    def _show_recent(self):
        cutoff = pd.Timestamp(datetime.now().date()) - pd.Timedelta(days=10)
        recent = self.df[self.df["Date"] >= cutoff].sort_values("Date", ascending=False)
        self._populate_table(recent)
        self.status_var.set(f"Stockings in the last 10 days ({len(recent)} records)")

    def _populate_table(self, df: pd.DataFrame):
        self.tree.delete(*self.tree.get_children())
        for i, (_, row) in enumerate(df.iterrows()):
            date_str = row["Date"].strftime("%Y-%m-%d") if hasattr(row["Date"], "strftime") else str(row["Date"])
            tag = ("oddrow",) if i % 2 else ()
            self.tree.insert("", tk.END, values=(
                date_str, row["County"], row["Waterbody"], row["Category"], row["Species"],
            ), tags=tag)

    def _sort_column(self, col: str):
        self._sort_reverse[col] = not self._sort_reverse[col]
        items = [(self.tree.set(iid, col), iid) for iid in self.tree.get_children()]
        items.sort(reverse=self._sort_reverse[col])
        for idx, (_, iid) in enumerate(items):
            self.tree.move(iid, "", idx)
        for i, iid in enumerate(self.tree.get_children()):
            self.tree.item(iid, tags=("oddrow",) if i % 2 else ())

    def _on_search(self):
        if self.df is None:
            self.status_var.set("No data loaded. Click 'Update Data' first.")
            return

        query = self.search_var.get().strip()
        if not query:
            self.status_var.set("Enter a search term.")
            return

        mode = self.search_mode.get()
        mask = self.df[mode].str.contains(query, case=False, na=False)
        filtered = self.df[mask].sort_values("Date", ascending=False)

        if filtered.empty:
            self.tree.delete(*self.tree.get_children())
            self.status_var.set(f"No results for {mode.lower()} matching \"{query}\"")
            return

        if mode == "Waterbody":
            results = filtered.groupby("Waterbody", sort=False).head(3)
            waters = results["Waterbody"].nunique()
            self._populate_table(results)
            self.status_var.set(f"Last 3 stockings for {waters} waterbody(s) matching \"{query}\"")
        else:
            most_recent = filtered.drop_duplicates(subset="Waterbody", keep="first")
            self._populate_table(most_recent)
            self.status_var.set(f"{len(most_recent)} waterbody(s) in counties matching \"{query}\"")

    def _on_update(self):
        self.update_btn.config(state=tk.DISABLED)
        self.status_var.set("Updating stocking data...")
        threading.Thread(target=self._run_update, daemon=True).start()

    def _run_update(self):
        try:
            update(CSV_FILE)
            self.root.after(0, self._update_finished, None)
        except Exception as exc:
            self.root.after(0, self._update_finished, str(exc))

    def _update_finished(self, error: str | None):
        self.update_btn.config(state=tk.NORMAL)
        if error:
            self.status_var.set(f"Update failed: {error}")
        else:
            self._load_csv()
            self.status_var.set(f"Update complete. {len(self.df):,} records loaded.")


def main():
    root = tk.Tk()
    TroutFinderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
