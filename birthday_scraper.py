import os
import re
import datetime
from pathlib import Path
from typing import List, Tuple

import requests

API = "https://en.wikipedia.org/w/api.php"
HEADERS = {
    "User-Agent": "daily-birthdays-script/1.0 (https://github.com/srw3804/daily-birthdays)",
    "Accept-Language": "en",
}

# Bullet lines look like: "* 1969 – Name, occupation (d. 2015)"
BULLET_RE = re.compile(r"^\*\s*(\d{3,4})\s*[–—-]\s*(.+)$")

def get_sections(month: str, day: int):
    """Return the sections array for the page Month_Day via the API."""
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
    data = r.json()
    sections = data.get("parse", {}).get("sections", []) or []
    return sections

def find_births_range(sections) -> List[int]:
    """
    Find the 'Births' section index and all subsequent subsection indices
    until the next top-level (toclevel 2) section.
    Returns a list of section indices (as strings) to fetch.
    """
    # Find the top-level Births section (usually toclevel == 2 and line == 'Births')
    births_idx = None
    births_level = None

    for s in sections:
        line = (s.get("line") or "").strip().lower()
        if line == "births":
            births_idx = s.get("index")
            births_level = s.get("toclevel", 2)
            break

    if not births_idx:
        return []

    # Collect this section and everything that follows with a deeper level,
    # stopping when we hit the next section of the same or higher level.
    indices = [births_idx]
    start_found = False
    for s in sections:
        if s.get("index") == births_idx:
            start_found = True
            continue
        if not start_found:
            continue

        lvl = s.get("toclevel", 2)
        if lvl <= births_level:
            # we've reached the next top-level section (e.g., 'Deaths')
            break
        indices.append(s.get("index"))

    return indices

def fetch_wikitext(page: str, section_index: str) -> str:
    """Fetch the wikitext for a single section index."""
    params = {
        "action": "parse",
        "page": page,
        "section": section_index,
        "prop": "wikitext",
        "format": "json",
        "formatversion": "2",
    }
    r = requests.get(API, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json().get("parse", {}).get("wikitext", "") or ""

def parse_births_from_wikitext(wikitext: str) -> List[Tuple[int, int, str]]:
    """Extract (year, age, description) from wikitext bullet lines."""
    out: List[Tuple[int, int, str]] = []
    current_year = datetime.date.today().year

    for raw in wikitext.splitlines():
        m = BULLET_RE.match(raw.strip())
        if not m:
            continue
        year_str, desc = m.groups()
        try:
            year = int(year_str)
        except ValueError:
            continue
        # Skip obvious junk
        if not (1 <= year <= current_year):
            continue
        # Must have letters in the description (filters numbers-only bullets)
        if not re.search(r"[A-Za-z]", desc):
            continue
        age = current_year - year
        out.append((year, age, desc.strip()))
    return out

def get_birthdays(month: str, day: int):
    """Main: resolve sections via API, fetch wikitext for Births range, parse."""
    page = f"{month}_{day}"
    sections = get_sections(month, day)
    print(f"DEBUG: sections returned: {len(sections)}")

    indices = find_births_range(sections)
    print(f"DEBUG: births section indices: {indices}")
    if not indices:
        return []

    items: List[Tuple[int, int, str]] = []
    for idx in indices:
        wt = fetch_wikitext(page, idx)
        parsed = parse_births_from_wikitext(wt)
        print(f"DEBUG: section {idx}: parsed {len(parsed)} items")
        items.extend(parsed)

    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for year, age, desc in items:
        key = (year, desc)
        if key in seen:
            continue
        seen.add(key)
        deduped.append((year, age, desc))

    print(f"DEBUG: total parsed after dedupe: {len(deduped)}")
    return deduped

def main():
    # Local date (America/Detroit) to match your posting day
    try:
        from zoneinfo import ZoneInfo
        today = datetime.datetime.now(ZoneInfo("America/Detroit")).date()
    except Exception:
        today = datetime.date.today()

    month = os.getenv("MONTH_OVERRIDE") or today.strftime("%B")  # e.g., "September"
    day = int(os.getenv("DAY_OVERRIDE") or today.day)

    items = get_birthdays(month, day)

    out_dir = Path("docs/birthdays")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{month.lower()}-{day}.html"

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
