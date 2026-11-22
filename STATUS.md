# Status — 2026-11-22

## Google 3D coverage for Park City

The probe (`cam/parkcity_probe.json`) found photorealistic 3D at all 20 sample points: the anchor,
11 landmarks, and the corners of both areas. Imagery is credited to Google.

- **The mesh is summer.** Google's capture has bare ground and green trees. Every bit of snow,
  every skier and every lit window comes from the painter. The render only fixes geometry.
- **Terrain is large.** The detail SW corner sits +382 m above the anchor ground, and the overview
  SW corner +580 m. The tallest detail square (`r3_c-1`) reaches +551 m. The height encoding
  (−300 to +2,321 m in 4 cm steps) covers this. Frame planning only looks at ground and
  `terrain_margin_m` (+300 m), so raise that before extending the area up the mountain, and do it
  before any square there is painted: the grid is frozen once painting starts.
- Anchor ground height h0 = 2,131.0 m ellipsoidal (the 2,115 m guess plus the anchor patch's
  5th-percentile surface, +16 m), frozen.

## Grid

| Level | ppm | Squares | State |
|---|---|---|---|
| detail | 3.4 | 73 (~7.4 km²) | all rendered; 3 painted (`r-1_c-1`, `r-1_c0`, `r0_c-1`) |
| overview | 1.7 | 81 (~33.1 km²) | planned (`cam/parkcity_overview_shots.json`), not rendered |

The live site has two layers: `detail_render` (the summer renders) and `detail` (the winter
paintings). The viewer hides each painted layer's empty background so the render shows through.

## Measured so far

- Render: 73 detail squares, median 5.2 s and at most 15.1 s each, 6.7 min in total. QA flagged none.
- Registration: re-registering the three committed paintings onto their renders gives scale 1.000
  and zero shift, so the commit step is stable.
- Seams: painted neighbours differ by 12.5–13.3 / 255 (mean absolute) across their 256 px overlap.
  The raw renders differ by 0.3. `stitch.py` evens out brightness and blends the overlap, but
  content that differs between two paintings shows as a soft ghost in the band. Painting in
  wavefront order with the neighbour context keeps this down: never paint a square before its top
  and left neighbours.

## Known issues

1. **Ski runs and lifts are hand-drawn, not OpenStreetMap.** All three Overpass endpoints failed
   when `osm_ski.py` first ran, and `data/osm_ski.json` was written by hand: 3 runs and 2 lifts of
   3–6 points each. They are off. The hand PayDay line ends about 1 km from OSM's top terminal,
   and Town Lift about 500 m short. The viewer still credits them to OpenStreetMap. On 2026-11-22
   overpass-api.de answered for the overview area with 16 lifts and 147 downhill runs, so
   re-running `pipeline/osm_ski.py` replaces them. Check the viewer for clutter afterwards.
2. **The winter prompt lived only in the Antigravity session.** It is recorded below. `paint.py`
   still carries the Salt Lake summer prompt, and is not what painted these squares.
3. **`paint.py` and `painters.py` are an older copy of Salt Lake's.** They lack Salt Lake's
   "no trees on open lawns, plazas, parking lots" line and the Windows Codex fix. Neither matters
   for the Antigravity route; port both if Codex ever paints here.

## Painting a square (Antigravity)

1. Pick the next square in wavefront order (top and left neighbours painted first). Wave 2 is
   `r-1_c1`, `r0_c0`, `r1_c-1`, which finishes the 3×3 core around the anchor.
2. `.venv/bin/python pipeline/winter_paint_prep.py prep <name> --out /tmp/pc_<name>_ctx.png`
   writes the render with the painted neighbours' overlap feathered in, and says which edges have art.
3. Generate with the context image as Image 1 and `style/ref.png` as Image 2, using the prompt below.
4. `.venv/bin/python pipeline/winter_paint_prep.py commit <name> <generated.jpg>` registers the image
   onto the render. Repaint if the scale lands at the edge of the 0.94–1.06 search, or if
   `overlap_mad` comes out well above the 12.5–13.3 measured so far.
5. `stitch.py --level detail --source painted`, then `deploy/build_site.py`, `deploy/sync_tiles.py`
   and `wrangler pages deploy` (see README).

The prompt used for the first squares. Name the edges that already hold art:

> Edit Image 1 into a 1:1 square winter alpine pixel-art map tile using Image 2 as the exact style
> reference. Image 1 is a summer 3D render of one map tile of Park City, Utah. The TOP edge of
> Image 1 already contains finished winter pixel art from the neighboring tile; keep that top-edge
> art unchanged and continue its exact snow brightness, color palette, outline thickness, and pixel
> scale seamlessly across the rest of the tile with NO horizontal seam or brightness step. Repaint
> the summer portion as a lively WINTER SKI TOWN matching Image 2 and the top strip: bright snow
> with cool blue-violet shadows on roofs and slopes, snow-dusted conifers, plowed dark-grey roads
> with snowbanks, warm glowing amber storefront/house windows, and tiny skiers on any groomed open
> ski runs. Keep the exact camera, framing, scale, and layout of Image 1: every building, road,
> tree cluster, and hillside stays in the exact same position, shape, and size. Leave out most cars
> so streets and parking lots feel clean. No text, labels, borders, or UI. Output one 1:1 square
> image with exactly the framing of Image 1.

Image 2 is a style reference only: copy its palette, outlines, snow shading and conifers, never its
buildings or layout. `style/ref.png` is the winter bootstrap of `r0_c0`; that square itself is not
yet committed to `painted/`.
