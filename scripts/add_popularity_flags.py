"""
Add is_popular and is_uncommon flags to all markdown frontmatter.
Reads the lookup sets from instruments.instrument_data and updates .md files.
"""
import os
import re
import sys

# Add project root to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from instruments.instrument_data import get_instrument_flags

CONTENT_DIR = os.path.join(BASE_DIR, "content", "instruments")
FRONTMATTER_RE = re.compile(r"^(---\s*\n.*?\n---)", re.DOTALL)
POP_FIELD = "is_popular"
UNCOMMON_FIELD = "is_uncommon"


def parse_frontmatter(text):
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    data = {}
    for line in m.group(1).split("\n"):
        if ":" in line:
            key, _, val = line.partition(":")
            data[key.strip()] = val.strip()
    return data, m.group(1)


def update_md_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    fm_data, fm_raw = parse_frontmatter(content)

    # Check if already has the field
    if POP_FIELD in fm_data or UNCOMMON_FIELD in fm_data:
        return False, "already has flags"

    title = fm_data.get("title", "")
    original_name = fm_data.get("original_name", "")

    lookup_names = [title]
    if original_name and original_name != title:
        lookup_names.append(original_name)

    is_pop = False
    is_un = False
    for name in lookup_names:
        p, u = get_instrument_flags(name)
        if p:
            is_pop = True
        if u:
            is_un = True

    if not is_pop and not is_un:
        return False, "neither popular nor uncommon"

    # Insert flags after the first line of frontmatter (after "---\n")
    insertions = []
    if is_pop:
        insertions.append(f"{POP_FIELD}: true")
    if is_un:
        insertions.append(f"{UNCOMMON_FIELD}: true")

    insert_str = "\n".join(insertions) + "\n"
    new_fm = fm_raw.replace("---\n", "---\n" + insert_str, 1)
    new_content = content.replace(fm_raw, new_fm, 1)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)

    return True, f"popular={is_pop}, uncommon={is_un}"


def main():
    updated = 0
    skipped_already = 0
    skipped_no_match = 0

    for filename in sorted(os.listdir(CONTENT_DIR)):
        if not filename.endswith(".md"):
            continue
        filepath = os.path.join(CONTENT_DIR, filename)
        ok, msg = update_md_file(filepath)
        if ok:
            print(f"  [OK] {filename} -> {msg}")
            updated += 1
        elif "already" in msg:
            skipped_already += 1
        else:
            skipped_no_match += 1

    print(f"\nDone: {updated} updated, {skipped_already} already had flags, {skipped_no_match} not popular/uncommon")


if __name__ == "__main__":
    main()
