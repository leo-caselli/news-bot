#!/usr/bin/env python3
import os, datetime, textwrap, feedparser, requests, html
from bs4 import BeautifulSoup                        # for simple text extraction

# 1️⃣  Load feeds
with open("feeds.txt", encoding="utf‑8") as f:
    FEEDS = [l.strip() for l in f if l.strip() and not l.startswith("#")]

# 2️⃣  Helper: pull article text (first 1,500 chars for speed)
def extract_text(url, limit=1500):
    try:
        html_doc = requests.get(url, timeout=10).text
        soup = BeautifulSoup(html_doc, "html.parser")
        # crude but works: drop scripts/styles, join paragraphs
        for tag in soup(["script", "style"]): tag.decompose()
        text = " ".join(p.get_text(" ", strip=True) for p in soup.find_all("p"))
        return text[:limit]
    except Exception as e:
        return ""

# 3️⃣  Very‑light summariser (first sentence OR TextRank fallback)
def summarize(text, max_sent=2):
    if not text: return ""
    sentences = textwrap.wrap(text, width=800)  # crude split
    summary = ". ".join(sentences[0:max_sent])
    return html.unescape(summary).strip()

# 4️⃣  Collect today’s items 🗞️
today = datetime.datetime.utcnow()
cutoff = today - datetime.timedelta(hours=24)
sections = {"World": [], "Italy": [], "Politics": [], "Economy": [], "Other": []}

for feed in FEEDS:
    parsed = feedparser.parse(feed)
    for e in parsed.entries:
        # Ignore stale stories
        if "published_parsed" in e and datetime.datetime(*e.published_parsed[:6]) < cutoff:
            continue
        # Fetch & summarise
        plaintext = extract_text(e.link)
        blurb = summarize(plaintext)
        # Categorise (very simple—you can refine keywords later)
        sec = "Italy" if "Italy" in feed or ".it" in feed else "World"
        headline = f"• **{e.title}** – {blurb or e.summary[:120]} … ({e.link})"
        sections[sec].append(headline)

# 5️⃣  Build bulletin
date_str = today.strftime("%A %d %B %Y")
bulletin = [f"🗞️  *Daily News Bulletin*  – {date_str}", ""]
for sec, items in sections.items():
    if not items: continue
    bulletin.append(f"__{sec}__")
    bulletin.extend(items[:5])          # up to 5 per section
    bulletin.append("")                 # blank line
BODY = "\n".join(bulletin).strip()

# 6️⃣  Push via Shortcuts
import base64, json, urllib.parse
req = urllib.parse.urlencode({"body": BODY})
requests.get(os.environ["PUSH_URL"] + "?" + req)
