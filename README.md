# VA Trout Stocking Finder

A command-line tool that scrapes the [Virginia DWR Daily Trout Stocking Schedule](https://dwr.virginia.gov/fishing/trout-stocking-schedule/) and saves the data to a CSV file. You can then search the CSV to find the most recent stocking for any waterbody or county.

## Setup

Install the required Python packages:

```
pip install -r requirements.txt
```

This installs `requests`, `beautifulsoup4`, and `pandas`.

## Commands

The tool has two commands: `scrape` and `search`.

### Scrape

Downloads stocking records for a date range and saves them to a CSV file.

```
python va_trout_scraper.py scrape --start <START_DATE> --end <END_DATE> [--output <FILENAME>]
```

| Flag       | Required | Description                                          | Default              |
|------------|----------|------------------------------------------------------|----------------------|
| `--start`  | Yes      | Start date in `M/DD/YYYY` format                     |                      |
| `--end`    | Yes      | End date in `M/DD/YYYY` format                       |                      |
| `--output` | No       | Name of the CSV file to write                        | `trout_stocking.csv` |

**Example** -- scrape the full 2025-2026 stocking season:

```
python va_trout_scraper.py scrape --start 10/01/2025 --end 03/18/2026
```

The DWR archive goes back to October 1, 2016.

### Search

Searches a previously scraped CSV for the most recent stocking of each waterbody matching your query. Provide either `--waterbody` or `--county` (not both).

```
python va_trout_scraper.py search --waterbody <NAME> [--file <CSV>]
python va_trout_scraper.py search --county <NAME> [--file <CSV>]
```

| Flag           | Required       | Description                                           | Default              |
|----------------|----------------|-------------------------------------------------------|----------------------|
| `--waterbody`  | One of the two | Waterbody name to search for (partial, case-insensitive) |                   |
| `--county`     | One of the two | County name to search for (partial, case-insensitive)    |                   |
| `--file`       | No             | CSV file to search                                    | `trout_stocking.csv` |

**Example** -- find the most recent stocking of the Roanoke River:

```
python va_trout_scraper.py search --waterbody "Roanoke River"
```

Output:

```
Most recent stocking(s) matching 'Roanoke River':

      Date         County                       Waterbody Category                    Species
2026-03-12 Roanoke County           Roanoke River (Salem)        A Rainbow Trout, Brook Trout
2026-02-13 Roanoke County Roanoke River (Green Hill Park)       DH Rainbow Trout, Brook Trout
2026-02-10 Roanoke County            Roanoke River (City)        A Rainbow Trout, Brook Trout
```

**Example** -- find the most recent stocking for every waterbody in Bath County:

```
python va_trout_scraper.py search --county "Bath"
```

## CSV Format

The output CSV has the following columns:

| Column     | Description                                                        | Example                  |
|------------|--------------------------------------------------------------------|--------------------------|
| Date       | Stocking date (`YYYY-MM-DD`)                                       | `2026-03-18`             |
| County     | Virginia county or independent city                                | `Bath County`            |
| Waterbody  | Name of the stream, river, or lake                                 | `Cowpasture River`       |
| Category   | DWR stocking category (`A`, `B`, `C`, `DH`, `CR`, `U`, `+`)       | `A`                      |
| Species    | Fish species stocked, comma-separated                              | `Rainbow Trout, Brook Trout` |

## Typical Workflow

1. Scrape the current season's data:
   ```
   python va_trout_scraper.py scrape --start 10/01/2025 --end 03/18/2026
   ```
2. Search for a specific spot:
   ```
   python va_trout_scraper.py search --waterbody "Jackson River"
   ```
3. Or browse everything in a county:
   ```
   python va_trout_scraper.py search --county "Rockingham"
   ```
4. Re-run the scrape with a later `--end` date whenever you want to pull in newer records.
