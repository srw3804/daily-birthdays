import os
import re
import datetime
import requests
from bs4 import BeautifulSoup

UA = "daily-birthdays/1.0 (+https://github.com/srw3804/daily-birthdays)"
API = "https://en.wikipedia.org/w/api.php"

def wiki_api(params):
    p = {"format": "json"}
    p.update(params)
    r = requests.get(API, params=p, headers={"User-Agent": UA}, timeout=30)
    r.raise_for_status()
    return r.json()

def find_births_section_index(title: str) -> str | None:
    data = wiki_api({"action": "parse", "page": title, "prop": "sections"})
    for sec in data.get("parse", {}).get("sections", []):
        if sec.get("line") == "Births":
            return sec.get("index")
    return None

def fetch_births_html(title: str, section_index: str) -> str:
    data = wiki_api({
        "action": "parse",
        "page": title,
        "prop": "text",
        "section": section_index
    })
    return data["parse"]["text"]["*"]

def strip_refs_and_footnotes(soup: BeautifulSoup) -> None:
    for sup in soup.select("sup.reference, sup"):
        sup.decompose()
    for t in soup.find_all(string=True):
        cleaned = re.sub(r"\s*\[\d+\]\s*", " ", t)
        if cleaned != t:
            t.replace_with(cleaned)

# -------- Filters --------

_dead_patterns = [
    r"\b(died|death)\b",
    r"\b(d\.)\s*\d",          # d. 1988
    r"\((?:d|died)\s*\d",     # (d 1941)  (died 1999)
    r"†\s*\d",                # crosses sometimes used
]
_dead_re = re.compile("|".join(_dead_patterns), re.IGNORECASE)

def is_living(text: str) -> bool:
    return _dead_re.search(text) is None

def is_americanish(desc: str) -> bool:
    # Accept if "American" appears anywhere OR any -American hyphenated identity.
    # Evaluate BEFORE we remove a leading "American ".
    return re.search(r"\bAmerican\b|-American\b", desc) is not None

def tidy_descriptor(desc: str) -> str:
    desc = desc.strip(" –-—;,. ")
    # Remove a LEADING "American " for nicer output; keep hyphenated identities.
    if desc.lower().startswith("american "):
        desc = desc[9:].lstrip()
        if desc:
            desc = desc[0].upper() + desc[1:]
    return desc

# -------- Parsing --------

def parse_birth_item(li) -> tuple[int, str, str] | None:
    """
    Return (year, name, descriptor) or None if can't parse / not living / not American.
    """
    work = li.__copy__()
    strip_refs_and_footnotes(work)

    text = work.get_text(" ", strip=True)

    # YEAR – rest
    m_year = re.match(r"^(\d{1,4})\s*[–-]\s*(.+)$", text)
    if not m_year:
        return None
    year = int(m_year.group(1))
    rest = m_year.group(2)

    # If the line explicitly contains a death marker, skip it.
    if not is_living(rest):
        return None

    # Remove parenthetical death snippets anywhere, e.g. "(d 1941)" "(died 2001)"
    rest = re.sub(r"\([^)]*\b(?:d|died)\b[^)]*\)", "", rest, flags=re.IGNORECASE).strip()

    # Split into name + descriptor
    if "," in rest:
        name, desc = rest.split(",", 1)
    else:
        parts = re.split(r"\s[–-]\s", rest, maxsplit=1)
        name = parts[0]
        desc = parts[1] if len(parts) == 2 else ""

    name = name.strip()
    desc_original = desc.strip()

    # Require American(-ish)
    if not is_americanish(desc_original):
        return None

    desc = tidy_descriptor(desc_original)
    return (year, name, desc)

def format_entry(year: int, name: str, desc: str, target_date: datetime.date) -> str:
    age = target_date.year - year
    if desc:
        return f"<p><strong>{name}</strong> – {age} years old ({year}) – {desc}</p>"
    else:
        return f"<p><strong>{name}</strong> – {age} years old ({year})</p>"

def generate_for(month: int, day: int) -> list[str]:
    title = f"{datetime.date(2000, month, 1).strftime('%B')} {day}"
    sec_index = find_births_section_index(title)
    if not sec_index:
        print(f"DEBUG: couldn't find Births section index for {title}")
        return []

    html = fetch_births_html(title, sec_index)
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("li")
    print(f"DEBUG: collected {len(items)} raw <li> items in section")

    target_date = datetime.date(datetime.date.today().year, month, day)
    out = []
    for li in items:
        parsed = parse_birth_item(li)
        if not parsed:
            continue
        year, name, desc = parsed
        out.append(format_entry(year, name, desc, target_date))

    print(f"DEBUG: parsed {len(out)} living American birthdays")
    return out

if __name__ == "__main__":
    # Use today by default; allow overrides for manual tests
    today = datetime.date.today()
    month = int(os.getenv("BIRTH_MONTH") or today.strftime("%m"))
    day   = int(os.getenv("BIRTH_DAY") or today.strftime("%d"))

    entries = generate_for(month, day)

    outdir = os.path.join("docs", "birthdays")
    os.makedirs(outdir, exist_ok=True)
    month_name = datetime.date(2000, month, 1).strftime("%B").lower()
    path = os.path.join(outdir, f"{month_name}-{day}.html")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(entries) + ("\n" if entries else ""))

    print(f"DEBUG: wrote {path} ({len(entries)} entries)")
