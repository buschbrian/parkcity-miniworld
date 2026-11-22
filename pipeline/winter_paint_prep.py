"""Helper for interactive / Antigravity winter tile painting in parkcity-miniworld.

  .venv/bin/python pipeline/winter_paint_prep.py prep r-1_c-1 --out /tmp/pc_r-1_c-1_ctx.png
      -> writes the 3D render with every painted neighbour's overlap band feathered in,
         and prints which edges and corners already contain finished winter art.

  .venv/bin/python pipeline/winter_paint_prep.py commit r-1_c-1 /path/to/generated.jpg
      -> registers the generated tile onto renders/detail/<name>.jpg and saves the registered
         1024x1024 PNG to painted/detail/<name>.png only if drift, scale, peak and every
         neighbour overlap pass. A refused square prints its reasons and exits 1.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from geo import ROOT, load_cam, parse_name
from paint import affine, painted_path, register

# The eight neighbours, by offset; edges first so corners blend over them.
NEIGHBOURS = (
    (-1, 0, "top"), (1, 0, "bottom"), (0, -1, "left"), (0, 1, "right"),
    (-1, -1, "top-left"), (-1, 1, "top-right"), (1, -1, "bottom-left"), (1, 1, "bottom-right"),
)
MAX_SHIFT_PX = 48  # same limits as paint.py
MIN_PEAK = 6
SCALE_RANGE = (0.94, 1.06)  # register()'s search; a result on either end means it hit the edge
MAX_OVERLAP_MAD = 15.0  # the first painted neighbours measured 12.5-13.3


def band(size, step, d):
    """Slice of this frame covered by a neighbour at offset d (-1, 0, 1) along one axis,
    and the matching slice of the neighbour."""
    o = -d * step  # this frame's pixel x == neighbour pixel x + o
    lo, hi = max(0, -o), min(size, size - o)
    return slice(lo, hi), slice(lo + o, hi + o)


def ramp(n, d, ov, feather):
    """Alpha along one axis of a band: 1 at the outer edge, falling to 0 at the inner edge."""
    if d == 0:
        return np.ones(n, np.float32)
    x = np.arange(n, dtype=np.float32)
    dist_to_inner = ov - x if d < 0 else x + 1
    return np.clip(dist_to_inner / feather, 0.0, 1.0)


def feathered_context(cam, level, r, c, render, hard_px=192):
    """Paste every painted neighbour's overlap band, keeping the outer hard_px and feathering the rest."""
    ctx = np.asarray(render, np.float32).copy()
    size, step = cam["frame_px"], cam["step_px"]
    ov = size - step  # 256
    feather = max(1, ov - hard_px)
    sides = []
    for dr, dc, side in NEIGHBOURS:
        p = painted_path(level, r + dr, c + dc)
        if not p.exists():
            continue
        nb = np.asarray(Image.open(p).convert("RGB"), np.float32)
        ys, nys = band(size, step, dr)
        xs, nxs = band(size, step, dc)
        crop = nb[nys, nxs]
        alpha = ramp(crop.shape[0], dr, ov, feather)[:, None] * ramp(crop.shape[1], dc, ov, feather)[None, :]
        a3 = alpha[..., None]
        ctx[ys, xs] = crop * a3 + ctx[ys, xs] * (1.0 - a3)
        sides.append(side)
    return Image.fromarray(np.clip(ctx, 0, 255).astype(np.uint8)), sides


def overlap_mads(cam, level, r, c, img):
    """Mean absolute difference against each painted edge neighbour across the shared band."""
    size, step = cam["frame_px"], cam["step_px"]
    a = np.asarray(img, np.float32)
    mads = {}
    for dr, dc, side in NEIGHBOURS[:4]:
        p = painted_path(level, r + dr, c + dc)
        if not p.exists():
            continue
        nb = np.asarray(Image.open(p).convert("RGB"), np.float32)
        ys, nys = band(size, step, dr)
        xs, nxs = band(size, step, dc)
        mads[side] = round(float(np.abs(nb[nys, nxs] - a[ys, xs]).mean()), 2)
    return mads


def cmd_prep(level, name, out_path):
    cam = load_cam()
    r, c = parse_name(name)
    render = Image.open(ROOT / "renders" / level / f"{name}.jpg").convert("RGB")
    ctx, sides = feathered_context(cam, level, r, c, render)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    ctx.save(out)
    print(json.dumps({"name": name, "sides": sides, "out": str(out)}))


def cmd_commit(level, name, src_path, force=False):
    cam = load_cam()
    r, c = parse_name(name)
    size = cam["frame_px"]
    render = Image.open(ROOT / "renders" / level / f"{name}.jpg").convert("RGB")
    raw = Image.open(src_path).convert("RGB").resize((size, size), Image.LANCZOS)
    s, dx, dy, peak = register(raw, render)
    reg = affine(raw, s, dx, dy, size)
    mads = overlap_mads(cam, level, r, c, reg)

    problems = []
    if abs(dx) > MAX_SHIFT_PX or abs(dy) > MAX_SHIFT_PX:
        problems.append(f"shift ({dx:.0f}, {dy:.0f}) px is over {MAX_SHIFT_PX}")
    if peak < MIN_PEAK:
        problems.append(f"registration peak {peak:.1f} is under {MIN_PEAK}")
    if not SCALE_RANGE[0] < round(s, 2) < SCALE_RANGE[1]:
        problems.append(f"scale {s:.2f} is at the edge of the {SCALE_RANGE[0]}-{SCALE_RANGE[1]} search")
    problems += [f"{side} overlap differs by {m} (limit {MAX_OVERLAP_MAD})" for side, m in mads.items()
                 if m > MAX_OVERLAP_MAD]

    ok = not problems or force
    out = painted_path(level, r, c)
    if ok:
        out.parent.mkdir(parents=True, exist_ok=True)
        reg.save(out)
    print(json.dumps({"name": name, "scale": round(s, 3), "dx": round(dx, 2), "dy": round(dy, 2),
                      "peak": round(peak, 2), "overlap_mad": mads, "problems": problems,
                      "saved": str(out) if ok else None}))
    if not ok:
        raise SystemExit(1)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("prep")
    p1.add_argument("name")
    p1.add_argument("--level", default="detail")
    p1.add_argument("--out", required=True)
    p2 = sub.add_parser("commit")
    p2.add_argument("name")
    p2.add_argument("src")
    p2.add_argument("--level", default="detail")
    p2.add_argument("--force", action="store_true", help="save even when a check fails")
    a = ap.parse_args()
    if a.cmd == "prep":
        cmd_prep(a.level, a.name, a.out)
    else:
        cmd_commit(a.level, a.name, a.src, a.force)


if __name__ == "__main__":
    main()
