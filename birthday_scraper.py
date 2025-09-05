# birthday_scraper.py
import os
import re
import datetime
import requests
from bs4 import BeautifulSoup

USER_AGENT = "daily-birthdays-script/1.0 (+https://github.com/srw3804/daily-birthdays)"

def fetch_birthdays_for(month_name: str, day: int):
    """
    Fetch birthdays for a given month/day from https://en.wikipedia.org/wiki/Month_Day
    Returns a list of tuples: (birth_year:int, age:int, description:str)
    """
    # Wikipedia day page (NOT the Selected_anniversaries page)
    url = f"https://en.wikipedia.org/wiki/{month_name}_{day}"

    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")

    # Find the "Births" section (it's usually an <h2> with a <span id="Births">)
    births_anchor = soup.find("span", {"id": "Births"})
    if not births_anchor:
        return []

    # Collect all <li> items under the Births section until the next <h2>
    birthdays = []
    ul = births_anchor.find_parent().find_next_sibling()

    lis = []
    while ul and ul.name != "h2":
        if ul.name == "ul":
            lis.extend(ul.find_all("li", recursive=False))
        ul = ul.find_next_sibling()

    # Split on first dash (en dash, em dash, or hyphen)
    dash_pattern = re.compile(r"\s*[–—-]\s*", re.UNICODE)
    ref_pattern = re.compile(r"\[\d+\]")  # remove citation markers like [1], [12]

    current_year = datetime.datetime.utcnow().year

    for li in lis:
        text = ref_pattern.sub("", li.get_text(" ", strip=True))
        parts = dash_pattern.split(text, maxsplit=1)
        if len(parts) != 2:
            continue
        year_str, description = parts[0].strip(), parts[1].strip()

        # Year should be an int; skip ranges like "c. 350" or "AD 12"
        try:
            birth_year = int(re.sub(r"[^\d]", "", year_str))
        except ValueError:
            continue

        # Compute age (skip obviously future/invalid years)
        if 0 < birth_year <= current_year:
            age = current_year - birth_year
        else:
            continue

        birthdays.append((birth_year, age, description))

    return birthdays

def main():
    # Today's date (UTC)
    today = datetime.datetime.utcnow().date()
    month_name_cap = today.strftime("%B")       # e.g., "September"
    month_slug = month_name_cap.lower()         # e.g., "september"
    day = today.day

    items = fetch_birthdays_for(month_name_cap, day)

    # Ensure output folder exists for GitHub Pages
    output_dir = os.path.join("docs", "birthdays")
    os.makedirs(output_dir, exist_ok=True)

    # File name like "september-4.html"
    filename = f"{month_slug}-{day}.html"
    out_path = os.path.join(output_dir, filename)

    # Write HTML
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("<div class='birthdays'>\n")
        f.write(f"<h3>🎉 Celebrity Birthdays – {month_name_cap} {day:02d}</h3>\n")

        if not items:
            f.write("<p>No birthdays found.</p>\n</div>\n")
            return

        f.write("<ul>\n")
        for birth_year, age, desc in items:
            f.write(f"<li>{desc} – {age} years old ({birth_year})</li>\n")
        f.write("</ul>\n</div>\n")

if __name__ == "__main__":
    main()
