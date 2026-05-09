"""
Konfigurasjon for kommer-for-salg-monitor — hele Norge.

I stedet for å liste 357 kommuner, søker vi uten location-filter.
Finn returnerer da alle "Kommer for salg"-prosjekter i hele landet.
Kommune utledes fra postnummer i adresselinjen.
"""

# Tom liste betyr "ingen location-filter" — vi henter hele Norge.
MUNICIPALITIES = []

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

DELAY_BETWEEN_REQUESTS_S = 4
REQUEST_TIMEOUT_S = 25
