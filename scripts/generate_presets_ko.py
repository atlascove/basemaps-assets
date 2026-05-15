#!/usr/bin/env python3
"""Generate a Korean preset localization sidecar.

The canonical matching source remains meta/presets.json. This script creates
meta/presets_ko.json keyed by preset id, containing Korean display names and
search terms for UI/search localization.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRESETS = ROOT / "meta" / "presets.json"
DEFAULT_OUTPUT = ROOT / "meta" / "presets_ko.json"


EXACT_NAMES = {
    "ATM": "ATM",
    "BBQ/Grill": "바비큐장",
    "BMX Track": "BMX 트랙",
    "Baby Hatch/Safe Haven": "베이비박스",
    "Bar": "바",
    "Bench": "벤치",
    "Bicycle Parking": "자전거 주차장",
    "Bicycle Rental": "자전거 대여소",
    "Bicycle Repair Station": "자전거 수리대",
    "Bicycle Shop": "자전거 매장",
    "Biergarten": "비어가든",
    "Bus Station": "버스 터미널",
    "Bus Stop": "버스 정류장",
    "Bus Stopping Location": "버스 정류 위치",
    "Cafe": "카페",
    "Camp Site": "캠핑장",
    "Car Rental": "렌터카",
    "Car Sharing": "카셰어링",
    "Car Wash": "세차장",
    "Charging Station": "충전소",
    "Cinema": "영화관",
    "Convenience Store": "편의점",
    "Crosswalk": "횡단보도",
    "Deli": "델리",
    "Dentist": "치과",
    "Dialysis Center": "투석 센터",
    "Doctor": "의원",
    "Drinking Water": "식수대",
    "Drugstore": "약국",
    "Fast Food": "패스트푸드",
    "Fire Station": "소방서",
    "Fish & Chips Fast Food": "피시앤칩스",
    "Gas Station": "주유소",
    "Hospital": "병원",
    "Hotel": "호텔",
    "Hotel & Restaurant": "호텔 및 식당",
    "Library": "도서관",
    "Mall": "쇼핑몰",
    "Museum": "박물관",
    "Motel": "모텔",
    "Parking": "주차장",
    "Pharmacy": "약국",
    "Place of Worship": "종교 시설",
    "Police": "경찰서",
    "Post Box": "우체통",
    "Post Office": "우체국",
    "Pub": "펍",
    "Public Transport Platform": "대중교통 승강장",
    "Restaurant": "음식점",
    "School": "학교",
    "Supermarket": "슈퍼마켓",
    "Taxi": "택시",
    "Theatre": "극장",
    "Toilets": "화장실",
    "Train Station": "기차역",
    "Transit Stopping Location": "대중교통 정차 위치",
    "Tram Stop": "트램 정류장",
    "Visitor Center": "방문자 센터",
    "Veterinary": "동물병원",
}


PHRASE_REPLACEMENTS = [
    ("Access Point", "접근 지점"),
    ("Administrative Boundary", "행정 경계"),
    ("Advertising Column", "광고 기둥"),
    ("Advertising Totem", "광고 토템"),
    ("Animal Shelter", "동물 보호소"),
    ("Apartment Building", "아파트 건물"),
    ("Art Gallery", "미술관"),
    ("Arts Centre", "문화예술센터"),
    ("Baggage Claim", "수하물 찾는 곳"),
    ("Bank", "은행"),
    ("Beach Resort", "해변 리조트"),
    ("Beauty Shop", "미용실"),
    ("Betting Shop", "베팅 숍"),
    ("Boarding Gate", "탑승구"),
    ("Boat Rental", "보트 대여소"),
    ("Book Store", "서점"),
    ("Border Control", "출입국 심사"),
    ("Bowling Alley", "볼링장"),
    ("Bridge", "다리"),
    ("Building", "건물"),
    ("Butcher", "정육점"),
    ("Cable Car", "케이블카"),
    ("Camp Pitch", "캠핑 구획"),
    ("Car Dealer", "자동차 판매점"),
    ("Car Parts", "자동차 부품점"),
    ("Casino", "카지노"),
    ("Castle", "성"),
    ("Cemetery", "묘지"),
    ("Changing Room", "탈의실"),
    ("Chemist", "약국"),
    ("Childcare", "보육 시설"),
    ("Christian Church", "기독교 교회"),
    ("City Gate", "성문"),
    ("Climbing", "클라이밍"),
    ("Clothes Shop", "의류 매장"),
    ("Coffee Shop", "커피숍"),
    ("Community Centre", "커뮤니티 센터"),
    ("Computer Shop", "컴퓨터 매장"),
    ("Confectionery", "제과점"),
    ("Construction Site", "공사 현장"),
    ("Copy Shop", "복사점"),
    ("Courthouse", "법원"),
    ("Craft Shop", "공예품점"),
    ("Cycleway", "자전거 도로"),
    ("Department Store", "백화점"),
    ("Dive Centre", "다이빙 센터"),
    ("Dormitory", "기숙사"),
    ("Dry Cleaner", "드라이클리닝"),
    ("Electronics Shop", "전자제품 매장"),
    ("Emergency Phone", "긴급 전화"),
    ("Escape Game", "방탈출 카페"),
    ("Farm Shop", "농산물 매장"),
    ("Farm", "농장"),
    ("Fashion Accessories", "패션 액세서리"),
    ("Ferry Terminal", "페리 터미널"),
    ("Fish & Chips", "피시앤칩스"),
    ("Fitness Centre", "피트니스 센터"),
    ("Florist", "꽃집"),
    ("Food Court", "푸드코트"),
    ("Footbridge", "보행자 다리"),
    ("Footway", "보행로"),
    ("Fountain", "분수"),
    ("Funeral Home", "장례식장"),
    ("Furniture Shop", "가구점"),
    ("Garden Centre", "가든 센터"),
    ("Gift Shop", "선물 가게"),
    ("Government Office", "공공기관"),
    ("Greengrocer", "청과물 가게"),
    ("Guest House", "게스트하우스"),
    ("Hairdresser", "미용실"),
    ("Hardware Store", "철물점"),
    ("Health Centre", "보건소"),
    ("Hostel", "호스텔"),
    ("Ice Cream", "아이스크림 가게"),
    ("Jewelry Store", "보석상"),
    ("Kindergarten", "유치원"),
    ("Laundry", "세탁소"),
    ("Mobile Phone Shop", "휴대폰 매장"),
    ("Motorcycle Parking", "오토바이 주차장"),
    ("Music School", "음악 학원"),
    ("Newsagent", "신문 가판대"),
    ("Nightclub", "나이트클럽"),
    ("Optician", "안경점"),
    ("Outdoor Shop", "아웃도어 매장"),
    ("Park", "공원"),
    ("Parking Entrance", "주차장 입구"),
    ("Parking Space", "주차 구역"),
    ("Path", "길"),
    ("Pedestrian Street", "보행자 거리"),
    ("Pet Shop", "반려동물 매장"),
    ("Picnic Site", "피크닉 장소"),
    ("Playground", "놀이터"),
    ("Public Building", "공공 건물"),
    ("Recycling", "재활용 시설"),
    ("Residential Road", "주거 도로"),
    ("Rest Area", "휴게소"),
    ("Road", "도로"),
    ("Seafood", "수산물 가게"),
    ("Shoe Shop", "신발 가게"),
    ("Shopping Centre", "쇼핑센터"),
    ("Social Facility", "복지 시설"),
    ("Sports Centre", "스포츠 센터"),
    ("Stadium", "경기장"),
    ("Station", "역"),
    ("Street Lamp", "가로등"),
    ("Swimming Pool", "수영장"),
    ("Ticket Office", "매표소"),
    ("Tourist Information", "관광 안내소"),
    ("Town Hall", "시청"),
    ("Traffic Signals", "신호등"),
    ("Travel Agency", "여행사"),
    ("University", "대학교"),
    ("Viewpoint", "전망대"),
    ("Water Park", "워터파크"),
    ("Wayside Shrine", "길가 사당"),
    ("Wine Shop", "와인숍"),
]


WORD_TRANSLATIONS = {
    "abandoned": "폐쇄된",
    "access": "접근",
    "accommodation": "숙박",
    "administrative": "행정",
    "advisor": "상담사",
    "agency": "대행사",
    "agent": "중개인",
    "advertising": "광고",
    "aerialway": "삭도",
    "agricultural": "농업",
    "aid": "구호",
    "air": "항공",
    "aircraft": "항공기",
    "airport": "공항",
    "alcohol": "주류",
    "alternative": "대체",
    "amenity": "편의시설",
    "and": "및",
    "animal": "동물",
    "apparel": "의류",
    "apartment": "아파트",
    "area": "구역",
    "art": "예술",
    "artist": "예술가",
    "assistance": "지원",
    "association": "협회",
    "auto": "자동차",
    "bakery": "빵집",
    "bar": "바",
    "barrier": "장애물",
    "basket": "바구니",
    "beach": "해변",
    "beauty": "미용",
    "bench": "벤치",
    "bicycle": "자전거",
    "bike": "자전거",
    "board": "게시판",
    "boat": "보트",
    "book": "책",
    "boundary": "경계",
    "box": "상자",
    "bridge": "다리",
    "building": "건물",
    "bunker": "벙커",
    "bus": "버스",
    "business": "사업",
    "cafe": "카페",
    "camp": "캠프",
    "car": "자동차",
    "care": "케어",
    "center": "센터",
    "centre": "센터",
    "charging": "충전",
    "church": "교회",
    "city": "도시",
    "civil": "민간",
    "clinic": "클리닉",
    "closed": "폐쇄",
    "club": "클럽",
    "coffee": "커피",
    "college": "대학",
    "clothing": "의류",
    "commercial": "상업",
    "community": "커뮤니티",
    "company": "회사",
    "companies": "회사",
    "consultant": "컨설턴트",
    "consulting": "컨설팅",
    "control": "관리",
    "construction": "공사",
    "contractor": "시공업체",
    "course": "코스",
    "court": "코트",
    "crossing": "횡단",
    "crosswalk": "횡단보도",
    "dance": "댄스",
    "dealer": "판매점",
    "dealership": "판매점",
    "designated": "지정",
    "destination": "목적지",
    "development": "개발",
    "digital": "디지털",
    "disused": "사용 중지",
    "dog": "개",
    "drinking": "식수",
    "drive": "드라이브",
    "dry": "드라이",
    "education": "교육",
    "educational": "교육",
    "electric": "전기",
    "electrical": "전기",
    "emergency": "긴급",
    "energy": "에너지",
    "engineer": "엔지니어",
    "engineering": "엔지니어링",
    "engineers": "엔지니어",
    "entrance": "입구",
    "equipment": "장비",
    "estate": "부동산",
    "event": "이벤트",
    "events": "이벤트",
    "exercise": "운동",
    "exchange": "환전",
    "factory": "공장",
    "facility": "시설",
    "family": "가족",
    "fast": "패스트",
    "ferry": "페리",
    "field": "필드",
    "financial": "금융",
    "fire": "소방",
    "fitness": "피트니스",
    "food": "음식",
    "foot": "보행",
    "footway": "보행로",
    "forest": "숲",
    "fuel": "연료",
    "garden": "정원",
    "gas": "가스",
    "gate": "문",
    "golf": "골프",
    "government": "정부",
    "grass": "잔디",
    "green": "녹색",
    "greenhouse": "온실",
    "grounds": "부지",
    "group": "그룹",
    "gym": "체육관",
    "hair": "헤어",
    "hall": "홀",
    "health": "건강",
    "height": "높이",
    "historic": "역사",
    "home": "주택",
    "horse": "말",
    "horseback": "승마",
    "house": "주택",
    "housing": "주거",
    "hut": "오두막",
    "ice": "얼음",
    "indoor": "실내",
    "industrial": "산업",
    "industry": "산업",
    "information": "정보",
    "installation": "설치",
    "instruction": "교육",
    "insurance": "보험",
    "internet": "인터넷",
    "island": "섬",
    "law": "법률",
    "left": "좌회전",
    "legal": "법률",
    "library": "도서관",
    "lift": "리프트",
    "line": "선",
    "link": "연결로",
    "location": "위치",
    "machine": "기계",
    "maker": "제작자",
    "management": "관리",
    "manufacturer": "제조업체",
    "manufacturers": "제조업체",
    "manufacturing": "제조",
    "market": "시장",
    "mast": "마스트",
    "media": "미디어",
    "medical": "의료",
    "medicine": "의학",
    "memorial": "기념물",
    "metal": "금속",
    "military": "군사",
    "mill": "제분소",
    "mobile": "모바일",
    "motor": "자동차",
    "motorcycle": "오토바이",
    "motorsport": "모터스포츠",
    "mountain": "산",
    "museum": "박물관",
    "natural": "자연",
    "network": "네트워크",
    "no": "금지",
    "node": "노드",
    "occupational": "직업",
    "of": "의",
    "office": "사무실",
    "oil": "석유",
    "only": "전용",
    "official": "공식",
    "organization": "조직",
    "outdoor": "아웃도어",
    "panel": "패널",
    "parking": "주차",
    "pediatric": "소아",
    "personal": "개인",
    "pet": "반려동물",
    "pharmacy": "약국",
    "photography": "사진",
    "physician": "의사",
    "pit": "구덩이",
    "place": "장소",
    "planning": "계획",
    "plant": "시설",
    "plastic": "플라스틱",
    "play": "놀이",
    "platform": "승강장",
    "pole": "기둥",
    "power": "전력",
    "printing": "인쇄",
    "private": "사유",
    "production": "제작",
    "professional": "전문",
    "provider": "제공업체",
    "public": "공공",
    "railway": "철도",
    "range": "연습장",
    "real": "부동산",
    "recycling": "재활용",
    "rental": "대여",
    "rentals": "대여",
    "repair": "수리",
    "residential": "주거",
    "restaurant": "음식점",
    "right": "우회전",
    "ride": "놀이기구",
    "riding": "승마",
    "road": "도로",
    "room": "방",
    "route": "노선",
    "rv": "캠핑카",
    "school": "학교",
    "schools": "학교",
    "security": "보안",
    "service": "서비스",
    "services": "서비스",
    "shop": "상점",
    "sign": "표지판",
    "site": "장소",
    "ski": "스키",
    "social": "사회",
    "solar": "태양광",
    "sports": "스포츠",
    "stand": "승강장",
    "station": "역",
    "stop": "정류장",
    "stopping": "정차",
    "store": "상점",
    "street": "거리",
    "studio": "스튜디오",
    "supplier": "공급업체",
    "supplies": "용품",
    "supply": "공급",
    "surgery": "수술",
    "surgeon": "외과의",
    "table": "테이블",
    "tax": "세무",
    "tea": "차",
    "temple": "사원",
    "therapist": "치료사",
    "therapy": "치료",
    "ticket": "티켓",
    "toilets": "화장실",
    "tower": "탑",
    "track": "트랙",
    "traffic": "교통",
    "trail": "트레일",
    "training": "교육",
    "train": "기차",
    "transport": "교통",
    "transportation": "교통",
    "tree": "나무",
    "truck": "트럭",
    "turn": "회전",
    "utility": "공공설비",
    "vehicle": "차량",
    "vending": "자판기",
    "veterinary": "동물병원",
    "video": "비디오",
    "visitor": "방문자",
    "water": "물",
    "waste": "폐기물",
    "wholesaler": "도매상",
    "wholesalers": "도매상",
    "wine": "와인",
    "yes": "예",
}


TERM_TRANSLATIONS = {
    **WORD_TRANSLATIONS,
    "atm": "atm",
    "bank": "은행",
    "bar": "바",
    "bathroom": "화장실",
    "bike": "자전거",
    "bikes": "자전거",
    "bus stop": "버스 정류장",
    "car park": "주차장",
    "chemist": "약국",
    "coffee shop": "커피숍",
    "convenience": "편의점",
    "crosswalk": "횡단보도",
    "doctor": "의원",
    "drugstore": "약국",
    "gas": "주유소",
    "gas station": "주유소",
    "grocery": "식료품점",
    "loo": "화장실",
    "parking lot": "주차장",
    "petrol": "휘발유",
    "pharmacy": "약국",
    "restaurant": "음식점",
    "restroom": "화장실",
    "shop": "상점",
    "store": "상점",
    "supermarket": "슈퍼마켓",
    "toilet": "화장실",
    "wc": "화장실",
}


SEARCH_TERMS_BY_NAME = {
    "Restaurant": ["음식점", "식당", "맛집", "레스토랑"],
    "Cafe": ["카페", "커피", "커피숍"],
    "Bar": ["바", "술집", "칵테일 바"],
    "Pub": ["펍", "맥주집", "술집"],
    "Fast Food": ["패스트푸드", "햄버거", "테이크아웃"],
    "Ice Cream": ["아이스크림", "젤라토"],
    "Gas Station": ["주유소", "충전소", "연료"],
    "Pharmacy": ["약국", "약"],
    "Supermarket": ["슈퍼마켓", "마트", "식료품"],
    "Convenience Store": ["편의점", "24시", "마트"],
    "Hotel": ["호텔", "숙소"],
    "Guest House": ["게스트하우스", "숙소"],
    "Bus Stop": ["버스 정류장", "버스"],
    "Train Station": ["기차역", "역", "철도"],
    "Parking": ["주차장", "주차"],
    "Toilets": ["화장실", "공중화장실"],
    "Drinking Water": ["식수대", "음수대", "물"],
    "Police": ["경찰서", "경찰"],
    "Hospital": ["병원", "응급실"],
    "Post Office": ["우체국", "우편"],
    "Post Box": ["우체통", "우편함"],
    "Library": ["도서관"],
    "School": ["학교"],
    "Museum": ["박물관"],
    "Park": ["공원"],
}


TOKEN_RE = re.compile(r"[A-Za-z0-9]+|[가-힣]+|[/&()'-]")


def title_ko(text: str) -> str:
    words = text.split()
    out = []
    for word in words:
        if re.fullmatch(r"[A-Za-z]{2,}", word):
            out.append(word[:1].upper() + word[1:])
        else:
            out.append(word)
    return " ".join(out)


def translate_name(name: str) -> tuple[str, str]:
    if name in EXACT_NAMES:
        return EXACT_NAMES[name], "curated_exact"

    translated = name
    for source, target in sorted(PHRASE_REPLACEMENTS, key=lambda item: len(item[0]), reverse=True):
        translated = re.sub(rf"\b{re.escape(source)}\b", target, translated, flags=re.IGNORECASE)

    tokens = TOKEN_RE.findall(translated)
    if not tokens:
        if translated != name:
            return translated, "curated_rules"
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
        return title_ko(name), "fallback_original"

    text = " ".join(out)
    text = text.replace(" / ", "/").replace(" ' ", "'").replace(" ( ", " (").replace(" )", ")")
    text = re.sub(r"\s+", " ", text).strip()
    return title_ko(text), "curated_rules"


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
