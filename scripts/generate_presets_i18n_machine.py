#!/usr/bin/env python3
"""Generate preset localization sidecars with phrase-level machine translation.

The canonical matching source remains meta/presets.json. This script writes a
sidecar keyed by preset id with localized display names and search terms. It
intentionally translates only canonical preset names and terms; it does not use
natural_language_category.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRESETS = ROOT / "meta" / "presets.json"
DEFAULT_CACHE = ROOT / "tmp" / "preset_i18n_translation_cache.json"

SUPPORTED_LANGUAGES = {"es", "it", "ko"}

CURATED_NAMES = {
    "es": {
        "ATM": "Cajero automático",
        "BBQ/Grill": "Parrilla",
        "Cable Car": "Teleférico",
        "Cafe": "Cafetería",
        "Convenience Store": "Tienda de conveniencia",
        "Dialysis Center": "Centro de diálisis",
        "Dinner Theater": "Teatro con cena",
        "Donation Center": "Centro de donaciones",
        "Drinking Water": "Agua potable",
        "Fish & Chips Fast Food": "Fish and chips",
        "Gas Station": "Gasolinera",
        "Hotel & Restaurant": "Hotel y restaurante",
        "Place of Worship": "Lugar de culto",
        "Public Transport Platform": "Andén de transporte público",
        "Transit Stopping Location": "Parada de transporte público",
        "Visitor Center": "Centro de visitantes",
    },
    "it": {
        "ATM": "Bancomat",
        "BBQ/Grill": "Barbecue",
        "Cable Car": "Funivia",
        "Cafe": "Caffè",
        "Convenience Store": "Minimarket",
        "Dialysis Center": "Centro dialisi",
        "Dinner Theater": "Teatro con cena",
        "Donation Center": "Centro donazioni",
        "Drinking Water": "Acqua potabile",
        "Fish & Chips Fast Food": "Fish and chips",
        "Gas Station": "Stazione di servizio",
        "Hotel & Restaurant": "Hotel e ristorante",
        "Place of Worship": "Luogo di culto",
        "Public Transport Platform": "Piattaforma del trasporto pubblico",
        "Transit Stopping Location": "Fermata del trasporto pubblico",
        "Visitor Center": "Centro visitatori",
    },
    "ko": {
        "ATM": "ATM",
        "BBQ/Grill": "바비큐장",
        "Cable Car": "케이블카",
        "Cafe": "카페",
        "Convenience Store": "편의점",
        "Dialysis Center": "투석 센터",
        "Dinner Theater": "디너 극장",
        "Donation Center": "기부 센터",
        "Drinking Water": "식수대",
        "Fish & Chips Fast Food": "피시앤칩스",
        "Gas Station": "주유소",
        "Hotel & Restaurant": "호텔 및 식당",
        "Place of Worship": "종교 시설",
        "Public Transport Platform": "대중교통 승강장",
        "Transit Stopping Location": "대중교통 정차 위치",
        "Visitor Center": "방문자 센터",
    },
}

CURATED_TERMS = {
    "es": {
        "amenity": "servicio",
        "charity": "caridad",
        "dinner show": "cena espectáculo",
        "dinner theater": "teatro con cena",
        "dinner theatre": "teatro con cena",
        "donation": "donación",
        "donation center": "centro de donaciones",
        "chips fast": "fish and chips",
        "fish": "pescado",
        "fish chip": "fish and chips",
        "fish and chip eatery": "fish and chips",
        "fish and chips fast": "fish and chips",
        "fish chips": "fish and chips",
        "fish chips fast food": "fish and chips",
        "fish fry": "pescado frito",
        "gas station": "gasolinera",
        "supper club": "club con cena",
        "theatre restaurant": "teatro restaurante",
    },
    "it": {
        "amenity": "servizio",
        "charity": "beneficenza",
        "dinner show": "cena spettacolo",
        "dinner theater": "teatro con cena",
        "dinner theatre": "teatro con cena",
        "donation": "donazione",
        "donation center": "centro donazioni",
        "chips fast": "fish and chips",
        "fish": "pesce",
        "fish chip": "fish and chips",
        "fish and chip eatery": "fish and chips",
        "fish and chips fast": "fish and chips",
        "fish chips": "fish and chips",
        "fish chips fast food": "fish and chips",
        "fish fry": "frittura di pesce",
        "gas station": "stazione di servizio",
        "supper club": "club con cena",
        "theatre restaurant": "teatro ristorante",
    },
    "ko": {
        "amenity": "편의시설",
        "charity": "자선",
        "dinner show": "디너 쇼",
        "dinner theater": "디너 극장",
        "dinner theatre": "디너 극장",
        "donation": "기부",
        "donation center": "기부 센터",
        "chips fast": "피시앤칩스",
        "fish": "생선",
        "fish chip": "피시앤칩스",
        "fish chips": "피시앤칩스",
        "fish fry": "생선튀김",
        "gas station": "주유소",
        "supper club": "디너 클럽",
        "theatre restaurant": "극장식 식당",
    },
}

SEARCH_TERMS_BY_NAME = {
    "es": {
        "Restaurant": ["restaurante", "comedor", "tapas", "bar"],
        "Cafe": ["cafetería", "café", "coffee shop"],
        "Gas Station": ["gasolinera", "estación de servicio", "combustible"],
        "Pharmacy": ["farmacia", "medicamentos"],
        "Supermarket": ["supermercado", "mercado", "comestibles"],
        "Convenience Store": ["tienda de conveniencia", "minimarket", "tienda"],
        "Toilets": ["baño", "aseos", "servicios", "wc"],
        "Donation Center": ["centro de donaciones", "donaciones", "caridad"],
        "Dinner Theater": ["teatro con cena", "cena espectáculo", "teatro restaurante"],
    },
    "it": {
        "Restaurant": ["ristorante", "trattoria", "osteria", "pizzeria", "tavola calda"],
        "Cafe": ["caffè", "caffetteria", "bar", "coffee shop"],
        "Gas Station": ["stazione di servizio", "benzinaio", "distributore", "carburante"],
        "Pharmacy": ["farmacia", "parafarmacia", "medicinali"],
        "Supermarket": ["supermercato", "alimentari", "spesa"],
        "Convenience Store": ["minimarket", "alimentari", "negozio di alimentari"],
        "Toilets": ["bagno", "servizi igienici", "toilette", "wc"],
        "Donation Center": ["centro donazioni", "donazioni", "beneficenza", "carità"],
        "Dinner Theater": ["teatro con cena", "cena spettacolo", "teatro ristorante", "cabaret"],
    },
    "ko": {
        "Restaurant": ["음식점", "식당", "맛집", "레스토랑"],
        "Cafe": ["카페", "커피", "커피숍"],
        "Gas Station": ["주유소", "충전소", "연료"],
        "Pharmacy": ["약국", "약"],
        "Supermarket": ["슈퍼마켓", "마트", "식료품"],
        "Convenience Store": ["편의점", "24시", "마트"],
        "Toilets": ["화장실", "공중화장실"],
        "Donation Center": ["기부 센터", "기부", "자선"],
        "Dinner Theater": ["디너 극장", "디너 쇼", "극장식 식당"],
    },
}


def normalize_term(term: str) -> str:
    term = term.strip().lower()
    term = re.sub(r"\s+", " ", term)
    return term


def load_cache(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_cache(path: Path, cache: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def translate_query(text: str, lang: str, attempts: int = 4) -> str:
    query = urllib.parse.urlencode({"client": "gtx", "sl": "en", "tl": lang, "dt": "t", "q": text})
    url = f"https://translate.googleapis.com/translate_a/single?{query}"
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=20) as response:
                payload = json.load(response)
            translated = "".join(part[0] for part in payload[0] if part and part[0])
            return re.sub(r"\s+", " ", translated).strip()
        except Exception:
            if attempt == attempts - 1:
                raise
            time.sleep(0.4 * (attempt + 1))
    raise RuntimeError("unreachable")


def translate_one(text: str, lang: str) -> str:
    return translate_query(text, lang)


def translate_batch(texts: list[str], lang: str) -> dict[str, str]:
    joined = "\n".join(texts)
    translated = translate_query(joined, lang)
    lines = translated.splitlines()
    if len(lines) != len(texts):
        return {text: translate_one(text, lang) for text in texts}
    return dict(zip(texts, lines))


def chunked(items: list[str], size: int) -> list[list[str]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def translate_many(texts: set[str], lang: str, cache_path: Path, workers: int) -> dict[str, str]:
    cache = load_cache(cache_path)
    prefix = f"{lang}:"
    missing = sorted(text for text in texts if f"{prefix}{text}" not in cache)

    if missing:
        batches = chunked(missing, 80)
        print(f"translating {len(missing)} uncached strings for {lang} in {len(batches)} batches", flush=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_batch = {executor.submit(translate_batch, batch, lang): batch for batch in batches}
            completed = 0
            for future in concurrent.futures.as_completed(future_to_batch):
                translated_batch = future.result()
                for text, translated in translated_batch.items():
                    cache[f"{prefix}{text}"] = translated
                completed += len(translated_batch)
                if completed % 800 == 0 or completed == len(missing):
                    save_cache(cache_path, cache)
                    print(f"translated {completed}/{len(missing)}", flush=True)
        save_cache(cache_path, cache)

    return {text: cache[f"{prefix}{text}"] for text in texts}


def collect_texts(presets: list[dict], lang: str) -> set[str]:
    curated_names = CURATED_NAMES.get(lang, {})
    curated_terms = CURATED_TERMS.get(lang, {})
    texts = set()
    for preset in presets:
        name = str(preset["name"])
        if name not in curated_names:
            texts.add(name)
        for term in preset.get("terms", []) or []:
            term = str(term).strip()
            if term and normalize_term(term) not in curated_terms:
                texts.add(term)
    return texts


def terms_for_preset(preset: dict, translated_name: str, translations: dict[str, str], lang: str) -> list[str]:
    terms = {normalize_term(translated_name)}
    terms.update(normalize_term(term) for term in SEARCH_TERMS_BY_NAME.get(lang, {}).get(preset["name"], []))
    curated_terms = CURATED_TERMS.get(lang, {})
    for term in preset.get("terms", []) or []:
        source = str(term).strip()
        if not source:
            continue
        translated = curated_terms.get(normalize_term(source), translations.get(source, source))
        if translated:
            terms.add(normalize_term(translated))
    return sorted(term for term in terms if term)


def build(presets: list[dict], lang: str, translations: dict[str, str]) -> dict[str, dict]:
    output: dict[str, dict] = {}
    curated_names = CURATED_NAMES.get(lang, {})
    for preset in presets:
        pid = str(preset["id"])
        source_name = str(preset["name"])
        if source_name in curated_names:
            name = curated_names[source_name]
            quality = "curated_exact"
        else:
            name = translations.get(source_name, source_name)
            quality = "machine_translation" if name != source_name else "fallback_original"
        output[pid] = {
            "name": name,
            "terms": terms_for_preset(preset, name, translations, lang),
            "quality": quality,
        }
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", required=True, choices=sorted(SUPPORTED_LANGUAGES))
    parser.add_argument("--presets", default=DEFAULT_PRESETS)
    parser.add_argument("--output")
    parser.add_argument("--cache", default=DEFAULT_CACHE)
    parser.add_argument("--workers", type=int, default=12)
    args = parser.parse_args()

    presets = json.loads(Path(args.presets).read_text(encoding="utf-8"))
    output_path = Path(args.output) if args.output else ROOT / "meta" / f"presets_{args.lang}.json"
    cache_path = Path(args.cache)
    texts = collect_texts(presets, args.lang)
    translations = translate_many(texts, args.lang, cache_path, args.workers)
    output = build(presets, args.lang, translations)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    counts: dict[str, int] = {}
    for item in output.values():
        counts[item["quality"]] = counts.get(item["quality"], 0) + 1
    print(f"wrote {output_path}: {len(output)} translations; quality={counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
