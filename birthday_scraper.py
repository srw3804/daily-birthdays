# birthday_scraper.py
# Writes docs/birthdays/<month>-<day>.html for *today and tomorrow* each run.
# Test version: celebrity names link to their Wikipedia pages.

import os
import re
import datetime as dt
from typing import Optional, Tuple, List
import requests
from bs4 import BeautifulSoup

UA = "daily-birthdays/1.0 (+https://github.com/srw3804/daily-birthdays)"
API = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": UA}
DASH = "–"  # en dash

# ---------- Helpers ----------

def wiki_api(params: dict) -> dict:
    p = {"format": "json", "formatversion": "2"}
    p.update(params)
    r = requests.get(API, params=p, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()

def find_births_section_index(title: str) -> Optional[str]:
    data = wiki_api({"action": "parse", "page": title, "prop": "sections", "redirects": 1})
    for sec in data.get("parse", {}).get("sections", []):
        if (sec.get("line") or "").strip().lower() == "births":
            return sec.get("index")
    return None

def fetch_births_html(title: str, section_index: str) -> str:
    data = wiki_api({
        "action": "parse", "page": title, "prop": "text",
        "section": section_index, "redirects": 1
    })
    t = data.get("parse", {}).get("text", "")
    if isinstance(t, dict):
        return t.get("*", "")
    return t or ""

def strip_refs_and_footnotes(soup: BeautifulSoup) -> None:
    for sup in soup.select("sup.reference, sup"):
        sup.decompose()
    for node in soup.find_all(string=True):
        cleaned = re.sub(r"\[[^\]]*\]", "", node)
        if cleaned != node:
            node.replace_with(cleaned)

# --- Filters ---

_DEAD_RE = re.compile(
    r"(?:\b(died|death)\b|\(d\.?\s*\d{3,4}\)|\bd\.?\s*\d{3,4}\b|†\s*\d{3,4})",
    re.IGNORECASE,
)

def is_living(text: str) -> bool:
    return _DEAD_RE.search(text) is None

def is_americanish(text: str) -> bool:
    return re.search(r"\bAmerican\b|-American\b", text, re.IGNORECASE) is not None

def tidy_descriptor(desc: str) -> str:
    d = re.sub(r"\s+", " ", desc).strip(" –-—;,. ").strip()
    if d.lower().startswith("american "):
        d = d[9:].lstrip()
        if d:
            d = d[0].upper() + d[1:]
    return d

# --- Parsing ---

def parse_birth_item(li) -> Optional[Tuple[int, str, str]]:
    work = li.__copy__()
    strip_refs_and_footnotes(work)
    text = work.get_text(" ", strip=True)
    if not text:
        return None

    m_year = re.match(r"^(\d{3,4})\s*[–-]\s*(.+)$", text)
    if not m_year:
        return None

    year = int(m_year.group(1))
    rest = m_year.group(2)

    if not is_living(rest):
        return None

    rest = re.sub(r"\([^)]*\b(died|d\.)[^)]*\)", "", rest, flags=re.IGNORECASE).strip()

    if "," in rest:
        name, desc = rest.split(",", 1)
    else:
        parts = re.split(r"\s[–-]\s", rest, maxsplit=1)
        name = parts[0]
        desc = parts[1] if len(parts) == 2 else ""

    name = re.sub(r"\s+", " ", name).strip()
    desc_original = re.sub(r"\s+", " ", desc).strip()

    if not is_americanish(desc_original):
        return None

    desc_clean = tidy_descriptor(desc_original)
    return (year, name, desc_clean)

def format_entry(year: int, name: str, desc: str, target_date: dt.date) -> str:
    age = target_date.year - year
    # Build Wikipedia link for the name
    wiki_name = name.strip().replace(" ", "_")
    url = f"https://en.wikipedia.org/wiki/{wiki_name}"
    if desc:
        return f"<p><strong><a href='{url}' target='_blank' rel='noopener'>{name}</a></strong> {DASH} {age} years old ({year}) {DASH} {desc}</p>"
    else:
        return f"<p><strong><a href='{url}' target='_blank' rel='noopener'>{name}</a></strong> {DASH} {age} years old ({year})</p>"

# --- Generation ---

def month_name_from_int(m: int) -> str:
    return dt.date(2000, m, 1).strftime("%B")

def title_from_date(d: dt.date) -> str:
    return f"{d.strftime('%B')} {d.day}"

def generate_for_date(d: dt.date) -> List[str]:
    title = title_from_date(d)
    print(f"DEBUG: building for {title}")
    idx = find_births_section_index(title)
    if not idx:
        print(f"DEBUG: couldn't find Births section index for {title}")
        return []

    html = fetch_births_html(title, idx)
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("li")
    print(f"DEBUG: collected {len(items)} raw <li> items in section")

    out: List[str] = []
    for li in items:
        parsed = parse_birth_item(li)
        if not parsed:
            continue
        year, name, desc = parsed
        out.append(format_entry(year, name, desc, d))

    print(f"DEBUG: parsed {len(out)} living American birthdays")
    return out

def write_fragment(d: dt.date, entries: List[str]) -> None:
    outdir = os.path.join("docs", "birthdays")
    os.makedirs(outdir, exist_ok=True)
    fname = f"{d.strftime('%B').lower()}-{d.day}.html"
    path = os.path.join(outdir, fname)

    with open(path, "w", encoding="utf-8") as f:
        if entries:
            f.write("\n".join(entries) + "\n")
        else:
            f.write("<p><em>No birthdays found.</em></p>\n")
    print(f"DEBUG: wrote {path} ({len(entries)} entries)")

# --- Main ---

if __name__ == "__main__":
    today = dt.date.today()
    if os.getenv("BIRTH_MONTH") and os.getenv("BIRTH_DAY"):
        m = int(os.getenv("BIRTH_MONTH"))
        d = int(os.getenv("BIRTH_DAY"))
        base = dt.date(today.year, m, d)
    else:
        base = today

    for offset in (0, 1):  # today and tomorrow
        target = base + dt.timedelta(days=offset)
        entries = generate_for_date(target)
        write_fragment(target, entries)
