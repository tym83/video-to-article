#!/usr/bin/env python3
"""Stage: frames. Two modes.

    frames.py <workfolder> scenes [--threshold 0.3] [--min-gap 20]
        Detect visual scene changes, save one small preview per scene to frames/candidates/ and the
        list to frames/candidates.json (timestamp + file). The assembler picks illustration points from it.

    frames.py <workfolder> extract
        Read the IMAGE requests (ID + TIMESTAMP) from the newest article draft (or --from FILE),
        save full-size frames to frames/<id>.jpg, skip near-black/blurred frames by nudging the
        timestamp a little, and write frames/frames.json.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def sec(ts):
    """'00:12:34', '[00:12:34]', '12:34', '00:01:23,5' → seconds; raises ValueError on garbage."""
    parts = [float(p) for p in ts.strip().strip("[]").replace(",", ".").split(":")]
    while len(parts) < 3:
        parts.insert(0, 0.0)
    return parts[0] * 3600 + parts[1] * 60 + parts[2]


def hms(t):
    t = int(t)
    return f"{t // 3600:02d}:{t % 3600 // 60:02d}:{t % 60:02d}"


def video_path(root):
    src = root / "01-source"
    meta = json.loads((src / "source.json").read_text(encoding="utf-8"))
    video = src / meta["video"]
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=codec_type",
                            "-of", "csv=p=0", str(video)], capture_output=True, text=True).stdout
    if "video" not in probe:
        sys.exit("the source has no video stream (audio-only input): there are no frames to take")
    return video, meta


def scenes(root, threshold, min_gap):
    video, meta = video_path(root)
    out = root / "frames" / "candidates"
    out.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-hide_banner", "-i", str(video), "-filter:v", f"select='gt(scene,{threshold})',showinfo",
           "-f", "null", "-"]
    log = subprocess.run(cmd, capture_output=True, text=True).stderr
    times = [float(m) for m in re.findall(r"pts_time:([0-9.]+)", log)]
    picked, last = [], -1e9
    for t in [5.0] + times:
        if t - last >= min_gap:
            picked.append(t)
            last = t
    dur = meta.get("duration") or (picked[-1] if picked else 0)
    if len(picked) < 6 and dur:  # talking-head videos barely change: fall back to an even grid
        step = max(min_gap, dur / 12)
        picked = [5.0 + k * step for k in range(int((dur - 5) / step) + 1)]
    items = []
    for i, t in enumerate(picked):
        f = out / f"c{i:03d}_{hms(t).replace(':', '-')}.jpg"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{t + 1.0:.2f}", "-i", str(video), "-frames:v", "1",
                        "-vf", "scale=480:-2", "-q:v", "4", str(f)], check=False, capture_output=True)
        if f.exists():
            items.append({"timestamp": hms(t + 1.0), "seconds": round(t + 1.0, 2), "file": str(f.relative_to(root))})
    (root / "frames" / "candidates.json").write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(items)} scene candidates → frames/candidates.json")


IMAGE_RE = re.compile(r"^> IMAGE:[ \t]*$(?P<body>(?:\n>(?! [A-Z]+:[ \t]*$).*)+)", re.M)


def parse_requests(text):
    reqs = []
    for m in IMAGE_RE.finditer(text):
        fields = dict(re.findall(r"^>[ \t]*([A-Z_]+):[ \t]*(.*)$", m.group("body"), re.M))
        if "TIMESTAMP" in fields:
            reqs.append({"id": fields.get("ID") or f"img-{len(reqs) + 1:02d}", "timestamp": fields["TIMESTAMP"].strip(),
                         "alt": fields.get("ALT", ""), "caption": fields.get("CAPTION", "")})
    return reqs


def mean_luma_and_sharpness(path):
    try:
        from PIL import Image, ImageFilter, ImageStat
    except ImportError:
        return 128, 100
    im = Image.open(path).convert("L").resize((320, 180))
    luma = ImageStat.Stat(im).mean[0]
    edges = ImageStat.Stat(im.filter(ImageFilter.FIND_EDGES)).var[0]
    return luma, edges


def extract(root, src_file):
    video, _ = video_path(root)
    drafts = [p for p in root.glob("*.md") if p.name[0].isdigit()]
    if not src_file and not drafts:
        sys.exit("no draft with IMAGE requests found: pass --from <file>")
    draft = Path(src_file) if src_file else max(drafts, key=lambda p: p.stat().st_mtime)
    reqs = parse_requests(draft.read_text(encoding="utf-8"))
    out = root / "frames"
    out.mkdir(exist_ok=True)
    done = []
    failed = []
    for r in reqs:
        try:
            base = sec(r["timestamp"])
        except ValueError:
            failed.append(f"{r['id']}: unreadable TIMESTAMP '{r['timestamp']}'")
            continue
        f = out / f"{r['id']}.jpg"
        best = None
        for nudge in (0, 1.5, -1.5, 3, -3, 5):
            f.unlink(missing_ok=True)
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{max(0, base + nudge):.2f}", "-i", str(video),
                            "-frames:v", "1", "-q:v", "2", str(f)], check=False, capture_output=True)
            if not f.exists():
                continue
            luma, sharp = mean_luma_and_sharpness(f)
            score = sharp if 18 < luma < 240 else -1
            if best is None or score > best[0]:
                best = (score, nudge)
            if score > 60:
                break
        if best is None:
            failed.append(f"{r['id']}: no frame at {r['timestamp']} (past the end of the video?)")
            continue
        if best[1] != nudge or not f.exists():
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{max(0, base + best[1]):.2f}", "-i", str(video),
                            "-frames:v", "1", "-q:v", "2", str(f)], check=False, capture_output=True)
        if f.exists():
            done.append(dict(r, file=str(f.relative_to(root)), used_offset=best[1]))
        else:
            failed.append(f"{r['id']}: extraction failed at {r['timestamp']}")
    (out / "frames.json").write_text(json.dumps(done, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(done)} frames from {draft.name} → frames/")
    for msg in failed:
        print(f"FAILED {msg}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("workfolder")
    ap.add_argument("mode", choices=["scenes", "extract"])
    ap.add_argument("--threshold", type=float, default=0.3)
    ap.add_argument("--min-gap", type=float, default=20)
    ap.add_argument("--from", dest="src", help="draft to read IMAGE requests from (default: newest NN-*.md)")
    a = ap.parse_args()
    root = Path(a.workfolder)
    if a.mode == "scenes":
        scenes(root, a.threshold, a.min_gap)
    else:
        extract(root, a.src)


if __name__ == "__main__":
    sys.exit(main())
