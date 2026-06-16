#!/usr/bin/env python3
"""validate-gitbook.py — validate a GitBook Markdown documentation tree.

Checks run per .md file:
  - Unclosed GitBook tag blocks (hint, content-ref, tabs, etc.)
  - Broken relative image references (with cross-space awareness)
  - Broken content-ref URLs
  - Broken include paths
  - Invalid YAML frontmatter
  - SUMMARY.md link integrity

Exit codes:
  0 = all clean (or only cross-space warnings when --allow-cross-space)
  1 = hard errors found
  2 = bad arguments / root not found

Usage:
  python3 scripts/validate-gitbook.py [root_dir]
  python3 scripts/validate-gitbook.py --fail-on-warnings gitbook-export/
"""
import re
import sys
import argparse
from pathlib import Path
from typing import List, Set, Optional


def build_image_index(root: Path) -> dict[str, Path]:
    """Index every image in the project by filename."""
    index: dict[str, Path] = {}
    for img_path in root.rglob("*"):
        if img_path.suffix.lower() in (
            ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico",
        ):
            index[img_path.name] = img_path
    return index


def find_space_root(path: Path, root: Path) -> Optional[Path]:
    """Walk up from path until we find a directory containing .gitbook/."""
    for parent in [path.parent, *path.parents]:
        if parent == root or str(parent).startswith(str(root)):
            if (parent / ".gitbook").is_dir():
                return parent
    if (root / ".gitbook").is_dir():
        return root
    return None


def validate_frontmatter(text: str, path: Path) -> List[str]:
    """Check YAML frontmatter if present."""
    errors: List[str] = []
    if text.startswith("---"):
        try:
            import yaml  # type: ignore

            parts = text.split("---", 2)
            if len(parts) >= 3:
                yaml.safe_load(parts[1])
        except ImportError:
            pass
        except Exception as e:
            errors.append(f"{path}: invalid YAML frontmatter — {e}")
    return errors


def validate_gitbook_tags(text: str, path: Path) -> List[str]:
    """Check that GitBook tag blocks are balanced."""
    errors: List[str] = []
    TAG_PAIRS = [
        ("content-ref", r"{%\s*content-ref", r"{%\s*endcontent-ref\s*%}"),
        ("hint", r"{%\s*hint\s+style=", r"{%\s*endhint\s*%}"),
        ("tabs", r"{%\s*tabs", r"{%\s*endtabs\s*%}"),
        ("tab", r"{%\s*tab\s+title=", r"{%\s*endtab\s*%}"),
    ]
    for name, open_pat, close_pat in TAG_PAIRS:
        open_count = len(re.findall(open_pat, text, re.IGNORECASE))
        close_count = len(re.findall(close_pat, text, re.IGNORECASE))
        if open_count != close_count:
            errors.append(
                f"{path}: unclosed {name} block ({open_count} open, {close_count} close)"
            )
    return errors


def validate_images(
    text: str,
    path: Path,
    root: Path,
    image_index: dict[str, Path],
    allow_cross_space: bool = False,
) -> tuple[List[str], List[str]]:
    """Check all ![]() image references. Returns (errors, warnings)."""
    errors: List[str] = []
    warnings: List[str] = []
    for match in re.finditer(r"!\[([^\]]*)\]\(([^)]+)\)", text):
        raw = match.group(2).strip()
        if raw.startswith(("http://", "https://", "//", "data:")):
            continue
        img_target = path.parent / raw
        if img_target.exists():
            continue
        if (root / raw).exists():
            continue
        space_root = find_space_root(path, root)
        if space_root and (space_root / raw).exists():
            continue

        # Cross-space check: does the image exist in *any* space?
        img_name = Path(raw).name
        if img_name in image_index:
            msg = (
                f"{path}: cross-space image '{raw}' "
                f"(found in {image_index[img_name].parent})"
            )
            if allow_cross_space:
                warnings.append(msg)
            else:
                errors.append(msg)
        else:
            errors.append(f"{path}: broken image reference '{raw}'")

    return errors, warnings


def validate_content_refs(text: str, path: Path, root: Path) -> List[str]:
    """Check that content-ref URLs point to real .md files."""
    errors: List[str] = []
    for match in re.finditer(r"{%\s*content-ref\s+url=\"([^\"]+)\"", text):
        raw = match.group(1).strip()
        if raw.startswith(("http://", "https://", "//")):
            continue
        target = path.parent / raw
        if target.exists():
            continue
        space_root = find_space_root(path, root)
        if space_root and (space_root / raw).exists():
            continue
        errors.append(f"{path}: broken content-ref '{raw}'")
    return errors


def validate_includes(text: str, path: Path, root: Path) -> List[str]:
    """Check that {% include "path" %} targets exist."""
    errors: List[str] = []
    for match in re.finditer(r"{%\s*include\s+\"([^\"]+)\"", text):
        raw = match.group(1).strip()
        target = path.parent / raw
        if target.exists():
            continue
        space_root = find_space_root(path, root)
        if space_root and (space_root / raw).exists():
            continue
        if (root / raw).exists():
            continue
        errors.append(f"{path}: broken include '{raw}'")
    return errors


def validate_summary(path: Path, root: Path) -> List[str]:
    """Check that every * [Title](path) in SUMMARY.md points to a real file."""
    errors: List[str] = []
    text = path.read_text()
    for line in text.splitlines():
        match = re.search(r"\*\s*\[[^\]]+\]\(([^)]+)\)", line)
        if match:
            raw = match.group(1).strip()
            target = path.parent / raw
            if not target.exists():
                errors.append(f"{path}: broken SUMMARY link '{raw}'")
    return errors


def validate_file(
    path: Path,
    root: Path,
    image_index: dict[str, Path],
    allow_cross_space: bool = False,
) -> tuple[List[str], List[str]]:
    """Run all per-file checks. Returns (errors, warnings)."""
    errors: List[str] = []
    warnings: List[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="latin-1")

    errors.extend(validate_frontmatter(text, path))
    errors.extend(validate_gitbook_tags(text, path))

    img_errs, img_warns = validate_images(text, path, root, image_index, allow_cross_space)
    errors.extend(img_errs)
    warnings.extend(img_warns)

    errors.extend(validate_content_refs(text, path, root))
    errors.extend(validate_includes(text, path, root))
    return errors, warnings


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Validate GitBook Markdown docs.")
    parser.add_argument(
        "root",
        nargs="?",
        default="gitbook-export",
        help="Root directory to scan (default: gitbook-export)",
    )
    parser.add_argument(
        "--allow-cross-space",
        action="store_true",
        help="Treat cross-space image references as warnings instead of errors",
    )
    parser.add_argument(
        "--fail-on-warnings",
        action="store_true",
        help="Exit non-zero even if only warnings exist",
    )
    parser.add_argument(
        "--report-json",
        action="store_true",
        help="Output a JSON summary (last line) for CI parsing",
    )
    args = parser.parse_args(argv[1:])

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"ERROR: root directory not found: {root}", file=sys.stderr)
        return 2

    image_index = build_image_index(root)
    all_errors: List[str] = []
    all_warnings: List[str] = []
    md_files = list(root.rglob("*.md"))

    for path in md_files:
        errs, warns = validate_file(path, root, image_index, args.allow_cross_space)
        all_errors.extend(errs)
        all_warnings.extend(warns)

    for summary in root.rglob("SUMMARY.md"):
        all_errors.extend(validate_summary(summary, root))

    # Report
    print(f"Scanned {len(md_files)} .md files in {root}")
    print(f"  Images indexed: {len(image_index)}")
    if all_warnings:
        print(f"  Warnings: {len(all_warnings)}")
    if all_errors:
        print(f"  ❌ Hard errors: {len(all_errors)}")
        for err in all_errors:
            print(f"    • {err}")
    else:
        print("  ✅ No hard errors.")

    if args.report_json:
        import json
        summary = {
            "scanned": len(md_files),
            "images_indexed": len(image_index),
            "errors": len(all_errors),
            "warnings": len(all_warnings),
            "clean": len(all_errors) == 0 and (len(all_warnings) == 0 or not args.fail_on_warnings),
        }
        print(f"\nJSON_REPORT:{json.dumps(summary)}")

    if all_errors:
        return 1
    if all_warnings and args.fail_on_warnings:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
