# birthday_scraper.py
# Generates docs/birthdays/<month>-<day>.html for GitHub Pages.
# - Parses the Wikipedia "Births" section
# - Keeps only LIVING people
# - Keeps entries that contain "American" (including hyphen-American)
# - Formats: <p><strong>Name</strong> – {age} years old ({year}) – {desc}</p>
# - Strips all bracketed references like [5], [a], etc.

import os
import re
import sys
import datetime as dt
import requests
from bs4 import BeautifulSoup, Tag, NavigableString

# ------------- Config -------------
OUTPUT_DIR = "docs/birthdays"
USER_AGENT = "daily-birthdays-script/1.0 (+https://github.com/srw3804/daily-birthdays)"
HEADERS = {"User-Agent": USER_AGENT}
DASH = "–"  # en dash
# ---------------------------------

def clean_text(s: str) -> str:
    if not s:
        return ""
    # Remove ALL bracketed refs: [5], [12], [a], [citation needed], etc.
    s = re.sub(r"\[[^\]]*\]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def looks_dead(text: str) -> bool:
    t = text.lower()
    death_patterns = [
        r"\bdied\b",
        r"\bdeath\b",
        r"\bd\.\s*\d{3,4}\b",
        r"\b†\b",
        r"\b\(d[.)]",
        r"\b\(died\b",
        r"\b–\s*\d{3,4}\)",
    ]
    return any(re.search(p, t) for p in death_patterns)

def americanish(text: str) -> bool:
    return re.search(r"\b[A-Za-z-]*American\b", text) is not None

def fix_profession(desc: str) -> str:
    d = desc.strip()
    if d.startswith("American "):
        d = d[len("American "):].strip()
        d = d[:1].upper() + d[1:] if d else d
    d = re.sub(r"\s*,\s*", ", ", d)
    d = re.sub(r"\s*–\s*", f" {DASH} ", d)
    return clean_text(d)

def parse_birth_li(li_text: str, current_year: int):
    raw = clean_text(li_text)

    parts = re.split(r"\s[–-]\s", raw, maxsplit=1)
    if len(parts) != 2:
        return None

    year_str, right = parts[0].strip(), parts[1].strip()

    if not re.match(r"^\d{3,4}$", year_str):
        return None
    birth_year = int(year_str)

    if "," in right:
        name, desc = right.split(",", 1)
        name = clean_text(name)
        desc = clean_text(desc)
    else:
        tokens = right.split()
        if len(tokens) < 2:
            return None
        name = clean_text(" ".join(tokens[:2]))
        desc = clean_text(" ".join(tokens[2:]))

    if looks_dead(right):
        return None
    if not americanish(right):
        return None

    age = current_year - birth_year
    desc = fix_profession(desc)
    return birth_year, name, desc, age

def find_births_section(soup: BeautifulSoup) -> list[Tag]:
    """
    Find the 'Births' h2 (various HTML structures) and gather all <li> items
    from subsequent <ul> siblings up to the next <h2>.
    """
    # Try several robust ways to find the Births header
    header = (
        soup.select_one("h2#Births") or
        soup.select_one("h2 > span#Births") or
        soup.select_one("span.mw-headline#Births")
    )

    # If we only got the span, climb to the h2
    if header and header.name != "h2":
        p = header
        while p and p.name != "h2":
            p = p.parent
        header = p

    # Fallback: find an h2 whose visible headline text is "Births"
    if not header:
        for h2 in soup.select("h2"):
            span = h2.find("span", class_="mw-headline")
            text = (span.get_text(strip=True) if span else h2.get_text(strip=True)) or ""
            if text.lower() == "births":
                header = h2
                break

    if not header:
        return []

    lis: list[Tag] = []
    node = header.next_sibling
    while node:
        if isinstance(node, NavigableString):
            node = node.next_sibling
            continue
        if isinstance(node, Tag):
            if node.name == "h2":
                break
            if node.name == "ul":
                lis.extend(node.find_all("li", recursive=False))
        node = node.next_sibling
    return lis

def build_html(entries):
    lines = []
    for year, name, desc, age in entries:
        line = (
            f"<p><strong>{name}</strong> {DASH} {age} years old ({year})"
            + (f" {DASH} {desc}" if desc else "")
            + "</p>"
        )
        lines.append(line)
    return "<div class='birthdays'>\n" + "\n".join(lines) + "\n</div>\n"

def main():
    today = dt.date.today()
    env_month = os.getenv("BIRTHDAY_MONTH")
    env_day = os.getenv("BIRTHDAY_DAY")

    month_name = (env_month or today.strftime("%B")).strip()
    day = int(env_day or today.day)

    url = f"https://en.wikipedia.org/wiki/{month_name}_{day}"
    print(f"DEBUG: fetching birthdays for {month_name} {day} -> {url}")

    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.content, "html.parser")

    li_tags = find_births_section(soup)
    print(f"DEBUG: found {len(li_tags)} raw <li> items under Births")

    current_year = today.year
    entries = []
    for li in li_tags:
        txt = li.get_text(" ", strip=True)
        parsed = parse_birth_li(txt, current_year)
        if parsed:
            entries.append(parsed)

    print(f"DEBUG: parsed {len(entries)} living American(-ish) birthdays")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    file_name = f"{month_name.lower()}-{day}.html"
    out_path = os.path.join(OUTPUT_DIR, file_name)

    html = build_html(entries)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"DEBUG: wrote {out_path} ({len(entries)} entries)")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
