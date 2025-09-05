import os
import re
import datetime
import requests
from bs4 import BeautifulSoup, Tag, NavigableString

HEADERS = {
    "User-Agent": "daily-birthdays-script/1.0 (https://github.com/srw3804/daily-birthdays)"
}

DASH_RE = re.compile(r'^\s*(\d{1,4})\s*[–—-]\s*(.*)$')  # year + (en/em/hyphen) + rest

def get_births_from_date_page(month_cap: str, day: int):
    """Scrape Births from https://en.wikipedia.org/wiki/{Month}_{day}"""
    url = f"https://en.wikipedia.org/wiki/{month_cap}_{day}"
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    # Find the Births heading: usually <span class="mw-headline" id="Births">Births</span>
    anchor = soup.select_one('#Births')
    if anchor:
        # climb to its heading element (h2 or h3)
        h = anchor
        while h and isinstance(h, Tag) and h.name not in ("h2", "h3"):
            h = h.parent
        births_heading = h if h and h.name in ("h2", "h3") else None
    else:
        births_heading = None
        for h in soup.find_all(["h2", "h3"]):
            if "births" in h.get_text(" ", strip=True).lower():
                births_heading = h
                break

    if not births_heading:
        return []

    # Iterate siblings until the next h2/h3, collecting all <ul> children
    results = []
    node = births_heading.next_sibling
    current_year = datetime.date.today().year

    while node:
        if isinstance(node, NavigableString):
            node = node.next_sibling
            continue
        if isinstance(node, Tag) and node.name in ("h2", "h3"):
            break  # end of Births section
        if isinstance(node, Tag) and node.name == "ul":
            for li in node.find_all("li", recursive=False):
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
                    results.append((year, age, desc))
        node = node.next_sibling

    return results

# ---------------- main: write file ----------------
today = datetime.date.today()
month_cap = today.strftime("%B")      # e.g., "September" for URL
month_slug = month_cap.lower()        # e.g., "september" for filename
day_num = today.day

birthdays = get_births_from_date_page(month_cap, day_num)

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
