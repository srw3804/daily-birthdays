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
    # remove citation footnotes like [5] and ref superscripts
    for sup in soup.select("sup.reference, sup"):
        sup.decompose()
    # also drop bracketed numbers that may linger in plain text
    for t in soup.find_all(text=True):
        cleaned = re.sub(r"\s*\[\d+\]\s*", " ", t)
        if cleaned != t:
            t.replace_with(cleaned)

def is_living(text: str) -> bool:
    # Exclude entries that obviously indicate death
    return not re.search(r"\b(died|d\.)\b", text, flags=re.IGNORECASE)

def tidy_descriptor(desc: str) -> str:
    desc = desc.strip(" –-—;,. ")
    # If descriptor begins with "American " exactly, drop it and capitalize next word
    if desc.lower().startswith("american "):
        desc = desc[9:].lstrip()
        if desc:
            desc = desc[0].upper() + desc[1:]
    return desc

def parse_birth_item(li) -> tuple[int, str, str] | None:
    """
    Return (year, name, descriptor) or None if we can't parse / not living.
    """
    # clone & clean a working copy
    li = li.__copy__()
    strip_refs_and_footnotes(li)

    text = li.get_text(" ", strip=True)
    # Expect pattern: "YEAR – Name, descriptor ..." (varies—but year is at start)
    m_year = re.match(r"^(\d{1,4})\s*[–-]\s*(.+)$", text)
    if not m_year:
        return None
    year = int(m_year.group(1))
    rest = m_year.group(2)

    if not is_living(rest):
        return None

    # Split name vs descriptor at the first comma
    if "," in rest:
        name, desc = rest.split(",", 1)
    else:
        # Fallback if no comma—use first en dash OR whole string
        parts = re.split(r"\s[–-]\s", rest, maxsplit=1)
        name = parts[0]
        desc = parts[1] if len(parts) == 2 else ""

    name = name.strip()
    desc = tidy_descriptor(desc)

    return (year, name, desc)

def format_entry(year: int, name: str, desc: str, target_date: datetime.date) -> str:
    age = target_date.year - year
    # Each entry as its own paragraph; name in bold
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

    print(f"DEBUG: parsed {len(out)} living birthdays")
    return out

if __name__ == "__main__":
    # Allow override for testing via env, otherwise "today"
    today = datetime.date.today()
    month = int(os.getenv("BIRTH_MONTH") or today.strftime("%m"))
    day = int(os.getenv("BIRTH_DAY") or today.strftime("%d"))

    entries = generate_for(month, day)

    # Write to docs/birthdays/{monthname-lower}-{day}.html with *no* heading
    outdir = os.path.join("docs", "birthdays")
    os.makedirs(outdir, exist_ok=True)
    month_name = datetime.date(2000, month, 1).strftime("%B").lower()
    path = os.path.join(outdir, f"{month_name}-{day}.html")

    with open(path, "w", encoding="utf-8") as f:
        if entries:
            f.write("\n".join(entries) + "\n")
        else:
            # Keep file but empty body if none; shortcode will just render nothing
            f.write("")

    print(f"DEBUG: wrote {path} ({len(entries)} entries)")
