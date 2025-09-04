import datetime
import requests
from bs4 import BeautifulSoup
import os

def get_birthdays(month: str, day: int):
    url = f"https://en.wikipedia.org/wiki/Wikipedia:Selected_anniversaries/{month}_{day}"
    headers = {
        'User-Agent': 'daily-birthdays-script/1.0 (https://github.com/srw3804/daily-birthdays)'
    }
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.content, 'html.parser')

    # Find "Births" section
    births_section = soup.find('span', {'id': 'Births'})
    if not births_section:
        return []

    ul = births_section.find_next('ul')
    items = ul.find_all('li')

    birthdays = []
    for item in items:
        text = item.get_text()
        parts = text.split('–', 1)
        if len(parts) == 2:
            year_str, description = parts
            try:
                birth_year = int(year_str.strip())
                age = datetime.datetime.now().year - birth_year
                birthdays.append((birth_year, age, description.strip()))
            except ValueError:
                continue

    return birthdays

# Prepare today's date
month = "september"
day = 4
today = datetime.date (2025, 9, 4)

# Get birthday data
birthday_list = get_birthdays(month.capitalize(), day)

print(f"Found {len(birthday_list)} birthdays.")

if not birthday_list:
    print("No birthdays found for today. Skipping file generation.")
    exit()

# Create output folder if missing
output_folder = "docs/birthdays"
os.makedirs(output_folder, exist_ok=True)

# Construct file name like 'september-4.html'
filename = f"{month}-{day}.html"
file_path = os.path.join(output_folder, filename)

# Write to HTML file
with open(file_path, "w", encoding="utf-8") as f:
    f.write("<div class='birthdays'>\n<h3>🎉 Celebrity Birthdays – ")
    f.write(today.strftime("%B %d"))
    f.write("</h3>\n<ul>\n")
    for birth_year, age, desc in birthday_list:
        f.write(f"<li>{desc} – {age} years old ({birth_year})</li>\n")
    f.write("</ul>\n</div>")
