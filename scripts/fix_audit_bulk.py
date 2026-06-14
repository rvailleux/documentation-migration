#!/usr/bin/env python3
"""Wave 1 bulk fixes for the GitBook documentation audit.

Removes stale footers, fixes French leftovers and grammar errors,
renames asset files with spaces, and updates all references.
"""

import os
import re
import sys
from pathlib import Path

# Base path to gitbook-export/
GITBOOK_DIR = Path(__file__).parent.parent / "gitbook-export"


# ── 1. Footer patterns ──────────────────────────────────────────────────────
FOOTER_PATTERNS = [
    # Pattern A: with preceding copyright line
    re.compile(
        r"(?:\r?\n)? *© Apizee\. All rights reserved\.\r?\n *\[Send feedback\]\(mailto:support@clickhelp\.co\) on this topic to Apizee\.(?:\r?\n)?",
        re.MULTILINE,
    ),
    # Pattern B: just the mailto line (no copyright)
    re.compile(
        r"(?:\r?\n)? *\[Send feedback\]\(mailto:support@clickhelp\.co\) on this topic to Apizee\.(?:\r?\n)?",
        re.MULTILINE,
    ),
]


# ── 2. Simple text replacements ──────────────────────────────────────────────
# Each tuple: (old, new, description, case_sensitive)
TEXT_REPLACEMENTS = [
    # Grammar / French leftovers
    ("authentification", "authentication", "French spelling: authentification", False),
    ("join de video call", "join the video call", "French preposition: join de", False),
    ("The video call begin", "The video call begins", "Grammar: begin → begins", True),
    ("Datagramme", "Datagram", "French spelling: Datagramme", True),
    ("### Enable/Disable Micro\r\n", "### Enable/Disable Microphone\r\n", "Grammar: Micro → Microphone", True),
    ("### Enable/Disable Micro\n", "### Enable/Disable Microphone\n", "Grammar: Micro → Microphone", True),
    # Space-before-colon fixes (only when preceded by an English word, not URLs)
    # We handle this carefully via regex later
]


def remove_footers(content: str) -> str:
    """Strip the ClickHelp feedback footer from markdown content."""
    for pat in FOOTER_PATTERNS:
        content = pat.sub("\n", content)
    # Collapse any trailing blank lines to a single newline
    content = re.sub(r"\n{3,}$", "\n\n", content)
    return content


def fix_simple_replacements(content: str) -> tuple[str, list[str]]:
    """Apply simple find-and-replace rules."""
    changes = []
    for old, new, desc, case_sensitive in TEXT_REPLACEMENTS:
        if case_sensitive:
            count = content.count(old)
            content = content.replace(old, new)
        else:
            count = sum(
                1 for m in re.finditer(re.escape(old), content, re.IGNORECASE)
            )
            content = re.sub(re.escape(old), new, content, flags=re.IGNORECASE)
        if count:
            changes.append(f"  {desc}: {count} instance(s)")
    return content, changes


def fix_informations(content: str) -> tuple[str, int]:
    """Fix 'informations' → 'information'.

    We do a word-boundary replace, but keep 'Informations' when it is clearly
    part of a UI label that the user must literally see on-screen. In practice,
    the Apizee UI is English, so 'Information' is the correct label.
    """
    count = 0

    def repl(m):
        nonlocal count
        count += 1
        matched = m.group(0)
        if matched[0].isupper():
            return "Information"
        return "information"

    # Use word boundary but allow trailing 's' to be consumed
    content = re.sub(r"\binformations\b", repl, content, flags=re.IGNORECASE)
    return content, count


def fix_space_before_colon(content: str) -> tuple[str, int]:
    """Remove French-style space before colon in English prose.

    Only acts when the preceding character is a letter (not a URL or code).
    """
    count = 0

    def repl(m):
        nonlocal count
        count += 1
        return m.group(1) + ":"

    # Look for 'word :' where the colon is followed by a space or end of line
    content = re.sub(r"(\w) +:( |\n|$)", repl, content)
    return content, count


# ── 3. Asset file renaming ───────────────────────────────────────────────────

def get_asset_files_with_spaces(base: Path) -> list[tuple[Path, str, str]]:
    """Return list of (full_path, old_basename, new_basename) for assets with spaces."""
    results = []
    for d in base.rglob(".gitbook/assets"):
        if not d.is_dir():
            continue
        for f in d.iterdir():
            if f.is_file() and " " in f.name:
                new_name = f.name.replace(" ", "-")
                # Also clean up other problematic chars if any
                new_name = new_name.replace("(", "").replace(")", "")
                results.append((f, f.name, new_name))
    return results


def rename_assets_and_update_references(base: Path) -> tuple[list[str], list[str]]:
    """Rename asset files and update all .md references."""
    asset_map = get_asset_files_with_spaces(base)
    if not asset_map:
        return [], []

    renamed = []
    for old_path, old_name, new_name in asset_map:
        new_path = old_path.parent / new_name
        if new_path.exists():
            # Collision: skip
            continue
        os.rename(str(old_path), str(new_path))
        renamed.append(f"  {old_name} -> {new_name}")

    # Build a mapping from old basename to new basename
    name_map = {old_name: new_name for _, old_name, new_name in asset_map}

    # Update all .md files
    md_files = list(base.rglob("*.md"))
    updated_files = []
    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8")
        original = content
        for old_name, new_name in name_map.items():
            # Only replace inside markdown image/link syntax to be safe
            # Pattern: anything that references the old filename
            content = content.replace(old_name, new_name)
        if content != original:
            md_file.write_text(content, encoding="utf-8")
            updated_files.append(str(md_file.relative_to(base)))

    return renamed, updated_files


# ── 4. SUMMARY.md French headers ─────────────────────────────────────────────

def fix_summary_french(filepath: Path) -> bool:
    content = filepath.read_text(encoding="utf-8")
    original = content
    content = content.replace("## Pour les administrateurs", "## For administrators")
    content = content.replace("## Pour les agents", "## For agents")
    content = content.replace("## Pour les invités", "## For guests")
    if content != original:
        filepath.write_text(content, encoding="utf-8")
        return True
    return False


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    if not GITBOOK_DIR.is_dir():
        print(f"ERROR: Directory not found: {GITBOOK_DIR}")
        sys.exit(1)

    print(f"Working in: {GITBOOK_DIR}\n")

    all_md = list(GITBOOK_DIR.rglob("*.md"))
    print(f"Found {len(all_md)} markdown files.\n")

    # ── Footer removal + text fixes ──
    footer_count = 0
    total_changes = []
    for md_file in all_md:
        content = md_file.read_text(encoding="utf-8")
        original = content

        content = remove_footers(content)
        if content != original:
            footer_count += 1

        content, simple_changes = fix_simple_replacements(content)

        content, info_count = fix_informations(content)
        if info_count:
            simple_changes.append(f"  informations -> information: {info_count} instance(s)")

        content, colon_count = fix_space_before_colon(content)
        if colon_count:
            simple_changes.append(f"  French space-before-colon fix: {colon_count} instance(s)")

        if simple_changes:
            total_changes.append(
                f"{md_file.relative_to(GITBOOK_DIR)}:\n" + "\n".join(simple_changes)
            )

        if content != original:
            md_file.write_text(content, encoding="utf-8")

    if footer_count:
        print(f"Removed stale footers from {footer_count} file(s).\n")
    if total_changes:
        print("Text replacements applied:")
        for chunk in total_changes:
            print(chunk)
        print()

    # ── Asset renaming ──
    renamed, updated_files = rename_assets_and_update_references(GITBOOK_DIR)
    if renamed:
        print(f"Renamed {len(renamed)} asset file(s):")
        for r in renamed:
            print(r)
        print()
    if updated_files:
        print(f"Updated references in {len(updated_files)} markdown file(s).\n")

    # ── SUMMARY.md French headers ──
    summary_path = GITBOOK_DIR / "video-assistance-multi" / "SUMMARY.md"
    if summary_path.exists() and fix_summary_french(summary_path):
        print(f"Fixed French headers in {summary_path.relative_to(GITBOOK_DIR)}\n")

    print("Wave 1 bulk fixes complete.")


if __name__ == "__main__":
    main()
