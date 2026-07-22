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
ALLOWED_FIELDS = {"title", "description", "relics"}

# Schema for a single relic inside the relics array
RELIC_SCHEMA = {
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
    match = re.search(r"```\s*\n(\{.*?\})\s*\n\s*```", body, re.DOTALL)
    if match:
        return match.group(1)
    return None


def validate_relic(r: dict, i: int) -> None:
    """Validate a single relic entry."""
    for field, ftype in RELIC_SCHEMA.items():
        if field not in r:
            fail(f"relics[{i}] 缺少字段 '{field}'")
        if not isinstance(r[field], ftype):
            fail(f"relics[{i}].{field} 应为 {ftype.__name__}")
    if r["shop"] not in VALID_SHOPS and r["shop"] != "unknown":
        fail(f"relics[{i}] 无效的 shop: '{r['shop']}'")
    if r["color"] not in {0, 1, 2, 3} and r["color"] != -1:
        fail(f"relics[{i}] 无效的 color: {r['color']}")
    for j, e in enumerate(r.get("effects", [])):
        if not isinstance(e, dict) or "eff_id" not in e:
            fail(f"relics[{i}].effects[{j}] 缺少 eff_id")


def validate_user_data(data: dict) -> None:
    """Validate user-submitted folder data."""
    if not data.get("title", "").strip():
        fail("title 不能为空")
    if len(data["title"]) > 100:
        fail("title 过长（最多100字符）")
    if len(data.get("description", "")) > 500:
        fail("description 过长（最多500字符）")
    relics = data.get("relics")
    if not isinstance(relics, list) or len(relics) == 0:
        fail("relics 必须是非空数组")
    for i, r in enumerate(relics):
        if not isinstance(r, dict):
            fail(f"relics[{i}] 必须是对象")
        validate_relic(r, i)


def process_share():
    body = os.environ.get("ISSUE_BODY", "")
    issue_author = os.environ.get("ISSUE_AUTHOR", "")

    ok(f"处理分享请求 — Issue author: {issue_author}")

    json_str = extract_json_from_body(body)
    if not json_str:
        fail("无法从 Issue 正文中找到 JSON 数据")

    try:
        raw = json.loads(json_str)
    except json.JSONDecodeError as e:
        fail(f"JSON 解析失败: {e}")

    if not isinstance(raw, dict):
        fail("JSON 必须是对象")

    # Strip unknown / forged fields
    user_data = {}
    for field in ALLOWED_FIELDS:
        if field in raw:
            user_data[field] = raw[field]

    validate_user_data(user_data)
    ok(f"格式验证通过: '{user_data['title']}' ({len(user_data['relics'])} 个遗物)")

    # Auto-generate management fields
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

    sp = Path(SUBMISSIONS_DIR)
    sp.mkdir(parents=True, exist_ok=True)
    filepath = sp / f"{submission_id}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(submission, f, ensure_ascii=False, indent=2)

    ok(f"已写入: {filepath}")


def process_delete():
    body = os.environ.get("ISSUE_BODY", "")
    issue_author = os.environ.get("ISSUE_AUTHOR", "")

    ok(f"处理删除请求 — Issue author: {issue_author}")

    match = re.search(r"submission_id:\s*`?([a-f0-9-]{36})`?", body)
    if not match:
        fail("无法从 Issue 中找到 submission_id")

    submission_id = match.group(1)
    filepath = Path(SUBMISSIONS_DIR) / f"{submission_id}.json"
    if not filepath.exists():
        fail(f"配置不存在: {submission_id}.json")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            submission = json.load(f)
    except json.JSONDecodeError as e:
        fail(f"无法读取配置: {e}")

    file_author = submission.get("author", "")
    if file_author.lower() != issue_author.lower():
        fail(f"无权删除 — 配置作者是 '{file_author}'，但 Issue 作者是 '{issue_author}'")

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
