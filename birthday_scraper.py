import os
import datetime
import requests
from bs4 import BeautifulSoup

USER_AGENT = "daily-birthdays-script/1.0 (https://github.com/srw3804/daily-birthdays)"

def get_birthdays(month: str, day: int):
    """
    Scrape Wikipedia Selected Anniversaries page for the given month/day
    and return a list of (birth_year, age, description) tuples.
    """
    url = f"https://en.wikipedia.org/wiki/Wikipedia:Selected_anniversaries/{month.capitalize()}_{day}"
    headers = {"User-Agent": USER_AGENT}
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()

    soup = BeautifulSoup(r.content, "html.parser")

    # Find "Births" section
    births_section = soup.find("span", {"id": "Births"})
    if not births_section:
        return []

    ul = births_section.find_next("ul")
    if not ul:
        return []

    birthdays = []
    for li in ul.find_all("li", recursive=False):
        text = li.get_text(" ", strip=True)

        # Split on en-dash first, fallback to hyphen
        parts = text.split("–", 1)
        if len(parts) == 1:
            parts = text.split("-", 1)
        if len(parts) != 2:
            continue

        year_str, description = parts
        try:
            birth_year = int(year_str.strip())
        except ValueError:
            continue

        age = datetime.datetime.now().year - birth_year
        birthdays.append((birth_year, age, description.strip()))

    return birthdays


# ---------- DATE SELECTION ----------
# For testing a specific page (Sept 4):
month = "september"
day = 4
today = datetime.date(2023, 9, 4)

# For daily automatic use, comment the 3 lines above and uncomment:
# today = datetime.date.today()
# month = today.strftime("%B").lower()
# day = today.day
# -----------------------------------

# Scrape
birthday_list = get_birthdays(month, day)

# Ensure output folder
output_folder = os.path.join("docs", "birthdays")
os.makedirs(output_folder, exist_ok=True)

# File name like 'september-4.html'
filename = f"{month}-{day}.html"
file_path = os.path.join(output_folder, filename)

# Build HTML (always write a file so the workflow can commit something)
if not birthday_list:
    inner = "<p>No birthdays found.</p>"
else:
    items = "\n".join(
        f"<li>{desc} – {age} years old ({by})</li>"
        for (by, age, desc) in birthday_list
    )
    inner = f"<ul>\n{items}\n</ul>"

html = (
    "<div class='birthdays'>\n"
    f"<h3>🎉 Celebrity Birthdays – {today.strftime('%B %d')}</h3>\n"
    f"{inner}\n"
    "</div>\n"
)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Writing file to: {file_path}")
print(f"Found {len(birthday_list)} birthdays.")
