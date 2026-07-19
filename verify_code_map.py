#!/usr/bin/env python3
"""
verify_code_map.py — confirm every anchor in CODE_MAP.md still grep-matches the game file.

Usage:
    python3 verify_code_map.py <game>.html CODE_MAP.md

Exit code 0 = all anchors matched. Exit code 1 = one or more broken (and they're printed).

What it checks: the backtick-quoted anchor string in every `###`/`####` heading, and in every
`- **Anchor**: \`...\`` line (the nested entry format). Inline backticks inside prose (What/Does)
are ignored. An anchor is "good" if its literal text appears anywhere in the game file.

When an anchor breaks, it means the code moved/renamed under it. Fix: grep a shorter substring
of the anchor (or a unique token from its description) to relocate the construct, then update
that entry's anchor in CODE_MAP.md so it greps again.
"""
import re
import sys


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2

    game_path, map_path = sys.argv[1], sys.argv[2]
    try:
        src = open(game_path, encoding="utf-8", errors="replace").read()
    except OSError as e:
        print(f"cannot read game file {game_path!r}: {e}")
        return 2
    try:
        map_lines = open(map_path, encoding="utf-8", errors="replace").read().splitlines()
    except OSError as e:
        print(f"cannot read map file {map_path!r}: {e}")
        return 2

    tested = 0
    broken = []
    for ln in map_lines:
        candidates = []
        h = re.match(r"^#{3,4}\s+(.*)$", ln)
        a = re.match(r"^\s*-\s*\*\*Anchor\*\*:\s*`([^`]+)`", ln)
        if h:
            candidates += re.findall(r"`([^`]+)`", h.group(1))
        if a:
            candidates.append(a.group(1))
        for c in candidates:
            tested += 1
            if c not in src:
                broken.append(c)

    print(f"anchors tested: {tested}")
    print(f"broken:         {len(broken)}")
    if broken:
        print("\nThese anchors no longer match the game file (code moved under them):")
        for b in broken:
            print(f"  BROKEN: {b!r}")
        print(
            "\nFix each by grepping a shorter substring to relocate the construct, "
            "then update its anchor in the map."
        )
        return 1
    print("\nAll anchors match. The map is sound.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
