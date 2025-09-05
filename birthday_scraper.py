
# birthday_scraper.py
# Generates docs/birthdays/<month>-<day>.html for GitHub Pages.
# - Parses the Wikipedia "Births" section
# - Keeps only LIVING people
# - Keeps entries that contain "American" (including hyphen-American, e.g. "Chinese-American")
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
    """Remove footnote markers and tidy whitespace."""
    if not s:
        return ""
    # Remove ALL bracketed refs: [5], [12], [a], [citation needed], etc.
    s = re.sub(r"\[[^\]]*\]", "", s)
    # Replace multiple spaces / weird whitespace with single space
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def looks_dead(text: str) -> bool:
    """Heuristics to detect if a person is deceased from the line text."""
    t = text.lower()
    # Common death indicators
    death_patterns = [
        r"\bdied\b",
        r"\bdeath\b",
        r"\bd\.\s*\d{3,4}\b",        # (d. 1987)
        r"\b†\b",                    # dagger
        r"\b\(d[.)]",                # (d.
        r"\b\(died\b",               # (died ....
        r"\b–\s*\d{3,4}\)",          # "– 1988)" sometimes appears
    ]
    return any(re.search(p, t) for p in death_patterns)

def americanish(text: str) -> bool:
    """
    Keep entries that mention 'American' anywhere, including hyphen forms (e.g., 'Chinese-American').
    """
    return re.search(r"\b[A-Za-z-]*American\b", text) is not None

def fix_profession(desc: str) -> str:
    """
    - If desc starts with 'American ' exactly, drop that word and capitalize the next word.
    - Keep hyphen-nationalities like 'Chinese-American' as-is.
    - Normalize spaces & punctuation a bit.
    """
    d = desc.strip()
    # If it *starts* with 'American ', remove and capitalize next word.
    if d.startswith("American "):
        d = d[len("American "):].strip()
        # Capitalize first word (profession) if it's all lower
        d = d[:1].upper() + d[1:]
    # Collapse spaces after commas
    d = re.sub(r"\s*,\s*", ", ", d)
    # Collapse spaces around en dashes
    d = re.sub(r"\s*–\s*", f" {DASH} ", d)
    d = clean_text(d)
    return d

def parse_birth_li(li_text: str, current_year: int):
    """
    Parse a line like:
      '1932 – Carol Lawrence, American actress and singer'
    -> (year: int, name: str, desc: str, age: int)
    Returns None on failure or if not living.
    """
    raw = clean_text(li_text)

    # Split at first en dash or hyphen minus if en dash missing
    # Wikipedia uses en dash, but be tolerant
    parts = re.split(r"\s[–-]\s", raw, maxsplit=1)
    if len(parts) != 2:
        return None

    year_str, right = parts[0].strip(), parts[1].strip()

    # Year must be 3-4 digits
    m = re.match(r"^\d{3,4}$", year_str)
    if not m:
        return None
    birth_year = int(year_str)

    # name, description split by first comma
    if "," in right:
        name, desc = right.split(",", 1)
        name = clean_text(name)
        desc = clean_text(desc)
    else:
        # Sometimes no comma appears; try to best-effort
        # Assume first token(s) before first ' – ' are the name; otherwise bail
        tokens = right.split()
        if len(tokens) < 2:
            return None
        name = clean_text(tokens[0] + (" " + tokens[1] if len(tokens) > 1 else ""))
        desc = clean_text(" ".join(tokens[2:]))

    # Must be living
    if looks_dead(right):
        return None

    # Must be American-ish
    if not americanish(right):
        return None

    # Age
    age = current_year - birth_year

    # Profession / extra details cleanup
    desc = fix_profession(desc)

    return birth_year, name, desc, age

def find_births_section(soup: BeautifulSoup) -> list[Tag]:
    """
    Return a list of <li> tags under the 'Births' section.
    We navigate from the <h2><span id="Births"> to the next <ul> (and possibly subsequent lists
    until the next <h2>).
    """
    # Prefer h2 span with id "Births"
    h2_span = soup.select_one("h2 span#Births")
    if not h2_span:
        # Fallback: any span with id=Births
        h2_span = soup.select_one("span#Births")
    if not h2_span:
        return []

    # climb to the h2 header (if needed)
    header = h2_span
    while header and header.name != "h2":
        header = header.parent

    if not header:
        return []

    # Collect <li> until the next h2
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

def build_html(entries: list[tuple[int, str, str, int]]) -> str:
    """
    Build the HTML fragment with <p> blocks, no heading, name bolded.
    """
    lines = []
    for year, name, desc, age in entries:
        # Example:
        # <p><strong>Debbie Turner</strong> – 69 years old (1956) – Actress</p>
        line = (
            f"<p><strong>{name}</strong> {DASH} {age} years old ({year})"
            + (f" {DASH} {desc}" if desc else "")
            + "</p>"
        )
        lines.append(line)
    return "<div class='birthdays'>\n" + "\n".join(lines) + "\n</div>\n"

def main():
    today = dt.date.today()

    # Allow override via env for testing
    env_month = os.getenv("BIRTHDAY_MONTH")  # e.g., 'September'
    env_day = os.getenv("BIRTHDAY_DAY")      # e.g., '5'

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

    # Ensure output dir
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
        # Make failures easy to spot in Action logs
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
