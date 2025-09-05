import datetime
import requests
from bs4 import BeautifulSoup
import os
import re

def get_birthdays(month: str, day: int):
    url = f"https://en.wikipedia.org/wiki/{month}_{day}"
    print(f"DEBUG: fetching birthdays for {month} {day} -> {url}")

    headers = {
        'User-Agent': 'daily-birthdays-script/1.0 (https://github.com/srw3804/daily-birthdays)'
    }
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.content, 'html.parser')

    # Locate Births section by headline id
    headline = soup.find('span', {'id': 'Births'})
    if not headline:
        print("DEBUG: couldn't find <span id='Births'>")
        return []

    # Find the parent <h2> tag, then all <li> entries until next <h2>
    h2 = headline.find_parent('h2')
    items = []
    for sib in h2.find_next_siblings():
        if sib.name == 'h2':  # stop at the next main section
            break
        if sib.name == 'ul':
            items.extend(sib.find_all('li'))

    print(f"DEBUG: collected {len(items)} raw <li> items in section")

    birthdays = []
    current_year = datetime.datetime.now().year
    for item in items:
        text = item.get_text(" ", strip=True)
        if not text:
            continue

        # Split into "year – description"
        parts = text.split("–", 1)
        if len(parts) != 2:
            continue

        year_str, description = parts
        year_str = year_str.strip()
        description = description.strip()

        # Skip if "died" is in description → person is deceased
        if re.search(r"\bdied\b", description, re.IGNORECASE):
            continue

        try:
            birth_year = int(re.findall(r"\d{3,4}", year_str)[0])
        except Exception:
            continue

        age = current_year - birth_year
        birthdays.append((birth_year, age, description))

    print(f"DEBUG: parsed {len(birthdays)} living birthdays")
    return birthdays


# --- Main execution ---

today = datetime.date.today()
month = today.strftime("%B")
day = today.day

birthday_list = get_birthdays(month, day)

output_folder = "docs/birthdays"
os.makedirs(output_folder, exist_ok=True)

filename = f"{month.lower()}-{day}.html"
file_path = os.path.join(output_folder, filename)

# Write HTML (paragraph format, bold name, no heading, no bullets)
with open(file_path, "w", encoding="utf-8") as f:
    for birth_year, age, desc in birthday_list:
        # Split description into "Name – details"
        parts = desc.split("–", 1)
        if len(parts) == 2:
            name, details = parts
            line = f"<p><strong>{name.strip()}</strong> – {age} years old ({birth_year}) – {details.strip()}</p>\n"
        else:
            line = f"<p><strong>{desc.strip()}</strong> – {age} years old ({birth_year})</p>\n"
        f.write(line)

print(f"DEBUG: wrote {file_path} ({len(birthday_list)} living birthdays)")
