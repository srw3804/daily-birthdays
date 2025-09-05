import os
import re
import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup


def get_birthdays(month: str, day: int):
    """
    Scrape the Wikipedia {Month}_{Day} page and collect all <li> entries
    under the Births section (until the next <h2>).
    Returns a list of tuples: (birth_year, age, description).
    """
    url = f"https://en.wikipedia.org/wiki/{month}_{day}"
    print(f"DEBUG: fetching {url}")

    headers = {
        "User-Agent": "daily-birthdays-script/1.0 (https://github.com/srw3804/daily-birthdays)"
    }
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()

    soup = BeautifulSoup(r.content, "html.parser")

    # The date pages use: <h2><span class="mw-headline" id="Births">Births</span></h2>
    births_span = soup.find("span", {"id": "Births", "class": "mw-headline"})
    if not births_span:
        print("DEBUG: couldn't find <span class='mw-headline' id='Births'>")
        return []

    birthdays = []
    ul_count = 0
    kept = 0

    # Start from the <h2> that contains this span and walk forward until next <h2>
    current = births_span.parent  # <h2>
    for tag in current.find_all_next():
        if tag.name == "h2":
            break

        if tag.name == "ul":
            ul_count += 1
            # Only take top-level <li> in this UL (nested ULs will be processed when reached)
            for li in tag.find_all("li", recursive=False):
                text = li.get_text(" ", strip=True)

                # Expected form: "1877 – Name, occupation (d. 1939)"
                m = re.match(r"^(\d{3,4})\s*[–-]\s*(.+)$", text)
                if not m:
                    continue

                year_str, desc = m.group(1), m.group(2).strip()

                # Skip junky bullets that don’t contain any letters
                if not re.search(r"[A-Za-z]", desc):
                    continue

                try:
                    birth_year = int(year_str)
                except ValueError:
                    continue

                age = datetime.datetime.now().year - birth_year
                birthdays.append((birth_year, age, desc))
                kept += 1

    print(f"DEBUG: scanned {ul_count} UL blocks; kept {kept} li items; parsed {len(birthdays)} birthdays")
    return birthdays


def main():
    # Allow overrides for testing via environment variables
    # e.g. MONTH_OVERRIDE=September DAY_OVERRIDE=4
    today = datetime.date.today()
    month = os.getenv("MONTH_OVERRIDE") or today.strftime("%B")
    day = int(os.getenv("DAY_OVERRIDE") or today.day)

    birthdays = get_birthdays(month, day)

    # Output folder for GitHub Pages
    output_dir = Path("docs/birthdays")
    output_dir.mkdir(parents=True, exist_ok=True)

    # File name like 'september-5.html'
    month_slug = month.lower()
    file_path = output_dir / f"{month_slug}-{day}.html"

    # Write HTML
    with file_path.open("w", encoding="utf-8") as f:
        f.write("<div class='birthdays'>\n")
        f.write(f"<h3>🎉 Celebrity Birthdays – {month} {day:02d}</h3>\n")

        if not birthdays:
            f.write("<p>No birthdays found.</p>\n</div>")
            print(f"DEBUG: wrote {file_path} (0 birthdays)")
            return

        f.write("<ul>\n")
        for birth_year, age, desc in birthdays:
            f.write(f"<li>{desc} – {age} years old ({birth_year})</li>\n")
        f.write("</ul>\n</div>")

    print(f"DEBUG: wrote {file_path} ({len(birthdays)} birthdays)")


if __name__ == "__main__":
    main()
