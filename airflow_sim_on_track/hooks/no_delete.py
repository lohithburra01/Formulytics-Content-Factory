"""Claude Code PreToolUse hook (user rule: never delete anything): "never delete anything" is enforced, not remembered.

Reads the hook JSON on stdin; if a Bash/PowerShell command deletes files, exits 2 with the reason
(Claude Code blocks the call and shows the reason to the model). Move/rename (mv, Move-Item, os.replace) is fine.
"""
import json
import re
import sys

PATTERNS = [
    r"(^|[\s;&|(`])(rm|rmdir|unlink|shred|del|erase|rd)(\s|$)",
    r"Remove-Item|Clear-Content|\bri\s",
    r"\bgit\s+(rm|clean)\b",
    r"\bfind\b.*\s-delete\b",
    r"shutil\.rmtree|os\.remove\(|os\.unlink\(|os\.rmdir\(|\.unlink\(\)|\.rmdir\(\)",
]


def is_delete(cmd: str) -> bool:
    return any(re.search(p, cmd, re.IGNORECASE if "Remove" in p else 0) for p in PATTERNS)


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:  # noqa: BLE001
        return 0
    cmd = (data.get("tool_input") or {}).get("command") or ""
    if is_delete(cmd):
        print("Blocked by the no-delete guard: never delete anything in this repo - move or rename instead "
              "(e.g. mv x _retired/x, or rename to *_rejected).", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
