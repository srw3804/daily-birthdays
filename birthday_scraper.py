import os
import re
import datetime
from pathlib import Path
import requests
from bs4 import BeautifulSoup

API = "https://en.wikipedia.org/w/api.php"
HEADERS = {
    # Add a way to reach you to be nice to Wikipedia
    "User-Agent": "daily-birthdays-script/1.0 (+https://github.com/srw3804/daily-birthdays; contact: srw3804)",
    "Accept-Language": "en",
}

# ---------- Helpers ----------

def fetch_html(month: str, day: int) -> str:
    """Fetch rendered HTML of the date page via Wikipedia API."""
    page = f"{month}_{day}"
    params = {
        "action": "parse",
        "page": page,
        "prop": "text",
        "format": "json",
        "formatversion": "2",
    }
    r = requests.get(API, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json().get("parse", {}).get("text", "")

_DEATH_PAT = re.compile(
    r"(?:\((?:d\.|died)\s*\d{3,4}\)|\b(?:died|death)\b|\u2020)",  # (d. 2009) / (died 2009) / died / †
    flags=re.IGNORECASE,
)

def looks_deceased(text: str) -> bool:
    """Heuristic: entry mentions death markers like (d. 2009), (died 2009), †."""
    return bool(_DEATH_PAT.search(text))

def clean_text(s: str) -> str:
    """Remove refs like [23] and excessive whitespace."""
    s = re.sub(r"\[\d+\]", "", s)
    return re.sub(r"\s+", " ", s).strip()

# ---------- Core scraping ----------

def get_birthdays(month: str, day: int):
    """Return list of (year, age, description) for LIVING people only."""
    html = fetch_html(month, day)
    soup = BeautifulSoup(html, "html.parser")

    births_span = soup.find("span", {"id": "Births"})
    if not births_span:
        print("DEBUG: couldn't find <span id='Births'>")
        return []

    h2 = births_span.find_parent("h2")
    if not h2:
        print("DEBUG: id='Births' not inside an <h2>; aborting")
        return []

    current_year = datetime.date.today().year
    max_age = 125
    results = []

    # Walk siblings until next h2 (usually the 'Deaths' section)
    for sib in h2.find_next_siblings():
        if sib.name == "h2":
            break
        if sib.name == "ul":
            # Top-level <li> children only (avoid nested lists like “see also”)
            for li in sib.find_all("li", recursive=False):
                text = clean_text(li.get_text(" ", strip=True))

                # Split on the FIRST en dash / hyphen separating year and description
                # Using a regex that matches a single dash-like char
                m = re.split(r"\s*[–-]\s*", text, maxsplit=1)
                if len(m) != 2:
                    continue

                year_str, desc = m[0], m[1]

                # Parse a 3–4 digit year only (skip BCE, ranges, etc.)
                ymatch = re.fullmatch(r"\d{3,4}", year_str.strip())
                if not ymatch:
                    continue

                year = int(ymatch.group(0))
                age = current_year - year

                # Filter out obviously impossible ages (and anything older than max_age)
                if age < 0 or age > max_age:
                    continue

                # Only keep likely-living people (skip if any death marker present)
                if looks_deceased(desc):
                    continue

                results.append((year, age, desc))

    print(f"DEBUG: parsed {len(results)} living birthdays")
    return results

# ---------- CLI entry ----------

def main():
    today = datetime.date.today()
    month = (os.getenv("MONTH_OVERRIDE") or today.strftime("%B")).strip()
    day = int(os.getenv("DAY_OVERRIDE") or today.day)

    print(f"DEBUG: fetching birthdays for {month} {day}")
    living_birthdays = get_birthdays(month, day)

    out_dir = Path("docs/birthdays")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{month.lower()}-{day}.html"

    with out_file.open("w", encoding="utf-8") as f:
        f.write("<div class='birthdays'>\n")
        f.write(f"<h3>🎉 Celebrity Birthdays – {month} {day:02d}</h3>\n")
        if living_birthdays:
            f.write("<ul>\n")
            for year, age, desc in living_birthdays:
                f.write(f"<li>{desc} – {age} years old ({year})</li>\n")
            f.write("</ul>\n")
        else:
            f.write("<p>No birthdays found.</p>\n")
        f.write("</div>\n")

    print(f"DEBUG: wrote {out_file} ({len(living_birthdays)} living birthdays)")

if __name__ == "__main__":
    main()
