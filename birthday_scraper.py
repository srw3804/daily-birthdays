# birthday_scraper.py

import os
import re
import datetime
import requests
from bs4 import BeautifulSoup

# ---------- Config ----------
USER_AGENT = "daily-birthdays-script/1.0 (https://github.com/srw3804/daily-birthdays)"
OUTPUT_DIR = "docs/birthdays"  # GitHub Pages: /docs is the published root
# ---------------------------

# Regex to strip citation footnotes like [1], [2], [a], etc.
REF_RE = re.compile(r"\[\s*[0-9a-zA-Z]+\s*\]")
# Common dash characters used on Wikipedia between year and description
DASH_RE = re.compile(r"\s*[–—-]\s*")  # en/em/hyphen

def month_title(month_name: str) -> str:
    """Return the Wikipedia page month title form ('September')."""
    # Wikipedia expects capitalized English month names
    return month_name.capitalize()

def find_births_header(soup: BeautifulSoup):
    """
    Locate the 'Births' section header on a {Month}_{Day} page.
    Works for:
    - <span id="Births">
    - <h2><span class="mw-headline" id="Births">Births</span></h2>
    - Headings that contain the word 'Births'
    """
    # Direct anchor <span id="Births">
    anchor = soup.find("span", id="Births")
    if anchor:
        return anchor

    # Headline with id="Births"
    headline = soup.find("span", {"class": "mw-headline", "id": "Births"})
    if headline:
        return headline

    # Fallback: any heading that contains text 'Births'
    for tag in soup.find_all(["h2", "h3", "span"]):
        txt = (tag.get_text(strip=True) or "").lower()
        if "births" in txt:
            return tag

    return None

def fetch_births(month_name: str, day: int):
    """
    Fetch and parse the 'Births' list from the Wikipedia page /{Month}_{day}.
    Returns list of tuples: (birth_year, age, description)
    """
    url = f"https://en.wikipedia.org/wiki/{month_title(month_name)}_{day}"
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "en"}

    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")

    header = find_births_header(soup)
    if not header:
        print("DEBUG: Births header not found with any strategy.")
        return []

    # Be tolerant: find the **first <ul> anywhere after** the header/anchor.
    ul = header.find_next("ul")
    if not ul:
        print("DEBUG: No <ul> found after Births header")
        return []

    items = ul.find_all("li")
    print(f"DEBUG: collected {len(items)} li items under Births")

    current_year = datetime.datetime.utcnow().year
    birthdays = []

    for li in items:
        # Collapse references and trim whitespace
        text = REF_RE.sub("", li.get_text(" ", strip=True))

        # Split on the first dash-like delimiter into "year" + "description"
        parts = DASH_RE.split(text, maxsplit=1)
        if len(parts) != 2:
            continue

        year_raw, description = parts[0].strip(), parts[1].strip()

        # Extract the first 1-4 digit year (many entries are like "1949 – ...")
        m = re.match(r"^\D*(\d{1,4})\b", year_raw)
        if not m:
            continue

        birth_year = int(m.group(1))
        if not (1 <= birth_year <= current_year):
            continue

        age = current_year - birth_year
        birthdays.append((birth_year, age, description))

    print(f"DEBUG: parsed {len(birthdays)} birthdays")
    return birthdays

def main():
    # Allow manual override via environment (handy for testing specific dates)
    env_month = os.getenv("FORCE_MONTH")  # e.g., "september"
    env_day = os.getenv("FORCE_DAY")      # e.g., "4"

    if env_month and env_day:
        month_name = env_month.strip().lower()
        day = int(env_day)
        today = datetime.date(datetime.datetime.utcnow().year, datetime.datetime.strptime(month_name[:3], "%b").month, day)
    else:
        today = datetime.date.today()
        month_name = today.strftime("%B").lower()
        day = today.day

    # Scrape
    birthdays = fetch_births(month_name, day)

    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # File name like 'september-4.html'
    filename = f"{month_name}-{day}.html"
    filepath = os.path.join(OUTPUT_DIR, filename)

    # Write minimal, safe HTML fragment
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("<div class='birthdays'>\n")
        f.write(f"<h3>🎉 Celebrity Birthdays – {today.strftime('%B %d')}</h3>\n")

        if birthdays:
            f.write("<ul>\n")
            # Sort by (birth_year ASC), oldest first (optional)
            for birth_year, age, desc in sorted(birthdays, key=lambda t: t[0]):
                f.write(f"  <li>{desc} – {age} years old ({birth_year})</li>\n")
            f.write("</ul>\n")
        else:
            f.write("<p>No birthdays found.</p>\n")

        f.write("</div>\n")

    print(f"DEBUG: wrote {filepath}")

if __name__ == "__main__":
    main()
