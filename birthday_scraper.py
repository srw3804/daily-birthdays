import os
import re
import datetime
import requests

API = "https://en.wikipedia.org/w/api.php"
HEADERS = {
    "User-Agent": "daily-birthdays-script/1.0 (https://github.com/srw3804/daily-birthdays)"
}

# * 1965 – Person (…)
LINE_RE = re.compile(r'^\*\s*(\d{1,4})\s*[–—-]\s*(.+)$')

def find_births_section_index(month_cap: str, day: int) -> str | None:
    page = f"{month_cap}_{day}"
    params = {
        "action": "parse",
        "page": page,
        "prop": "sections",
        "format": "json",
        "formatversion": "2",
    }
    r = requests.get(API, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    sections = r.json().get("parse", {}).get("sections", [])
    for s in sections:
        if s.get("line", "").strip().lower() == "births":
            return s.get("index")
    return None

def fetch_births_wikitext(month_cap: str, day: int) -> str | None:
    idx = find_births_section_index(month_cap, day)
    if not idx:
        return None
    params = {
        "action": "parse",
        "page": f"{month_cap}_{day}",
        "section": idx,
        "prop": "wikitext",
        "format": "json",
        "formatversion": "2",
    }
    r = requests.get(API, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json().get("parse", {}).get("wikitext")

def parse_births_from_wikitext(wikitext: str) -> list[tuple[int, int, str]]:
    out: list[tuple[int, int, str]] = []
    current_year = datetime.date.today().year
    for raw in wikitext.splitlines():
        m = LINE_RE.match(raw.strip())
        if not m:
            continue
        year_str, desc = m.groups()
        try:
            year = int(year_str)
            if 0 < year <= current_year:
                out.append((year, current_year - year, desc.strip()))
        except ValueError:
            continue
    return out

def main():
    today = datetime.date.today()
    month_cap = today.strftime("%B")       # "September"
    month_slug = month_cap.lower()         # "september"
    day_num = today.day

    wikitext = fetch_births_wikitext(month_cap, day_num)
    birthdays = parse_births_from_wikitext(wikitext or "")

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
