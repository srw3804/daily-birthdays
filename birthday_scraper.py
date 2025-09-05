import os
import re
import datetime
import requests
from bs4 import BeautifulSoup

UA = "daily-birthdays-bot/1.0 (+https://github.com/srw3804/daily-birthdays)"
HEADERS = {"User-Agent": UA}
API = "https://en.wikipedia.org/w/api.php"

TODAY = datetime.date.today()
MONTH = TODAY.strftime("%B")
DAY = TODAY.day
CURRENT_YEAR = TODAY.year

OUT_DIR = os.path.join("docs", "birthdays")
os.makedirs(OUT_DIR, exist_ok=True)
OUT_PATH = os.path.join(OUT_DIR, f"{MONTH.lower()}-{DAY}.html")

def debug(msg: str):
    print(f"DEBUG: {msg}")

def clean_text(s: str) -> str:
    # Remove footnote markers like [1], [12]
    s = re.sub(r"\[\d+\]", "", s)
    # Collapse spaces
    s = re.sub(r"\s+", " ", s).strip()
    return s

def api_get(params: dict) -> dict:
    r = requests.get(API, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()

def fetch_births_html_via_api(month: str, day: int) -> str | None:
    title = f"{month}_{day}"
    # 1) discover sections
    debug(f"querying sections for {month} {day}")
    data = api_get({
        "action": "parse",
        "page": title,
        "prop": "sections",
        "format": "json",
        "redirects": 1
    })
    if "parse" not in data:
        return None

    sections = data["parse"].get("sections", [])
    births_idx = None
    for s in sections:
        # the section title text for Births is "Births"
        if s.get("line") == "Births":
            births_idx = s.get("index")
            break

    if not births_idx:
        return None

    # 2) fetch just the births section HTML
    debug(f"fetching section index {births_idx} (Births)")
    section_data = api_get({
        "action": "parse",
        "page": title,
        "prop": "text",
        "section": births_idx,
        "format": "json",
        "redirects": 1
    })
    html = section_data.get("parse", {}).get("text", {}).get("*", "")
    return html or None

def fetch_births_html_fallback(month: str, day: int) -> str | None:
    # very last-resort direct HTML (rarely used)
    url = f"https://en.wikipedia.org/wiki/{month}_{day}"
    debug(f"fetching {url}")
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    # find headline for Births
    h2 = None
    for tag in soup.select("h2"):
        span = tag.find("span", class_="mw-headline")
        if span and span.get("id") == "Births":
            h2 = tag
            break
    if not h2:
        return None
    # everything until next h2 belongs to this section
    html_parts = []
    for sib in h2.find_all_next():
        if sib.name == "h2":
            break
        html_parts.append(str(sib))
    return "".join(html_parts)

def parse_births(html: str) -> list[tuple[int, int, str]]:
    """
    Returns list of (birth_year, age, description_string)
    Description format we’ll turn into: Name, details...
    """
    soup = BeautifulSoup(html, "html.parser")

    # Get top-level <li> items under this section (not nested inside other li)
    lis = [li for li in soup.find_all("li") if li.find_parent("li") is None]
    debug(f"collected {len(lis)} raw <li> items in section")

    results = []
    for li in lis:
        text = clean_text(li.get_text(" ", strip=True))
        if not text:
            continue

        # Split on first en dash (Wikipedia uses U+2013)
        if " – " not in text:
            continue
        year_str, rest = text.split(" – ", 1)

        # birth year as int
        try:
            birth_year = int(year_str.strip())
        except ValueError:
            continue

        # exclude deceased: patterns like “(d. 2010)” or “…, died 2010 …”
        low = rest.lower()
        if re.search(r"\((?:d\.|died)\s*\d{3,4}\)", low) or re.search(r"\b(died|d\.)\s*\d{3,4}", low):
            continue

        # keep only entries that mention "American" somewhere (case-insensitive)
        if "american" not in low:
            continue

        # remove a standalone "American " when it’s not hyphenated (keeps Chinese-American, etc.)
        # - remove “, American …” or “ American …” but not “-American”
        rest_clean = re.sub(r"(?i)(?<!-)\bAmerican\b\s+", "", rest).strip()
        rest_clean = clean_text(rest_clean)

        # separate name and details at first comma if present
        if "," in rest_clean:
            name, details = rest_clean.split(",", 1)
        else:
            # fallback: if no comma, try splitting on " – " again
            parts = rest_clean.split(" – ", 1)
            name = parts[0]
            details = parts[1] if len(parts) == 2 else ""

        name = clean_text(name)
        details = clean_text(details)

        # capitalize first letter of details (profession/extra)
        if details:
            details = details[0].upper() + details[1:]

        age = CURRENT_YEAR - birth_year
        # Ensure age makes sense
        if age <= 0 or age > 120:
            continue

        description = f"{name}, {details}" if details else name
        results.append((birth_year, age, description))

    debug(f"parsed {len(results)} living birthdays")
    return results

def write_html(birthdays: list[tuple[int, int, str]]):
    # Paragraph list, bold name, no heading (matches your blog style)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        if not birthdays:
            f.write("<p><em>No birthdays found.</em></p>\n")
            return
        for birth_year, age, desc in birthdays:
            # desc is "Name, Details…"
            if "," in desc:
                name, details = desc.split(",", 1)
                line = f"<p><strong>{name.strip()}</strong> – {age} years old ({birth_year}) – {details.strip()}</p>\n"
            else:
                line = f"<p><strong>{desc.strip()}</strong> – {age} years old ({birth_year})</p>\n"
            f.write(line)

def main():
    debug(f"fetching birthdays for {MONTH} {DAY} -> https://en.wikipedia.org/wiki/{MONTH}_{DAY}")
    html = fetch_births_html_via_api(MONTH, DAY)
    if not html:
        debug("API path failed; trying HTML fallback")
        html = fetch_births_html_fallback(MONTH, DAY)
    if not html:
        debug("could not obtain Births HTML")
        write_html([])
        return

    birthdays = parse_births(html)
    write_html(birthdays)
    debug(f"wrote {OUT_PATH} ({len(birthdays)} living birthdays)")

if __name__ == "__main__":
    main()
