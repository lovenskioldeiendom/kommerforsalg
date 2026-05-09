"""
Scraper for "Kommer for salg"-prosjekter på Finn — hele Norge.

Strategi: vi gjør ett enkelt søk uten location-filter, men med
sub_form_type=planned. Finn returnerer alle kommer-for-salg-prosjekter
i hele landet.

For hvert prosjekt utleder vi kommune og fylke fra postnummer i adressen.
"""

import argparse
import logging
import sys
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from .config import USER_AGENT, DELAY_BETWEEN_REQUESTS_S, REQUEST_TIMEOUT_S
from .parser import parse_planned_page, extract_planned_links_from_search
from .database import save_snapshot
from .postnr import resolve_municipality_and_fylke

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def fetch(url: str):
    req = Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "nb-NO,nb;q=0.9",
    })
    try:
        with urlopen(req, timeout=REQUEST_TIMEOUT_S) as resp:
            if resp.status != 200:
                logger.warning(f"HTTP {resp.status} for {url}")
                return None
            return resp.read().decode("utf-8", errors="replace")
    except HTTPError as e:
        logger.warning(f"HTTPError {e.code} for {url}")
        return None
    except (URLError, TimeoutError) as e:
        logger.warning(f"Network error for {url}: {e}")
        return None
    except Exception as e:
        logger.warning(f"Unexpected error for {url}: {e}")
        return None


def gather_all_planned_urls() -> list[str]:
    """
    Henter alle planned-prosjekter i hele Norge ved å pagine gjennom søket
    uten location-filter.
    """
    base = "https://www.finn.no/realestate/newbuildings/search.html"
    urls = set()
    page = 1
    max_pages = 30  # Sikkerhet — hver side har ~50 annonser, så 30 sider = 1500
    while page <= max_pages:
        url = f"{base}?sub_form_type=planned&page={page}"
        logger.info(f"Søkeside {page}: {url}")
        html = fetch(url)
        if not html:
            break
        page_urls = extract_planned_links_from_search(html)
        if not page_urls:
            logger.info(f"Side {page}: ingen lenker, stopper")
            break
        new_count = len(set(page_urls) - urls)
        urls.update(page_urls)
        logger.info(f"Side {page}: {len(page_urls)} lenker ({new_count} nye, totalt {len(urls)})")
        if new_count == 0:
            break
        page += 1
        time.sleep(DELAY_BETWEEN_REQUESTS_S)
    return sorted(urls)


def scrape_all(dry_run: bool = False, limit: int | None = None) -> dict:
    summary = {"found": 0, "scraped": 0, "errors": 0, "no_postnr": 0,
               "by_fylke": {}}

    project_urls = gather_all_planned_urls()
    summary["found"] = len(project_urls)
    logger.info(f"Fant {len(project_urls)} kommer-for-salg-prosjekter totalt")

    if limit:
        project_urls = project_urls[:limit]

    for i, url in enumerate(project_urls, 1):
        logger.info(f"{i}/{len(project_urls)}: {url}")
        html = fetch(url)
        if not html:
            summary["errors"] += 1
            continue

        try:
            project = parse_planned_page(html, source_url=url)
        except Exception as e:
            logger.warning(f"Parse-feil for {url}: {e}")
            summary["errors"] += 1
            continue

        if not project.get("finn_code"):
            logger.info(f"  mangler finn-kode, hopper over")
            continue

        # Utled kommune og fylke fra postnummer
        kommune, fylke = resolve_municipality_and_fylke(project.get("address"))
        if not kommune:
            summary["no_postnr"] += 1
            logger.info(f"  ingen postnummer i adressen, kommune ukjent")

        if not dry_run:
            try:
                save_snapshot(kommune, fylke, project, url)
            except Exception as e:
                logger.warning(f"DB-feil for {url}: {e}")
                summary["errors"] += 1
                continue

        summary["scraped"] += 1
        f = fylke or "Ukjent"
        summary["by_fylke"][f] = summary["by_fylke"].get(f, 0) + 1
        time.sleep(DELAY_BETWEEN_REQUESTS_S)

    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    summary = scrape_all(dry_run=args.dry_run, limit=args.limit)

    logger.info("━━━ OPPSUMMERING ━━━")
    logger.info(f"  Funnet: {summary['found']}")
    logger.info(f"  Scrapet: {summary['scraped']}")
    logger.info(f"  Errors: {summary['errors']}")
    logger.info(f"  Uten postnummer: {summary['no_postnr']}")
    logger.info(f"  Per fylke:")
    for fylke, count in sorted(summary["by_fylke"].items(), key=lambda x: -x[1]):
        logger.info(f"    {fylke}: {count}")


if __name__ == "__main__":
    main()
