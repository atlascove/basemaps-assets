#!/usr/bin/env python3
"""Generate lightweight preset localization files with machine translation.

The canonical matching source remains meta/presets.json. This script writes a
lightweight list of objects with preset id, localized display name, localized
search terms, and translation quality. It intentionally translates only
canonical preset names and terms; it does not use natural_language_category.
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
DEFAULT_MANIFEST = ROOT / "meta" / "presets_i18n_manifest.json"

LANGUAGE_CONFIG = {
    "ar": {
        "code": "ar",
        "google": "ar",
        "name": "Arabic",
        "native_name": "العربية",
        "direction": "rtl",
        "tier": 1,
    },
    "am": {
        "code": "am",
        "google": "am",
        "name": "Amharic",
        "native_name": "አማርኛ",
        "direction": "ltr",
        "tier": 3,
    },
    "bg": {
        "code": "bg",
        "google": "bg",
        "name": "Bulgarian",
        "native_name": "Български",
        "direction": "ltr",
        "tier": 3,
    },
    "bn": {
        "code": "bn",
        "google": "bn",
        "name": "Bengali",
        "native_name": "বাংলা",
        "direction": "ltr",
        "tier": 2,
    },
    "cs": {
        "code": "cs",
        "google": "cs",
        "name": "Czech",
        "native_name": "Čeština",
        "direction": "ltr",
        "tier": 3,
    },
    "de": {
        "code": "de",
        "google": "de",
        "name": "German",
        "native_name": "Deutsch",
        "direction": "ltr",
        "tier": 1,
    },
    "el": {
        "code": "el",
        "google": "el",
        "name": "Greek",
        "native_name": "Ελληνικά",
        "direction": "ltr",
        "tier": 3,
    },
    "es": {
        "code": "es",
        "google": "es",
        "name": "Spanish",
        "native_name": "Español",
        "direction": "ltr",
        "tier": 1,
    },
    "fa": {
        "code": "fa",
        "google": "fa",
        "name": "Persian",
        "native_name": "فارسی",
        "direction": "rtl",
        "tier": 3,
    },
    "hr": {
        "code": "hr",
        "google": "hr",
        "name": "Croatian",
        "native_name": "Hrvatski",
        "direction": "ltr",
        "tier": 3,
    },
    "hy": {
        "code": "hy",
        "google": "hy",
        "name": "Armenian",
        "native_name": "Հայերեն",
        "direction": "ltr",
        "tier": 3,
    },
    "fil": {
        "code": "fil",
        "google": "tl",
        "name": "Filipino",
        "native_name": "Filipino",
        "direction": "ltr",
        "tier": 3,
    },
    "fr": {
        "code": "fr",
        "google": "fr",
        "name": "French",
        "native_name": "Français",
        "direction": "ltr",
        "tier": 1,
    },
    "he": {
        "code": "he",
        "google": "iw",
        "name": "Hebrew",
        "native_name": "עברית",
        "direction": "rtl",
        "tier": 3,
    },
    "hi": {
        "code": "hi",
        "google": "hi",
        "name": "Hindi",
        "native_name": "हिन्दी",
        "direction": "ltr",
        "tier": 1,
    },
    "hu": {
        "code": "hu",
        "google": "hu",
        "name": "Hungarian",
        "native_name": "Magyar",
        "direction": "ltr",
        "tier": None,
    },
    "id": {
        "code": "id",
        "google": "id",
        "name": "Indonesian",
        "native_name": "Bahasa Indonesia",
        "direction": "ltr",
        "tier": 1,
    },
    "it": {
        "code": "it",
        "google": "it",
        "name": "Italian",
        "native_name": "Italiano",
        "direction": "ltr",
        "tier": None,
    },
    "ja": {
        "code": "ja",
        "google": "ja",
        "name": "Japanese",
        "native_name": "日本語",
        "direction": "ltr",
        "tier": 1,
    },
    "ka": {
        "code": "ka",
        "google": "ka",
        "name": "Georgian",
        "native_name": "ქართული",
        "direction": "ltr",
        "tier": 3,
    },
    "ko": {
        "code": "ko",
        "google": "ko",
        "name": "Korean",
        "native_name": "한국어",
        "direction": "ltr",
        "tier": 1,
    },
    "pl": {
        "code": "pl",
        "google": "pl",
        "name": "Polish",
        "native_name": "Polski",
        "direction": "ltr",
        "tier": 3,
    },
    "pt_br": {
        "code": "pt-BR",
        "google": "pt",
        "name": "Portuguese",
        "native_name": "Português",
        "direction": "ltr",
        "tier": 1,
    },
    "ro": {
        "code": "ro",
        "google": "ro",
        "name": "Romanian",
        "native_name": "Română",
        "direction": "ltr",
        "tier": 2,
    },
    "ru": {
        "code": "ru",
        "google": "ru",
        "name": "Russian",
        "native_name": "Русский",
        "direction": "ltr",
        "tier": 2,
    },
    "sr": {
        "code": "sr",
        "google": "sr",
        "name": "Serbian",
        "native_name": "Српски",
        "direction": "ltr",
        "tier": 2,
    },
    "sw": {
        "code": "sw",
        "google": "sw",
        "name": "Swahili",
        "native_name": "Kiswahili",
        "direction": "ltr",
        "tier": 3,
    },
    "ta": {
        "code": "ta",
        "google": "ta",
        "name": "Tamil",
        "native_name": "தமிழ்",
        "direction": "ltr",
        "tier": 3,
    },
    "th": {
        "code": "th",
        "google": "th",
        "name": "Thai",
        "native_name": "ไทย",
        "direction": "ltr",
        "tier": 2,
    },
    "tr": {
        "code": "tr",
        "google": "tr",
        "name": "Turkish",
        "native_name": "Türkçe",
        "direction": "ltr",
        "tier": 1,
    },
    "uk": {
        "code": "uk",
        "google": "uk",
        "name": "Ukrainian",
        "native_name": "Українська",
        "direction": "ltr",
        "tier": 2,
    },
    "ur": {
        "code": "ur",
        "google": "ur",
        "name": "Urdu",
        "native_name": "اردو",
        "direction": "rtl",
        "tier": 2,
    },
    "vi": {
        "code": "vi",
        "google": "vi",
        "name": "Vietnamese",
        "native_name": "Tiếng Việt",
        "direction": "ltr",
        "tier": 1,
    },
    "zh_hans": {
        "code": "zh-Hans",
        "google": "zh-CN",
        "name": "Simplified Chinese",
        "native_name": "简体中文",
        "direction": "ltr",
        "tier": 3,
    },
    "zh_hant": {
        "code": "zh-Hant",
        "google": "zh-TW",
        "name": "Traditional Chinese",
        "native_name": "繁體中文",
        "direction": "ltr",
        "tier": 3,
    },
}

SUPPORTED_LANGUAGES = set(LANGUAGE_CONFIG)

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
    "ja": {
        "ATM": "ATM",
        "BBQ/Grill": "バーベキュー場",
        "Cable Car": "ケーブルカー",
        "Cafe": "カフェ",
        "Convenience Store": "コンビニ",
        "Dialysis Center": "透析センター",
        "Dinner Theater": "ディナーシアター",
        "Donation Center": "寄付センター",
        "Drinking Water": "飲料水",
        "Fish & Chips Fast Food": "フィッシュアンドチップス",
        "Gas Station": "ガソリンスタンド",
        "Hotel & Restaurant": "ホテルとレストラン",
        "Place of Worship": "礼拝所",
        "Public Transport Platform": "公共交通機関の乗り場",
        "Transit Stopping Location": "公共交通機関の停留所",
        "Visitor Center": "ビジターセンター",
    },
    "ar": {
        "ATM": "صراف آلي",
        "BBQ/Grill": "منطقة شواء",
        "Cable Car": "تلفريك",
        "Cafe": "مقهى",
        "Convenience Store": "متجر صغير",
        "Dialysis Center": "مركز غسيل الكلى",
        "Dinner Theater": "مسرح مع عشاء",
        "Donation Center": "مركز تبرعات",
        "Drinking Water": "مياه شرب",
        "Fish & Chips Fast Food": "فيش آند تشيبس",
        "Gas Station": "محطة وقود",
        "Hotel & Restaurant": "فندق ومطعم",
        "Place of Worship": "مكان عبادة",
        "Public Transport Platform": "رصيف نقل عام",
        "Transit Stopping Location": "موقف نقل عام",
        "Visitor Center": "مركز زوار",
    },
    "hu": {
        "ATM": "ATM",
        "BBQ/Grill": "Grillezőhely",
        "Cable Car": "Felvonó",
        "Cafe": "Kávézó",
        "Convenience Store": "Kisbolt",
        "Dialysis Center": "Dialízisközpont",
        "Dinner Theater": "Vacsoraszínház",
        "Donation Center": "Adományközpont",
        "Drinking Water": "Ivóvíz",
        "Fish & Chips Fast Food": "Fish and chips",
        "Gas Station": "Benzinkút",
        "Hotel & Restaurant": "Hotel és étterem",
        "Place of Worship": "Vallási hely",
        "Public Transport Platform": "Tömegközlekedési peron",
        "Transit Stopping Location": "Tömegközlekedési megálló",
        "Visitor Center": "Látogatóközpont",
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
    "ja": {
        "amenity": "施設",
        "charity": "慈善",
        "dinner show": "ディナーショー",
        "dinner theater": "ディナーシアター",
        "dinner theatre": "ディナーシアター",
        "donation": "寄付",
        "donation center": "寄付センター",
        "fish": "魚",
        "fish chip": "フィッシュアンドチップス",
        "fish chips": "フィッシュアンドチップス",
        "fish fry": "魚のフライ",
        "gas station": "ガソリンスタンド",
        "supper club": "サパークラブ",
        "theatre restaurant": "劇場レストラン",
    },
    "ar": {
        "amenity": "مرفق",
        "charity": "خيرية",
        "dinner show": "عرض عشاء",
        "dinner theater": "مسرح مع عشاء",
        "dinner theatre": "مسرح مع عشاء",
        "donation": "تبرع",
        "donation center": "مركز تبرعات",
        "fish": "سمك",
        "fish chip": "فيش آند تشيبس",
        "fish chips": "فيش آند تشيبس",
        "fish fry": "سمك مقلي",
        "gas station": "محطة وقود",
        "supper club": "نادي عشاء",
        "theatre restaurant": "مطعم مسرحي",
    },
    "hu": {
        "amenity": "szolgáltatás",
        "charity": "jótékonyság",
        "dinner show": "vacsoraműsor",
        "dinner theater": "vacsoraszínház",
        "dinner theatre": "vacsoraszínház",
        "donation": "adomány",
        "donation center": "adományközpont",
        "fish": "hal",
        "fish chip": "fish and chips",
        "fish chips": "fish and chips",
        "fish fry": "sült hal",
        "gas station": "benzinkút",
        "supper club": "vacsoraklub",
        "theatre restaurant": "színházi étterem",
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
    "ja": {
        "Restaurant": ["レストラン", "食堂", "飲食店"],
        "Cafe": ["カフェ", "喫茶店", "コーヒー"],
        "Gas Station": ["ガソリンスタンド", "給油所", "燃料"],
        "Pharmacy": ["薬局", "ドラッグストア", "薬"],
        "Supermarket": ["スーパー", "スーパーマーケット", "食料品"],
        "Convenience Store": ["コンビニ", "コンビニエンスストア"],
        "Toilets": ["トイレ", "公衆トイレ", "wc"],
        "Donation Center": ["寄付センター", "寄付", "慈善"],
        "Dinner Theater": ["ディナーシアター", "ディナーショー", "劇場レストラン"],
    },
    "ar": {
        "Restaurant": ["مطعم", "طعام", "أكل"],
        "Cafe": ["مقهى", "قهوة"],
        "Gas Station": ["محطة وقود", "بنزين", "وقود"],
        "Pharmacy": ["صيدلية", "أدوية"],
        "Supermarket": ["سوبرماركت", "بقالة", "مواد غذائية"],
        "Convenience Store": ["متجر صغير", "بقالة"],
        "Toilets": ["دورات مياه", "حمام", "مرحاض", "wc"],
        "Donation Center": ["مركز تبرعات", "تبرعات", "خيرية"],
        "Dinner Theater": ["مسرح مع عشاء", "عرض عشاء", "مطعم مسرحي"],
    },
    "hu": {
        "Restaurant": ["étterem", "vendéglő", "ebédlő"],
        "Cafe": ["kávézó", "kávé", "presszó"],
        "Gas Station": ["benzinkút", "üzemanyag", "töltőállomás"],
        "Pharmacy": ["gyógyszertár", "patika", "gyógyszer"],
        "Supermarket": ["szupermarket", "élelmiszerbolt", "bevásárlás"],
        "Convenience Store": ["kisbolt", "élelmiszerbolt"],
        "Toilets": ["mosdó", "wc", "illemhely"],
        "Donation Center": ["adományközpont", "adomány", "jótékonyság"],
        "Dinner Theater": ["vacsoraszínház", "vacsoraműsor", "színházi étterem"],
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
    google_lang = LANGUAGE_CONFIG[lang]["google"]
    query = urllib.parse.urlencode({"client": "gtx", "sl": "en", "tl": google_lang, "dt": "t", "q": text})
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


def build(presets: list[dict], lang: str, translations: dict[str, str]) -> list[dict]:
    output: list[dict] = []
    curated_names = CURATED_NAMES.get(lang, {})
    for preset in presets:
        source_name = str(preset["name"])
        if source_name in curated_names:
            name = curated_names[source_name]
            quality = "curated_exact"
        else:
            name = translations.get(source_name, source_name)
            quality = "machine_translation" if name != source_name else "fallback_original"
        output.append({
            "id": int(preset["id"]),
            "name": name,
            "terms": terms_for_preset(preset, name, translations, lang),
            "quality": quality,
        })
    return output


def preset_file_for_lang(lang: str) -> str:
    return f"presets_{lang}.json"


def build_manifest() -> dict:
    languages = [
        {
            "code": "en",
            "name": "English",
            "native_name": "English",
            "direction": "ltr",
            "file": "presets.json",
            "format": "canonical",
            "tier": 1,
        }
    ]
    for lang in sorted(SUPPORTED_LANGUAGES, key=lambda item: (LANGUAGE_CONFIG[item]["tier"] is None, LANGUAGE_CONFIG[item]["tier"] or 99, LANGUAGE_CONFIG[item]["name"])):
        config = LANGUAGE_CONFIG[lang]
        languages.append({
            "code": config["code"],
            "name": config["name"],
            "native_name": config["native_name"],
            "direction": config["direction"],
            "file": preset_file_for_lang(lang),
            "format": "localized_lightweight",
            **({"tier": config["tier"]} if config["tier"] is not None else {}),
        })
    return {
        "version": 1,
        "default_language": "en",
        "languages": languages,
    }


def write_manifest(path: Path) -> None:
    path.write_text(json.dumps(build_manifest(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", required=True, choices=sorted(SUPPORTED_LANGUAGES))
    parser.add_argument("--presets", default=DEFAULT_PRESETS)
    parser.add_argument("--output")
    parser.add_argument("--cache", default=DEFAULT_CACHE)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    parser.add_argument("--skip-manifest", action="store_true")
    args = parser.parse_args()

    presets = json.loads(Path(args.presets).read_text(encoding="utf-8"))
    output_path = Path(args.output) if args.output else ROOT / "meta" / preset_file_for_lang(args.lang)
    cache_path = Path(args.cache)
    texts = collect_texts(presets, args.lang)
    translations = translate_many(texts, args.lang, cache_path, args.workers)
    output = build(presets, args.lang, translations)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not args.skip_manifest:
        write_manifest(Path(args.manifest))

    counts: dict[str, int] = {}
    for item in output:
        counts[item["quality"]] = counts.get(item["quality"], 0) + 1
    print(f"wrote {output_path}: {len(output)} translations; quality={counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
