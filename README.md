# Kommer-for-salg-monitor — hele Norge

Daglig overvåkning av "Kommer for salg"-prosjekter på Finn.no for hele Norge.

I motsetning til andre versjoner (per-kommune-konfigurasjon), gjør denne ett enkelt søk uten location-filter — Finn returnerer da alle planned-prosjekter i hele landet på én sveip. Kommune og fylke utledes automatisk fra postnummer i adressen, ved hjelp av Brings offentlige postnummerregister.

## Slik virker det

1. GitHub Actions kjører kl 06:59 norsk tid (med backup 09:59)
2. Scraperen henter Finn-søkeresultatene uten location-filter, bare `sub_form_type=planned`
3. Ved oppstart lastes Brings postnummerregister inn i minne (~5000 postnumre)
4. For hvert prosjekt parses tidslinje, nøkkelinfo, beskrivelse, og kommune+fylke utledes fra postnummer
5. Snapshot lagres i `kommer-for-salg.db`
6. Endringer detekteres ved diff mot tidligere snapshot

## Dashbord

Tre nedtrekksmenyer som henger sammen:
- **Fylke** — alle 15 norske fylker
- **Kommune** — automatisk filtrert til kun kommuner i valgt fylke
- **Søk** — fritekst på tittel

Kart viser alle prosjekter i Norge med fargene per fylke. Endringer-fanen viser nye, forsvunne og oppdaterte prosjekter siste uke / måned.

## Forventet kjøretid

~250 prosjekter × 4 sek = 17 minutter for selve scrapingen, pluss 1-2 minutter for postnummer-data og dashbord-bygg. Totalt ca. 20 minutter — godt innenfor 60-minutters grensen i GitHub Actions.

## Begrensninger

- Postnummer som ikke finnes i Brings register vises som "Ukjent kommune"
- Adresser uten 4-sifret postnummer (f.eks. "Fornebu") får heller ikke kommune
- Fylkesinndelingen følger 2024-strukturen — eldre data kan ha "Viken", "Vestfold og Telemark", "Troms og Finnmark"
