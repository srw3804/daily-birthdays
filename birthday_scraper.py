import datetime
import os
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "daily-birthdays-script/1.0 (https://github.com/srw3804/daily-birthdays)"
}

def get_birthdays_for_date(month: str, day: int):
    """
    Scrape births from:
    https://en.wikipedia.org/wiki/Wikipedia:Selected_anniversaries/{Month}_{Day}
    """
    url = f"https://en.wikipedia.org/wiki/Wikipedia:Selected_anniversaries/{month}_{day}"
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    anchor = soup.select_one("span#Births")
    if not anchor:
        return []

    # go up to the heading containing the anchor (usually <h2> or <h3>)
    heading = anchor.parent
    while heading and heading.name not in ("h2", "h3"):
        heading = heading.parent

    if not heading:
        return []

    birthdays = []
    # iterate forward until the next section heading
    for sib in heading.next_siblings:
        # stop when we hit another section heading
        if getattr(sib, "name", None) in ("h2", "h3"):
            break
        # collect list items directly under ULs in this section
        if getattr(sib, "name", None) == "ul":
            for li in sib.find_all("li", recursive=False):
                text = " ".join(li.get_text(" ", strip=True).split())
                # split on en dash or em dash
                parts = (text.split(" – ", 1) if " – " in text else text.split(" — ", 1))
                if len(parts) == 2:
                    year_str, description = parts[0].strip(), parts[1].strip()
                    if year_str.isdigit():
                        year = int(year_str)
                        age = datetime.date.today().year - year
                        birthdays.append((year, age, description))

    return birthdays

# ---------- main: write to docs/birthdays/{month}-{day}.html ----------

today = datetime.date.today()

# For “september-4.html”-style filenames:
month_slug = today.strftime("%B").lower()
day_num = today.day

# For URL/page (Wikipedia expects Month capitalized, day without leading zero)
wiki_month = today.strftime("%B")
wiki_day = day_num

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
