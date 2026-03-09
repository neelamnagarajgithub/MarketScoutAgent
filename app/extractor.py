# app/extractor.py
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
import hashlib
import datetime
from typing import Optional

def extract_main_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    # remove scripts/styles
    for s in soup(["script", "style", "noscript", "iframe"]):
        s.decompose()
    # prefer article tags
    article = soup.find("article")
    if article:
        paragraphs = [p.get_text(strip=True) for p in article.find_all("p")]
    else:
        paragraphs = [p.get_text(strip=True) for p in soup.find_all("p")]
    text = "\n\n".join([p for p in paragraphs if p])
    # fallback to body text
    if not text:
        text = soup.get_text(separator="\n")
    return text.strip()

def canonical_datetime(dt_string: str) -> Optional[datetime.datetime]:
    if not dt_string:
        return None
    try:
        return date_parser.parse(dt_string)
    except Exception:
        return None

def compute_hash(text: str) -> str:
    if not text:
        return ""
    return hashlib.md5(text.encode("utf-8")).hexdigest()