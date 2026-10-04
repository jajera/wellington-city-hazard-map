#!/usr/bin/env python3
"""Bake published WCC/GWRC hazard overlays into ../hazards.geojson."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "hazards.geojson"
UA = "wcc-flood-heatmap-sample/0.3 (static bake)"
# Wellington City suburb extent (matches wellington-city.geojson)
BBOX = "174.613,-41.363,174.896,-41.143"
OFFSET = "0.00012"

# key, url, group, label, use_bbox, is_point, detail_fields
LAYERS = [
    ("ponding",
     "https://gis.wcc.govt.nz/arcgis/rest/services/DistrictPlanProposed/DistrictPlanProposed/MapServer/52",
     "flood", "Ponding / inundation", True, False, ["OverlayName", "SuburbArea"]),
    ("stream-corridor",
     "https://gis.wcc.govt.nz/arcgis/rest/services/DistrictPlanProposed/DistrictPlanProposed/MapServer/53",
     "flood", "Stream corridor", True, False, ["OverlayName", "SuburbArea"]),
    ("overland-flowpath",
     "https://gis.wcc.govt.nz/arcgis/rest/services/DistrictPlanProposed/DistrictPlanProposed/MapServer/51",
     "flood", "Overland flowpath", True, False, ["OverlayName", "SuburbArea"]),
    ("coastal-high",
     "https://gis.wcc.govt.nz/arcgis/rest/services/DistrictPlanProposed/DistrictPlanProposed/MapServer/40",
     "coastal", "High coastal inundation", False, False, ["Type", "Name", "dp_source"]),
    ("coastal-medium",
     "https://gis.wcc.govt.nz/arcgis/rest/services/DistrictPlanProposed/DistrictPlanProposed/MapServer/39",
     "coastal", "Medium coastal inundation", False, False, ["Type", "Name", "dp_source"]),
    ("tsunami-evac",
     "https://gis.wcc.govt.nz/arcgis/rest/services/Environment/TsunamiEvacuationZones/MapServer/1",
     "tsunami", "Tsunami evacuation zone", True, False, ["Evac_Zone", "Col_Code", "Location", "Info"]),
    ("tsunami-low",
     "https://gis.wcc.govt.nz/arcgis/rest/services/DistrictPlanProposed/DistrictPlanProposed/MapServer/42",
     "tsunami", "Low coastal tsunami hazard", False, False, ["Name", "Type"]),
    ("tsunami-med",
     "https://gis.wcc.govt.nz/arcgis/rest/services/DistrictPlanProposed/DistrictPlanProposed/MapServer/43",
     "tsunami", "Medium coastal tsunami hazard", False, False, ["Name", "Type"]),
    ("tsunami-high",
     "https://gis.wcc.govt.nz/arcgis/rest/services/DistrictPlanProposed/DistrictPlanProposed/MapServer/44",
     "tsunami", "High coastal tsunami hazard", False, False, ["Name", "Type"]),
    ("fault-ohariu",
     "https://gis.wcc.govt.nz/arcgis/rest/services/DistrictPlanProposed/DistrictPlanProposed/MapServer/46",
     "fault", "Ohariu Fault hazard", False, False, ["Name", "Fault_comp", "RI_Class"]),
    ("fault-shepherds",
     "https://gis.wcc.govt.nz/arcgis/rest/services/DistrictPlanProposed/DistrictPlanProposed/MapServer/47",
     "fault", "Shepherds Gully Fault hazard", False, False, ["Name", "Fault_comp", "RI_Class"]),
    ("fault-terawhiti",
     "https://gis.wcc.govt.nz/arcgis/rest/services/DistrictPlanProposed/DistrictPlanProposed/MapServer/48",
     "fault", "Terawhiti Fault hazard", False, False, ["Name", "Fault_comp", "RI_Class"]),
    ("fault-wellington",
     "https://gis.wcc.govt.nz/arcgis/rest/services/DistrictPlanProposed/DistrictPlanProposed/MapServer/49",
     "fault", "Wellington Fault hazard", False, False, ["Name", "Fault_comp", "RI_Class"]),
    ("liquefaction",
     "https://gis.wcc.govt.nz/arcgis/rest/services/DistrictPlanProposed/DistrictPlanProposed/MapServer/54",
     "liquefaction", "Liquefaction hazard", True, False, ["Liquefacti", "Simplified", "Source"]),
    ("slope-failure",
     "https://mapping1.gw.govt.nz/arcgis/rest/services/GW/Emergencies_P/MapServer/11",
     "landslide", "Slope failure susceptibility", True, False, ["SEVERITY"]),
    ("wind-zones",
     "https://gis.wcc.govt.nz/arcgis/rest/services/Environment/WindZones/MapServer/0",
     "wind", "Wind zone", True, False, ["wind_zone", "wind_code"]),
    ("eq-prone",
     "https://services1.arcgis.com/CPYspmTk3abe6d7i/arcgis/rest/services/MBIE_EPB_WCC_VW/FeatureServer/0",
     "earthquake", "Earthquake-prone building", True, True, ["Address", "URL"]),
]


def fetch(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.load(resp)


def simplify_ring(ring: list, eps: float = 1.4e-4) -> list:
    if len(ring) <= 4:
        return ring
    keep = [ring[0]]
    for i in range(1, len(ring) - 1):
        ax, ay = keep[-1]
        bx, by = ring[i]
        cx, cy = ring[i + 1]
        ab = ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5
        if ab < eps * 0.4:
            continue
        area2 = abs((bx - ax) * (cy - ay) - (by - ay) * (cx - ax))
        if area2 / max(ab, 1e-12) < eps:
            continue
        keep.append(ring[i])
    keep.append(ring[-1])
    if keep[0] != keep[-1]:
        keep.append(keep[0])
    return keep if len(keep) >= 4 else ring


def simplify_coords(coords):
    if not coords:
        return coords
    if isinstance(coords[0][0], (int, float)):
        return simplify_ring(coords)
    return [simplify_coords(c) for c in coords]


def detail_from(props: dict, fields: list[str]) -> str:
    parts = []
    for k in fields:
        v = props.get(k)
        if v not in (None, ""):
            parts.append(str(v))
    return " · ".join(parts)


# Official-ish colours from WCC DP Symbology / tsunami Col_Code / GWRC severity.
LAYER_COLOURS = {
    "ponding": ("#65C7EA", "#114CA8"),
    "stream-corridor": ("#114CA8", "#005CE6"),
    "overland-flowpath": ("#FFD37E", "#FFAA00"),
    "coastal-high": ("#73004C", "#73004C"),
    "coastal-medium": ("#0084A8", "#0084A8"),
    "tsunami-low": ("#00C5FF", "#00C5FF"),
    "tsunami-med": ("#0084A8", "#0084A8"),
    "tsunami-high": ("#73004C", "#73004C"),
    "fault-ohariu": ("#730000", "#1C6794"),
    "fault-shepherds": ("#730000", "#1C6794"),
    "fault-terawhiti": ("#730000", "#1C6794"),
    "fault-wellington": ("#730000", "#1C6794"),
    "liquefaction": ("#E6E600", "#E6E600"),
    "eq-prone": ("#DC2626", "#FFFFFF"),
}

TSUNAMI_EVAC = {
    "red": ("#E31A1C", "#E31A1C"),      # Shore Exclusion
    "orange": ("#FD8D3C", "#FD8D3C"),   # CDEM Evacuation
    "yellow": ("#FCCC0A", "#C9A000"),   # Self Evacuation
}

SLOPE = {
    "1": ("#FFFFB2", "#BDB76B"),
    "2": ("#FECC5C", "#D4A017"),
    "3": ("#FD8D3C", "#CC5500"),
    "4": ("#F03B20", "#A50F15"),
    "5": ("#BD0026", "#7A0019"),
}

WIND = {
    "L": ("#DEEBF7", "#6BAED6"),
    "M": ("#C6DBEF", "#4292C6"),
    "H": ("#9ECAE1", "#2171B5"),
    "VH": ("#6BAED6", "#08519C"),
    "EH": ("#3182BD", "#08306B"),
    "SED": ("#08519C", "#041C34"),
}


def colours_for(key: str, props: dict) -> tuple[str, str]:
    if key == "tsunami-evac":
        code = (props.get("Col_Code") or "").strip().lower()
        return TSUNAMI_EVAC.get(code, ("#0369A1", "#0369A1"))
    if key == "slope-failure":
        sev = str(props.get("SEVERITY") or "")
        digit = next((c for c in sev if c.isdigit()), "")
        return SLOPE.get(digit, ("#B45309", "#7C2D12"))
    if key == "wind-zones":
        code = (props.get("wind_zone") or "").strip().upper()
        return WIND.get(code, ("#64748B", "#334155"))
    return LAYER_COLOURS.get(key, ("#64748B", "#334155"))


def main() -> None:
    out = {
        "type": "FeatureCollection",
        "name": "wellington-city-hazards",
        "attribution": (
            "WCC / GWRC published layers (via wcc-emergency-gis-data). "
            "Planning/modelled — not live emergency information."
        ),
        "features": [],
    }

    for key, base, group, label, use_bbox, is_point, fields in LAYERS:
        params = {
            "where": "1=1",
            "outFields": "*",
            "returnGeometry": "true",
            "f": "geojson",
            "outSR": "4326",
            "geometryPrecision": "5",
            "resultRecordCount": "500",
        }
        if use_bbox:
            params.update(
                {
                    "geometry": BBOX,
                    "geometryType": "esriGeometryEnvelope",
                    "inSR": "4326",
                    "spatialRel": "esriSpatialRelIntersects",
                }
            )
        if not is_point:
            params["maxAllowableOffset"] = OFFSET

        print(f"fetching {key} …")
        data = fetch(f"{base}/query?{urllib.parse.urlencode(params)}")
        if data.get("error") and not is_point:
            params.pop("maxAllowableOffset", None)
            data = fetch(f"{base}/query?{urllib.parse.urlencode(params)}")
        if data.get("error"):
            print(f"  ERR {data['error']}")
            continue

        feats = data.get("features") or []
        print(f"  {len(feats)} features")
        for feat in feats:
            props = feat.get("properties") or {}
            geom = feat["geometry"]
            if not is_point and geom and geom.get("coordinates") is not None:
                geom["coordinates"] = simplify_coords(geom["coordinates"])
            fill, line = colours_for(key, props)
            out["features"].append(
                {
                    "type": "Feature",
                    "properties": {
                        "layer": key,
                        "group": group,
                        "layerLabel": label,
                        "detail": detail_from(props, fields),
                        "suburb": props.get("SuburbArea") or "",
                        "fill": fill,
                        "line": line,
                    },
                    "geometry": geom,
                }
            )

    OUT.write_text(json.dumps(out, separators=(",", ":")))
    print(f"wrote {OUT} ({OUT.stat().st_size / 1e6:.2f} MB, {len(out['features'])} features)")


if __name__ == "__main__":
    main()
