#!/usr/bin/env python3
"""Build preset compatibility graph keyed by preset id using taxonomy-first rules.

Design:
- Default deny (no compatibility edge).
- Explicit allow via semantic family compatibility.
- Hard blocks for known non-place/structural classes.
- Self edge always included.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Structural/non-place presets: never broadly merge.
BLOCK_KEYS = {
    "emergency",
    "barrier",
    "traffic_calming",
    "traffic_sign",
    "crossing",
    "man_made",
}

TRANSIT_KEYS = {"railway", "public_transport", "aerialway", "aeroway"}

# Explicit pairwise exceptions approved from real-world audits.
# Keep this small and intentional.
FORCED_ALLOW_PAIRS: Set[Tuple[int, int]] = {
    (72, 36),     # Cafe <-> Community Center
    (189, 970),   # Embassy <-> Embassy Others
    (416, 659),   # Sports Club <-> Bowling Alley
    (503, 603),   # Driving Range <-> Golf Course
    (731, 1201),  # Yoga Studio <-> Sporting Goods Store
    (1174, 1449), # Electronics Store <-> Event Photography
    (1144, 1461), # Cannabis Shop <-> Cannabis Clinic
}


@dataclass(frozen=True)
class PresetInfo:
    pid: int
    name: str
    tags: Dict[str, str]
    geometry: List[str]
    overture_categories: List[str]

    @property
    def point_capable(self) -> bool:
        return "point" in self.geometry or "vertex" in self.geometry


@dataclass
class Semantic:
    families: Set[str]
    hard_block: bool


def norm_tags(raw: Dict[str, object]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for k, v in (raw or {}).items():
        if k is None or v is None:
            continue
        ks = str(k).strip().lower()
        vs = str(v).strip().lower()
        if ks and vs:
            out[ks] = vs
    return out


def load_presets(path: Path) -> List[PresetInfo]:
    rows = json.loads(path.read_text())
    out: List[PresetInfo] = []
    for r in rows:
        out.append(
            PresetInfo(
                pid=int(r["id"]),
                name=str(r.get("name", "")),
                tags=norm_tags(r.get("tags", {})),
                geometry=[str(g).lower() for g in r.get("geometry", []) if g is not None],
                overture_categories=[str(x).strip().lower() for x in r.get("overture_categories", []) if x],
            )
        )
    return out


def tag(p: PresetInfo, key: str) -> str | None:
    return p.tags.get(key)


def classify(p: PresetInfo) -> Semantic:
    f: Set[str] = set()

    # Hard blocks first.
    if any(k in p.tags for k in BLOCK_KEYS):
        return Semantic(families={"non_place"}, hard_block=True)

    # Emergency equipment is non-place.
    em = tag(p, "emergency")
    if em in {"defibrillator", "fire_hydrant", "fire_alarm_box", "fire_extinguisher", "life_ring", "yes", "private", "official", "destination", "designated", "no"}:
        return Semantic(families={"non_place"}, hard_block=True)

    # Transport taxonomy.
    if any(k in p.tags for k in TRANSIT_KEYS):
        f.add("transit")
        pt = tag(p, "public_transport")
        rw = tag(p, "railway")
        aw = tag(p, "aerialway")
        if pt in {"platform", "stop_position", "stop_area", "station"}:
            f.add("transit_stop")
        if rw in {"station", "halt", "tram_stop", "subway_entrance", "platform"}:
            f.add("transit_stop")
        if aw:
            f.add("transit_lift")

    # Office.
    off = tag(p, "office")
    if off:
        f.add("office")
        if off in {"it", "software_development", "company", "consulting", "coworking", "telecommunication", "engineer", "architect"}:
            f.add("office_knowledge")
        if off in {"government", "administrative", "diplomatic", "ngo", "association"}:
            f.add("civic")
        if off in {"bus_service", "transport", "travel_agent"}:
            f.add("transit_service")

    # Amenity.
    am = tag(p, "amenity")
    if am:
        if am in {"restaurant", "cafe", "fast_food", "bar", "pub", "biergarten", "food_court", "ice_cream"}:
            f.add("food_service")
        if am in {"school", "kindergarten", "college", "university", "library", "childcare"}:
            f.add("education")
        # Early childhood institutions are often mapped as kindergarten vs childcare.
        if am in {"kindergarten", "childcare"}:
            f.add("early_education")
        if am in {"hospital", "clinic", "doctors", "dentist", "pharmacy", "veterinary"}:
            f.add("health")
        if am in {"bank", "atm", "bureau_de_change"}:
            f.add("finance")
        if am in {"community_centre", "townhall", "courthouse", "post_office", "police", "fire_station", "social_facility"}:
            f.add("civic")
        # Library and social facility frequently represent the same municipal/community node.
        if am in {"library", "social_facility"}:
            f.add("community_learning")
        if am in {"arts_centre", "theatre", "cinema"}:
            f.add("culture")

    # Healthcare key family (covers presets like healthcare=alternative, healthcare:speciality=chiropractic).
    hc = tag(p, "healthcare")
    hcs = tag(p, "healthcare:speciality")
    if hc:
        if hc in {"hospital", "clinic", "doctor", "dentist", "pharmacy", "veterinary", "alternative"}:
            f.add("health")
    if hcs:
        if hcs in {"chiropractic", "chiropractor", "general", "dentistry", "physiotherapy"}:
            f.add("health")

    # Shop.
    sh = tag(p, "shop")
    if sh:
        f.add("retail")
        if sh in {"bakery", "deli", "butcher", "greengrocer", "convenience", "supermarket", "seafood", "beverages", "confectionery"}:
            f.add("food_retail")
        if sh in {"clothes", "shoes", "jewelry", "bag", "fashion_accessories", "beauty"}:
            f.add("retail_fashion")
        if sh in {"electronics", "computer", "mobile_phone", "hifi"}:
            f.add("retail_electronics")

    # Tourism.
    tr = tag(p, "tourism")
    if tr:
        if tr in {"hotel", "hostel", "motel", "guest_house", "apartment", "resort"}:
            f.add("lodging")
        if tr in {"museum", "gallery", "attraction", "viewpoint", "zoo", "aquarium", "theme_park"}:
            f.add("culture")

    # Leisure/sport.
    le = tag(p, "leisure")
    if le:
        if le in {"sports_centre", "stadium", "fitness_centre", "pitch", "golf_course", "swimming_pool", "bowling_alley"}:
            f.add("sports")
        if le in {"park", "garden", "nature_reserve"}:
            f.add("park")
    club = tag(p, "club")
    if club in {"sport", "sports"}:
        f.add("sports")

    # Religion.
    if tag(p, "amenity") == "place_of_worship":
        f.add("religion")

    # If unknown but point-like and named POI preset, keep generic place bucket.
    if not f:
        f.add("generic_place")

    return Semantic(families=f, hard_block=False)


def edge_score(pa: PresetInfo, sa: Semantic, pb: PresetInfo, sb: Semantic) -> float:
    if pa.pid == pb.pid:
        return 1.0

    if (pa.pid, pb.pid) in FORCED_ALLOW_PAIRS or (pb.pid, pa.pid) in FORCED_ALLOW_PAIRS:
        return 0.95

    # Hard blocks: default no, unless exact same key/value tags (already handled above by pid in practice).
    if sa.hard_block or sb.hard_block:
        return 0.0

    # Exact same tag dict is strong (duplicate taxonomy split across ids).
    if pa.tags and pa.tags == pb.tags:
        return 0.98

    # Never merge transit with non-transit unless both transit families present.
    a_transit = "transit" in sa.families or "transit_service" in sa.families
    b_transit = "transit" in sb.families or "transit_service" in sb.families
    if a_transit != b_transit:
        return 0.0

    common = sa.families.intersection(sb.families)
    if common:
        # Same high-confidence family.
        if any(x in common for x in {"office_knowledge", "food_service", "food_retail", "lodging", "education", "early_education", "community_learning", "health", "culture", "sports", "park", "religion", "transit_stop", "transit_lift"}):
            return 0.92
        # Generic common family.
        if any(x in common for x in {"office", "retail", "finance", "civic", "transit", "transit_service"}):
            return 0.84

    # Cross-family allowances for common messy map taxonomy drift.
    # Food service vs food retail often represent same storefront with different tagging.
    if ({"food_service", "food_retail"}.issubset(sa.families.union(sb.families))):
        return 0.82

    # Culture/education overlap (arts schools, museum-education complexes) - weaker.
    if ({"culture", "education"}.issubset(sa.families.union(sb.families))):
        return 0.76

    # Office knowledge vs retail (e.g. showroom) should not auto-merge.
    return 0.0


def build_graph(presets: List[PresetInfo], threshold: float, all_geometries: bool) -> Tuple[Dict[str, List[int]], Dict[str, Dict[str, object]]]:
    scope = presets if all_geometries else [p for p in presets if p.point_capable]
    sem = {p.pid: classify(p) for p in presets}

    graph: Dict[str, List[int]] = {str(p.pid): [p.pid] for p in presets}  # self-edge always
    meta: Dict[str, Dict[str, object]] = {}

    for p in presets:
        s = sem[p.pid]
        meta[str(p.pid)] = {
            "name": p.name,
            "families": sorted(s.families),
            "hard_block": s.hard_block,
            "point_capable": p.point_capable,
            "tags": p.tags,
        }

    for a in scope:
        out: List[Tuple[int, float]] = [(a.pid, 1.0)]
        sa = sem[a.pid]
        for b in scope:
            if a.pid == b.pid:
                continue
            sb = sem[b.pid]
            s = edge_score(a, sa, b, sb)
            if s >= threshold:
                out.append((b.pid, s))
        out.sort(key=lambda t: (-t[1], t[0]))
        graph[str(a.pid)] = [pid for pid, _ in out]

    return graph, meta


def main() -> None:
    parser = argparse.ArgumentParser(description="Build preset compatibility graph")
    parser.add_argument("--presets", default="meta/presets.json")
    parser.add_argument("--out", default="meta/poi_preset_compat_graph_v1.json")
    parser.add_argument("--out-meta", default="meta/poi_preset_compat_graph_v1_meta.json")
    parser.add_argument("--threshold", type=float, default=0.8)
    parser.add_argument("--all-geometries", action="store_true", help="Compute edges for all preset geometries, not only point/vertex")
    args = parser.parse_args()

    presets = load_presets(Path(args.presets))
    graph, meta = build_graph(presets, threshold=args.threshold, all_geometries=args.all_geometries)

    output = {
        "version": 1,
        "kind": "preset_compatibility_graph",
        "model": "taxonomy_pairwise_allowlist",
        "threshold": args.threshold,
        "all_geometries": bool(args.all_geometries),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": args.presets,
        "preset_count": len(presets),
        "node_count": len(graph),
        "graph": graph,
    }

    Path(args.out).write_text(json.dumps(output, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
    Path(args.out_meta).write_text(json.dumps({"version": 1, "meta": meta}, ensure_ascii=False, separators=(",", ":"), sort_keys=True))

    print(f"Wrote {args.out}")
    print(f"Wrote {args.out_meta}")
    print(f"Nodes: {len(graph)}")


if __name__ == "__main__":
    main()
