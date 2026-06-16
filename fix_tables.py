#!/usr/bin/env python3
"""
Fix broken markdown pipe tables in GitBook export files.

Main issue: table rows split across multiple lines because cell content
contains line breaks (from bullet lists, paragraphs, images). Markdown pipe
tables require each row on a single line; GitBook breaks the table when rows
span lines.

Strategy:
- Walk all .md files
- For each file, identify table regions (lines that start with | or are
  continuation lines between | lines)
- If the region contains block-level elements (hint blocks, HTML tables,
  headings), skip it and flag for manual review
- Otherwise, merge broken rows into single lines using <br> tags
"""

import re
import sys
from pathlib import Path

GITBOOK_ROOT = Path(__file__).parent / "gitbook-export"

# Block-level elements that should NOT appear inside table regions we auto-fix
BLOCK_PATTERN = re.compile(
    r'{%\s*hint\b|{%\s*endhint\b|'
    r'<table\b|<tbody\b|<tr\b|<td\b|<th\b|</table>|</tbody>|</tr>|</td>|</th>|'
    r'<div\b|</div>|'
    r'<ul\b|</ul>|<li\b|</li>|'
    r'<h[1-6]\b|</h[1-6]>|'
    r'<p\b|</p>|'
    r'<br\b'
)


def is_table_line(line):
    return line.strip().startswith("|")


def is_separator(line):
    s = line.strip()
    if not s.startswith("|"):
        return False
    inner = s[1:-1] if s.endswith("|") else s[1:]
    parts = [p.strip() for p in inner.split("|")]
    return all(re.match(r'^[\-:]+$', p) for p in parts if p)


def find_table_regions(lines):
    """
    Find all table regions. A table region is a consecutive sequence of lines
    where each line is either a table line (starts with |) or a non-table line
    that is "between" table lines (i.e., it's a continuation of a broken row).
    """
    regions = []
    i = 0
    n = len(lines)

    while i < n:
        if not is_table_line(lines[i]):
            i += 1
            continue

        # Found start of a table region
        start = i
        j = i + 1

        while j < n:
            if is_table_line(lines[j]):
                j += 1
                continue

            # This line doesn't start with |. Check if it's a valid continuation
            # by looking ahead to see if we hit another table line before a
            # non-continuation (a line that isn't blank and doesn't end with |)
            k = j
            while k < n and not is_table_line(lines[k]):
                k += 1

            if k < n and is_table_line(lines[k]):
                # There's a table line ahead; include the gap lines in the region
                j = k + 1
            else:
                # No more table lines; stop here
                break

        # Only include if there are at least 2 table lines (header + something)
        pipe_count = sum(1 for idx in range(start, j) if is_table_line(lines[idx]))
        if pipe_count >= 2:
            regions.append((start, j))

        i = j

    return regions


def region_has_block_elements(lines, start, end):
    for idx in range(start, end):
        if BLOCK_PATTERN.search(lines[idx]):
            return True
    return False


def is_complete_row(line):
    s = line.strip()
    if not s.startswith("|"):
        return False
    if not s.endswith("|"):
        return False
    return s.count("|") >= 3


def fix_table_region(lines, start, end):
    result = []
    i = start

    while i < end:
        line = lines[i]
        s = line.strip()

        if not s.startswith("|"):
            result.append(line)
            i += 1
            continue

        if is_separator(line):
            result.append(line)
            i += 1
            continue

        if is_complete_row(line):
            result.append(line)
            i += 1
            continue

        # Broken row: merge with continuation lines
        row_parts = [line.rstrip("\n")]
        j = i + 1

        while j < end:
            next_line = lines[j]
            next_s = next_line.strip()

            if next_s.startswith("|"):
                break

            row_parts.append(next_line.rstrip("\n"))
            j += 1

        if len(row_parts) > 1:
            merged = merge_row_parts(row_parts)
            result.append(merged + "\n")
        else:
            result.append(line)

        i = j

    return result


def merge_row_parts(parts):
    merged = parts[0].rstrip()
    prev_was_blank = False

    for part in parts[1:]:
        part_stripped = part.strip()

        if part_stripped == "":
            merged += " <br><br> "
            prev_was_blank = True
        else:
            if prev_was_blank:
                merged += part_stripped
                prev_was_blank = False
            else:
                merged += " <br> " + part_stripped

    merged = re.sub(r'\s+<br>\s+', ' <br> ', merged)
    merged = re.sub(r'\s+<br><br>\s+', ' <br><br> ', merged)
    merged = re.sub(r'  +', ' ', merged)
    merged = merged.strip()

    return merged


def fix_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.splitlines(keepends=True)
    regions = find_table_regions(lines)

    if not regions:
        return False, None

    for start, end in regions:
        if region_has_block_elements(lines, start, end):
            return False, "contains block-level elements (hint blocks, HTML, etc.)"

    new_lines = []
    last_end = 0
    for start, end in regions:
        new_lines.extend(lines[last_end:start])
        new_lines.extend(fix_table_region(lines, start, end))
        last_end = end
    new_lines.extend(lines[last_end:])

    new_content = "".join(new_lines)

    if new_content != content:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
        return True, None
    return False, None


def main():
    changed_files = []
    skipped_files = []
    error_files = []

    for filepath in sorted(GITBOOK_ROOT.rglob("*.md")):
        try:
            changed, reason = fix_file(filepath)
            if changed:
                changed_files.append(str(filepath.relative_to(GITBOOK_ROOT)))
            elif reason:
                skipped_files.append((str(filepath.relative_to(GITBOOK_ROOT)), reason))
        except Exception as e:
            error_files.append((str(filepath.relative_to(GITBOOK_ROOT)), str(e)))
            print(f"Error processing {filepath}: {e}", file=sys.stderr)

    print(f"Fixed {len(changed_files)} files:")
    for f in changed_files:
        print(f"  - {f}")

    if skipped_files:
        print(f"\nSkipped {len(skipped_files)} files:")
        for f, reason in skipped_files:
            print(f"  - {f}: {reason}")

    if error_files:
        print(f"\nErrors in {len(error_files)} files:")
        for f, e in error_files:
            print(f"  - {f}: {e}")


if __name__ == "__main__":
    main()
