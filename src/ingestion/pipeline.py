import json
import pathlib
from datetime import datetime, timezone

from src.common.ids import content_hash, doc_id
from src.common.logging import get_logger
from src.config.schema import AppConfig

from .cleaner import normalize
from .scraper import extract_main, fetch_html

log = get_logger(__name__)


def load_document(
    cfg: AppConfig, url: str, scheme: str | None, page_type: str
) -> dict | None:
    did = doc_id(url)
    clean_dir = pathlib.Path(cfg.paths.clean)
    clean_path = clean_dir / f"{did}.json"

    html = fetch_html(url)
    title, text = extract_main(html, url)
    text = normalize(text)
    if not text:
        log.warning("empty extraction: %s", url)
        return None

    ch = content_hash(text)
    if clean_path.exists():
        try:
            old = json.loads(clean_path.read_text(encoding="utf-8"))
            if old.get("content_hash") == ch:
                log.info("unchanged, skip: %s", url)
                return old
        except json.JSONDecodeError:
            pass  # corrupt cache: overwrite below

    raw_dir = pathlib.Path(cfg.paths.raw)
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / f"{did}.html").write_text(html, encoding="utf-8")

    doc = {
        "doc_id": did,
        "url": url,
        "scheme": scheme,
        "page_type": page_type,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "content_hash": ch,
        "title": title,
        "text": text,
    }
    clean_dir.mkdir(parents=True, exist_ok=True)
    clean_path.write_text(
        json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log.info("saved %s | %s | %d chars", did, scheme or page_type, len(text))
    return doc
