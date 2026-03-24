import os
import threading
import tkinter as tk
from tkinter import ttk
from datetime import datetime

import pandas as pd

from va_trout_scraper import CSV_FILE, update as update_csv

CATEGORY_MEDIAN_DAYS = {
    "A": 26, "B": 37, "C": 64, "DH": 146, "CR": 48, "+": 3, "U": 34,
}
MAX_SEASON_GAP = 120
MIN_STOCKINGS_FOR_OWN_CADENCE = 3
INACTIVE_THRESHOLD_DAYS = 365

COLUMNS = (
    "Overdue Score", "Days Until", "Predicted Date", "County", "Waterbody",
    "Category", "Avg Interval", "Last Stocked", "Typical Days",
)

TAG_COLORS = {
    "overdue_high": {"background": "#FDECEC", "foreground": "#B91C1C"},
    "overdue_med":  {"background": "#FFF7ED", "foreground": "#C2410C"},
    "due_soon":     {"background": "#FEFCE8", "foreground": "#A16207"},
    "upcoming":     {"background": "#F0FDF4", "foreground": "#15803D"},
    "future":       {"background": "#FFFFFF", "foreground": "#334155"},
}


def build_predictions(df: pd.DataFrame) -> pd.DataFrame:
    today = pd.Timestamp(datetime.now().date())

    records = []
    for (wb, county, cat), grp in df.groupby(["Waterbody", "County", "Category"]):
        dates = grp["Date"].sort_values()
        last_stocked = dates.iloc[-1]

        if (today - last_stocked).days > INACTIVE_THRESHOLD_DAYS:
            continue

        diffs = dates.diff().dropna().dt.days
        in_season = diffs[diffs <= MAX_SEASON_GAP]

        if len(in_season) >= MIN_STOCKINGS_FOR_OWN_CADENCE:
            median_interval = int(in_season.median())
        else:
            median_interval = CATEGORY_MEDIAN_DAYS.get(cat, 30)

        predicted = last_stocked + pd.Timedelta(days=median_interval)
        days_until = (predicted - today).days
        days_since = (today - last_stocked).days
        overdue = round(days_since / median_interval, 2) if median_interval > 0 else 0.0

        day_counts = dates.dt.day_name().value_counts()
        top_days = ", ".join(day_counts.head(2).index.tolist())

        records.append({
            "Overdue Score": overdue,
            "Days Until": days_until,
            "Predicted Date": predicted.strftime("%Y-%m-%d"),
            "County": county,
            "Waterbody": wb,
            "Category": cat,
            "Avg Interval": f"{median_interval}d",
            "Last Stocked": last_stocked.strftime("%Y-%m-%d"),
            "Typical Days": top_days,
        })

    result = pd.DataFrame(records)
    if not result.empty:
        result = result.sort_values("Overdue Score", ascending=False).reset_index(drop=True)
    return result


def _overdue_tag(score: float, days_until: int) -> str:
    if score >= 1.5:
        return "overdue_high"
    if score >= 1.0:
        return "overdue_med"
    if days_until <= 7:
        return "due_soon"
    if days_until <= 30:
        return "upcoming"
    return "future"


class StockingPredictApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("VA Trout Stocking Predictor")
        self.root.geometry("1200x680")
        self.root.minsize(960, 440)
        self.df: pd.DataFrame | None = None
        self.predictions: pd.DataFrame | None = None

        self._apply_theme()
        self._build_toolbar()
        self._build_filter_bar()
        self._build_table()
        self._build_status_bar()

        self._load_and_predict()

    def _apply_theme(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")

        style.configure("Title.TLabel", font=("Segoe UI", 15, "bold"), foreground="#1E293B")
        style.configure("TButton", font=("Segoe UI", 10), padding=4)
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), foreground="#FFFFFF", background="#2563EB")
        style.map("Accent.TButton",
                  background=[("active", "#1D4ED8"), ("disabled", "#94A3B8")],
                  foreground=[("disabled", "#E2E8F0")])
        style.configure("Treeview", font=("Segoe UI", 10), rowheight=26)
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), foreground="#475569")
        style.configure("TLabel", font=("Segoe UI", 10))
        style.configure("Status.TLabel", font=("Segoe UI", 9), background="#F1F5F9", foreground="#475569")

    def _build_toolbar(self):
        toolbar = ttk.Frame(self.root, padding=(12, 8))
        toolbar.pack(fill=tk.X)

        ttk.Label(toolbar, text="VA Trout Stocking Predictor", style="Title.TLabel").pack(side=tk.LEFT)

        btn_frame = ttk.Frame(toolbar)
        btn_frame.pack(side=tk.RIGHT)

        self.update_btn = ttk.Button(btn_frame, text="Update Data", style="Accent.TButton", command=self._on_update)
        self.update_btn.pack(side=tk.LEFT, padx=(0, 6))

        ttk.Button(btn_frame, text="Refresh Predictions", command=self._refresh).pack(side=tk.LEFT)

    def _build_filter_bar(self):
        frame = ttk.Frame(self.root, padding=(12, 4))
        frame.pack(fill=tk.X)

        ttk.Label(frame, text="Search:").pack(side=tk.LEFT, padx=(0, 4))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(frame, textvariable=self.search_var, width=28)
        search_entry.pack(side=tk.LEFT, padx=(0, 12))
        search_entry.bind("<KeyRelease>", lambda _: self._apply_filters())

        ttk.Label(frame, text="County:").pack(side=tk.LEFT, padx=(0, 4))
        self.county_var = tk.StringVar(value="All")
        self.county_combo = ttk.Combobox(frame, textvariable=self.county_var, width=22, state="readonly")
        self.county_combo.pack(side=tk.LEFT, padx=(0, 12))
        self.county_combo.bind("<<ComboboxSelected>>", lambda _: self._apply_filters())

        ttk.Label(frame, text="Category:").pack(side=tk.LEFT, padx=(0, 4))
        self.cat_var = tk.StringVar(value="All")
        self.cat_combo = ttk.Combobox(frame, textvariable=self.cat_var, width=10, state="readonly")
        self.cat_combo.pack(side=tk.LEFT, padx=(0, 12))
        self.cat_combo.bind("<<ComboboxSelected>>", lambda _: self._apply_filters())

        self.overdue_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, text="Overdue only", variable=self.overdue_var, command=self._apply_filters).pack(side=tk.LEFT, padx=(0, 12))

        ttk.Button(frame, text="Clear Filters", command=self._clear_filters).pack(side=tk.RIGHT)

    def _build_table(self):
        container = ttk.Frame(self.root)
        container.pack(fill=tk.BOTH, expand=True, padx=12, pady=(4, 0))

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

        col_widths = {
            "Overdue Score": 100, "Days Until": 85, "Predicted Date": 105,
            "County": 155, "Waterbody": 240, "Category": 70,
            "Avg Interval": 90, "Last Stocked": 100, "Typical Days": 130,
        }
        for col in COLUMNS:
            self.tree.heading(col, text=col, command=lambda c=col: self._sort_column(c))
            self.tree.column(col, width=col_widths.get(col, 100), minwidth=50)

        for tag, colors in TAG_COLORS.items():
            self.tree.tag_configure(tag, **colors)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")

        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        self._sort_reverse: dict[str, bool] = {c: False for c in COLUMNS}

    def _build_status_bar(self):
        self.status_var = tk.StringVar(value="Loading...")
        status = ttk.Label(
            self.root, textvariable=self.status_var,
            style="Status.TLabel", relief=tk.SUNKEN, anchor=tk.W, padding=(12, 5),
        )
        status.pack(fill=tk.X, side=tk.BOTTOM)

    def _load_and_predict(self):
        if not os.path.exists(CSV_FILE):
            self.status_var.set(
                f"No data file found ({CSV_FILE}). Click 'Update Data' to download stocking records."
            )
            return

        self.df = pd.read_csv(CSV_FILE)
        self.df["Date"] = pd.to_datetime(self.df["Date"])
        self._refresh()

    def _refresh(self):
        if self.df is None:
            return
        self.predictions = build_predictions(self.df)
        self._update_filter_options()
        self._apply_filters()

    def _update_filter_options(self):
        if self.predictions is None or self.predictions.empty:
            return
        counties = sorted(self.predictions["County"].unique())
        self.county_combo["values"] = ["All"] + counties
        cats = sorted(self.predictions["Category"].unique())
        self.cat_combo["values"] = ["All"] + cats

    def _apply_filters(self):
        if self.predictions is None:
            return

        filtered = self.predictions.copy()

        query = self.search_var.get().strip()
        if query:
            mask = (
                filtered["Waterbody"].str.contains(query, case=False, na=False)
                | filtered["County"].str.contains(query, case=False, na=False)
            )
            filtered = filtered[mask]

        county = self.county_var.get()
        if county != "All":
            filtered = filtered[filtered["County"] == county]

        cat = self.cat_var.get()
        if cat != "All":
            filtered = filtered[filtered["Category"] == cat]

        if self.overdue_var.get():
            filtered = filtered[filtered["Overdue Score"] >= 1.0]

        self._populate_table(filtered)

        overdue_count = len(filtered[filtered["Overdue Score"] >= 1.0]) if not filtered.empty else 0
        due_soon = len(filtered[filtered["Days Until"].between(-999, 7)]) if not filtered.empty else 0
        self.status_var.set(
            f"{len(filtered)} waterbodies shown "
            f"({overdue_count} overdue, {due_soon} due within 7 days)  "
            f"\u2022  {len(self.predictions)} total active  "
            f"\u2022  {len(self.df):,} historical records"
        )

    def _clear_filters(self):
        self.search_var.set("")
        self.county_var.set("All")
        self.cat_var.set("All")
        self.overdue_var.set(False)
        self._apply_filters()

    def _populate_table(self, df: pd.DataFrame):
        self.tree.delete(*self.tree.get_children())
        for _, row in df.iterrows():
            score = row["Overdue Score"]
            days_until = row["Days Until"]
            tag = _overdue_tag(float(score), int(days_until))
            self.tree.insert(
                "", tk.END,
                values=tuple(row[c] for c in COLUMNS),
                tags=(tag,),
            )

    def _sort_column(self, col: str):
        self._sort_reverse[col] = not self._sort_reverse[col]
        items = [(self.tree.set(iid, col), iid) for iid in self.tree.get_children()]
        try:
            items.sort(key=lambda x: float(x[0]), reverse=self._sort_reverse[col])
        except ValueError:
            items.sort(key=lambda x: x[0], reverse=self._sort_reverse[col])
        for idx, (_, iid) in enumerate(items):
            self.tree.move(iid, "", idx)

    def _on_update(self):
        self.update_btn.config(state=tk.DISABLED)
        self.status_var.set("Updating stocking data from DWR website... this may take a moment.")
        threading.Thread(target=self._run_update, daemon=True).start()

    def _run_update(self):
        try:
            update_csv(CSV_FILE)
            self.root.after(0, self._update_finished, None)
        except Exception as exc:
            self.root.after(0, self._update_finished, str(exc))

    def _update_finished(self, error: str | None):
        self.update_btn.config(state=tk.NORMAL)
        if error:
            self.status_var.set(f"Update failed: {error}")
        else:
            self.df = pd.read_csv(CSV_FILE)
            self.df["Date"] = pd.to_datetime(self.df["Date"])
            self._refresh()


def main():
    root = tk.Tk()
    StockingPredictApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
