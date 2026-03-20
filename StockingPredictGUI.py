import os
import tkinter as tk
from tkinter import ttk
from datetime import datetime

import pandas as pd

from va_trout_scraper import CSV_FILE

CATEGORY_MEDIAN_DAYS = {
    "A": 26, "B": 37, "C": 64, "DH": 146, "CR": 48, "+": 3, "U": 34,
}
MAX_SEASON_GAP = 120
MIN_STOCKINGS_FOR_OWN_CADENCE = 3
INACTIVE_THRESHOLD_DAYS = 365

COLUMNS = (
    "Overdue Score", "Predicted Date", "County", "Waterbody",
    "Category", "Avg Interval", "Last Stocked", "Typical Days",
)


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
        days_since = (today - last_stocked).days
        overdue = round(days_since / median_interval, 2) if median_interval > 0 else 0.0

        day_counts = dates.dt.day_name().value_counts()
        top_days = ", ".join(day_counts.head(2).index.tolist())

        records.append({
            "Overdue Score": overdue,
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


class StockingPredictApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("VA Trout Stocking Predictor")
        self.root.geometry("1100x620")
        self.root.minsize(900, 400)
        self.df: pd.DataFrame | None = None
        self.predictions: pd.DataFrame | None = None

        self._build_toolbar()
        self._build_table()
        self._build_status_bar()

        self._load_and_predict()

    def _build_toolbar(self):
        toolbar = ttk.Frame(self.root, padding=(10, 6))
        toolbar.pack(fill=tk.X)

        ttk.Label(
            toolbar, text="VA Trout Stocking Predictor", font=("Segoe UI", 14, "bold"),
        ).pack(side=tk.LEFT)

        ttk.Button(toolbar, text="Refresh", command=self._refresh).pack(side=tk.RIGHT)

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

        col_widths = {
            "Overdue Score": 95, "Predicted Date": 100, "County": 150,
            "Waterbody": 240, "Category": 65, "Avg Interval": 85,
            "Last Stocked": 100, "Typical Days": 130,
        }
        for col in COLUMNS:
            self.tree.heading(col, text=col, command=lambda c=col: self._sort_column(c))
            self.tree.column(col, width=col_widths.get(col, 100), minwidth=50)

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
            relief=tk.SUNKEN, anchor=tk.W, padding=(10, 4),
        )
        status.pack(fill=tk.X, side=tk.BOTTOM)

    def _load_and_predict(self):
        if not os.path.exists(CSV_FILE):
            self.status_var.set(
                f"No data file found ({CSV_FILE}). Run 'python va_trout_scraper.py update' first."
            )
            return

        self.df = pd.read_csv(CSV_FILE)
        self.df["Date"] = pd.to_datetime(self.df["Date"])
        self._refresh()

    def _refresh(self):
        if self.df is None:
            return
        self.predictions = build_predictions(self.df)
        self._populate_table(self.predictions)
        self.status_var.set(
            f"{len(self.predictions)} active waterbodies ranked by overdue score  "
            f"(based on {len(self.df)} historical records)"
        )

    def _populate_table(self, df: pd.DataFrame):
        self.tree.delete(*self.tree.get_children())
        for _, row in df.iterrows():
            self.tree.insert("", tk.END, values=tuple(row[c] for c in COLUMNS))

    def _sort_column(self, col: str):
        self._sort_reverse[col] = not self._sort_reverse[col]
        items = [(self.tree.set(iid, col), iid) for iid in self.tree.get_children()]
        try:
            items.sort(key=lambda x: float(x[0]), reverse=self._sort_reverse[col])
        except ValueError:
            items.sort(key=lambda x: x[0], reverse=self._sort_reverse[col])
        for idx, (_, iid) in enumerate(items):
            self.tree.move(iid, "", idx)


def main():
    root = tk.Tk()
    StockingPredictApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
