import os
import re
import datetime
import requests
from bs4 import BeautifulSoup, NavigableString, Tag

HEADERS = {
    "User-Agent": "daily-birthdays-script/1.0 (https://github.com/srw3804/daily-birthdays)"
}

DASH_RE = re.compile(r'^\s*(\d{1,4})\s*[–—-]\s*(.*)$')  # year + dash + text

def _find_births_heading(soup: BeautifulSoup) -> Tag | None:
    # 1) Normal case: <span id="Births"> inside a heading
    anchor = soup.select_one('span#Births')
    if anchor:
        h = anchor
        while h and isinstance(h, Tag) and h.name not in ("h2", "h3"):
            h = h.parent
        if h and h.name in ("h2", "h3"):
            return h

    # 2) Fallback: a heading whose text contains "Births"
    for h in soup.find_all(["h2", "h3"]):
        if h.get_text(strip=True).lower() == "births" or "births" in h.get_text(" ", strip=True).lower():
            return h

    return None

def _iter_section_content(start_heading: Tag):
    """
    Yield siblings after start_heading until the next h2/h3.
    """
    node = start_heading.next_sibling
    while node:
        if isinstance(node, NavigableString):
            node = node.next_sibling
            continue
        if isinstance(node, Tag) and node.name in ("h2", "h3"):
            break
        if isinstance(node, Tag):
            yield node
        node = node.next_sibling

def get_birthdays_for_date(month: str, day: int):
    """Scrape births from:
       https://en.wikipedia.org/wiki/Wikipedia:Selected_anniversaries/{Month}_{Day}
    """
    url = f"https://en.wikipedia.org/wiki/Wikipedia:Selected_anniversaries/{month}_{day}"
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    heading = _find_births_heading(soup)
    if not heading:
        return []

    birthdays = []
    for block in _iter_section_content(heading):
        # Collect only direct <ul> blocks (there can be multiple)
        if block.name == "ul":
            for li in block.find_all("li", recursive=False):
                text = " ".join(li.get_text(" ", strip=True).split())
                m = DASH_RE.match(text)
                if not m:
                    continue
                year_str, desc = m.groups()
                try:
                    year = int(year_str)
                except ValueError:
                    continue
                # Compute age (simple)
                current_year = datetime.date.today().year
                if 0 < year <= current_year:
                    age = current_year - year
                    birthdays.append((year, age, desc))
    return birthdays

# ---------------- main: write to docs/birthdays/{month}-{day}.html ----------------

today = datetime.date.today()
month_slug = today.strftime("%B").lower()     # e.g., 'september'
day_num    = today.day                         # e.g., 4

wiki_month = today.strftime("%B")              # Wikipedia expects capitalized month
wiki_day   = day_num

birthday_list = get_birthdays_for_date(wiki_month, wiki_day)

output_folder = "docs/birthdays"
os.makedirs(output_folder, exist_ok=True)

filename = f"{month_slug}-{day_num}.html"
file_path = os.path.join(output_folder, filename)

with open(file_path, "w", encoding="utf-8") as f:
    f.write("<div class='birthdays'>\n")
    f.write(f"<h3>🎉 Celebrity Birthdays – {today.strftime('%B %d')}</h3>\n")
    if birthday_list:
        f.write("<ul>\n")
        for birth_year, age, desc in birthday_list:
            f.write(f"<li>{desc} – {age} years old ({birth_year})</li>\n")
        f.write("</ul>\n")
    else:
        f.write("<p>No birthdays found.</p>\n")
    f.write("</div>\n")

print(f"Wrote {len(birthday_list)} birthdays to {file_path}")
