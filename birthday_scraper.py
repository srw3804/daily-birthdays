import os
import re
import datetime
import requests
from bs4 import BeautifulSoup

API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "daily-birthdays-script/1.0 (https://github.com/srw3804/daily-birthdays)"

# --- Regex patterns ---
FOOTNOTE_RE = re.compile(r"\s*\[\s*\d+\s*\]\s*")  # remove [5], [ 5 ], etc.
DECEASED_RE = re.compile(r"\((?:died|d\.)\s*\d{3,4}\)", re.IGNORECASE)
DASH_RE = re.compile(r"\s[–-]\s")
AMERICAN_RE = re.compile(r"\b(american|u\.s\.|united\s+states)\b", re.IGNORECASE)
# Generic nationality prefix remover (start of string, before profession)
NATIONALITY_RE = re.compile(r"^\s*(American|British|Canadian|Australian|Irish|German|French|Italian|Mexican|Chinese|Japanese|Russian|Spanish|Scottish|Welsh)\s+", re.IGNORECASE)

def clean_text(s: str) -> str:
    s = FOOTNOTE_RE.sub("", s)  # remove footnotes like [5]
    return " ".join(s.split())

def split_year_and_rest(li_text: str):
    parts = DASH_RE.split(li_text, maxsplit=1)
    if len(parts) != 2:
        return None, None
    y, rest = parts[0].strip(), parts[1].strip()
    try:
        year = int(y)
    except ValueError:
        return None, None
    return year, rest

def parse_name_and_details(rest: str):
    if "," not in rest:
        return clean_text(rest), ""
    name, details = rest.split(",", 1)
    return clean_text(name.strip()), clean_text(details.strip())

def normalize_details(details: str) -> str:
    # Strip leading nationality if present
    new_details = NATIONALITY_RE.sub("", details).strip()
    if not new_details:
        return ""
    # Capitalize first word to keep it looking natural
    new_details = new_details[0].upper() + new_details[1:]
    return new_details

def fetch_births_section_html(month: str, day: int) -> str | None:
    page = f"{month}_{day}"
    headers = {"User-Agent": USER_AGENT}

    # 1) Find the section index for "Births"
    params = {
        "action": "parse",
        "page": page,
        "prop": "sections",
        "redirects": "1",
        "format": "json",
        "formatversion": "2",
    }
    r = requests.get(API, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    sections = r.json().get("parse", {}).get("sections", [])
    births_idx = None
    for s in sections:
        if s.get("line", "").strip().lower() == "births":
            births_idx = s.get("index")
            break
    if births_idx is None:
        print("DEBUG: no 'Births' section index found via API")
        return None

    # 2) Pull that section’s HTML only
    params = {
        "action": "parse",
        "page": page,
        "section": births_idx,
        "prop": "text",
        "redirects": "1",
        "format": "json",
        "formatversion": "2",
    }
    r = requests.get(API, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json().get("parse", {}).get("text", "")

def get_living_american_birthdays(month: str, day: int):
    print(f"DEBUG: querying sections for {month} {day}")
    html = fetch_births_section_html(month, day)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    items = soup.find_all("li", recursive=True)
    print(f"DEBUG: collected {len(items)} raw <li> items in section")

    current_year = datetime.date.today().year
    results = []

    for li in items:
        raw = li.get_text(" ", strip=True)
        text = clean_text(raw)
        if not text:
            continue

        if DECEASED_RE.search(text):  # skip if marked as deceased
            continue

        year, rest = split_year_and_rest(text)
        if not year or not rest:
            continue

        name, details = parse_name_and_details(rest)
        if not name:
            continue

        # Only keep Americans
        american_field = f"{name} {details}"
        if not AMERICAN_RE.search(american_field):
            continue

        age = current_year - year
        details = normalize_details(details)
        results.append((name, age, year, details))

    print(f"DEBUG: parsed {len(results)} living American birthdays")
    return results

def main():
    today = datetime.date.today()
    month = today.strftime("%B")
    day = today.day

    bdays = get_living_american_birthdays(month, day)

    out_dir = os.path.join("docs", "birthdays")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{month.lower()}-{day}.html")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("<div class='birthdays'>\n")
        f.write(f"<h3>🎉 Celebrity Birthdays – {today.strftime('%B %d')}</h3>\n")
        f.write("<ul>\n")
        for name, age, year, details in bdays:
            line = f"{name} – {age} years old ({year})"
            if details:
                line += f" – {details}"
            f.write(f"  <li>{line}</li>\n")
        f.write("</ul>\n</div>\n")

    print(f"DEBUG: wrote {out_path} ({len(bdays)} living American birthdays)")

if __name__ == "__main__":
    main()
