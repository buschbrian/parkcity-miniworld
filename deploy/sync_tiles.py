"""Upload new or changed tiles, painted squares, and style/ref.png to R2 (parkcity-miniworld-tiles).
Tracks MD5 hashes in deploy/.synced.json so repeated runs only upload changed files.

usage: .venv/bin/python deploy/sync_tiles.py [--workers 12] [--dry-run]
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEPLOY = Path(__file__).resolve().parent
BUCKET = "parkcity-miniworld-tiles"
STATE = DEPLOY / ".synced.json"


def md5_file(p: Path) -> str:
    h = hashlib.md5()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_files():
    items = []
    tiles_dir = ROOT / "tiles"
    if tiles_dir.exists():
        for p in sorted(tiles_dir.rglob("*.jpg")):
            key = p.relative_to(tiles_dir).as_posix()
            items.append((key, p, "image/jpeg"))
    painted_dir = ROOT / "painted" / "detail"
    if painted_dir.exists():
        for p in sorted(painted_dir.glob("r*_c*.png")):
            items.append((f"painted/detail/{p.name}", p, "image/png"))
    ref = ROOT / "style" / "ref.png"
    if ref.exists():
        items.append(("style/ref.png", ref, "image/png"))
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    wrangler = shutil.which("wrangler") or "/opt/homebrew/bin/wrangler"
    sent = json.loads(STATE.read_text()) if STATE.exists() else {}
    todo = []
    for key, path, ctype in collect_files():
        sig = md5_file(path)
        if sent.get(key) != sig:
            todo.append((key, path, sig, ctype))

    print(f"{len(todo)} files to upload to {BUCKET}")
    if a.dry_run or not todo:
        return

    env = {**os.environ, "PATH": f"/opt/homebrew/bin:{os.environ.get('PATH', '')}"}

    def upload(item):
        key, path, sig, ctype = item
        pr = subprocess.run(
            [wrangler, "r2", "object", "put", f"{BUCKET}/{key}", "--file", str(path),
             "--content-type", ctype, "--remote"],
            cwd=str(DEPLOY), capture_output=True, text=True, env=env,
        )
        return key, sig, pr.returncode == 0, (pr.stderr or pr.stdout).strip().splitlines()[-1:]

    ok, failed = 0, []
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = [ex.submit(upload, it) for it in todo]
        for fut in as_completed(futs):
            key, sig, good, err = fut.result()
            if good:
                sent[key] = sig
                ok += 1
            else:
                failed.append((key, err))
            if (ok + len(failed)) % 100 == 0:
                print(f"  progress: {ok} uploaded, {len(failed)} failed")

    STATE.write_text(json.dumps(sent, indent=1))
    print(f"{ok} uploaded, {len(failed)} failed")
    for k, e in failed[:5]:
        print(f"  FAIL {k}: {e}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
