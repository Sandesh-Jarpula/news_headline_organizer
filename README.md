# News Headline Organizer

A small Python terminal project that collects, categorizes, searches, summarizes, and saves news headlines.

It also includes a browser-based interface built with Streamlit.

## Run it

1. Install Python 3.10 or newer.
2. Open a terminal in this folder.
3. For the browser app, install its packages and start Streamlit:

   ```powershell
   py -m pip install -r requirements.txt
   py -m streamlit run app.py
   ```

   On macOS/Linux, use `python3 -m pip install -r requirements.txt` and `python3 -m streamlit run app.py`.

4. To use the terminal version instead, run `py news_headline_organizer.py` on Windows, or `python3 news_headline_organizer.py` on macOS/Linux.

The first run copies the included sample headlines into `headlines.json`. The browser app requires Streamlit and pandas (installed from `requirements.txt`); the terminal version uses only Python's standard library. Neither version requires an API key to browse the sample data.

The Streamlit page uses a colorful classic newspaper design with story cards. Readers must create an account before entering; the first visit opens the registration form, and later visits offer sign-in or registration. Passwords are stored as salted PBKDF2 hashes, and each reader's headline list is saved separately under `reader_data/`.

The newsroom lets readers filter and search headlines, add records, see category counts and a chart, fetch live headlines, and download a CSV. Accounts are stored locally in `users.json`; there is no external account service.

## Menu

1. Show all headlines
2. Fetch live headlines
3. Add a headline manually
4. Search headlines by any word or category
5. Show category totals and percentages
6. Export the saved headlines to CSV
7. Create a category chart (optional Matplotlib install)
0. Exit

## Optional live headlines

Live fetching uses the NewsAPI `/v2/top-headlines` endpoint. Create an API key with NewsAPI, then set it as an environment variable before starting the program:

```powershell
$env:NEWS_API_KEY = "your_api_key_here"
py news_headline_organizer.py
```

On macOS/Linux:

```bash
export NEWS_API_KEY="your_api_key_here"
python3 news_headline_organizer.py
```

The app asks for a two-letter country code and a category. Network errors or API errors are shown in the terminal; they do not remove saved headlines. API access and terms depend on your NewsAPI account and plan.

## Files created while using the app

- `headlines.json`: persistent local data
- `headlines_export.csv`: CSV export
- `category_chart.png`: chart, if Matplotlib is installed

`sample_headlines.json` contains fictional example records and uses `example.com` links.
