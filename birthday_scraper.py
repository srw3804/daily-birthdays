import datetime
import requests
from bs4 import BeautifulSoup
import os
import re
from zoneinfo import ZoneInfo

def get_birthdays(month: str, day: int):
    url = f"https://en.wikipedia.org/wiki/{month}_{day}"
    headers = {
        'User-Agent': 'daily-birthdays-script/1.0 (https://github.com/srw3804/daily-birthdays)'
    }
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.content, 'html.parser')

    # Find the "Births" section
    births_span = soup.find('span', {'id': 'Births'})
    if not births_span:
        print("DEBUG: Births section not found")
        return []

    ul = births_span.find_next('ul')
    if not ul:
        print("DEBUG: Births list not found")
        return []

    items = ul.find_all('li', recursive=False)
    birthdays = []

    for item in items:
        text = item.get_text(" ", strip=True)
        # Match leading year (3–4 digits)
        m = re.match(r'^(\d{3,4})\s*[–-]\s*(.*)', text)
        if m:
            birth_year = int(m.group(1))
            desc = m.group(2).strip()
            age = datetime.datetime.now().year - birth_year
            birthdays.append((birth_year, age, desc))

    return birthdays

# --- MAIN SCRIPT ---

today = datetime.datetime.now(ZoneInfo("America/Detroit")).date()
month = today.strftime("%B")
day = today.day

birthday_list = get_birthdays(month, day)

output_folder = "docs/birthdays"
os.makedirs(output_folder, exist_ok=True)

filename = f"{month.lower()}-{day}.html"
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

print(f"DEBUG: parsed {len(birthday_list)} birthdays")
