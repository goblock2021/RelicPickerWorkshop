"""
Creative Workshop — Issue Processor
Called by GitHub Actions when a workshop Issue is opened.

Usage:
    python process_issue.py share    # Process a share submission
    python process_issue.py delete   # Process a delete request

Environment variables:
    ISSUE_BODY   — the Issue body text
    ISSUE_NUMBER — the Issue number
    ISSUE_AUTHOR — the GitHub username of the Issue author
"""

import json
import os
import re
import sys
import time
import uuid as uuid_module
from pathlib import Path

SUBMISSIONS_DIR = "submissions"
FILE_VERSION = 1

# ── Allowed user fields (everything else is stripped) ─────────────
# These are the ONLY fields accepted from the client submission.
ALLOWED_FIELDS = {
    "title",
    "description",
    "effects",
    "shop",
    "color",
    "relic_id",
    "effect_names",
    "curse_names",
    "relic_name",
}

# Schema for user fields (inside the "data" key)
USER_SCHEMA = {
    "title": str,
    "description": str,
    "effects": list,
    "shop": str,
    "color": int,
    "relic_id": int,
    "effect_names": list,
    "curse_names": list,
    "relic_name": str,
}

VALID_SHOPS = {"normal-old", "normal-new", "deep-old", "deep-new"}


def fail(msg: str):
    print(f"❌ ERROR: {msg}")
    sys.exit(1)


def ok(msg: str):
    print(f"✓ {msg}")


def extract_json_from_body(body: str) -> str | None:
    """Extract JSON string from between ```json ... ``` markers."""
    match = re.search(r"```json\s*\n(.*?)\n\s*```", body, re.DOTALL)
    if match:
        return match.group(1)
    # Fallback: try ``` without language tag
    match = re.search(r"```\s*\n(\{.*?\})\s*\n\s*```", body, re.DOTALL)
    if match:
        return match.group(1)
    return None


def validate_user_data(data: dict) -> None:
    """Validate user-submitted fields. Fails on invalid."""
    for field, ftype in USER_SCHEMA.items():
        if field not in data:
            fail(f"缺少必填字段 '{field}'")
        if not isinstance(data[field], ftype):
            fail(f"字段 '{field}' 应为 {ftype.__name__}，实际为 {type(data[field]).__name__}")

    if data["shop"] not in VALID_SHOPS and data["shop"] != "unknown":
        fail(f"无效的 shop 值: '{data['shop']}'")

    if data["color"] not in {0, 1, 2, 3} and data["color"] != -1:
        fail(f"无效的 color 值: {data['color']}")

    for i, e in enumerate(data.get("effects", [])):
        if not isinstance(e, dict):
            fail(f"effects[{i}] 必须是对象")
        if "eff_id" not in e:
            fail(f"effects[{i}] 缺少 eff_id")

    if not data.get("title", "").strip():
        fail("title 不能为空")
    if len(data["title"]) > 100:
        fail("title 过长（最多100字符）")

    if len(data.get("description", "")) > 500:
        fail("description 过长（最多500字符）")


def submission_key(data: dict) -> tuple:
    """Generate a dedup key from user data."""
    eff_key = tuple(
        (e.get("eff_id"), e.get("curse_id"))
        for e in sorted(data.get("effects", []), key=lambda x: x.get("eff_id", 0))
    )
    return (eff_key, data.get("shop"), data.get("color"), data.get("relic_id"))


def load_all_submissions() -> dict[str, dict]:
    """Load all existing submissions into a dict {id: full_submission}."""
    result = {}
    sp = Path(SUBMISSIONS_DIR)
    if not sp.exists():
        sp.mkdir(parents=True, exist_ok=True)
        return result

    for f in sp.glob("*.json"):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                result[f.stem] = json.load(fh)
        except (json.JSONDecodeError, OSError):
            pass
    return result


def process_share():
    """Handle a share submission Issue."""
    body = os.environ.get("ISSUE_BODY", "")
    issue_author = os.environ.get("ISSUE_AUTHOR", "")

    ok(f"处理分享请求 — Issue author: {issue_author}")

    # Extract raw JSON from Issue body
    json_str = extract_json_from_body(body)
    if not json_str:
        fail("无法从 Issue 正文中找到 JSON 数据")

    try:
        raw = json.loads(json_str)
    except json.JSONDecodeError as e:
        fail(f"JSON 解析失败: {e}")

    if not isinstance(raw, dict):
        fail("JSON 必须是对象")

    # ── Strip unknown / forged fields — only keep ALLOWED_FIELDS ──
    user_data = {}
    for field in ALLOWED_FIELDS:
        if field in raw:
            user_data[field] = raw[field]

    # Validate user data
    validate_user_data(user_data)
    ok(f"格式验证通过: '{user_data['title']}'")

    # ── Check for duplicates ──
    existing = load_all_submissions()
    new_key = submission_key(user_data)
    for eid, esub in existing.items():
        esub_data = esub.get("data", esub)  # tolerate legacy flat format
        if submission_key(esub_data) == new_key:
            fail(f"重复的配置 — 相同的效果+商店+颜色+遗物已存在于 '{eid}'")

    ok("去重检查通过")

    # ── Auto-generate management fields ──
    submission_id = str(uuid_module.uuid4())
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    submission = {
        "id": submission_id,
        "author": issue_author,
        "created_at": now,
        "version": FILE_VERSION,
        "issue_number": int(os.environ.get("ISSUE_NUMBER", 0)),
        "data": user_data,
    }

    # ── Write file ──
    sp = Path(SUBMISSIONS_DIR)
    sp.mkdir(parents=True, exist_ok=True)
    filepath = sp / f"{submission_id}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(submission, f, ensure_ascii=False, indent=2)

    ok(f"已写入: {filepath}")


def process_delete():
    """Handle a delete submission Issue."""
    body = os.environ.get("ISSUE_BODY", "")
    issue_author = os.environ.get("ISSUE_AUTHOR", "")

    ok(f"处理删除请求 — Issue author: {issue_author}")

    # Extract submission_id from body
    match = re.search(r"submission_id:\s*`?([a-f0-9-]{36})`?", body)
    if not match:
        fail("无法从 Issue 中找到 submission_id")

    submission_id = match.group(1)
    ok(f"submission_id: {submission_id}")

    # Load the file
    filepath = Path(SUBMISSIONS_DIR) / f"{submission_id}.json"
    if not filepath.exists():
        fail(f"配置不存在: {submission_id}.json")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            submission = json.load(f)
    except json.JSONDecodeError as e:
        fail(f"无法读取配置: {e}")

    # Author verification — read from top-level (management field, cannot be forged)
    file_author = submission.get("author", "")
    if file_author.lower() != issue_author.lower():
        fail(f"无权删除 — 配置作者是 '{file_author}'，但 Issue 作者是 '{issue_author}'")

    ok("删除授权验证通过")

    # Delete the file
    filepath.unlink()
    ok(f"已删除: {filepath}")


def main():
    if len(sys.argv) < 2:
        fail("用法: python process_issue.py <share|delete>")

    action = sys.argv[1]
    if action == "share":
        process_share()
    elif action == "delete":
        process_delete()
    else:
        fail(f"未知操作: {action}")

    print("\n✅ 处理完成")


if __name__ == "__main__":
    main()
