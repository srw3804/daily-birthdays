import os
import re
import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

API = "https://en.wikipedia.org/w/api.php"
HEADERS = {
    "User-Agent": "daily-birthdays-script/1.0 (+https://github.com/srw3804/daily-birthdays; contact: srw3804)",
    "Accept-Language": "en",
}

# --------- Utilities ---------

def get_sections(month: str, day: int):
    """Return the list of sections for the date page via Wikipedia API."""
    page = f"{month}_{day}"
    params = {
        "action": "parse",
        "page": page,
        "prop": "sections",
        "format": "json",
        "formatversion": "2",
    }
    r = requests.get(API, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json().get("parse", {}).get("sections", []) or []


def get_section_html(month: str, day: int, section_index: int) -> str:
    """Return HTML for a specific section index on the date page."""
    page = f"{month}_{day}"
    params = {
        "action": "parse",
        "page": page,
        "prop": "text",
        "section": str(section_index),
        "format": "json",
        "formatversion": "2",
    }
    r = requests.get(API, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json().get("parse", {}).get("text", "")


_DEATH_PAT = re.compile(
    r"(?:\((?:d\.|died)\s*\d{3,4}\)|\b(?:died|death)\b|\u2020)",  # (d. 2009) (died 2009) died / †
    flags=re.IGNORECASE,
)

def looks_deceased(text: str) -> bool:
    return bool(_DEATH_PAT.search(text))

def clean_text(s: str) -> str:
    s = re.sub(r"\[\d+\]", "", s)           # strip reference markers [12]
    s = re.sub(r"\s+", " ", s).strip()
    return s

# --------- Core ---------

def get_birthdays(month: str, day: int):
    """Return list[(year, age, description)] for living people in the Births section."""
    print(f"DEBUG: querying sections for {month} {day}")
    sections = get_sections(month, day)

    births_index = None
    for sec in sections:
        # 'line' is the section title (e.g., "Births", "Deaths", etc.)
        if (sec.get("line") or "").strip().lower() == "births":
            births_index = sec.get("index")
            break

    if births_index is None:
        print("DEBUG: couldn't find a 'Births' section in sections list")
        return []

    print(f"DEBUG: fetching section index {births_index} (Births)")
    html = get_section_html(month, day, births_index)
    soup = BeautifulSoup(html, "html.parser")

    current_year = datetime.date.today().year
    max_age = 125
    results = []

    # The section HTML usually starts right at the first <ul> of births ranges.
    # Only walk top-level <ul> and their immediate <li> children.
    for ul in soup.find_all("ul", recursive=False):
        for li in ul.find_all("li", recursive=False):
            text = clean_text(li.get_text(" ", strip=True))
            # Split on first dash between year and description
            parts = re.split(r"\s*[–-]\s*", text, maxsplit=1)
            if len(parts) != 2:
                continue
            year_str, desc = parts[0], parts[1]

            ymatch = re.fullmatch(r"\d{3,4}", year_str.strip())
            if not ymatch:
                # skip ranges or non-year headings inside the section
                continue

            year = int(ymatch.group(0))
            age = current_year - year
            if age < 0 or age > max_age:
                continue

            if looks_deceased(desc):
                continue

            results.append((year, age, desc))

    print(f"DEBUG: collected {len(results)} living birthdays")
    return results


def main():
    today = datetime.date.today()
    month = (os.getenv("MONTH_OVERRIDE") or today.strftime("%B")).strip()
    day = int(os.getenv("DAY_OVERRIDE") or today.day)

    living = get_birthdays(month, day)

    out_dir = Path("docs/birthdays")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{month.lower()}-{day}.html"

    with out_file.open("w", encoding="utf-8") as f:
        f.write("<div class='birthdays'>\n")
        f.write(f"<h3>🎉 Celebrity Birthdays – {month} {day:02d}</h3>\n")
        if living:
            f.write("<ul>\n")
            for year, age, desc in living:
                f.write(f"<li>{desc} – {age} years old ({year})</li>\n")
            f.write("</ul>\n")
        else:
            f.write("<p>No birthdays found.</p>\n")
        f.write("</div>\n")

    print(f"DEBUG: wrote {out_file} ({len(living)} living birthdays)")


if __name__ == "__main__":
    main()
