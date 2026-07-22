"""
Creative Workshop — Submission Validator
Runs in GitHub Actions on every PR to validate submissions.

Checks:
1. All JSON files in submissions/ are valid and conform to schema
2. No duplicate submissions (same effects + shop + color + relic_id)
3. Deletions are authorized (PR author matches submission author)
4. Filename matches the submission's id field

Usage:
    python validate_submissions.py

Environment variables:
    PR_AUTHOR — the GitHub username of the PR author (from github.event.pull_request.user.login)
"""

import json
import os
import sys
from pathlib import Path

SUBMISSIONS_DIR = "submissions"

# Required fields and their types
SCHEMA = {
    "id": str,
    "author": str,
    "title": str,
    "description": str,
    "effects": list,
    "shop": str,
    "color": int,
    "relic_id": int,
    "effect_names": list,
    "curse_names": list,
    "relic_name": str,
    "created_at": str,
}

# Valid shop values
VALID_SHOPS = {"normal-old", "normal-new", "deep-old", "deep-new"}

# Valid color values
VALID_COLORS = {0, 1, 2, 3}


def fail(msg: str):
    print(f"❌ VALIDATION FAILED: {msg}")
    sys.exit(1)


def ok(msg: str):
    print(f"✓ {msg}")


def load_submission(filepath: Path) -> dict | None:
    """Load and validate a single submission JSON file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        fail(f"Invalid JSON in {filepath.name}: {e}")
    except Exception as e:
        fail(f"Cannot read {filepath.name}: {e}")

    # Schema validation
    for field, ftype in SCHEMA.items():
        if field not in data:
            fail(f"{filepath.name}: missing required field '{field}'")
        if not isinstance(data[field], ftype):
            fail(f"{filepath.name}: field '{field}' must be {ftype.__name__}, got {type(data[field]).__name__}")

    # Validate shop
    if data["shop"] not in VALID_SHOPS and data["shop"] != "unknown":
        fail(f"{filepath.name}: invalid shop value '{data['shop']}'")

    # Validate color
    if data["color"] not in VALID_COLORS and data["color"] != -1:
        fail(f"{filepath.name}: invalid color value {data['color']}")

    # Validate effects list — each must be {eff_id, curse_id}
    for i, e in enumerate(data.get("effects", [])):
        if not isinstance(e, dict):
            fail(f"{filepath.name}: effects[{i}] must be a dict")
        if "eff_id" not in e:
            fail(f"{filepath.name}: effects[{i}] missing eff_id")

    # Validate filename matches id
    expected_name = f"{data['id']}.json"
    if filepath.name != expected_name:
        fail(f"{filepath.name}: filename must match submission id ({expected_name})")

    # Title length
    if len(data.get("title", "").strip()) == 0:
        fail(f"{filepath.name}: title cannot be empty")
    if len(data["title"]) > 100:
        fail(f"{filepath.name}: title too long (max 100 chars)")

    # Description length
    if len(data.get("description", "")) > 500:
        fail(f"{filepath.name}: description too long (max 500 chars)")

    return data


def submission_key(sub: dict) -> tuple:
    """Generate a dedup key for a submission."""
    eff_key = tuple(
        (e.get("eff_id"), e.get("curse_id"))
        for e in sorted(sub.get("effects", []), key=lambda x: x.get("eff_id", 0))
    )
    return (eff_key, sub.get("shop"), sub.get("color"), sub.get("relic_id"))


def main():
    pr_author = os.environ.get("PR_AUTHOR", "").strip()
    if not pr_author:
        fail("PR_AUTHOR environment variable is not set")

    ok(f"PR Author: {pr_author}")

    submissions_path = Path(SUBMISSIONS_DIR)
    if not submissions_path.exists():
        fail(f"'{SUBMISSIONS_DIR}' directory not found")

    # Collect all existing submissions on main (pre-PR state) by loading from the
    # current checkout (which includes merged content). We check for duplicates
    # across all files, then verify author for deletions.

    # Get changed files from git diff against base
    import subprocess
    try:
        result = subprocess.run(
            ["git", "diff", "--name-status", "HEAD^", "HEAD"],
            capture_output=True, text=True, check=True
        )
        changes = result.stdout.strip().splitlines()
    except subprocess.CalledProcessError:
        # Fallback: try diff against origin/main
        try:
            result = subprocess.run(
                ["git", "diff", "--name-status", "origin/main", "HEAD"],
                capture_output=True, text=True, check=True
            )
            changes = result.stdout.strip().splitlines()
        except subprocess.CalledProcessError:
            # Last fallback: just validate all files in submissions/
            ok("Could not determine changed files — validating all submissions")
            changes = [f"A\tsubmissions/{f.name}" for f in submissions_path.glob("*.json")]

    if not changes:
        ok("No changes to submissions/ — nothing to validate")
        return

    added_files = []
    deleted_files = []
    modified_files = []

    for line in changes:
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status, filepath = parts[0], parts[1]
        if not filepath.startswith(SUBMISSIONS_DIR + "/"):
            continue
        if not filepath.endswith(".json"):
            continue

        if status == "D":
            deleted_files.append(filepath)
        elif status == "A":
            added_files.append(filepath)
        elif status == "M":
            modified_files.append(filepath)

    ok(f"Changes: {len(added_files)} added, {len(modified_files)} modified, {len(deleted_files)} deleted")

    # Load all current submissions (for dup checks)
    all_subs = {}
    dedup_keys = {}

    for f in submissions_path.glob("*.json"):
        try:
            sub = load_submission(f)
            if sub:
                all_subs[str(f)] = sub
                # Track dedup keys for non-deleted files
                if str(f) not in deleted_files:
                    key = submission_key(sub)
                    dedup_keys[key] = sub["id"]
        except SystemExit:
            # load_submission calls fail() which exits — but we want to validate
            # only the changed files strictly, existing files are assumed valid.
            # Re-raise if it's a changed file.
            if str(f) in added_files or str(f) in modified_files:
                raise

    # Validate added/modified files
    for filepath_str in added_files + modified_files:
        fp = Path(filepath_str)
        if not fp.exists():
            fail(f"{filepath_str}: file listed as added/modified but does not exist")

        sub = load_submission(fp)
        if sub is None:
            continue

        # Check for duplicates (skip if this exact file exists in the index)
        key = submission_key(sub)
        existing_id = dedup_keys.get(key)
        if existing_id and existing_id != sub["id"]:
            fail(
                f"{filepath_str}: duplicate submission — "
                f"same effects+shop+color+relic_id already exists as '{existing_id}'"
            )

        ok(f"Validated: {filepath_str} — '{sub['title']}' by {sub['author']}")

    # Validate deletions
    for filepath_str in deleted_files:
        fp = Path(filepath_str)
        # File is already deleted, but we might have it in git history
        # Try to get the content from git
        try:
            result = subprocess.run(
                ["git", "show", f"HEAD^:{filepath_str}"],
                capture_output=True, text=True, check=True
            )
            sub = json.loads(result.stdout)
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            fail(f"{filepath_str}: cannot verify deleted file — unable to read original content")

        author = sub.get("author", "")
        if author.lower() != pr_author.lower():
            fail(
                f"{filepath_str}: unauthorized deletion — "
                f"file author is '{author}' but PR author is '{pr_author}'"
            )

        ok(f"Deletion authorized: {filepath_str} — '{sub.get('title', '?')}' by {author}")

    print("\n✅ All validations passed!")
    print(f"   {len(added_files)} added, {len(modified_files)} modified, {len(deleted_files)} deleted")


if __name__ == "__main__":
    main()
