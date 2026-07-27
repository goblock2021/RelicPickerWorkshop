"""
Generate workshop.json -- a compact single-file index of all workshop submissions.
Reads submissions/*.json and produces workshop.json at the repo root.

Usage:
    python generate_workshop_json.py

The output workshop.json contains:
    - min_app_version: minimum RelicPicker version required
    - generated_at: ISO timestamp of generation
    - total: number of submissions
    - submissions[]: each with id, t(itle), a(uthor), d(escription), c(reated_at), r(elics)

The 'r' field uses the clipboard import format:
    RELIC_ID:EFFECT_ID1,EFFECT_ID2,...[:CURSE_ID1,CURSE_ID2,...]
    One relic per line. Curse IDs map positionally to effect IDs.
"""

import json
import sys
import time
from pathlib import Path

SUBMISSIONS_DIR = "submissions"
OUTPUT_FILE = "workshop.json"

# Bump this when the workshop data format requires a newer RelicPicker version.
# Older RelicPicker versions will see this and prompt the user to upgrade.
MIN_APP_VERSION = "0.2.0"


def relic_to_clipboard(relic: dict) -> str:
    """Convert a single relic dict to clipboard-format string.

    Format: RELIC_ID:EFFECT_ID1,EFFECT_ID2,...:CURSE_ID1,CURSE_ID2,...
    Curse IDs are positional (curse[0] -> effect[0]).
    If no curses exist, the curse segment is omitted entirely.
    """
    effects = relic.get("effects", [])
    eff_ids = [str(e["eff_id"]) for e in effects]
    curse_ids = [str(e["curse_id"]) for e in effects if e.get("curse_id") is not None]

    line = f"{relic['relic_id']}:{','.join(eff_ids)}"
    if curse_ids:
        line += f":{','.join(curse_ids)}"
    return line


def submissions_to_compact(submissions: list[dict]) -> list[dict]:
    """Convert full submission dicts to compact workshop entries."""
    compact = []
    for sub in submissions:
        data = sub.get("data", {})
        relics = data.get("relics", [])

        # Convert each relic to clipboard format, one per line
        relic_lines = [relic_to_clipboard(r) for r in relics]

        entry = {
            "id": sub["id"],
            "i": sub.get("issue_number", 0),
            "t": data.get("title", ""),
            "a": sub.get("author", ""),
            "d": data.get("description", ""),
            "c": sub.get("created_at", ""),
            "r": "\n".join(relic_lines),
        }
        compact.append(entry)

    compact.sort(key=lambda s: s.get("c", ""), reverse=True)
    return compact


def generate():
    """Main entry point -- generate workshop.json from submissions/."""
    sp = Path(SUBMISSIONS_DIR)
    if not sp.is_dir():
        print(f"ERROR: '{SUBMISSIONS_DIR}' directory not found", file=sys.stderr)
        sys.exit(1)

    # Read all submission JSON files
    submissions = []
    errors = []
    for fpath in sorted(sp.glob("*.json")):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                sub = json.load(f)
            submissions.append(sub)
        except (json.JSONDecodeError, OSError) as e:
            errors.append((fpath.name, str(e)))

    if errors:
        for name, err in errors:
            print(f"  SKIP {name}: {err}", file=sys.stderr)

    # Convert to compact format
    compact = submissions_to_compact(submissions)

    # Build output
    workshop = {
        "min_app_version": MIN_APP_VERSION,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total": len(compact),
        "submissions": compact,
    }

    # Write
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(workshop, f, ensure_ascii=False, indent=2)

    print(f"Generated {OUTPUT_FILE}: {len(compact)} submissions")
    return workshop


if __name__ == "__main__":
    generate()
