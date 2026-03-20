# How to Set Up and Use the VA Trout Stocking Finder

This guide walks you through everything from scratch -- installing Python, getting the files ready, and using the app to find where trout have been stocked in Virginia.

---

## Part 1: Install Python

Python is the programming language this app runs on. You only need to install it once.

1. Open your web browser and go to **https://www.python.org/downloads/**
2. Click the big yellow **"Download Python"** button.
3. Once the file downloads, double-click it to open the installer.
4. **IMPORTANT:** On the very first screen, check the box at the bottom that says **"Add python.exe to PATH"**. This is the most important step. Do not skip it.
5. Click **"Install Now"** and wait for it to finish.
6. Click **"Close"** when it says the setup was successful.

To make sure it worked, open **PowerShell** (click the Start menu and type `PowerShell`, then click it) and type:

```
python --version
```

You should see something like `Python 3.12.x` or `Python 3.14.x`. If you see that, Python is installed and ready to go.

---

## Part 2: Install the Extra Packages

The app needs a few extra tools that don't come with Python. You install them by typing one command.

1. Open **PowerShell**.
2. Navigate to the folder where the app files are. For example:

```
cd "C:\Users\cheyn\Documents.C\Personal\Coding\VaTroutFinder"
```

3. Type this command and press Enter:

```
pip install -r requirements.txt
```

4. Wait for it to finish. You will see some text scroll by. When it stops and you get a new prompt, you are done.

If `pip` is not recognized, try this instead:

```
python -m pip install -r requirements.txt
```

---

## Part 3: Get the Stocking Data (First Time Only)

Before you can search, the app needs to download all the trout stocking records. This only takes a minute.

1. In the same PowerShell window, type:

```
python va_trout_scraper.py update
```

2. Wait for it to finish. It will download every stocking record going back to October 2016 and save them in a file called `trout_stocking.csv`. You will see a message like `Saved 11000 records to trout_stocking.csv`.

You are now ready to use the app.

---

## Part 4: Open the App

1. In the same PowerShell window, type:

```
python VaTroutFinderGUI.py
```

2. A window will pop up on your screen. That is the app. You can now search for trout stocking information.

---

## Part 5: How to Use the App

The app window has four parts from top to bottom:

### The Top Bar

- On the left it says **"VA Trout Stocking Finder"** -- that is just the name.
- On the right there is a button that says **"Update Data"**. Click this whenever you want to check for new stocking records. It will go to the Virginia DWR website, grab any new data, and add it to your file.

### The Search Area

- **Search by:** Pick one of two choices:
  - **Waterbody** -- use this to search for a specific river, creek, or lake by name.
  - **County** -- use this to see all the stocked waters in a county.
- **The text box** -- type what you are looking for here. You do not have to type the full name. For example, typing `Roanoke` will find anything with "Roanoke" in the name.
- **Search button** -- click this (or just press Enter) to run your search.

### The Results Table

This is the big area in the middle. After you search, it fills up with results. Each row is one stocking event and shows:

| Column    | What It Means                                          |
|-----------|--------------------------------------------------------|
| Date      | The day the fish were put in the water                 |
| County    | Which Virginia county the water is in                  |
| Waterbody | The name of the river, creek, or lake                  |
| Category  | A letter code the state uses (A, B, C, DH, etc.)      |
| Species   | What kind of trout were stocked (Rainbow, Brook, etc.) |

You can click on any column name to sort the table by that column. Click it again to reverse the sort.

The table shows the **most recent** stocking for each waterbody that matches your search. So if a river has been stocked ten times, you only see the latest one.

### The Status Bar

The thin bar at the very bottom tells you what is happening:
- `Loaded 11402 records` -- the data is ready.
- `Showing 5 result(s) for waterbody matching 'jackson'` -- your search found 5 waters.
- `Updating stocking data...` -- it is downloading new records. Wait a moment.
- `No results for county matching 'xyz'` -- nothing matched. Try a different spelling.

---

## Quick Examples

**"Where was trout stocked most recently near me in Bath County?"**

1. Click the **County** radio button.
2. Type `Bath` in the text box.
3. Press Enter.
4. The table shows every waterbody in Bath County and the most recent date each one was stocked.

**"When was the last time the Jackson River was stocked?"**

1. Click the **Waterbody** radio button.
2. Type `Jackson River` in the text box.
3. Press Enter.
4. The table shows each section of the Jackson River and the date it was last stocked.

**"I want to see the newest stocking data."**

1. Click the **Update Data** button in the top right.
2. Wait until the status bar at the bottom says `Update complete`.
3. Now search again -- your results will include the latest records.

---

## Troubleshooting

| Problem                                    | What to Do                                                                                         |
|--------------------------------------------|----------------------------------------------------------------------------------------------------|
| `python` is not recognized                 | You forgot to check "Add python.exe to PATH" during install. Reinstall Python and check that box.  |
| `pip` is not recognized                    | Use `python -m pip install -r requirements.txt` instead.                                           |
| The app says "No data file found"          | You need to click **Update Data** or run `python va_trout_scraper.py update` in PowerShell first.  |
| Update failed                              | Make sure you are connected to the internet and try again.                                         |
| No results for my search                   | Try a shorter or different spelling. The search looks for whatever you type anywhere in the name.   |
