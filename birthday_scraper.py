# birthday_scraper.py
import os
import re
import datetime
import requests
from bs4 import BeautifulSoup, Tag

USER_AGENT = "daily-birthdays-script/1.0 (+https://github.com/srw3804/daily-birthdays)"

DASH_RE = re.compile(r"\s*[–—-]\s*", re.UNICODE)
REF_RE = re.compile(r"\[\d+\]")  # strip [1], [12], etc.

def fetch_births(month_name: str, day: int):
    """
    Fetch birthdays for a given date from https://en.wikipedia.org/wiki/Month_Day.
    Returns a list of tuples: (birth_year:int, age:int, description:str)
    """
    url = f"https://en.wikipedia.org/wiki/{month_name}_{day}"
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "en",  # ensure English section ids/titles
    }

    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")

    # Find the Births <h2> header via its <span id="Births">
    anchor = soup.select_one("span#Births")
    if not anchor:
        print("DEBUG: span#Births not found")
        return []

    h2 = anchor.find_parent("h2")
    if not h2:
        print("DEBUG: Births anchor has no h2 parent")
        return []

    # Walk forward through siblings until the next <h2>, collecting all <li>
    lis = []
    for sib in h2.next_siblings:
        if isinstance(sib, Tag):
            if sib.name == "h2":
                break
            lis.extend(sib.find_all("li"))

    print(f"DEBUG: collected {len(lis)} li items under Births")

    current_year = datetime.datetime.utcnow().year
    birthdays = []

    for li in lis:
        # Flatten text, remove citation refs
        text = REF_RE.sub("", li.get_text(" ", strip=True))
        parts = DASH_RE.split(text, maxsplit=1)
        if len(parts) != 2:
            continue

        year_raw, description = parts[0].strip(), parts[1].strip()

        # Extract a plain integer year at the start (skip c. 123, AD 12, etc.)
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
    # Use UTC date so the daily run is stable in Actions
    today = datetime.datetime.utcnow().date()
    month_name = today.strftime("%B")       # e.g., "September"
    month_slug = month_name.lower()         # e.g., "september"
    day = today.day

    items = fetch_births(month_name, day)

    # Write to GitHub Pages folder
    out_dir = os.path.join("docs", "birthdays")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, f"{month_slug}-{day}.html")

    with open(out_file, "w", encoding="utf-8") as f:
        f.write("<div class='birthdays'>\n")
        f.write(f"<h3>🎉 Celebrity Birthdays – {month_name} {day:02d}</h3>\n")

        if not items:
            f.write("<p>No birthdays found.</p>\n</div>\n")
            return

        f.write("<ul>\n")
        for birth_year, age, desc in items:
            f.write(f"<li>{desc} – {age} years old ({birth_year})</li>\n")
        f.write("</ul>\n</div>\n")


if __name__ == "__main__":
    main()
