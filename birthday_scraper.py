import datetime
import os
import re
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup


def get_birthdays(month: str, day: int):
    """
    Scrape the Wikipedia {Month}_{Day} page.
    Collect all <li> entries under the Births section (including nested lists)
    until we reach the next <h2> section. Only keep lines that start with a year.
    """
    url = f"https://en.wikipedia.org/wiki/{month}_{day}"
    headers = {
        "User-Agent": "daily-birthdays-script/1.0 (https://github.com/srw3804/daily-birthdays)"
    }
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.content, "html.parser")

    # Find the "Births" section header
    births_span = soup.find("span", {"id": "Births"})
    if not births_span:
        print("DEBUG: Births <span id='Births'> not found")
        return []

    # From the parent (usually an <h2>), walk forward until the next <h2>.
    # Gather <ul> blocks we encounter in that range.
    birthdays = []
    current = births_span.parent
    ul_count = 0
    li_seen = 0

    for tag in current.find_all_next():
        # Stop when we hit the next main section
        if tag.name == "h2":
            break

        if tag.name == "ul":
            ul_count += 1
            # Only take direct li children to avoid double-counting
            for li in tag.find_all("li", recursive=False):
                text = li.get_text(" ", strip=True)
                # Match a leading year (3–4 digits) followed by a dash/en dash
                m = re.match(r"^(\d{3,4})\s*[–-]\s*(.+)", text)
                if not m:
                    continue

                year_str, desc = m.group(1), m.group(2).strip()
                # Extra sanity check: make sure description has letters
                if not re.search(r"[A-Za-z]", desc):
                    continue

                try:
                    birth_year = int(year_str)
                except ValueError:
                    continue

                age = datetime.datetime.now().year - birth_year
                birthdays.append((birth_year, age, desc))
                li_seen += 1

    print(f"DEBUG: scanned {ul_count} UL blocks; kept {li_seen} li items; parsed {len(birthdays)} birthdays")
    return birthdays


# -------- MAIN --------

# Use your timezone so the date matches your posts
today = datetime.datetime.now(ZoneInfo("America/Detroit")).date()
month = today.strftime("%B")      # e.g., "September"
day = today.day                   # e.g., 5

birthday_list = get_birthdays(month, day)

# Where GitHub Pages serves from (Repo Settings → Pages → /docs)
output_folder = "docs/birthdays"
os.makedirs(output_folder, exist_ok=True)

filename = f"{month.lower()}-{day}.html"   # e.g., "september-5.html"
file_path = os.path.join(output_folder, filename)

with open(file_path, "w", encoding="utf-8") as f:
    f.write("<div class='birthdays'>\n<h3>🎉 Celebrity Birthdays – ")
    f.write(today.strftime("%B %d"))
    f.write("</h3>\n<ul>\n")
    if birthday_list:
        for birth_year, age, desc in birthday_list:
            f.write(f"<li>{desc} – {age} years old ({birth_year})</li>\n")
    else:
        f.write("<p>No birthdays found.</p>\n")
    f.write("</ul>\n</div>")

print(f"DEBUG: wrote {file_path}")
