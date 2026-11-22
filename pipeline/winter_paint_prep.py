"""Helper for interactive / Antigravity winter tile painting in parkcity-miniworld.

  .venv/bin/python pipeline/winter_paint_prep.py prep r-1_c-1
      -> writes scratch/<name>_ctx.png (3D render with feathered painted neighbor overlap bands)
         and prints which edges already contain finished winter art.

  .venv/bin/python pipeline/winter_paint_prep.py commit r-1_c-1 /path/to/generated.jpg
      -> registers the generated tile onto renders/detail/<name>.jpg, checks drift & overlap MAD,
         and saves the registered 1024x1024 PNG to painted/detail/<name>.png.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from geo import ROOT, frame_name, load_cam, parse_name
from paint import affine, painted_path, register


def feathered_context(cam, level, r, c, render, hard_px=192):
    """Paste painted neighbor overlap bands with a soft alpha feather on the inner edge."""
    ctx = np.asarray(render, np.float32).copy()
    size, step = cam["frame_px"], cam["step_px"]
    ov = size - step  # 256
    feather = max(1, ov - hard_px)
    sides = []

    for dr, dc, side in ((-1, 0, "top"), (0, -1, "left"), (-1, -1, None)):
        p = painted_path(level, r + dr, c + dc)
        if not p.exists():
            continue
        nb = np.asarray(Image.open(p).convert("RGB"), np.float32)
        ox, oy = -dc * step, -dr * step
        x0, y0 = max(0, -ox), max(0, -oy)
        x1, y1 = min(size, size - ox), min(size, size - oy)
        crop = nb[y0 + oy:y1 + oy, x0 + ox:x1 + ox]

        # Build alpha ramp: 1.0 in outer hard_px, linearly fading to 0.0 across inner feather px
        alpha = np.ones((y1 - y0, x1 - x0), np.float32)
        if dr == -1:  # top neighbor -> fade near y1 (bottom of strip)
            yy = np.arange(y1 - y0, dtype=np.float32)
            ry = np.clip((ov - yy) / feather, 0.0, 1.0)
            alpha *= ry[:, None]
        if dc == -1:  # left neighbor -> fade near x1 (right of strip)
            xx = np.arange(x1 - x0, dtype=np.float32)
            rx = np.clip((ov - xx) / feather, 0.0, 1.0)
            alpha *= rx[None, :]

        a3 = alpha[..., None]
        ctx[y0:y1, x0:x1] = crop * a3 + ctx[y0:y1, x0:x1] * (1.0 - a3)
        if side:
            sides.append(side)

    return Image.fromarray(np.clip(ctx, 0, 255).astype(np.uint8)), sides


def cmd_prep(level, name, out_path):
    cam = load_cam()
    r, c = parse_name(name)
    render = Image.open(ROOT / "renders" / level / f"{name}.jpg").convert("RGB")
    ctx, sides = feathered_context(cam, level, r, c, render)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    ctx.save(out)
    print(json.dumps({"name": name, "sides": sides, "out": str(out)}))


def cmd_commit(level, name, src_path):
    cam = load_cam()
    r, c = parse_name(name)
    render = Image.open(ROOT / "renders" / level / f"{name}.jpg").convert("RGB")
    raw = Image.open(src_path).convert("RGB").resize((cam["frame_px"], cam["frame_px"]), Image.LANCZOS)
    s, dx, dy, peak = register(raw, render)
    reg = affine(raw, s, dx, dy, cam["frame_px"])

    out = painted_path(level, r, c)
    out.parent.mkdir(parents=True, exist_ok=True)
    reg.save(out)

    # Check overlap MAD against any existing top/left neighbors
    mads = {}
    size, step = cam["frame_px"], cam["step_px"]
    reg_a = np.asarray(reg, np.float32)
    for dr, dc, side in ((-1, 0, "top"), (0, -1, "left")):
        p = painted_path(level, r + dr, c + dc)
        if not p.exists():
            continue
        nb = np.asarray(Image.open(p).convert("RGB"), np.float32)
        if side == "left":
            mads[side] = round(float(np.abs(nb[:, step:] - reg_a[:, :size - step]).mean()), 2)
        else:
            mads[side] = round(float(np.abs(nb[step:, :] - reg_a[:size - step, :]).mean()), 2)

    print(json.dumps({"name": name, "scale": round(s, 3), "dx": round(dx, 2), "dy": round(dy, 2),
                      "peak": round(peak, 2), "overlap_mad": mads, "saved": str(out)}))


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
    a = ap.parse_args()
    if a.cmd == "prep":
        cmd_prep(a.level, a.name, a.out)
    else:
        cmd_commit(a.level, a.name, a.src)


if __name__ == "__main__":
    main()
