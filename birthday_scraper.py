import os
import re
import datetime
import requests
from bs4 import BeautifulSoup, NavigableString, Tag

UA = "daily-birthdays-script/1.0 (https://github.com/srw3804/daily-birthdays)"

CITATION_RE = re.compile(r"\[\d+\]")                 # [5], [12] …
DECEASED_RE  = re.compile(r"\(d\.\s*\d{3,4}\)", re.I) # (d. 1991) etc.

def clean(text: str) -> str:
    """Trim & drop Wikipedia citation markers like [5]."""
    return CITATION_RE.sub("", text).replace("  ", " ").strip()

def find_births_header(soup: BeautifulSoup) -> Tag | None:
    """
    Return the <h2> element that starts the Births section.
    Works for: <h2 id="Births"> and <h2><span id="Births"></span></h2>
    """
    anchor = soup.find(id="Births")
    if not anchor:
        return None
    return anchor if anchor.name == "h2" else anchor.find_parent("h2")

def collect_birth_li_items(header_h2: Tag) -> list[Tag]:
    """
    From the Births <h2>, walk forward through siblings until the next <h2>,
    collecting every <li> inside <ul> blocks (there’s one per era).
    """
    items = []
    node = header_h2.next_sibling
    while node:
        if isinstance(node, NavigableString):
            node = node.next_sibling
            continue
        if isinstance(node, Tag) and node.name == "h2":
            break  # reached next section
        if isinstance(node, Tag) and node.name == "ul":
            items.extend(node.find_all("li", recursive=False))
        node = node.next_sibling
    return items

def parse_item(li: Tag, current_year: int) -> str | None:
    """
    Parse a single 'YYYY – Person, details' line.
    Return formatted: 'Name – AGE years old (YEAR) – details'
    Skips deceased entries '(d. YEAR)'.
    """
    raw = clean(li.get_text(" ", strip=True))
    # Expected pattern: '1946 – Freddie Mercury, … (d. 1991)'
    if " – " not in raw:
        return None
    year_str, rest = raw.split(" – ", 1)
    year_str = year_str.strip()
    if not year_str.isdigit():
        return None
    birth_year = int(year_str)

    # Skip deceased
    if DECEASED_RE.search(rest) or " died " in rest.lower():
        return None

    # Split rest into name + details (first comma boundary)
    if ", " in rest:
        name, details = rest.split(", ", 1)
    else:
        # fallback if no comma present
        name, details = rest, ""

    name    = clean(name)
    details = clean(details)

    age = current_year - birth_year
    # Blog style: Name – AGE years old (YEAR) – details
    if details:
        return f"{name} – {age} years old ({birth_year}) – {details}"
    else:
        return f"{name} – {age} years old ({birth_year})"

def get_birthdays_for(month: str, day: int) -> list[str]:
    url = f"https://en.wikipedia.org/wiki/{month}_{day}"
    print(f"DEBUG: fetching birthdays for {month} {day} -> {url}")
    r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.content, "html.parser")

    header = find_births_header(soup)
    if not header:
        print("DEBUG: Births header not found")
        return []

    li_items = collect_birth_li_items(header)
    print(f"DEBUG: found {len(li_items)} raw <li> items under Births")

    out = []
    this_year = datetime.date.today().year
    for li in li_items:
        line = parse_item(li, this_year)
        if line:
            out.append(line)

    print(f"DEBUG: parsed {len(out)} living birthdays")
    return out

# -------- main --------
today  = datetime.date.today()
month  = today.strftime("%B")
day    = today.day

birthdays = get_birthdays_for(month, day)

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
