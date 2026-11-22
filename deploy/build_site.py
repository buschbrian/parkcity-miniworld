"""Copy the viewer into deploy/site/ with tile paths pointed at the /tiles/ Pages Function,
and list the painted squares in painted.json.

usage: .venv/bin/python deploy/build_site.py && (cd deploy && wrangler pages deploy)
"""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "deploy" / "site"

shutil.rmtree(SITE, ignore_errors=True)
shutil.copytree(ROOT / "viewer", SITE, ignore=shutil.ignore_patterns("config.json"))
cfg = json.loads((ROOT / "viewer" / "config.json").read_text(encoding="utf-8"))
for tag, layer in cfg["layers"].items():
    layer["path"] = f"/tiles/{tag}/{{z}}/{{x}}/{{y}}.jpg"
(SITE / "config.json").write_text(json.dumps(cfg, indent=1), encoding="utf-8")
painted_dir = ROOT / "painted" / "detail"
painted = sorted(p.stem for p in painted_dir.glob("r*_c*.png")) if painted_dir.exists() else []
(SITE / "painted.json").write_text(json.dumps({"detail": painted}), encoding="utf-8")
summary = ", ".join(f"{k} ({v['frames']} squares)" for k, v in cfg["layers"].items())
print(f"site built: {summary}; painted.json lists {len(painted)}")
