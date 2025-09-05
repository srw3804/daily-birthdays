import os
import re
import datetime
import requests
from bs4 import BeautifulSoup

API = "https://en.wikipedia.org/w/api.php"
HEADERS = {
    "User-Agent": "daily-birthdays-script/1.0 (https://github.com/srw3804/daily-birthdays)"
}

DASH_RE = re.compile(r'^\s*(\d{1,4})\s*[–—-]\s*(.*)$')  # year – desc

def fetch_births_section_html(month_cap: str, day: int) -> str | None:
    """
    Use the MediaWiki API to (1) find the section index whose line == 'Births'
    on the {Month}_{day} page, then (2) fetch that section's HTML.
    Returns HTML string for the 'Births' section or None.
    """
    page = f"{month_cap}_{day}"

    # 1) Find sections to locate the 'Births' section index
    params_sections = {
        "action": "parse",
        "page": page,
        "prop": "sections",
        "format": "json",
        "formatversion": "2",
    }
    r = requests.get(API, params=params_sections, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    sections = data.get("parse", {}).get("sections", [])
    births_index = None
    for s in sections:
        if s.get("line", "").strip().lower() == "births":
            births_index = s.get("index")
            break
    if births_index is None:
        return None

    # 2) Fetch the HTML for that section only
    params_section_html = {
        "action": "parse",
        "page": page,
        "section": births_index,
        "prop": "text",
        "format": "json",
        "formatversion": "2",
    }
    r2 = requests.get(API, params=params_section_html, headers=HEADERS, timeout=30)
    r2.raise_for_status()
    data2 = r2.json()
    html = data2.get("parse", {}).get("text", "")
    return html or None

def parse_births_from_html(html: str) -> list[tuple[int, int, str]]:
    """
    Parse the HTML of the Births section and return a list of tuples:
    (birth_year, age, description).
    """
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("ul > li")
    out = []
    current_year = datetime.date.today().year

    for li in items:
        text = " ".join(li.get_text(" ", strip=True).split())
        m = DASH_RE.match(text)
        if not m:
            continue
        year_str, desc = m.groups()
        try:
            year = int(year_str)
        except ValueError:
            continue
        if 0 < year <= current_year:
            age = current_year - year
            out.append((year, age, desc))
    return out

def main():
    today = datetime.date.today()
    month_cap = today.strftime("%B")       # e.g., "September" (for the wiki page)
    month_slug = month_cap.lower()         # e.g., "september" (for filename)
    day_num = today.day

    html = fetch_births_section_html(month_cap, day_num)
    birthdays = parse_births_from_html(html) if html else []

    out_dir = "docs/birthdays"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{month_slug}-{day_num}.html")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("<div class='birthdays'>\n")
        f.write(f"<h3>🎉 Celebrity Birthdays – {today.strftime('%B %d')}</h3>\n")
        if birthdays:
            f.write("<ul>\n")
            for year, age, desc in birthdays:
                f.write(f"<li>{desc} – {age} years old ({year})</li>\n")
            f.write("</ul>\n")
        else:
            f.write("<p>No birthdays found.</p>\n")
        f.write("</div>\n")

    print(f"Wrote {len(birthdays)} items to {out_path}")

if __name__ == "__main__":
    main()
