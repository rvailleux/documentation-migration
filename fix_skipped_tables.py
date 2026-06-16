#!/usr/bin/env python3
"""
Fix table files that were skipped because they contain hint blocks between
tables (but not inside table cells). The main script skips these because
the table region spans across the hint block.

Approach: for each skipped file, find tables that are NOT inside hint blocks
and fix only those.
"""

import re
import sys
from pathlib import Path

GITBOOK_ROOT = Path(__file__).parent / "gitbook-export"

# Only skip if the table region itself contains these; hint blocks BETWEEN
# tables are fine
BLOCK_INSIDE_CELL = re.compile(
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


def is_hint_line(line):
    s = line.strip()
    return s.startswith("{% hint") or s.startswith("{% endhint")


def is_complete_row(line):
    s = line.strip()
    if not s.startswith("|"):
        return False
    if not s.endswith("|"):
        return False
    return s.count("|") >= 3


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
            if is_hint_line(next_line):
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


def find_table_regions_skip_hints(lines):
    """
    Find table regions, but don't span across hint blocks.
    A region ends when we encounter a hint block line.
    """
    regions = []
    i = 0
    n = len(lines)

    while i < n:
        if not is_table_line(lines[i]):
            i += 1
            continue

        start = i
        j = i + 1

        while j < n:
            if is_hint_line(lines[j]):
                break

            if is_table_line(lines[j]):
                j += 1
                continue

            # Non-table line; look ahead to see if another table line exists
            # before the next hint block
            k = j
            while k < n and not is_hint_line(lines[k]) and not is_table_line(lines[k]):
                k += 1

            if k < n and is_table_line(lines[k]):
                j = k + 1
            else:
                break

        pipe_count = sum(1 for idx in range(start, j) if is_table_line(lines[idx]))
        if pipe_count >= 2:
            regions.append((start, j))

        i = j

    return regions


def fix_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.splitlines(keepends=True)
    regions = find_table_regions_skip_hints(lines)

    if not regions:
        return False, "no table regions found"

    # Check if any region has block-level elements inside cells
    for start, end in regions:
        for idx in range(start, end):
            if BLOCK_INSIDE_CELL.search(lines[idx]):
                return False, "contains block-level elements inside cells"

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
    return False, "no changes needed"


SKIPPED_FILES = [
    "_unassigned/apizee-for-salesforce-publication-admin/MD/configure-apizee-for-agentforce.md",
    "_unassigned/apizee-for-salesforce-publication-admin/MD/configure-interaction-template.md",
    "_unassigned/apizee-for-salesforce-publication-admin/MD/configure-your-salesforce-environment.md",
    "_unassigned/apizee-for-salesforce-publication-admin/MD/uninstall-apizee-for-agentforce.md",
    "_unassigned/customer-engagement-user-en/MD/about-apizee-customer-engagement.md",
    "_unassigned/customer-engagement-user-en/MD/check-the-offline-messages.md",
    "_unassigned/customer-engagement-user-en/MD/follow-the-conversations-history.md",
    "meetings/admins/configuration-on-the-apizee-portal/configure-the-conference/configure-the-end-of-session.md",
    "meetings/admins/configuration-on-the-apizee-portal/configure-the-conference/customize-the-notification-templates.md",
    "meetings/admins/configuration-on-the-apizee-portal/create-a-new-service.md",
    "meetings/admins/start-a-video-conference/join-and-leave-the-conference-as-a-guest.md",
    "meetings/guests/start-a-video-conference/join-and-leave-the-conference-as-a-guest.md",
    "meetings/users/start-a-video-conference/join-and-leave-the-conference-as-a-guest.md",
    "telehealth/admins/configuration-on-the-apizee-portal/configure-the-teleconsultation/configure-the-end-of-teleconsultation.md",
    "telehealth/admins/configuration-on-the-apizee-portal/configure-the-teleconsultation/customize-the-notification-templates.md",
    "telehealth/admins/configuration-on-the-apizee-portal/create-a-new-service.md",
    "video-assistance/admins/configuration-on-the-apizee-portal/configure-the-video-assistance/activate-the-ticket-notifications.md",
    "video-assistance/admins/configuration-on-the-apizee-portal/configure-the-video-assistance/customize-the-notification-templates.md",
    "video-assistance/admins/configuration-on-the-apizee-portal/configure-the-video-assistance/customize-the-tickets.md",
    "video-assistance/admins/configuration-on-the-apizee-portal/create-a-new-service.md",
    "video-assistance/admins/follow-up-the-assistances-on-the-portal/follow-a-ticket.md",
    "video-assistance/admins/follow-up-the-assistances-on-the-portal/video-assistance-ticket-status.md",
    "video-assistance/admins/follow-up-the-assistances-on-the-portal/what-is-timeline-for.md",
    "video-assistance/agents/follow-up-the-assistances-on-the-portal/follow-a-ticket.md",
    "video-assistance/agents/follow-up-the-assistances-on-the-portal/video-assistance-ticket-status.md",
    "video-assistance/agents/follow-up-the-assistances-on-the-portal/what-is-timeline-for.md",
    "video-assistance/help-desk/follow-up-the-assistances-on-the-portal/follow-a-ticket.md",
    "video-assistance-multi/admins/configuration-on-the-apizee-portal/configure-video-assistance/activate-the-ticket-notifications.md",
    "video-assistance-multi/admins/configuration-on-the-apizee-portal/configure-video-assistance/customize-the-notification-templates.md",
    "video-assistance-multi/admins/configuration-on-the-apizee-portal/create-a-new-service.md",
    "video-assistance-multi/admins/follow-up-the-assistances-on-the-portal/follow-a-ticket.md",
    "video-assistance-multi/admins/follow-up-the-assistances-on-the-portal/video-assistance-ticket-status.md",
    "video-assistance-multi/admins/follow-up-the-assistances-on-the-portal/what-is-timeline-for.md",
    "video-assistance-multi/admins/join-and-leave-assistance-as-guest.md",
    "video-assistance-multi/agents/follow-up-the-assistances-on-the-portal/follow-a-ticket.md",
    "video-assistance-multi/agents/follow-up-the-assistances-on-the-portal/video-assistance-ticket-status.md",
    "video-assistance-multi/agents/follow-up-the-assistances-on-the-portal/what-is-timeline-for.md",
    "video-assistance-multi/agents/join-and-leave-assistance-as-guest.md",
    "video-assistance-multi/guests/join-and-leave-assistance-as-guest.md",
]


def main():
    changed_files = []
    still_skipped = []
    error_files = []

    for rel_path in SKIPPED_FILES:
        filepath = GITBOOK_ROOT / rel_path
        if not filepath.exists():
            still_skipped.append((rel_path, "file not found"))
            continue

        try:
            changed, reason = fix_file(filepath)
            if changed:
                changed_files.append(rel_path)
            else:
                still_skipped.append((rel_path, reason))
        except Exception as e:
            error_files.append((rel_path, str(e)))
            print(f"Error processing {filepath}: {e}", file=sys.stderr)

    print(f"Fixed {len(changed_files)} additional files:")
    for f in changed_files:
        print(f"  - {f}")

    if still_skipped:
        print(f"\nStill skipped {len(still_skipped)} files:")
        for f, reason in still_skipped:
            print(f"  - {f}: {reason}")

    if error_files:
        print(f"\nErrors in {len(error_files)} files:")
        for f, e in error_files:
            print(f"  - {f}: {e}")


if __name__ == "__main__":
    main()
