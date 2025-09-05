import os
import re
import datetime
import requests
from bs4 import BeautifulSoup

USER_AGENT = "daily-birthdays-script/1.0 (https://github.com/srw3804/daily-birthdays)"

# --- Helpers ---------------------------------------------------------------

DASH_RE = re.compile(r"\s[–-]\s")                 # en dash or hyphen surrounded by spaces
FOOTNOTE_RE = re.compile(r"\s*\[\d+\]")           # remove [12] style refs
DECEASED_RE = re.compile(r"\((?:died|d\.)\s*\d{3,4}\)", re.IGNORECASE)

def clean_text(s: str) -> str:
    """Normalize spaces, remove footnote refs."""
    s = FOOTNOTE_RE.sub("", s)
    s = " ".join(s.split())
    return s

def split_year_and_rest(li_text: str):
    """
    Wikipedia lines look like:
      '1942 – Merald "Bubba" Knight, American singer (Gladys Knight & the Pips)'
    Return (year:int, rest:str) or (None, None) if not parseable.
    """
    parts = DASH_RE.split(li_text, maxsplit=1)
    if len(parts) != 2:
        return None, None
    year_str, rest = parts[0].strip(), parts[1].strip()
    try:
        year = int(year_str)
    except ValueError:
        return None, None
    return year, rest

def parse_name_and_details(rest: str):
    """
    Split 'Name, details …' at the FIRST comma.
    Keep any parentheses in the details portion.
    """
    # Some lines have no comma (rare) -> treat whole thing as name.
    if "," not in rest:
        return clean_text(rest), ""
    name, details = rest.split(",", 1)
    return clean_text(name.strip()), clean_text(details.strip())

# --- Core scraper ----------------------------------------------------------

def get_living_birthdays(month: str, day: int):
    url = f"https://en.wikipedia.org/wiki/{month}_{day}"
    print(f"DEBUG: fetching birthdays for {month} {day} -> {url}")

    r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.content, "html.parser")

    # Find the <h2> that contains <span id="Births">
    births_span = soup.find("span", {"id": "Births"})
    if not births_span:
        print("DEBUG: couldn't find <span id='Births'>")
        return []

    births_h2 = births_span.find_parent("h2")
    if not births_h2:
        print("DEBUG: id='Births' not inside an <h2>; aborting")
        return []

    # Collect all <li> items from the first <ul> after this h2 up to the next h2.
    living = []
    current_year = datetime.date.today().year
    li_count = 0

    for sib in births_h2.find_all_next():
        # Stop at the next top-level H2 (next big section like 'Deaths')
        if sib.name == "h2" and sib is not births_h2:
            break
        if sib.name == "ul":
            for li in sib.find_all("li", recursive=False):
                li_text = clean_text(li.get_text(" ", strip=True))
                # Skip obviously deceased entries
                if DECEASED_RE.search(li_text):
                    continue

                year, rest = split_year_and_rest(li_text)
                if not year or not rest:
                    continue

                # Parse name + details
                name, details = parse_name_and_details(rest)
                if not name:
                    continue

                age = current_year - year
                living.append((name, age, year, details))
                li_count += 1

    print(f"DEBUG: collected {li_count} raw <li> items under Births")
    print(f"DEBUG: parsed {len(living)} living birthdays")
    return living

# --- Main: write today's file ---------------------------------------------

def main():
    today = datetime.date.today()
    month = today.strftime("%B")       # e.g., 'September'
    day = today.day

    birthday_list = get_living_birthdays(month, day)

    out_dir = os.path.join("docs", "birthdays")
    os.makedirs(out_dir, exist_ok=True)

    filename = f"{month.lower()}-{day}.html"
    out_path = os.path.join(out_dir, filename)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("<div class='birthdays'>\n")
        f.write(f"<h3>🎉 Celebrity Birthdays – {today.strftime('%B %d')}</h3>\n")
        f.write("<ul>\n")
        for name, age, year, details in birthday_list:
            # Blog-style line:
            # Name – 83 years old (1942) – Profession/Details
            line = f"{name} – {age} years old ({year})"
            if details:
                line += f" – {details}"
            f.write(f"  <li>{line}</li>\n")
        f.write("</ul>\n</div>\n")

    print(f"DEBUG: wrote {out_path} ({len(birthday_list)} living birthdays)")

if __name__ == "__main__":
    main()
