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

    # Be flexible: find *any* tag with id="Births"
    births_anchor = soup.find(id="Births")
    if not births_anchor:
        print("DEBUG: couldn't find element with id='Births'")
        return []

    # Section header is typically an <h2> that contains that span
    header = births_anchor.find_parent("h2")
    if not header:
        print("DEBUG: id='Births' not inside an <h2>; aborting")
        return []

    birthdays = []
    ul_seen = 0
    kept = 0

    # Walk siblings until the next h2
    for sib in header.next_siblings:
        # Only element nodes have .name
        name = getattr(sib, "name", None)
        if not name:
            continue
        if name == "h2":
            break
        if name == "ul":
            ul_seen += 1
            # Only top-level LIs in this UL
            for li in sib.find_all("li", recursive=False):
                text = li.get_text(" ", strip=True)
                # Typical bullet: "1877 – Name, occupation (d. 1939)"
                # Split on hyphen/en-dash once
                parts = re.split(r"\s[–-]\s", text, maxsplit=1)
                if len(parts) != 2:
                    continue

                year_str, desc = parts[0].strip(), parts[1].strip()

                # Filter out era bullets like "1601–1900 (2)" or "pre-1600"
                if not re.search(r"[A-Za-z]", desc):
                    continue
                if "," not in desc:  # real entries almost always have a comma after the name
                    continue
                if re.fullmatch(r"(?i)pre[-\s]?1600.*|.*\d{3,4}\s*[-–]\s*\d{3,4}.*|.*present.*", year_str):
                    continue

                # Parse year; skip weird tokens like "AD 19" or "c. 1200" unless we can get a pure year
                m_year = re.search(r"\b(\d{3,4})\b", year_str)
                if not m_year:
                    continue
                birth_year = int(m_year.group(1))
                age = datetime.datetime.now().year - birth_year

                birthdays.append((birth_year, age, desc))
                kept += 1

    print(f"DEBUG: scanned {ul_seen} UL blocks; kept {kept} li items; parsed {len(birthdays)} birthdays")
    return birthdays


def main():
    # Allow overrides for testing
    today = datetime.date.today()
    month = os.getenv("MONTH_OVERRIDE") or today.strftime("%B")
    day = int(os.getenv("DAY_OVERRIDE") or today.day)

    birthdays = get_birthdays(month, day)

    output_dir = Path("docs/birthdays")
    output_dir.mkdir(parents=True, exist_ok=True)

    file_path = output_dir / f"{month.lower()}-{day}.html"

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
