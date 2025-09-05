import os
import re
import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup


USER_AGENT = "daily-birthdays-script/1.0 (https://github.com/srw3804/daily-birthdays)"
TZ = "America/Detroit"  # your local time for dating files


def get_birthdays(month: str, day: int):
    """
    Scrape https://en.wikipedia.org/wiki/{Month}_{Day}
    Collect all top-level <li> items under the Births section (until next <h2>).
    Return [(birth_year:int, age:int, description:str), ...]
    """
    url = f"https://en.wikipedia.org/wiki/{month}_{day}"
    print(f"DEBUG: fetching {url}")

    headers = {"User-Agent": USER_AGENT, "Accept-Language": "en"}
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.content, "html.parser")

    # Find the Births section header: <h2><span id="Births" class="mw-headline">Births</span></h2>
    span = soup.find("span", id="Births")
    if not span:
        print("DEBUG: couldn't find <span id='Births'>")
        return []

    h2 = span.find_parent("h2")
    if not h2:
        print("DEBUG: couldn't find parent <h2> for Births span")
        return []

    birthdays = []
    ul_seen = 0
    li_seen = 0

    # Walk sibling elements after this <h2> until the next <h2>
    for sib in h2.find_next_siblings():
        if getattr(sib, "name", None) == "h2":
            break
        if getattr(sib, "name", None) == "ul":
            ul_seen += 1
            # Only direct li children (avoid double-counting nested li)
            for li in sib.find_all("li", recursive=False):
                text = li.get_text(" ", strip=True)

                # Split once on en-dash/em-dash/hyphen surrounded by spaces
                parts = re.split(r"\s[–—-]\s", text, maxsplit=1)
                if len(parts) != 2:
                    continue

                year_str, desc = parts[0].strip(), parts[1].strip()

                # Filter out buckets like "1601–1900 (2)", "pre-1600", or lines without letters
                if not re.search(r"[A-Za-z]", desc):
                    continue
                if re.search(r"\bpre[-\s]?1600\b", year_str, flags=re.I):
                    continue
                if re.search(r"\b\d{3,4}\s*[–—-]\s*\d{3,4}\b", year_str):
                    continue
                if re.search(r"\bpresent\b", year_str, flags=re.I):
                    continue

                # Extract a clean year from the left part (handles "AD 19", "c. 1200", etc.)
                m_year = re.search(r"\b(\d{3,4})\b", year_str)
                if not m_year:
                    continue

                birth_year = int(m_year.group(1))
                current_year = datetime.datetime.now().year
                if not (1 <= birth_year <= current_year):
                    continue

                age = current_year - birth_year
                birthdays.append((birth_year, age, desc))
                li_seen += 1

    print(f"DEBUG: scanned {ul_seen} UL blocks; kept {li_seen} li items; parsed {len(birthdays)} birthdays")
    return birthdays


def main():
    # Use your local date so filenames match your day
    # (Avoids UTC day-shift on GitHub runners)
    try:
        from zoneinfo import ZoneInfo
        today = datetime.datetime.now(ZoneInfo(TZ)).date()
    except Exception:
        today = datetime.date.today()  # fallback if zoneinfo unavailable

    # Allow override via env for manual backfill (optional)
    month = os.getenv("MONTH_OVERRIDE") or today.strftime("%B")   # e.g., "September"
    day = int(os.getenv("DAY_OVERRIDE") or today.day)

    items = get_birthdays(month, day)

    # Output to GitHub Pages
    out_dir = Path("docs/birthdays")
    out_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{month.lower()}-{day}.html"   # e.g., "september-5.html"
    out_path = out_dir / filename

    with out_path.open("w", encoding="utf-8") as f:
        f.write("<div class='birthdays'>\n")
        f.write(f"<h3>🎉 Celebrity Birthdays – {month} {day:02d}</h3>\n")
        if items:
            f.write("<ul>\n")
            for year, age, desc in items:
                f.write(f"<li>{desc} – {age} years old ({year})</li>\n")
            f.write("</ul>\n")
        else:
            f.write("<p>No birthdays found.</p>\n")
        f.write("</div>\n")

    print(f"DEBUG: wrote {out_path} ({len(items)} birthdays)")


if __name__ == "__main__":
    main()
