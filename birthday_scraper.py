import datetime
import requests
from bs4 import BeautifulSoup
import os
import re

def clean_text(text):
    """Remove Wikipedia reference markers like [5], [6]."""
    return re.sub(r'\[\d+\]', '', text).strip()

def get_birthdays(month: str, day: int):
    url = f"https://en.wikipedia.org/wiki/{month}_{day}"
    headers = {
        'User-Agent': 'daily-birthdays-script/1.0 (https://github.com/srw3804/daily-birthdays)'
    }
    print(f"DEBUG: fetching {url}")
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.content, 'html.parser')

    # Find the <h2> with id="Births"
    births_header = soup.find('h2', {'id': 'Births'})
    if not births_header:
        print("DEBUG: couldn't find <h2 id='Births'>")
        return []

    # The next <ul> after the <h2> contains the birthdays
    ul = births_header.find_next('ul')
    if not ul:
        print("DEBUG: no <ul> found after Births header")
        return []

    items = ul.find_all('li')
    print(f"DEBUG: found {len(items)} raw items under Births")

    birthdays = []
    current_year = datetime.datetime.now().year
    for item in items:
        text = clean_text(item.get_text(" ", strip=True))
        parts = text.split(" – ", 1)
        if len(parts) == 2:
            year_str, description = parts
            try:
                birth_year = int(year_str.strip())
                age = current_year - birth_year
                # Only keep if still alive
                if "died" not in description.lower():
                    # Format: Name – age years old (year) – description
                    formatted = f"{description} – {age} years old ({birth_year})"
                    birthdays.append(formatted)
            except ValueError:
                continue

    print(f"DEBUG: parsed {len(birthdays)} living birthdays")
    return birthdays


# Prepare today's date
today = datetime.date.today()
month = today.strftime("%B")
day = today.day

# Get birthday data
birthday_list = get_birthdays(month, day)

# Create output folder if missing
output_folder = "docs/birthdays"
os.makedirs(output_folder, exist_ok=True)

# Construct file name like 'september-5.html'
filename = f"{month.lower()}-{day}.html"
file_path = os.path.join(output_folder, filename)

# Write to HTML file
with open(file_path, "w", encoding="utf-8") as f:
    f.write("<div class='birthdays'>\n")
    f.write(f"<h3>🎉 Celebrity Birthdays – {today.strftime('%B %d')}</h3>\n")
    if birthday_list:
        f.write("<ul>\n")
        for line in birthday_list:
            f.write(f"<li>{line}</li>\n")
        f.write("</ul>\n")
    else:
        f.write("<p>No living birthdays found.</p>\n")
    f.write("</div>")

print(f"DEBUG: wrote {file_path} ({len(birthday_list)} living birthdays)")
