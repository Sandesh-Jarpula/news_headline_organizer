"""A beginner-friendly terminal app for collecting and organizing news headlines."""

from __future__ import annotations

import csv
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


APP_DIR = Path(__file__).resolve().parent
DATA_FILE = APP_DIR / "headlines.json"
SAMPLE_FILE = APP_DIR / "sample_headlines.json"
CSV_FILE = APP_DIR / "headlines_export.csv"
CATEGORIES = ("business", "entertainment", "general", "health", "science", "sports", "technology")


def clean(value: object, limit: int = 500) -> str:
    """Normalize user/API text for storage and terminal display."""
    return " ".join(str(value or "").replace("\x00", "").split())[:limit]


def load_headlines() -> list[dict[str, str]]:
    """Load the saved JSON data, seeding it from the included sample on first run."""
    if not DATA_FILE.exists():
        try:
            records = json.loads(SAMPLE_FILE.read_text(encoding="utf-8"))
            if not isinstance(records, list):
                records = []
        except (OSError, json.JSONDecodeError):
            records = []
        save_headlines(records)
        return records
    try:
        records = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        if not isinstance(records, list):
            raise ValueError("The JSON root must be a list.")
        return [item for item in records if isinstance(item, dict) and item.get("title")]
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Could not read saved data ({exc}). Starting with an empty list.")
        return []


def save_headlines(records: list[dict[str, str]]) -> None:
    DATA_FILE.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def print_headlines(records: list[dict[str, str]]) -> None:
    if not records:
        print("No headlines found.")
        return
    for number, item in enumerate(records, start=1):
        title = clean(item.get("title"), 120)
        source = clean(item.get("source"), 35) or "Unknown source"
        category = clean(item.get("category"), 20).title() or "General"
        published = clean(item.get("published_at"), 25) or "Date unknown"
        print(f"{number:>2}. [{category:<13}] {title}\n    {source} | {published}")
        if item.get("url"):
            print(f"    {clean(item['url'], 180)}")


def fetch_headlines(records: list[dict[str, str]]) -> list[dict[str, str]]:
    api_key = os.environ.get("NEWS_API_KEY", "").strip()
    if not api_key:
        print("Live fetching needs a NewsAPI key in the NEWS_API_KEY environment variable.")
        print("Your saved headlines are unchanged. Choose another menu option to use the sample data.")
        return records

    country = input("Country code (for example us, in, gb) [us]: ").strip().lower() or "us"
    if len(country) != 2 or not country.isalpha():
        print("Please enter a two-letter country code.")
        return records
    category = input(f"Category ({', '.join(CATEGORIES)}) [general]: ").strip().lower() or "general"
    if category not in CATEGORIES:
        print("Unknown category. Using general.")
        category = "general"

    query = urlencode({"country": country, "category": category, "pageSize": 20, "apiKey": api_key})
    request = Request(
        f"https://newsapi.org/v2/top-headlines?{query}",
        headers={"User-Agent": "NewsHeadlineOrganizer/1.0"},
    )
    try:
        with urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if payload.get("status") != "ok":
            print("The news service returned an error:", clean(payload.get("message"), 200))
            return records
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        print(f"Could not fetch headlines: {exc}")
        return records

    existing = {item.get("url") for item in records if item.get("url")}
    added = 0
    for article in payload.get("articles", []):
        title = clean(article.get("title"))
        url = clean(article.get("url"), 1000)
        if not title or not url or url in existing:
            continue
        records.append({
            "title": title,
            "category": category,
            "source": clean((article.get("source") or {}).get("name"), 100),
            "published_at": clean(article.get("publishedAt"), 40),
            "url": url,
            "description": clean(article.get("description"), 500),
        })
        existing.add(url)
        added += 1
    save_headlines(records)
    print(f"Added {added} new headline(s); {len(records)} total saved.")
    return records


def add_headline(records: list[dict[str, str]]) -> list[dict[str, str]]:
    title = clean(input("Headline title: "))
    if not title:
        print("A title cannot be blank.")
        return records
    category = input(f"Category ({', '.join(CATEGORIES)}) [general]: ").strip().lower() or "general"
    if category not in CATEGORIES:
        print("Unknown category. Using general.")
        category = "general"
    source = clean(input("News source: "), 100) or "Added manually"
    url = clean(input("Article URL (optional): "), 1000)
    records.append({
        "title": title,
        "category": category,
        "source": source,
        "published_at": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "url": url,
        "description": "",
    })
    save_headlines(records)
    print("Headline saved.")
    return records


def summarize(records: list[dict[str, str]]) -> None:
    counts = Counter(clean(item.get("category"), 30).lower() or "general" for item in records)
    sources = {clean(item.get("source"), 100) for item in records if clean(item.get("source"))}
    print(f"\nSaved headlines: {len(records)}")
    print(f"News sources: {len(sources)}")
    print("By category:")
    if not counts:
        print("  No data yet.")
    for category, count in sorted(counts.items()):
        share = count / len(records) * 100 if records else 0
        print(f"  {category.title():<16} {count:>3} ({share:.0f}%)")


def search_headlines(records: list[dict[str, str]]) -> None:
    term = clean(input("Search keyword or category: ")).casefold()
    if not term:
        print("Enter a word to search for.")
        return
    matches = [item for item in records if term in " ".join(item.values()).casefold()]
    print(f"\nFound {len(matches)} match(es):")
    print_headlines(matches)


def export_csv(records: list[dict[str, str]]) -> None:
    fields = ("title", "category", "source", "published_at", "url", "description")
    with CSV_FILE.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)
    print(f"Exported {len(records)} headline(s) to {CSV_FILE.name}.")


def make_chart(records: list[dict[str, str]]) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("Charts need Matplotlib. Install it with: py -m pip install matplotlib")
        return
    counts = Counter(clean(item.get("category"), 30).title() or "General" for item in records)
    if not counts:
        print("There is no data to chart yet.")
        return
    labels, values = zip(*sorted(counts.items()))
    plt.figure(figsize=(9, 5))
    plt.bar(labels, values, color="#2f6f9f")
    plt.title("Saved headlines by category")
    plt.ylabel("Number of headlines")
    plt.xticks(rotation=25, ha="right")
    plt.tight_layout()
    path = APP_DIR / "category_chart.png"
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"Chart saved as {path.name}.")


def main() -> None:
    records = load_headlines()
    print("\n=== NEWS HEADLINE ORGANIZER ===")
    print(f"Loaded {len(records)} headline(s). Data is saved locally in headlines.json.\n")
    actions = {
        "1": ("Show all headlines", lambda: print_headlines(records)),
        "2": ("Fetch live headlines", None),
        "3": ("Add a headline manually", None),
        "4": ("Search headlines", lambda: search_headlines(records)),
        "5": ("Show summary", lambda: summarize(records)),
        "6": ("Export CSV", lambda: export_csv(records)),
        "7": ("Create category chart", lambda: make_chart(records)),
    }
    while True:
        print("\n".join(f"{key}. {label}" for key, (label, _) in actions.items()))
        print("0. Exit")
        choice = input("Choose an option: ").strip()
        if choice == "0":
            print("Goodbye!")
            break
        if choice not in actions:
            print("Please choose a number from 0 to 7.")
        elif choice == "2":
            records = fetch_headlines(records)
        elif choice == "3":
            records = add_headline(records)
        else:
            actions[choice][1]()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye!")
        sys.exit(0)
