# VA Trout Stocking Finder

A command-line tool that scrapes the [Virginia DWR Daily Trout Stocking Schedule](https://dwr.virginia.gov/fishing/trout-stocking-schedule/) and saves the data to a CSV file. You can then search the CSV to find the most recent stocking for any waterbody or county.

## Setup

Install the required Python packages:

```
pip install -r requirements.txt
```

This installs `requests`, `beautifulsoup4`, and `pandas`.

## Commands

The tool has two commands: `update` and `search`.

### Update

Fetches the latest stocking data and saves it to `trout_stocking.csv`.

```
python va_trout_scraper.py update
```

- **First run (no CSV exists):** performs a full historical scrape from October 1, 2016 to today.
- **Subsequent runs:** reads the existing CSV, scrapes from 3 days before the last recorded date to today, deduplicates, and appends only new records.

The 3-day overlap buffer catches any backdated entries that may have been added after the last scrape.

### Search

Searches the CSV for the most recent stocking of each waterbody matching your query. Provide either `--waterbody` or `--county`.

```
python va_trout_scraper.py search --waterbody <NAME> [--file <CSV>]
python va_trout_scraper.py search --county <NAME> [--file <CSV>]
```

| Flag           | Required       | Description                                              | Default              |
|----------------|----------------|----------------------------------------------------------|----------------------|
| `--waterbody`  | One of the two | Waterbody name to search for (partial, case-insensitive) |                      |
| `--county`     | One of the two | County name to search for (partial, case-insensitive)    |                      |
| `--file`       | No             | CSV file to search                                       | `trout_stocking.csv` |

**Example** -- find the most recent stocking of the Roanoke River:

```
python va_trout_scraper.py search --waterbody "Roanoke River"
```

**Example** -- find the most recent stocking for every waterbody in Bath County:

```
python va_trout_scraper.py search --county "Bath"
```

## CSV Format

The output CSV has the following columns:

| Column     | Description                                                        | Example                      |
|------------|--------------------------------------------------------------------|------------------------------|
| Date       | Stocking date (`YYYY-MM-DD`)                                       | `2026-03-18`                 |
| County     | Virginia county or independent city                                | `Bath County`                |
| Waterbody  | Name of the stream, river, or lake                                 | `Cowpasture River`           |
| Category   | DWR stocking category (`A`, `B`, `C`, `DH`, `CR`, `U`, `+`)       | `A`                          |
| Species    | Fish species stocked, comma-separated                              | `Rainbow Trout, Brook Trout` |

## Typical Workflow

1. Build or update the stocking database:
   ```
   python va_trout_scraper.py update
   ```
2. Search for a specific spot:
   ```
   python va_trout_scraper.py search --waterbody "Jackson River"
   ```
3. Or browse everything in a county:
   ```
   python va_trout_scraper.py search --county "Rockingham"
   ```
4. Run `update` again any time to pull in the latest records.
