import os
import re
import datetime
import html
import requests
from bs4 import BeautifulSoup

UA = "daily-birthdays-script/1.0 (https://github.com/srw3804/daily-birthdays)"
API = "https://en.wikipedia.org/w/api.php"

CITATION_RE = re.compile(r"\[\d+\]")                 # [12], [5], …
DECEASED_RE = re.compile(r"\(d\.\s*\d{3,4}\)", re.I)  # (d. 1991), (D. 2008)…
PAREN_AGE_RE = re.compile(r"\s*\([^)]*\)\s*$")        # trailing (…) often junk

def clean_text(t: str) -> str:
    t = html.unescape(t)
    t = CITATION_RE.sub("", t)
    t = t.replace("  ", " ").strip()
    return t

def fetch_births_section_html(month: str, day: int) -> str | None:
    """Use the MediaWiki API to find the 'Births' section and return its HTML."""
    title = f"{month}_{day}"
    print(f"DEBUG: querying sections for {month} {day}")

    # 1) Find section index for 'Births'
    r = requests.get(API, params={
        "action": "parse",
        "page": title,
        "prop": "sections",
        "format": "json"
    }, headers={"User-Agent": UA}, timeout=30)
    r.raise_for_status()
    data = r.json()

    sections = data.get("parse", {}).get("sections", [])
    idx = None
    for s in sections:
        if s.get("line") == "Births":
            idx = s.get("index")
            break

    if not idx:
        print("DEBUG: no 'Births' section index found")
        return None

    print(f"DEBUG: fetching section index {idx} (Births)")
    r2 = requests.get(API, params={
        "action": "parse",
        "page": title,
        "prop": "text",
        "section": idx,
        "format": "json"
    }, headers={"User-Agent": UA}, timeout=30)
    r2.raise_for_status()
    data2 = r2.json()
    html_text = data2.get("parse", {}).get("text", {}).get("*")
    if not html_text:
        print("DEBUG: section HTML missing")
        return None
    return html_text

def parse_births_from_section(section_html: str, current_year: int) -> list[str]:
    """Parse <li> items from the section HTML; keep only living people."""
    soup = BeautifulSoup(section_html, "html.parser")
    items = soup.find_all("li", recursive=True)
    print(f"DEBUG: collected {len(items)} raw <li> items in section")

    out: list[str] = []
    for li in items:
        raw = clean_text(li.get_text(" ", strip=True))
        if " – " not in raw:
            continue

        year_str, rest = raw.split(" – ", 1)
        year_str = year_str.strip()
        if not year_str.isdigit():
            continue
        birth_year = int(year_str)

        # Skip deceased entries
        if DECEASED_RE.search(rest) or " died " in rest.lower():
            continue

        # name + details: split at first ", "
        if ", " in rest:
            name, details = rest.split(", ", 1)
        else:
            name, details = rest, ""

        name    = clean_text(name)
        details = clean_text(details)

        # Strip trailing parenthetical cruft sometimes appended to details
        details = PAREN_AGE_RE.sub("", details).strip()

        age = current_year - birth_year
        if details:
            formatted = f"{name} – {age} years old ({birth_year}) – {details}"
        else:
            formatted = f"{name} – {age} years old ({birth_year})"
        out.append(formatted)

    print(f"DEBUG: parsed {len(out)} living birthdays")
    return out

def main():
    today = datetime.date.today()
    month = today.strftime("%B")
    day = today.day

    html_section = fetch_births_section_html(month, day)
    birthdays: list[str] = []
    if html_section:
        birthdays = parse_births_from_section(html_section, today.year)
    else:
        print("DEBUG: falling back — no section HTML retrieved")

    out_dir = os.path.join("docs", "birthdays")
    os.makedirs(out_dir, exist_ok=True)
    filename = f"{month.lower()}-{day}.html"
    path = os.path.join(out_dir, filename)

    with open(path, "w", encoding="utf-8") as f:
        f.write("<div class='birthdays'>\n")
        f.write(f"<h3>🎉 Celebrity Birthdays – {today.strftime('%B %d')}</h3>\n")
        if birthdays:
            f.write("<ul>\n")
            for line in birthdays:
                f.write(f"<li>{line}</li>\n")
            f.write("</ul>\n")
        else:
            f.write("<p>No living birthdays found.</p>\n")
        f.write("</div>\n")

    print(f"DEBUG: wrote {path} ({len(birthdays)} living birthdays)")

if __name__ == "__main__":
    main()
