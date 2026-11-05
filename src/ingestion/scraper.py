import re
from urllib.parse import urlparse

import httpx
import trafilatura
from tenacity import retry, stop_after_attempt, wait_exponential

UA = "Mozilla/5.0 (compatible; MF-FAQ-Bot/1.0; +https://groww.in)"

# Label -> regex capturing the value on the following line(s) of visible text.
FACT_PATTERNS = {
    "Expense ratio": r"Expense ratio\s*\n\s*([^\n]+)",
    "Minimum SIP": r"Min\.\s*for\s*SIP\s*\n\s*([^\n]+)",
    "Minimum Lumpsum": r"Min\.\s*for\s*Lumpsum\s*\n\s*([^\n]+)",
    "Fund size (AUM)": r"Fund size\s*\(AUM\)\s*\n\s*([^\n]+)",
    "NAV": r"NAV:\s*([^\n]+)",
    "Rating": r"\nRating\s*\n\s*([0-9.]+)",
    "Benchmark": r"Fund benchmark\s*\n\s*([^\n]+)",
    "Fund house": r"Fund house\s*\n\s*([^\n]+)",
    "Exit load": r"(Exit load of [^\n]+)",
    "Lock-in": r"([^\n]*lock[-\s]?in[^\n]*)",
}

RISK_PATTERN = r"is rated ([A-Za-z ]+?) risk"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True)
def fetch_html(url: str, timeout: int = 30) -> str:
    r = httpx.get(
        url,
        headers={"User-Agent": UA, "Accept-Language": "en-IN,en;q=0.9"},
        timeout=timeout,
        follow_redirects=True,
    )
    r.raise_for_status()
    return r.text


def _visible_text(html: str) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    return soup.get_text("\n", strip=True)


def extract_facts(visible: str) -> dict[str, str]:
    facts: dict[str, str] = {}
    for label, pattern in FACT_PATTERNS.items():
        m = re.search(pattern, visible, flags=re.I)
        if m:
            value = re.sub(r"\s+", " ", m.group(1)).strip()
            if value and value.lower() not in ("more", "show more"):
                facts[label] = value

    if "Exit load" not in facts:
        m = re.search(r"Exit load\s*\n\s*(Nil)\b", visible, flags=re.I)
        if m:
            facts["Exit load"] = "Nil"
        else:
            m = re.search(r"Exit load\s*\n\s*(\d[^\n]*)", visible, flags=re.I)
            if m:
                facts["Exit load"] = re.sub(r"\s+", " ", m.group(1)).strip()

    m = re.search(RISK_PATTERN, visible, flags=re.I)
    if m:
        facts["Riskometer (risk level)"] = f"{m.group(1).strip()} risk"
    return facts


def _fact_block(facts: dict[str, str]) -> str:
    if not facts:
        return ""
    lines = [f"- {k}: {v}" for k, v in facts.items()]
    return "Key Facts (from official page):\n" + "\n".join(lines)


def _url_tokens(url: str) -> list[str]:
    slug = urlparse(url).path.strip("/").split("/")[-1]
    return [t for t in re.split(r"[^a-z0-9]+", slug.lower()) if len(t) > 2]


def _is_relevant(article: str, url: str) -> bool:
    tokens = _url_tokens(url)
    if not tokens:
        return True
    low = article.lower()
    hits = sum(1 for t in tokens if t in low)
    return hits / len(tokens) >= 0.35


def extract_main(html: str, url: str) -> tuple[str, str]:
    article = (
        trafilatura.extract(
            html,
            url=url,
            include_tables=True,
            include_links=False,
            favor_precision=True,
        )
        or ""
    ).strip()

    visible = _visible_text(html)
    facts = extract_facts(visible)

    body = article
    if len(article) < 200 or not _is_relevant(article, url):
        body = visible

    parts = [p for p in (_fact_block(facts), body) if p]
    text = "\n\n".join(parts).strip()

    title = url
    try:
        meta = trafilatura.extract_metadata(html)
        if meta and meta.title:
            title = meta.title.strip()
    except Exception:
        pass

    return title, text
