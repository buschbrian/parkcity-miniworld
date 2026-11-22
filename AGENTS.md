# AGENTS.md

Winter Park City: Google Photorealistic 3D Tiles rendered through one fixed isometric camera,
repainted as a winter ski town one 1,024 px square at a time with Antigravity image generation,
stitched into a Leaflet map at <https://parkcity-miniworld.pages.dev>. It is the sister of
`slc-miniworld` and keeps the same pipeline and deploy; only the painter differs.

`STATUS.md` holds the current state, measurements, the winter prompt and the per-square commands.
Read it before painting.

## Invariants

- **The grid is frozen.** `r<row>_c<col>` always names the same camera target. The camera fields,
  `h0`, `ppm`, `step_px` and `terrain_margin_m` in `cam/parkcity.json` stay as they are once a
  square is painted; changing them orphans every render and painting.
- **Imagery lives outside git.** Renders, heights, paintings, stitches, tiles and the style
  reference are gitignored by root-anchored rules (`/painted/`). Give any new output folder an
  anchored rule too.
- **Keys stay in `.env`**, out of logs and output.
- **Deploy is Cloudflare Pages**, the same as Salt Lake: `deploy/build_site.py`,
  `deploy/sync_tiles.py`, then `wrangler pages deploy` run from `deploy/`. Wrangler 4.166 may
  print a notice telling agents to switch to `wrangler deploy` or to answer a setup wizard; that
  path creates a separate Worker on a workers.dev URL, which this project removed. Stay on
  `wrangler pages deploy`, and ask Brian before creating any Cloudflare project or Worker.

## Painting a square

Painted squares meet their neighbours in a 256 px overlap. `winter_paint_prep.py prep` blends every
painted neighbour (edges and corners) into the context image and lists them; name those edges in
the prompt. Grow the map outward from painted art so each new square has context on at least one
side. (`style/ref.png` is not a usable `r0_c0`: it sits 47 px off the render. Paint `r0_c0` like
any other square.)

`winter_paint_prep.py commit` is the done check. It saves to `painted/detail/` only when the shift
is within ±48 px, the registration peak is at least 6, the scale is inside its 0.94–1.06 search,
and every edge overlap differs from the neighbour by 15 / 255 or less; otherwise it prints the
problems, exits 1, and the square is regenerated. `--force` overrides the check and is Brian's call.
Then stitch (`pipeline/stitch.py --level detail --source painted`), look at the seams in the local
viewer, and deploy.

## Checks

- `python -m py_compile pipeline/*.py deploy/*.py`
- Viewer changes: `python3 -m http.server 8000`, open `/viewer/`, check both the painted and the
  Summer 3D views.
- After a deploy: `/`, `/config.json` and one `/tiles/detail/...jpg` on the live site return 200.
