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
today = datetime.date.today()
month = today.strftime("%B")
day = today.day

# Get birthday data
birthday_list = get_birthdays(month, day)

# Create output folder if missing
output_folder = "birthdays"
os.makedirs(output_folder, exist_ok=True)

# Write to HTML file
with open(os.path.join(output_folder, "today.html"), "w", encoding="utf-8") as f:
    f.write("<div class='birthdays'>\n<h3>🎉 Celebrity Birthdays – ")
    f.write(today.strftime("%B %d"))
    f.write("</h3>\n<ul>\n")
    for birth_year, age, desc in birthday_list:
        f.write(f"<li>{desc} – {age} years old ({birth_year})</li>\n")
    f.write("</ul>\n</div>")
