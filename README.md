# Winter Park City — Mini World

A winter-painted, isometric-style tile map of Park City, Utah, built on the Mini World pipeline (Google Photorealistic 3D Tiles rendered with a fixed 30° orthographic camera, transformed from summer 3D meshes into a cozy winter ski town with Antigravity image generation, and stitched into an interactive Leaflet visitor map).

## Camera and grid (frozen)

| | |
|---|---|
| Anchor | Historic Main Street, `40.6438, −111.4966`; frozen `h0 = 2,131.0 m` ellipsoidal (`cam/parkcity_probe.json`) |
| Camera | Orthographic, heading 45° (looking northeast), 30° down (2:1), no perspective |
| Squares | `1,024 px` painted, `768 px` step (`256 px` overlap), rendered at `2,048 px` then downscaled |
| `detail` (`zoom: 8`) | `3.4 px/m` — Old Town, Historic Main Street, Town Lift, Quit'N Time run, PCMR base (**73 squares**, ~7.4 km²) |
| `overview` (`zoom: 7`) | `1.7 px/m` — Expands to Deer Valley Snow Park and upper mountain runs (**81 squares**, ~33.1 km²) |

## Quick start

```bash
# View the interactive winter visitor map locally
python3 -m http.server 8000
# then open http://localhost:8000/viewer/
```

## Pipeline commands

Use `.venv/bin/python` for Python steps and `/opt/homebrew/bin/node` (or `node`) for 3D rendering:

```bash
# 1. Render more 3D tiles (resumable; skips finished squares)
node render3d/server.mjs --mode render --level detail [--only r0_c0,r0_c1] [--limit 10]
.venv/bin/python pipeline/prep_renders.py --level detail

# 2. Prep feathered overlap context for a winter tile, then commit after painting
.venv/bin/python pipeline/winter_paint_prep.py prep r-1_c1 --out /tmp/pc_r-1_c1_ctx.png
.venv/bin/python pipeline/winter_paint_prep.py commit r-1_c1 /path/to/painted.jpg

# 3. Refresh OSM ski runs & chairlifts (when Overpass is available)
.venv/bin/python pipeline/osm_ski.py

# 4. Stitch Leaflet pyramids (both winter painted and summer 3D comparison layer)
.venv/bin/python pipeline/stitch.py --level detail --source renders
.venv/bin/python pipeline/stitch.py --level detail --source painted
```

## Terms and attribution

Google's Map Tiles API terms restrict caching and storing Google content and making derivative works from it. `renders/`, `heights/`, `painted/`, `stitched/`, `tiles/`, `style/`, and `.env` are gitignored and stay local. The viewer displays Google and OpenStreetMap attribution.
