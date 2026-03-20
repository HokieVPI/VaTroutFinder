import argparse
import os
import re
import sys
from datetime import datetime, timedelta

import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://dwr.virginia.gov/fishing/trout-stocking-schedule/"
HISTORY_START = "2016-10-01"
OVERLAP_DAYS = 3
CSV_FILE = "trout_stocking.csv"

BRACKET_ANNOTATION_RE = re.compile(r"\[.*?\]")


def clean_waterbody(cell) -> str:
    for tag in cell.find_all("a"):
        tag.decompose()
    raw = cell.get_text(separator=" ").strip()
    cleaned = BRACKET_ANNOTATION_RE.sub("", raw)
    return " ".join(cleaned.split()).strip().rstrip("(").strip()


def extract_species(cell) -> str:
    items = cell.find_all("li")
    if items:
        return ", ".join(li.get_text(strip=True) for li in items)
    return cell.get_text(strip=True)


def fetch_stocking_data(start_iso: str, end_iso: str) -> pd.DataFrame:
    """Fetch stocking records from the DWR website for the given ISO date range."""
    print(f"Fetching stocking data from {start_iso} to {end_iso} ...")
    resp = requests.get(
        BASE_URL,
        params={"start_date": start_iso, "end_date": end_iso},
        timeout=120,
    )
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    table = None
    for t in soup.find_all("table"):
        if t.find("th", class_="date_stocked"):
            table = t
            break
    if not table:
        print("ERROR: Could not find the stocking table on the page.")
        sys.exit(1)

    rows = []
    for tr in table.find_all("tr")[1:]:
        cells = tr.find_all("td")
        if len(cells) < 5:
            continue

        date_text = cells[0].get_text(strip=True)
        try:
            parsed_date = datetime.strptime(date_text, "%B %d, %Y").strftime("%Y-%m-%d")
        except ValueError:
            parsed_date = date_text

        rows.append({
            "Date": parsed_date,
            "County": cells[1].get_text(strip=True),
            "Waterbody": clean_waterbody(cells[2]),
            "Category": cells[3].get_text(strip=True),
            "Species": extract_species(cells[4]),
        })

    return pd.DataFrame(rows)


def update(csv_file: str) -> None:
    today = datetime.now().strftime("%Y-%m-%d")

    if os.path.exists(csv_file):
        existing = pd.read_csv(csv_file)
        latest = pd.to_datetime(existing["Date"]).max()
        start = (latest - timedelta(days=OVERLAP_DAYS)).strftime("%Y-%m-%d")
        print(f"Existing CSV has {len(existing)} records through {latest.strftime('%Y-%m-%d')}.")

        new_data = fetch_stocking_data(start, today)
        if new_data.empty:
            print("No new records found.")
            return

        combined = pd.concat([existing, new_data], ignore_index=True)
        combined = combined.drop_duplicates(subset=["Date", "County", "Waterbody", "Category", "Species"])
        combined = combined.sort_values("Date", ascending=False).reset_index(drop=True)
        diff = len(combined) - len(existing)
        combined.to_csv(csv_file, index=False)
        if diff > 0:
            print(f"Added {diff} new records. Total: {len(combined)} records in {csv_file}")
        else:
            print(f"Already up to date. Total: {len(combined)} records in {csv_file}")
    else:
        print(f"No existing CSV found. Performing full historical scrape from {HISTORY_START} ...")
        df = fetch_stocking_data(HISTORY_START, today)
        if df.empty:
            print("WARNING: No stocking records found.")
            return
        df = df.sort_values("Date", ascending=False).reset_index(drop=True)
        df.to_csv(csv_file, index=False)
        print(f"Saved {len(df)} records to {csv_file}")


def search(csv_file: str, waterbody: str | None, county: str | None) -> None:
    try:
        df = pd.read_csv(csv_file)
    except FileNotFoundError:
        print(f"ERROR: CSV file '{csv_file}' not found. Run the 'update' command first.")
        sys.exit(1)

    df["Date"] = pd.to_datetime(df["Date"])

    if waterbody:
        mask = df["Waterbody"].str.contains(waterbody, case=False, na=False)
        filtered = df[mask].sort_values("Date", ascending=False)
        if filtered.empty:
            print(f"No results found for waterbody matching '{waterbody}'.")
            return
        most_recent = filtered.drop_duplicates(subset="Waterbody", keep="first")
        print(f"\nMost recent stocking(s) matching '{waterbody}':\n")
        print(most_recent.to_string(index=False))

    elif county:
        mask = df["County"].str.contains(county, case=False, na=False)
        filtered = df[mask].sort_values("Date", ascending=False)
        if filtered.empty:
            print(f"No results found for county matching '{county}'.")
            return
        most_recent = filtered.drop_duplicates(subset="Waterbody", keep="first")
        print(f"\nMost recent stocking(s) in counties matching '{county}':\n")
        print(most_recent.to_string(index=False))

    else:
        print("ERROR: Provide --waterbody or --county to search.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Scrape and search VA DWR trout stocking data."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("update", help="Update CSV with latest stocking data (full scrape if no CSV exists)")

    search_parser = subparsers.add_parser("search", help="Search saved CSV for stocking info")
    search_parser.add_argument("--waterbody", help="Search by waterbody name (partial match)")
    search_parser.add_argument("--county", help="Search by county name (partial match)")
    search_parser.add_argument("--file", default=CSV_FILE, help="CSV file to search")

    args = parser.parse_args()

    if args.command == "update":
        update(CSV_FILE)
    elif args.command == "search":
        search(args.file, args.waterbody, args.county)


if __name__ == "__main__":
    main()
