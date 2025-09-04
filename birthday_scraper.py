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
                birthdays.append((birth_year, age, d_
