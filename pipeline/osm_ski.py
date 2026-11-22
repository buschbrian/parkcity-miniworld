"""Fetch OSM downhill ski runs and chairlifts for the Park City AOI from Overpass.

Writes data/osm_ski.json:
  {"lifts": [{"name", "kind", "coords": [[lon, lat], ...]}],
   "runs":  [{"name", "difficulty", "coords": [[lon, lat], ...]}]}
Data (c) OpenStreetMap contributors, ODbL.
"""
import json
import urllib.parse
import urllib.request

from geo import ROOT, load_cam

OVERPASS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]


def query(bbox):
    s, w, n, e = bbox
    b = f"({s},{w},{n},{e})"
    return f"""[out:json][timeout:120];
(
  way["aerialway"~"^(chair_lift|gondola|mixed_lift|magic_carpet|drag_lift)$"]{b};
  way["piste:type"="downhill"]{b};
);
out geom;"""


def main():
    cam = load_cam()
    a = cam["levels"]["overview"]["aoi"]
    q = query((a["south"], a["west"], a["north"], a["east"]))
    els = None
    for url in OVERPASS:
        req = urllib.request.Request(
            url,
            data=urllib.parse.urlencode({"data": q}).encode(),
            headers={"User-Agent": "parkcity-miniworld/0.1"},
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                els = json.load(r)["elements"]
            break
        except Exception as e:
            print(f"{url}: {e}")
    if els is None:
        raise SystemExit("all Overpass endpoints failed")

    lifts, runs = [], []
    for el in els:
        if el.get("type") != "way":
            continue
        tags = el.get("tags", {})
        pts = [[p["lon"], p["lat"]] for p in el.get("geometry", [])]
        if len(pts) < 2:
            continue
        if "aerialway" in tags:
            lifts.append({"name": tags.get("name", ""), "kind": tags["aerialway"], "coords": pts})
        elif tags.get("piste:type") == "downhill":
            runs.append({
                "name": tags.get("name", ""),
                "difficulty": tags.get("piste:difficulty", "intermediate"),
                "coords": pts,
            })
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data" / "osm_ski.json").write_text(json.dumps({"lifts": lifts, "runs": runs}))
    print(f"{len(lifts)} lifts, {len(runs)} ski runs saved to data/osm_ski.json")
    print("lifts:", ", ".join(sorted({x["name"] for x in lifts if x["name"]})[:20]))


if __name__ == "__main__":
    main()
