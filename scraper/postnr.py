"""
Postnummer → kommune → fylke-oppslag.

Laster ned Bring sitt postnummerregister én gang per kjøring og lager
en in-memory mapping. Filen er ANSI-kodet (Windows-1252) og TAB-separert.

Format: postnr<TAB>poststed<TAB>kommunenr<TAB>kommunenavn<TAB>kategori

Fylke utledes fra de to første sifrene i kommunenummeret.
"""

import logging
import re
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

logger = logging.getLogger(__name__)

BRING_URL = (
    "https://www.bring.no/radgivning/sende-noe/adressetjenester/postnummer/"
    "_/attachment/download/7f0186f6-cf90-4657-8b5b-70707abeb789:"
    "676b821de9cff02aaa7a009daf0af8a2a346a1bc/Postnummerregister-ansi.txt"
)

# Fylkesnummer (første to siffer i kommunenummer) → fylkesnavn.
# Gjeldende inndeling per 2024.
FYLKE_BY_PREFIX = {
    "03": "Oslo",
    "11": "Rogaland",
    "15": "Møre og Romsdal",
    "18": "Nordland",
    "31": "Østfold",
    "32": "Akershus",
    "33": "Buskerud",
    "34": "Innlandet",
    "39": "Vestfold",
    "40": "Telemark",
    "42": "Agder",
    "46": "Vestland",
    "50": "Trøndelag",
    "55": "Troms",
    "56": "Finnmark",
    # Eldre koder som fortsatt kan dukke opp i historiske data:
    "30": "Viken",     # Erstattet av Østfold/Akershus/Buskerud i 2024
    "38": "Vestfold og Telemark",
    "54": "Troms og Finnmark",
}

# Cache på modul-nivå
_postnr_to_kommune: dict[str, tuple[str, str]] = {}  # postnr -> (kommune, fylke)


def _load_postnr_data() -> None:
    """Laster Bring sin postnummer-fil til in-memory cache."""
    global _postnr_to_kommune
    if _postnr_to_kommune:
        return  # Allerede lastet

    logger.info(f"Henter postnummer-data fra Bring...")
    req = Request(BRING_URL, headers={"User-Agent": "kommer-for-salg-monitor/1.0"})
    try:
        with urlopen(req, timeout=30) as resp:
            data = resp.read().decode("windows-1252")
    except (URLError, HTTPError, TimeoutError) as e:
        logger.error(f"Kunne ikke laste postnummer-data: {e}")
        return

    count = 0
    for line in data.splitlines():
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        postnr, _poststed, kommunenr, kommunenavn = parts[0], parts[1], parts[2], parts[3]
        if not postnr or len(postnr) != 4:
            continue
        if not kommunenr or len(kommunenr) != 4:
            continue
        prefix = kommunenr[:2]
        fylke = FYLKE_BY_PREFIX.get(prefix, "Ukjent fylke")
        _postnr_to_kommune[postnr] = (
            kommunenavn.title().strip(),  # FRA "BÆRUM" TIL "Bærum"
            fylke,
        )
        count += 1

    logger.info(f"Lastet {count} postnummer fra Bring.")


def lookup_postnr(postnr: str) -> tuple[str | None, str | None]:
    """
    Returnerer (kommune, fylke) for et postnummer, eller (None, None).
    """
    if not _postnr_to_kommune:
        _load_postnr_data()
    return _postnr_to_kommune.get(postnr, (None, None))


def extract_postnr_from_address(address: str | None) -> str | None:
    """
    Plukker ut 4-sifret postnummer fra en adressestreng.

    Eksempler:
        'Thorvald Meyers gate 68, 0552 Oslo' → '0552'
        'Storgata 1, 1337 Sandvika' → '1337'
        'Fornebu' → None
    """
    if not address:
        return None
    # Søk etter 4-sifret tall etterfulgt av mellomrom og bokstav
    m = re.search(r"\b(\d{4})\s+[A-ZÆØÅa-zæøå]", address)
    if m:
        return m.group(1)
    return None


def resolve_municipality_and_fylke(address: str | None) -> tuple[str | None, str | None]:
    """
    Hovedfunksjonen: gitt en adresse, returner (kommune, fylke).
    """
    postnr = extract_postnr_from_address(address)
    if not postnr:
        return (None, None)
    return lookup_postnr(postnr)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Test
    test_cases = [
        "Thorvald Meyers gate 68, 0552 Oslo",
        "Rådmann Halmrasts vei 7-9, 1337 Sandvika",
        "Storgata 1, 5003 Bergen",
        "Bare et stedsnavn uten postnr",
    ]
    for addr in test_cases:
        k, f = resolve_municipality_and_fylke(addr)
        print(f"{addr[:60]:<60} → {k}, {f}")
