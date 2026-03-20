import argparse
import re
import sys
from datetime import datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://dwr.virginia.gov/fishing/trout-stocking-schedule/"

BRACKET_ANNOTATION_RE = re.compile(r"\[.*?\]")


def parse_user_date(date_str: str) -> str:
    """Convert M/D/YYYY to YYYY-MM-DD for the URL query parameter."""
    dt = datetime.strptime(date_str.strip(), "%m/%d/%Y")
    return dt.strftime("%Y-%m-%d")


def clean_waterbody(cell) -> str:
    """Extract the waterbody name, stripping bracket annotations and extra whitespace."""
    for tag in cell.find_all("a"):
        tag.decompose()
    raw = cell.get_text(separator=" ").strip()
    cleaned = BRACKET_ANNOTATION_RE.sub("", raw)
    return " ".join(cleaned.split()).strip().rstrip("(").strip()


def extract_species(cell) -> str:
    """Join all <li> items (or fallback to cell text) into a comma-separated string."""
    items = cell.find_all("li")
    if items:
        return ", ".join(li.get_text(strip=True) for li in items)
    return cell.get_text(strip=True)


def scrape(start_date: str, end_date: str, output_file: str) -> None:
    start_iso = parse_user_date(start_date)
    end_iso = parse_user_date(end_date)

    print(f"Fetching stocking data from {start_iso} to {end_iso} ...")
    resp = requests.get(
        BASE_URL,
        params={"start_date": start_iso, "end_date": end_iso},
        timeout=60,
    )
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    table = None
    for t in soup.find_all("table"):
        header = t.find("th", class_="date_stocked")
        if header:
            table = t
            break
    if not table:
        print("ERROR: Could not find the stocking table on the page.")
        sys.exit(1)

    rows = []
    for tr in table.find_all("tr")[1:]:  # skip header row
        cells = tr.find_all("td")
        if len(cells) < 5:
            continue

        date_text = cells[0].get_text(strip=True)
        try:
            parsed_date = datetime.strptime(date_text, "%B %d, %Y").strftime("%Y-%m-%d")
        except ValueError:
            parsed_date = date_text

        county = cells[1].get_text(strip=True)
        waterbody = clean_waterbody(cells[2])
        category = cells[3].get_text(strip=True)
        species = extract_species(cells[4])

        rows.append({
            "Date": parsed_date,
            "County": county,
            "Waterbody": waterbody,
            "Category": category,
            "Species": species,
        })

    if not rows:
        print("WARNING: No stocking records found for that date range.")
        return

    df = pd.DataFrame(rows)
    df.to_csv(output_file, index=False)
    print(f"Saved {len(df)} records to {output_file}")


def search(csv_file: str, waterbody: str | None, county: str | None) -> None:
    try:
        df = pd.read_csv(csv_file)
    except FileNotFoundError:
        print(f"ERROR: CSV file '{csv_file}' not found. Run the 'scrape' command first.")
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

    scrape_parser = subparsers.add_parser("scrape", help="Scrape stocking data for a date range")
    scrape_parser.add_argument("--start", required=True, help="Start date (M/D/YYYY)")
    scrape_parser.add_argument("--end", required=True, help="End date (M/D/YYYY)")
    scrape_parser.add_argument("--output", default="trout_stocking.csv", help="Output CSV filename")

    search_parser = subparsers.add_parser("search", help="Search saved CSV for stocking info")
    search_parser.add_argument("--waterbody", help="Search by waterbody name (partial match)")
    search_parser.add_argument("--county", help="Search by county name (partial match)")
    search_parser.add_argument("--file", default="trout_stocking.csv", help="CSV file to search")

    args = parser.parse_args()

    if args.command == "scrape":
        scrape(args.start, args.end, args.output)
    elif args.command == "search":
        search(args.file, args.waterbody, args.county)


if __name__ == "__main__":
    main()
