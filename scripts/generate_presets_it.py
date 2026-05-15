#!/usr/bin/env python3
"""Generate an Italian preset localization sidecar.

The canonical matching source remains meta/presets.json. This script creates
meta/presets_it.json keyed by preset id, containing Italian display names and
search terms for UI/search localization.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRESETS = ROOT / "meta" / "presets.json"
DEFAULT_OUTPUT = ROOT / "meta" / "presets_it.json"


EXACT_NAMES = {
    "ATM": "Bancomat",
    "BBQ/Grill": "Barbecue",
    "BMX Track": "Pista BMX",
    "Baby Hatch/Safe Haven": "Culla per la vita",
    "Bar": "Bar",
    "Bench": "Panchina",
    "Bicycle Parking": "Parcheggio biciclette",
    "Bicycle Rental": "Noleggio biciclette",
    "Bicycle Repair Station": "Stazione riparazione biciclette",
    "Bicycle Shop": "Negozio di biciclette",
    "Biergarten": "Birreria all'aperto",
    "Bus Station": "Autostazione",
    "Bus Stop": "Fermata autobus",
    "Bus Stopping Location": "Fermata autobus",
    "Cafe": "Caffè",
    "Camp Site": "Campeggio",
    "Car Rental": "Autonoleggio",
    "Car Sharing": "Car sharing",
    "Car Wash": "Autolavaggio",
    "Charging Station": "Stazione di ricarica",
    "Cinema": "Cinema",
    "Convenience Store": "Minimarket",
    "Crosswalk": "Attraversamento pedonale",
    "Deli": "Gastronomia",
    "Dentist": "Dentista",
    "Dialysis Center": "Centro dialisi",
    "Dinner Theater": "Teatro con cena",
    "Doctor": "Medico",
    "Donation Center": "Centro donazioni",
    "Drinking Water": "Acqua potabile",
    "Drugstore": "Farmacia",
    "Fast Food": "Fast food",
    "Fire Station": "Caserma dei vigili del fuoco",
    "Fish & Chips Fast Food": "Fish and chips",
    "Gas Station": "Stazione di servizio",
    "Hospital": "Ospedale",
    "Hotel": "Hotel",
    "Hotel & Restaurant": "Hotel e ristorante",
    "Library": "Biblioteca",
    "Mall": "Centro commerciale",
    "Museum": "Museo",
    "Motel": "Motel",
    "Parking": "Parcheggio",
    "Pharmacy": "Farmacia",
    "Place of Worship": "Luogo di culto",
    "Police": "Polizia",
    "Post Box": "Cassetta postale",
    "Post Office": "Ufficio postale",
    "Pub": "Pub",
    "Public Transport Platform": "Piattaforma del trasporto pubblico",
    "Restaurant": "Ristorante",
    "School": "Scuola",
    "Supermarket": "Supermercato",
    "Taxi": "Taxi",
    "Theatre": "Teatro",
    "Toilets": "Servizi igienici",
    "Train Station": "Stazione ferroviaria",
    "Transit Stopping Location": "Fermata del trasporto pubblico",
    "Tram Stop": "Fermata tram",
    "Visitor Center": "Centro visitatori",
    "Veterinary": "Veterinario",
}


PHRASE_REPLACEMENTS = [
    ("Access Point", "Punto di accesso"),
    ("Administrative Boundary", "Confine amministrativo"),
    ("Advertising Column", "Colonna pubblicitaria"),
    ("Advertising Totem", "Totem pubblicitario"),
    ("Animal Shelter", "Rifugio per animali"),
    ("Apartment Building", "Condominio"),
    ("Art Gallery", "Galleria d'arte"),
    ("Arts Centre", "Centro artistico"),
    ("Baggage Claim", "Ritiro bagagli"),
    ("Bank", "Banca"),
    ("Beach Resort", "Stabilimento balneare"),
    ("Beauty Shop", "Centro estetico"),
    ("Betting Shop", "Agenzia scommesse"),
    ("Boarding Gate", "Gate d'imbarco"),
    ("Boat Rental", "Noleggio barche"),
    ("Book Store", "Libreria"),
    ("Border Control", "Controllo di frontiera"),
    ("Bowling Alley", "Bowling"),
    ("Bridge", "Ponte"),
    ("Building", "Edificio"),
    ("Butcher", "Macelleria"),
    ("Cable Car", "Funivia"),
    ("Camp Pitch", "Piazzola campeggio"),
    ("Car Dealer", "Concessionario auto"),
    ("Car Parts", "Ricambi auto"),
    ("Casino", "Casinò"),
    ("Castle", "Castello"),
    ("Cemetery", "Cimitero"),
    ("Changing Room", "Spogliatoio"),
    ("Chemist", "Parafarmacia"),
    ("Childcare", "Asilo nido"),
    ("Christian Church", "Chiesa cristiana"),
    ("City Gate", "Porta cittadina"),
    ("Climbing", "Arrampicata"),
    ("Clothes Shop", "Negozio di abbigliamento"),
    ("Coffee Shop", "Caffetteria"),
    ("Community Centre", "Centro civico"),
    ("Computer Shop", "Negozio di computer"),
    ("Confectionery", "Pasticceria"),
    ("Construction Site", "Cantiere"),
    ("Copy Shop", "Copisteria"),
    ("Courthouse", "Tribunale"),
    ("Craft Shop", "Negozio di artigianato"),
    ("Cycleway", "Pista ciclabile"),
    ("Department Store", "Grande magazzino"),
    ("Dive Centre", "Centro immersioni"),
    ("Dormitory", "Dormitorio"),
    ("Dry Cleaner", "Lavanderia a secco"),
    ("Electronics Shop", "Negozio di elettronica"),
    ("Emergency Phone", "Telefono di emergenza"),
    ("Escape Game", "Escape room"),
    ("Farm Shop", "Spaccio aziendale"),
    ("Farm", "Fattoria"),
    ("Fashion Accessories", "Accessori moda"),
    ("Ferry Terminal", "Terminal traghetti"),
    ("Fish & Chips", "Fish and chips"),
    ("Fitness Centre", "Palestra"),
    ("Florist", "Fioraio"),
    ("Food Court", "Area ristorazione"),
    ("Footbridge", "Ponte pedonale"),
    ("Footway", "Percorso pedonale"),
    ("Fountain", "Fontana"),
    ("Funeral Home", "Agenzia funebre"),
    ("Furniture Shop", "Negozio di mobili"),
    ("Garden Centre", "Centro giardinaggio"),
    ("Gift Shop", "Negozio di articoli da regalo"),
    ("Government Office", "Ufficio pubblico"),
    ("Greengrocer", "Fruttivendolo"),
    ("Guest House", "Affittacamere"),
    ("Hairdresser", "Parrucchiere"),
    ("Hardware Store", "Ferramenta"),
    ("Health Centre", "Centro sanitario"),
    ("Hotel & Restaurant", "Hotel e ristorante"),
    ("Hostel", "Ostello"),
    ("Ice Cream", "Gelateria"),
    ("Jewelry Store", "Gioielleria"),
    ("Kindergarten", "Scuola dell'infanzia"),
    ("Laundry", "Lavanderia"),
    ("Mobile Phone Shop", "Negozio di telefonia"),
    ("Motorcycle Parking", "Parcheggio motocicli"),
    ("Music School", "Scuola di musica"),
    ("Newsagent", "Edicola"),
    ("Nightclub", "Discoteca"),
    ("Optician", "Ottico"),
    ("Outdoor Shop", "Negozio outdoor"),
    ("Park", "Parco"),
    ("Parking Entrance", "Ingresso parcheggio"),
    ("Parking Space", "Posto auto"),
    ("Path", "Sentiero"),
    ("Pedestrian Street", "Area pedonale"),
    ("Pet Shop", "Negozio di animali"),
    ("Picnic Site", "Area picnic"),
    ("Playground", "Parco giochi"),
    ("Public Building", "Edificio pubblico"),
    ("Recycling", "Raccolta differenziata"),
    ("Residential Road", "Strada residenziale"),
    ("Rest Area", "Area di sosta"),
    ("Road", "Strada"),
    ("Seafood", "Pescheria"),
    ("Shoe Shop", "Negozio di scarpe"),
    ("Shopping Centre", "Centro commerciale"),
    ("Social Facility", "Servizio sociale"),
    ("Sports Centre", "Centro sportivo"),
    ("Stadium", "Stadio"),
    ("Station", "Stazione"),
    ("Street Lamp", "Lampione"),
    ("Swimming Pool", "Piscina"),
    ("Ticket Office", "Biglietteria"),
    ("Tourist Information", "Informazioni turistiche"),
    ("Town Hall", "Municipio"),
    ("Traffic Signals", "Semaforo"),
    ("Travel Agency", "Agenzia viaggi"),
    ("University", "Università"),
    ("Viewpoint", "Punto panoramico"),
    ("Water Park", "Parco acquatico"),
    ("Wayside Shrine", "Edicola votiva"),
    ("Wine Shop", "Enoteca"),
]


WORD_TRANSLATIONS = {
    "abandoned": "abbandonato",
    "access": "accesso",
    "accommodation": "alloggio",
    "administrative": "amministrativo",
    "advisor": "consulente",
    "agency": "agenzia",
    "agent": "agente",
    "advertising": "pubblicitario",
    "aerialway": "impianto a fune",
    "agricultural": "agricolo",
    "aid": "soccorso",
    "air": "aria",
    "aircraft": "aeromobile",
    "airport": "aeroporto",
    "alcohol": "alcolici",
    "all": "tutti",
    "alternative": "alternativa",
    "amenity": "servizio",
    "and": "e",
    "animal": "animale",
    "apparel": "abbigliamento",
    "apartment": "appartamento",
    "area": "area",
    "art": "arte",
    "artist": "artista",
    "assistance": "assistenza",
    "association": "associazione",
    "auto": "auto",
    "bakery": "panetteria",
    "bar": "bar",
    "barrier": "barriera",
    "basket": "cesto",
    "beach": "spiaggia",
    "beauty": "bellezza",
    "bench": "panchina",
    "bicycle": "bicicletta",
    "bike": "bici",
    "billiards": "biliardo",
    "board": "bacheca",
    "boat": "barca",
    "book": "libro",
    "boundary": "confine",
    "box": "cabina",
    "bridge": "ponte",
    "building": "edificio",
    "bunker": "bunker",
    "bus": "autobus",
    "business": "attività",
    "cafe": "caffè",
    "camp": "campeggio",
    "car": "auto",
    "care": "cura",
    "carpet": "tappeti",
    "channel": "canale",
    "center": "centro",
    "centre": "centro",
    "charging": "ricarica",
    "church": "chiesa",
    "city": "città",
    "civil": "civile",
    "clinic": "clinica",
    "closed": "chiuso",
    "club": "club",
    "coffee": "caffè",
    "college": "college",
    "clothing": "abbigliamento",
    "commercial": "commerciale",
    "community": "comunità",
    "company": "azienda",
    "companies": "aziende",
    "consultant": "consulente",
    "consulting": "consulenza",
    "control": "controllo",
    "construction": "costruzione",
    "contractor": "appaltatore",
    "course": "campo",
    "court": "campo",
    "crossing": "attraversamento",
    "crosswalk": "attraversamento pedonale",
    "dance": "danza",
    "dealer": "rivenditore",
    "dealership": "concessionario",
    "designated": "designato",
    "destination": "destinazione",
    "development": "sviluppo",
    "digital": "digitale",
    "disused": "in disuso",
    "dog": "cane",
    "drinking": "potabile",
    "drive": "drive",
    "dry": "secco",
    "education": "istruzione",
    "educational": "educativo",
    "electric": "elettrico",
    "electrical": "elettrico",
    "emergency": "emergenza",
    "energy": "energia",
    "engineer": "ingegnere",
    "engineers": "ingegneri",
    "engineering": "ingegneria",
    "entrance": "ingresso",
    "equipment": "attrezzature",
    "estate": "immobiliare",
    "event": "evento",
    "events": "eventi",
    "exercise": "esercizio",
    "exchange": "cambio",
    "factory": "fabbrica",
    "facility": "struttura",
    "family": "famiglia",
    "fast": "veloce",
    "ferry": "traghetto",
    "field": "campo",
    "financial": "finanziario",
    "fire": "vigili del fuoco",
    "fitness": "fitness",
    "forest": "bosco",
    "food": "cibo",
    "foot": "pedonale",
    "footway": "percorso pedonale",
    "fuel": "carburante",
    "garden": "giardino",
    "gate": "cancello",
    "gas": "gas",
    "golf": "golf",
    "government": "governo",
    "grass": "erba",
    "green": "verde",
    "greenhouse": "serra",
    "grounds": "area",
    "group": "gruppo",
    "gym": "palestra",
    "hair": "capelli",
    "hall": "sala",
    "health": "salute",
    "height": "altezza",
    "historic": "storico",
    "home": "casa",
    "horse": "cavallo",
    "horseback": "equitazione",
    "house": "casa",
    "housing": "abitazioni",
    "hut": "rifugio",
    "ice": "ghiaccio",
    "indoor": "interno",
    "industrial": "industriale",
    "industry": "industria",
    "information": "informazioni",
    "installation": "installazione",
    "instruction": "istruzione",
    "insurance": "assicurazione",
    "internet": "internet",
    "island": "isola",
    "law": "legale",
    "layer": "posa",
    "left": "sinistra",
    "legal": "legale",
    "light": "leggero",
    "lift": "impianto di risalita",
    "line": "linea",
    "link": "raccordo",
    "location": "posizione",
    "machine": "macchina",
    "maker": "produttore",
    "management": "gestione",
    "manufacturer": "produttore",
    "manufacturers": "produttori",
    "manufacturing": "produzione",
    "market": "mercato",
    "mast": "traliccio",
    "media": "media",
    "medical": "medico",
    "medicine": "medicina",
    "memorial": "monumento commemorativo",
    "metal": "metallo",
    "military": "militare",
    "mill": "mulino",
    "motor": "motore",
    "motorcycle": "motocicletta",
    "motorsport": "automobilismo",
    "mountain": "montagna",
    "museum": "museo",
    "natural": "naturale",
    "network": "rete",
    "no": "divieto",
    "node": "nodo",
    "occupational": "occupazionale",
    "of": "di",
    "office": "ufficio",
    "oil": "petrolio",
    "only": "solo",
    "official": "ufficiale",
    "organization": "organizzazione",
    "outdoor": "outdoor",
    "panel": "pannello",
    "parking": "parcheggio",
    "pediatric": "pediatrico",
    "personal": "personale",
    "pet": "animali",
    "photography": "fotografia",
    "physician": "medico",
    "pit": "fossa",
    "phone": "telefono",
    "place": "luogo",
    "planning": "pianificazione",
    "plant": "impianto",
    "plastic": "plastica",
    "play": "gioco",
    "platform": "piattaforma",
    "pole": "palo",
    "power": "energia",
    "printing": "stampa",
    "private": "privato",
    "production": "produzione",
    "professional": "professionale",
    "provider": "fornitore",
    "public": "pubblico",
    "railway": "ferrovia",
    "range": "campo",
    "real": "immobiliare",
    "recycling": "riciclaggio",
    "rental": "noleggio",
    "rentals": "noleggio",
    "repair": "riparazione",
    "residential": "residenziale",
    "restaurant": "ristorante",
    "right": "destra",
    "ride": "giostra",
    "riding": "equitazione",
    "room": "sala",
    "road": "strada",
    "route": "percorso",
    "rv": "camper",
    "sign": "segnale",
    "school": "scuola",
    "schools": "scuole",
    "security": "sicurezza",
    "service": "servizio",
    "services": "servizi",
    "shop": "negozio",
    "site": "sito",
    "ski": "sci",
    "social": "sociale",
    "solar": "solare",
    "sports": "sportivo",
    "stand": "postazione",
    "station": "stazione",
    "stop": "fermata",
    "stopping": "fermata",
    "store": "negozio",
    "street": "strada",
    "studio": "studio",
    "supplier": "fornitore",
    "supplies": "forniture",
    "supply": "fornitura",
    "surgery": "chirurgia",
    "surgeon": "chirurgo",
    "table": "tavolo",
    "tea": "tè",
    "temple": "tempio",
    "tax": "fiscale",
    "therapist": "terapista",
    "therapy": "terapia",
    "ticket": "biglietto",
    "toilets": "servizi igienici",
    "tower": "torre",
    "track": "pista",
    "traffic": "traffico",
    "trail": "sentiero",
    "training": "formazione",
    "train": "treno",
    "transport": "trasporto",
    "transportation": "trasporto",
    "tree": "albero",
    "truck": "camion",
    "turn": "svolta",
    "utility": "servizio",
    "vehicle": "veicolo",
    "vending": "distributore automatico",
    "veterinary": "veterinario",
    "video": "video",
    "water": "acqua",
    "waste": "rifiuti",
    "wholesaler": "grossista",
    "wholesalers": "grossisti",
    "wine": "vino",
    "yes": "sì",
}


TERM_TRANSLATIONS = {
    **WORD_TRANSLATIONS,
    "atm": "bancomat",
    "bank": "banca",
    "bar": "bar",
    "bathroom": "bagno",
    "bike": "bici",
    "bikes": "biciclette",
    "bus stop": "fermata autobus",
    "car park": "parcheggio",
    "charity": "beneficenza",
    "chemist": "farmacia",
    "coffee shop": "caffetteria",
    "convenience": "minimarket",
    "crosswalk": "strisce pedonali",
    "dinner show": "cena spettacolo",
    "dinner theater": "teatro con cena",
    "dinner theatre": "teatro con cena",
    "donation": "donazione",
    "donation center": "centro donazioni",
    "doctor": "medico",
    "drugstore": "farmacia",
    "gas": "benzina",
    "gas station": "stazione di servizio",
    "grocery": "alimentari",
    "loo": "bagno",
    "parking lot": "parcheggio",
    "petrol": "benzina",
    "pharmacy": "farmacia",
    "restaurant": "ristorante",
    "restroom": "bagno",
    "shop": "negozio",
    "store": "negozio",
    "supper club": "club con cena",
    "supermarket": "supermercato",
    "theatre restaurant": "teatro ristorante",
    "toilet": "bagno",
    "wc": "wc",
}


SEARCH_TERMS_BY_NAME = {
    "Restaurant": ["ristorante", "trattoria", "osteria", "pizzeria", "tavola calda"],
    "Cafe": ["caffè", "caffetteria", "bar", "coffee shop"],
    "Bar": ["bar", "locale", "cocktail bar"],
    "Pub": ["pub", "birreria", "bar"],
    "Fast Food": ["fast food", "paninoteca", "kebab", "hamburger", "take away"],
    "Ice Cream": ["gelateria", "gelato"],
    "Gas Station": ["stazione di servizio", "benzinaio", "distributore", "carburante"],
    "Pharmacy": ["farmacia", "parafarmacia", "medicinali"],
    "Supermarket": ["supermercato", "alimentari", "spesa"],
    "Convenience Store": ["minimarket", "alimentari", "negozio di alimentari"],
    "Hotel": ["hotel", "albergo"],
    "Guest House": ["affittacamere", "guest house", "pensione"],
    "Bus Stop": ["fermata autobus", "bus", "autobus"],
    "Train Station": ["stazione ferroviaria", "stazione treni", "treno"],
    "Parking": ["parcheggio", "posteggio", "sosta"],
    "Toilets": ["bagno", "servizi igienici", "toilette", "wc"],
    "Drinking Water": ["acqua potabile", "fontanella", "acqua"],
    "Police": ["polizia", "commissariato"],
    "Hospital": ["ospedale", "pronto soccorso"],
    "Post Office": ["ufficio postale", "posta"],
    "Post Box": ["cassetta postale", "buca delle lettere"],
    "Library": ["biblioteca"],
    "School": ["scuola"],
    "Museum": ["museo"],
    "Park": ["parco", "giardino"],
    "Donation Center": ["centro donazioni", "donazioni", "beneficenza", "carità"],
    "Dinner Theater": ["teatro con cena", "cena spettacolo", "teatro ristorante", "cabaret"],
}


TOKEN_RE = re.compile(r"[A-Za-z0-9]+|[/&()'-]")


def title_it(text: str) -> str:
    keep_lower = {"a", "al", "alla", "allo", "ai", "agli", "alle", "di", "del", "della", "dello", "dei", "degli", "delle", "per", "con", "in", "e", "o"}
    words = text.split()
    out = []
    for idx, word in enumerate(words):
        if idx > 0 and word.lower() in keep_lower:
            out.append(word.lower())
        elif word.isupper() and len(word) <= 4:
            out.append(word)
        else:
            out.append(word[:1].upper() + word[1:])
    return " ".join(out)


def translate_name(name: str) -> tuple[str, str]:
    if name in EXACT_NAMES:
        return EXACT_NAMES[name], "curated_exact"

    translated = name
    for source, target in sorted(PHRASE_REPLACEMENTS, key=lambda item: len(item[0]), reverse=True):
        translated = re.sub(rf"\b{re.escape(source)}\b", target, translated, flags=re.IGNORECASE)

    tokens = TOKEN_RE.findall(translated)
    if not tokens:
        return name, "fallback_original"

    out = []
    translated_any = translated != name
    for token in tokens:
        lower = token.lower()
        if lower in WORD_TRANSLATIONS:
            out.append(WORD_TRANSLATIONS[lower])
            translated_any = True
        else:
            out.append(token)

    if not translated_any:
        return title_it(name), "fallback_original"

    text = " ".join(out)
    text = text.replace(" / ", "/").replace(" ' ", "'").replace(" ( ", " (").replace(" )", ")")
    text = re.sub(r"\s+", " ", text).strip()
    return title_it(text), "curated_rules" if translated_any else "fallback_original"


def normalize_term(term: str) -> str:
    term = term.strip().lower()
    term = re.sub(r"\s+", " ", term)
    return term


def translate_term(term: str) -> str | None:
    source = normalize_term(term)
    if not source:
        return None
    if source in TERM_TRANSLATIONS:
        return normalize_term(TERM_TRANSLATIONS[source])
    words = re.findall(r"[A-Za-z0-9]+", source)
    if not words:
        return None
    translated_words = [TERM_TRANSLATIONS.get(word, WORD_TRANSLATIONS.get(word, word)) for word in words]
    return normalize_term(" ".join(translated_words))


def terms_for_preset(preset: dict, translated_name: str) -> list[str]:
    terms = {normalize_term(translated_name)}
    terms.update(normalize_term(term) for term in SEARCH_TERMS_BY_NAME.get(preset["name"], []))
    for key in ("terms", "natural_language_category"):
        for term in preset.get(key, []) or []:
            translated = translate_term(str(term))
            if translated:
                terms.add(translated)
    return sorted(term for term in terms if term)


def build(presets: list[dict]) -> dict[str, dict]:
    output: dict[str, dict] = {}
    for preset in presets:
        pid = str(preset["id"])
        name, quality = translate_name(str(preset["name"]))
        output[pid] = {
            "name": name,
            "terms": terms_for_preset(preset, name),
            "quality": quality,
        }
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--presets", default=DEFAULT_PRESETS)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    presets = json.loads(Path(args.presets).read_text(encoding="utf-8"))
    output = build(presets)
    Path(args.output).write_text(
        json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    counts: dict[str, int] = {}
    for item in output.values():
        counts[item["quality"]] = counts.get(item["quality"], 0) + 1
    print(f"wrote {args.output}: {len(output)} translations; quality={counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
