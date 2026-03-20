import os
import threading
import tkinter as tk
from tkinter import ttk

import pandas as pd

from va_trout_scraper import CSV_FILE, update

COLUMNS = ("Date", "County", "Waterbody", "Category", "Species")


class TroutFinderApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("VA Trout Stocking Finder")
        self.root.geometry("960x600")
        self.root.minsize(720, 400)
        self.df: pd.DataFrame | None = None

        self._build_toolbar()
        self._build_search_bar()
        self._build_table()
        self._build_status_bar()

        self._load_csv()

    def _build_toolbar(self):
        toolbar = ttk.Frame(self.root, padding=(10, 6))
        toolbar.pack(fill=tk.X)

        ttk.Label(toolbar, text="VA Trout Stocking Finder", font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT)

        self.update_btn = ttk.Button(toolbar, text="Update Data", command=self._on_update)
        self.update_btn.pack(side=tk.RIGHT)

    def _build_search_bar(self):
        frame = ttk.Frame(self.root, padding=(10, 4))
        frame.pack(fill=tk.X)

        ttk.Label(frame, text="Search by:").pack(side=tk.LEFT, padx=(0, 6))

        self.search_mode = tk.StringVar(value="Waterbody")
        ttk.Radiobutton(frame, text="Waterbody", variable=self.search_mode, value="Waterbody").pack(side=tk.LEFT)
        ttk.Radiobutton(frame, text="County", variable=self.search_mode, value="County").pack(side=tk.LEFT, padx=(6, 12))

        self.search_var = tk.StringVar()
        entry = ttk.Entry(frame, textvariable=self.search_var, width=40)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        entry.bind("<Return>", lambda _: self._on_search())

        ttk.Button(frame, text="Search", command=self._on_search).pack(side=tk.LEFT)

    def _build_table(self):
        container = ttk.Frame(self.root)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(4, 0))

        scrollbar_y = ttk.Scrollbar(container, orient=tk.VERTICAL)
        scrollbar_x = ttk.Scrollbar(container, orient=tk.HORIZONTAL)

        self.tree = ttk.Treeview(
            container,
            columns=COLUMNS,
            show="headings",
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set,
        )

        scrollbar_y.config(command=self.tree.yview)
        scrollbar_x.config(command=self.tree.xview)

        col_widths = {"Date": 100, "County": 160, "Waterbody": 280, "Category": 70, "Species": 220}
        for col in COLUMNS:
            self.tree.heading(col, text=col, command=lambda c=col: self._sort_column(c))
            self.tree.column(col, width=col_widths.get(col, 120), minwidth=60)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")

        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        self._sort_reverse: dict[str, bool] = {c: False for c in COLUMNS}

    def _build_status_bar(self):
        self.status_var = tk.StringVar(value="Ready")
        status = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=(10, 4))
        status.pack(fill=tk.X, side=tk.BOTTOM)

    def _load_csv(self):
        if not os.path.exists(CSV_FILE):
            self.df = None
            self.status_var.set(f"No data file found. Click 'Update Data' to download stocking records.")
            return
        self.df = pd.read_csv(CSV_FILE)
        self.df["Date"] = pd.to_datetime(self.df["Date"])
        self.status_var.set(f"Loaded {len(self.df)} records from {CSV_FILE}")

    def _populate_table(self, df: pd.DataFrame):
        self.tree.delete(*self.tree.get_children())
        for _, row in df.iterrows():
            date_str = row["Date"].strftime("%Y-%m-%d") if hasattr(row["Date"], "strftime") else str(row["Date"])
            self.tree.insert("", tk.END, values=(
                date_str,
                row["County"],
                row["Waterbody"],
                row["Category"],
                row["Species"],
            ))

    def _sort_column(self, col: str):
        self._sort_reverse[col] = not self._sort_reverse[col]
        items = [(self.tree.set(iid, col), iid) for iid in self.tree.get_children()]
        items.sort(reverse=self._sort_reverse[col])
        for idx, (_, iid) in enumerate(items):
            self.tree.move(iid, "", idx)

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
            self.status_var.set(f"No results for {mode.lower()} matching '{query}'.")
            return

        if mode == "Waterbody":
            results = filtered.groupby("Waterbody", sort=False).head(3)
            waters = results["Waterbody"].nunique()
            self._populate_table(results)
            self.status_var.set(
                f"Showing last 3 stockings for {waters} waterbody(s) matching '{query}'"
            )
        else:
            most_recent = filtered.drop_duplicates(subset="Waterbody", keep="first")
            self._populate_table(most_recent)
            self.status_var.set(f"Showing {len(most_recent)} result(s) for county matching '{query}'")

    def _on_update(self):
        self.update_btn.config(state=tk.DISABLED)
        self.status_var.set("Updating stocking data... this may take a moment.")
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
            self.status_var.set(f"Update complete. {len(self.df)} records loaded.")


def main():
    root = tk.Tk()
    TroutFinderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
