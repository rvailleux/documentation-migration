#!/usr/bin/env python3
"""
ClickHelp → GitBook Migration Script
Idempotent: rm -rf gitbook-export && python scripts/convert.py

Usage:
    python scripts/convert.py [--space SPACE] [--qa-only]
"""

import os
import re
import sys
import yaml
import shutil
import hashlib
import unicodedata
import csv
import json
import argparse
from pathlib import Path
from collections import defaultdict
from urllib.parse import unquote
from html import unescape as html_unescape

# ============================================================
#  PATHS
# ============================================================
SOURCE_BASE = Path("/sessions/eager-charming-newton/mnt/migration doc")
OUTPUT_BASE  = SOURCE_BASE / "gitbook-export"
SCRIPTS_DIR  = SOURCE_BASE / "scripts"

# ============================================================
#  SPACE / ARCHIVE MAPPING
# ============================================================
# Each group defines one "role section" within a space.
# 'prefix' is the sub-folder; empty string means root of space.
SPACES = {
    "faq": {
        "groups": [
            {"archive": "faq", "title": None, "prefix": ""},
        ]
    },
    "video-assistance": {
        "groups": [
            {"archive": "video-assistance-user-en",  "title": "For agents",         "prefix": "for-agents"},
            {"archive": "video-assistance-guest-en",  "title": "For guests",         "prefix": "for-guests"},
            {"archive": "video-assistance-admin-en",  "title": "For administrators", "prefix": "for-administrators"},
        ]
    },
    "video-assistance-fr": {
        "groups": [
            {"archive": "assistance-multi-participants-user",  "title": "Pour les agents",           "prefix": "pour-les-agents"},
            {"archive": "assistance-multi-participants-guest", "title": "Pour les invités",          "prefix": "pour-les-invites"},
            {"archive": "assistance-multi-participants-admin", "title": "Pour les administrateurs", "prefix": "pour-les-administrateurs"},
        ]
    },
    "embed": {
        "groups": [
            {"archive": "apizee-embed-for-agents",       "title": "For agents",       "prefix": "for-agents"},
            {"archive": "apizee-embed-for-guests",       "title": "For guests",       "prefix": "for-guests"},
            {"archive": "apizee-embed-for-it-operators", "title": "For IT operators", "prefix": "for-it-operators"},
        ]
    },
    "meetings": {
        "groups": [
            {"archive": "apizee-meeting-user-en",  "title": "For users",          "prefix": "for-users"},
            {"archive": "apizee-meeting-guest-en", "title": "For guests",         "prefix": "for-guests"},
            {"archive": "apizee-meeting-admin-en", "title": "For administrators", "prefix": "for-administrators"},
        ]
    },
    "customer-engagement": {
        "groups": [
            {"archive": "customer-engagement-admin-en", "title": "For administrators", "prefix": "for-administrators"}
        ]
    },
    "telehealth": {
        "groups": [
            {"archive": "health-user",  "title": "For practitioners", "prefix": "for-practitioners"},
            {"archive": "health-guest", "title": "For patients",      "prefix": "for-patients"},
            {"archive": "health-admin", "title": "For administrators","prefix": "for-administrators"},
        ]
    },
    "integrations": {
        "groups": [
            {"archive": "apizee-for-salesforce",             "title": "Salesforce",  "prefix": "salesforce"},
            {"archive": "apizee-for-servicenow-publication", "title": "ServiceNow",  "prefix": "servicenow"},
            {"archive": "apizee-for-genesys-admin",          "title": "Genesys",     "prefix": "genesys"},
        ]
    },
    "legal": {
        "groups": [
            {"archive": "legal-information", "title": None, "prefix": ""}
        ]
    },
    "contextual-help": {
        "hidden": True,
        "groups": [
            {"archive": "agents-tab-set-the-call-distribution-mode",         "title": None, "prefix": ""},
            {"archive": "ticket-advanced-option-scan-the-guest-video-tooltip","title": None, "prefix": ""},
        ]
    },
    "diag-help-desk": {
        "groups": [
            {"archive": "diag-help-desk-user", "title": None, "prefix": ""}
        ]
    },
}

# Archives NOT mapped to any space (reuse project – assets only)
REUSE_ARCHIVE = "_appvisio-reuse-publication"

# Missing archives (never exported) – for the report
MISSING_ARCHIVES = [
    "apizee-embed-for-admins",
    "apizee-for-salesforce-publication-admin",
    "customer-engagement-user-en",
    "agents-tab-prioritize-agents-availability",
    "apizee-meeting-user-fr",
    "apizee-meeting-guest-fr",
    "apizee-meeting-admin-fr",
]

# ============================================================
#  CALLOUT ICONS → GitBook hint style
# ============================================================
CALLOUT_ICONS = {
    "info.png":    "info",
    "warning.png": "warning",
    "alert.png":   "danger",
    "danger.png":  "danger",
    "tip.png":     "success",
    "ok.png":      "success",       # result/confirmation indicator
    "prerequis.png": "info",        # prerequisite block
}

# ============================================================
#  GLOBAL STATE
# ============================================================
# slug → (space, rel_path)  for link rewriting
GLOBAL_SLUG_MAP: dict[str, tuple[str, str]] = {}
# archive → {md_filename_stem → target_rel_path_in_space}
ARCHIVE_SLUG_MAP: dict[str, dict[str, str]] = defaultdict(dict)
# (source_path_str) → target_asset_path_rel_to_gitbook_assets
ASSET_HASH_MAP: dict[str, str] = {}   # hash → filename in .gitbook/assets/
# Redirects: original_url → new_gitbook_path
REDIRECTS: list[tuple[str, str]] = []
# QA issues
QA_ISSUES: list[dict] = []


# ============================================================
#  HELPERS
# ============================================================

def slugify(text: str) -> str:
    """Convert a title to a slug (lowercase, hyphenated)."""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text


def remove_bom(text: str) -> str:
    return text.lstrip("﻿")


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def load_toc(archive_dir: Path) -> list:
    """Load toc.yaml, returning list of entries."""
    toc_path = archive_dir / "toc.yaml"
    if not toc_path.exists():
        return []
    raw = toc_path.read_text(encoding="utf-8-sig")  # strips BOM
    return yaml.safe_load(raw) or []


def iter_toc_entries(entries: list, parent_path: str = ""):
    """Yield (entry, parent_path) for all entries recursively."""
    for entry in entries:
        yield entry, parent_path
        for child in entry.get("children", []):
            yield child, parent_path  # will recurse


def flatten_toc(entries: list) -> list[dict]:
    """Return flat list of all entries with computed slug_path."""
    result = []
    def _walk(items, parent_slug_path):
        for item in items:
            slug = None
            if "file" in item:
                slug = Path(item["file"]).stem
            else:
                slug = slugify(item.get("title", "untitled"))
            path = f"{parent_slug_path}/{slug}" if parent_slug_path else slug
            result.append({**item, "_slug": slug, "_path": path})
            if "children" in item:
                _walk(item["children"], path)
    _walk(entries, "")
    return result


# ============================================================
#  PHASE 1 – BUILD GLOBAL SLUG MAP
# ============================================================

def build_global_slug_map():
    """
    Walk every archive in every space and map
    md-stem → (space_name, group_prefix, target_rel_path)
    so we can rewrite cross-topic links later.
    """
    for space_name, space_cfg in SPACES.items():
        for group in space_cfg["groups"]:
            archive_name = group["archive"]
            prefix = group["prefix"]
            archive_dir = SOURCE_BASE / f"{archive_name}-exported"
            if not archive_dir.exists():
                continue
            toc = load_toc(archive_dir)
            flat = flatten_toc(toc)

            # Also pick up MD files not in TOC (orphans)
            md_dir = archive_dir / "MD"
            toc_files = {Path(e["file"]).stem for e in flat if "file" in e}
            if md_dir.exists():
                for md_file in md_dir.glob("*.md"):
                    if md_file.stem not in toc_files:
                        flat.append({"_slug": md_file.stem, "_path": md_file.stem,
                                     "title": md_file.stem, "file": f"MD/{md_file.name}",
                                     "_orphan": True})

            for entry in flat:
                slug = entry["_slug"]
                # Target path within space
                if prefix:
                    target = f"{prefix}/{entry['_path']}"
                else:
                    target = entry["_path"]

                # Has children → becomes a directory README
                has_children = bool(entry.get("children"))
                if has_children and "file" in entry:
                    target_rel = f"{target}/README.md"
                elif has_children:
                    target_rel = f"{target}/README.md"
                else:
                    target_rel = f"{target}.md"

                ARCHIVE_SLUG_MAP[archive_name][slug] = target_rel
                # Global map: slug → (space, target_rel)
                # (later archives overwrite if same slug – OK, most specific wins)
                GLOBAL_SLUG_MAP[slug] = (space_name, target_rel)

    print(f"[slug-map] {len(GLOBAL_SLUG_MAP)} unique slugs across all archives")


# ============================================================
#  PHASE 2 – ASSET HANDLING
# ============================================================

def copy_asset(src_path: Path, space_assets_dir: Path) -> str:
    """
    Copy asset to .gitbook/assets/, deduplicated by hash.
    Returns the filename relative to assets dir.
    """
    if not src_path.exists():
        return src_path.name  # Will be flagged in QA

    h = file_hash(src_path)
    if h in ASSET_HASH_MAP:
        return ASSET_HASH_MAP[h]

    # Keep original name; if collision, check if same content first
    dest_name = src_path.name
    dest_path = space_assets_dir / dest_name
    if dest_path.exists():
        if file_hash(dest_path) == h:
            # Same content already on disk (e.g. from a previous run) — just register
            ASSET_HASH_MAP[h] = dest_name
            return dest_name
        # Genuine name collision with different content → add hash suffix
        ext = src_path.suffix
        dest_name = f"{src_path.stem}-{h[:8]}{ext}"
        dest_path = space_assets_dir / dest_name

    space_assets_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_path, dest_path)
    ASSET_HASH_MAP[h] = dest_name
    return dest_name


def resolve_asset_path(img_ref: str, md_file: Path, archive_dir: Path,
                       space_assets_dir: Path) -> str:
    """
    Given an image path like ../Storage/pub/image.png from a .md file,
    copy the asset and return the new path relative to the output .md file.
    """
    # Strip surrounding ![...]() — we only receive the src part
    # Resolve relative to the MD/ directory
    md_dir = md_file.parent
    abs_path = (md_dir / img_ref).resolve()

    if not abs_path.exists():
        # Maybe it's a URL
        if img_ref.startswith("http"):
            return img_ref
        QA_ISSUES.append({"type": "missing_asset", "file": str(md_file), "ref": img_ref})
        return img_ref

    dest_name = copy_asset(abs_path, space_assets_dir)
    # Path from output md file to assets: since md is inside space dir,
    # assets are at <space>/.gitbook/assets/<name>
    # We'll compute relative path at write time; for now return the dest name
    return dest_name


# ============================================================
#  PHASE 3 – CONTENT CONVERSION
# ============================================================

def convert_callout_table(content: str) -> str:
    """
    Convert 2-column ClickHelp callout tables to GitBook hints.
    Pattern (single-row table):
        | ![](path/to/info.png) | text |
        | --- | --- |
    or
        | --- | --- |
        | ![](path/to/info.png) | text |
    """
    lines = content.split("\n")
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Check for a 2-cell table row where cell 0 is a callout image
        m = re.match(
            r"^\|\s*!\[[^\]]*\]\(([^)]+)\)\s*\|\s*(.*?)\s*\|?\s*$",
            line
        )
        if m:
            img_src = m.group(1)
            icon_name = Path(img_src).name
            style = CALLOUT_ICONS.get(icon_name)
            # Check if next line is a separator
            next_is_sep = (i + 1 < len(lines) and
                           re.match(r"^\|\s*[-:]+\s*\|\s*[-:]+\s*\|", lines[i + 1]))
            # Check if prev line was a separator (we already consumed it)
            # → if we already processed separator, this data row follows

            if style is not None:
                cell_text = m.group(2)
                # Convert <br> to newline in hint body
                cell_text = re.sub(r"<br\s*/?>", "\n", cell_text)
                hint_body = cell_text.strip()
                out.append(f'{{% hint style="{style}" %}}')
                out.append(hint_body)
                out.append("{% endhint %}")
                if next_is_sep:
                    i += 2  # skip separator too
                else:
                    i += 1
                continue
        # Separator-first pattern: | --- | --- | then callout row
        if re.match(r"^\|\s*[-:]+\s*\|\s*[-:]+\s*\|", line):
            # Look ahead for a callout row
            if i + 1 < len(lines):
                m2 = re.match(
                    r"^\|\s*!\[[^\]]*\]\(([^)]+)\)\s*\|\s*(.*?)\s*\|?\s*$",
                    lines[i + 1]
                )
                if m2:
                    icon_name = Path(m2.group(1)).name
                    style = CALLOUT_ICONS.get(icon_name)
                    if style is not None:
                        cell_text = m2.group(2)
                        cell_text = re.sub(r"<br\s*/?>", "\n", cell_text)
                        out.append(f'{{% hint style="{style}" %}}')
                        out.append(cell_text.strip())
                        out.append("{% endhint %}")
                        i += 2
                        continue
        out.append(line)
        i += 1
    return "\n".join(out)


def convert_html(content: str) -> str:
    """
    Clean up residual HTML in Markdown content:
    - <br> outside tables → newline
    - Strip inline styles
    - Convert <b>/<i> to Markdown
    - Remove <span> wrappers
    """
    # <br> in table cells (keep as-is) vs outside
    # We do a simple approach: replace <br> everywhere, tables already use \n fine
    content = re.sub(r"<br\s*/?>", "\n", content)

    # Strip style= and loading= attributes ONLY inside HTML tags (not in {%hint%} blocks)
    def strip_html_attrs(m):
        tag = m.group(0)
        tag = re.sub(r'\s+style="[^"]*"', "", tag)
        tag = re.sub(r"\s+style='[^']*'", "", tag)
        tag = re.sub(r'\s+loading="[^"]*"', "", tag)
        return tag
    content = re.sub(r"<[a-zA-Z][^>]*>", strip_html_attrs, content)

    # Convert <b>...</b> and <strong>...</strong>
    content = re.sub(r"<(?:b|strong)>(.*?)</(?:b|strong)>", r"**\1**", content,
                     flags=re.DOTALL)

    # Convert <i>...</i> and <em>...</em>
    content = re.sub(r"<(?:i|em)>(.*?)</(?:i|em)>", r"*\1*", content,
                     flags=re.DOTALL)

    # Unwrap <span>
    content = re.sub(r"<span[^>]*>(.*?)</span>", r"\1", content, flags=re.DOTALL)

    # Remove <ol>/<ul> wrappers but keep list items
    content = re.sub(r"<ul[^>]*>", "", content)
    content = re.sub(r"</ul>", "", content)
    content = re.sub(r"<ol[^>]*>", "", content)
    content = re.sub(r"</ol>", "", content)

    # Convert <li>...</li>
    content = re.sub(r"<li>(.*?)</li>", r"- \1", content, flags=re.DOTALL)

    # Strip remaining tags (aggressive – catches <table> leftovers etc.)
    # But leave HTML that looks like valid Markdown extensions
    # Only strip clearly wrapper-only tags
    for tag in ["p", "div", "section", "article"]:
        content = re.sub(rf"<{tag}[^>]*>", "", content)
        content = re.sub(rf"</{tag}>", "\n", content)

    # Remove inline HTML comments
    content = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)

    # Collapse multiple blank lines
    content = re.sub(r"\n{3,}", "\n\n", content)

    return content


def strip_proprietary_anchors(href: str) -> str:
    """Remove ClickHelp auto-generated anchors like #h1__1234567."""
    return re.sub(r"#h[123]_+\d+$", "", href)


def rewrite_links(content: str, archive_name: str, output_md_path: Path,
                  space_dir: Path) -> str:
    """
    Rewrite internal .md links and doc.apizee.com links to new paths.
    """
    def replace_link(m):
        text = m.group(1)
        href = m.group(2)
        href = strip_proprietary_anchors(href)

        # External URL — leave as-is
        if href.startswith("http://") or href.startswith("https://"):
            # Check if it's a doc.apizee.com internal link
            da = re.match(
                r"https://doc\.apizee\.com/(?:smart|articles)/([^/]+)/([^/#?]+)(.*)?",
                href
            )
            if da:
                pub = da.group(1)
                slug = da.group(2)
                anchor = da.group(3) or ""
                anchor = strip_proprietary_anchors(anchor)
                # Look up in global map
                # pub names in URLs use "project-" prefix or archive name
                target_slug_map = None
                for arch in ARCHIVE_SLUG_MAP:
                    if slug in ARCHIVE_SLUG_MAP[arch]:
                        target_slug_map = ARCHIVE_SLUG_MAP[arch][slug]
                        target_space = None
                        for sp, cfg in SPACES.items():
                            for g in cfg["groups"]:
                                if g["archive"] == arch:
                                    target_space = sp
                                    break
                        if target_space:
                            new_href = f"../{target_space}/{target_slug_map}{anchor}"
                            return f"[{text}]({new_href})"
            return m.group(0)

        # Relative .md link
        if href.endswith(".md") or ".md#" in href:
            parts = href.split("#", 1)
            md_part = parts[0]
            anchor = "#" + strip_proprietary_anchors("#" + parts[1]).lstrip("#") if len(parts) > 1 else ""
            anchor = re.sub(r"^#+", "#", anchor)
            if anchor == "#":
                anchor = ""

            stem = Path(md_part).stem
            # Lookup in current archive first, then global
            if stem in ARCHIVE_SLUG_MAP.get(archive_name, {}):
                new_rel = ARCHIVE_SLUG_MAP[archive_name][stem]
            elif stem in GLOBAL_SLUG_MAP:
                new_rel = GLOBAL_SLUG_MAP[stem][1]
            else:
                QA_ISSUES.append({
                    "type": "broken_internal_link",
                    "file": str(output_md_path),
                    "href": href
                })
                return m.group(0)

            # Compute relative path from output_md_path to space_dir/new_rel
            target_abs = space_dir / new_rel
            try:
                rel = os.path.relpath(target_abs, output_md_path.parent)
            except ValueError:
                rel = str(target_abs)
            return f"[{text}]({rel}{anchor})"

        return m.group(0)

    content = re.sub(r"\[([^\]]*)\]\(([^)]+)\)", replace_link, content)
    return content


def rewrite_assets(content: str, md_src_path: Path, space_assets_dir: Path,
                   output_md_path: Path) -> str:
    """
    Rewrite image paths ../Storage/... → relative path to .gitbook/assets/
    """
    def _resolve_src(src: str):
        """URL-decode + HTML-unescape a src path, then resolve to absolute.
        Falls back to fuzzy ASCII-key match for mojibake filenames on disk."""
        decoded = html_unescape(unquote(src))
        p = (md_src_path.parent / decoded).resolve()
        if p.exists():
            return p
        # Fuzzy fallback: strip non-ASCII from both sides and match
        def ascii_key(s):
            return re.sub(r'[^a-z0-9.\-_]', '', s.lower())
        target_key = ascii_key(p.name)
        parent_dir = p.parent
        if parent_dir.is_dir():
            for candidate in parent_dir.iterdir():
                if ascii_key(candidate.name) == target_key:
                    return candidate
        return p  # will be reported as missing

    def _copy_and_rel(abs_src: Path) -> str:
        dest_name = copy_asset(abs_src, space_assets_dir)
        assets_abs = space_assets_dir / dest_name
        return os.path.relpath(assets_abs, output_md_path.parent)

    def replace_img(m):
        alt = m.group(1)
        src = m.group(2)
        if src.startswith("http") or src.startswith("data:"):
            return m.group(0)
        abs_src = _resolve_src(src)
        if not abs_src.exists():
            QA_ISSUES.append({"type": "missing_asset", "file": str(output_md_path), "ref": src})
            return m.group(0)
        return f"![{alt}]({_copy_and_rel(abs_src)})"

    # Standard markdown images — allow balanced single-level parens in filenames e.g. Logs (1).png
    IMG_RE = r"!\[([^\]]*)\]\(((?:[^()]+|\([^()]*\))+)\)"
    content = re.sub(IMG_RE, replace_img, content)

    # Escaped image refs used as link text: [!\[alt\](src)](link)
    def replace_escaped_img(m):
        alt = m.group(1)
        src = m.group(2)
        if src.startswith("http") or src.startswith("data:"):
            return m.group(0)
        abs_src = _resolve_src(src)
        if not abs_src.exists():
            QA_ISSUES.append({"type": "missing_asset", "file": str(output_md_path), "ref": src})
            return m.group(0)
        return f"!\\[{alt}\\]({_copy_and_rel(abs_src)})"

    ESCAPED_IMG_RE = r"!\\\[([^\\\]]*)\\\]\(((?:[^()]+|\([^()]*\))+)\)"
    content = re.sub(ESCAPED_IMG_RE, replace_escaped_img, content)

    # HTML img tags
    def replace_html_img(m):
        src = m.group(1)
        if src.startswith("http") or src.startswith("data:"):
            return m.group(0)
        abs_src = _resolve_src(src)
        if not abs_src.exists():
            QA_ISSUES.append({"type": "missing_asset", "file": str(output_md_path), "ref": src})
            return m.group(0)
        return f'<img src="{_copy_and_rel(abs_src)}"'

    content = re.sub(r'<img\s[^>]*src="([^"]+)"', replace_html_img, content)
    return content


def convert_file(
    src_md: Path,
    archive_name: str,
    out_path: Path,
    space_dir: Path,
    space_assets_dir: Path,
) -> None:
    """Full conversion pipeline for one .md file."""
    out_path.parent.mkdir(parents=True, exist_ok=True)

    raw = src_md.read_text(encoding="utf-8-sig")  # strips BOM

    # 1. Callout tables FIRST: runs on original content while table rows are still single
    #    lines (convert_html would split them by turning <br> → \n).
    #    The callout converter handles <br> in cell content internally.
    #    Icon filename matching works on original ../Storage/.../ok.png paths.
    raw = convert_callout_table(raw)

    # 2. HTML cleanup (now safe: strips style= only from HTML tags, not from hint blocks)
    raw = convert_html(raw)

    # 3. Asset rewriting (rewrites remaining ../Storage/... paths → .gitbook/assets/)
    raw = rewrite_assets(raw, src_md, space_assets_dir, out_path)

    # 4. Link rewriting
    raw = rewrite_links(raw, archive_name, out_path, space_dir)

    # 5. Final cleanup
    raw = re.sub(r"\n{3,}", "\n\n", raw).strip() + "\n"

    out_path.write_text(raw, encoding="utf-8")


# ============================================================
#  PHASE 4 – TOC STRUCTURE → FILE TREE + SUMMARY.md
# ============================================================

def toc_to_file_tree(toc_entries: list, archive_dir: Path, archive_name: str,
                      space_dir: Path, space_assets_dir: Path, prefix: str,
                      md_dir: Path) -> list[tuple[str, str]]:
    """
    Recursively walk TOC entries, convert files, generate container READMEs.
    Returns list of (title, rel_path) for SUMMARY.md generation.
    """
    summary_entries = []

    def walk(entries, parent_rel_prefix):
        result = []
        for entry in entries:
            title = entry.get("title", "Untitled").strip()
            file_key = entry.get("file")   # e.g. "MD/foo.md"
            children = entry.get("children", [])

            if file_key:
                stem = Path(file_key).stem
            else:
                stem = slugify(title)

            # Target path within space
            if parent_rel_prefix:
                rel_base = f"{parent_rel_prefix}/{stem}"
            else:
                rel_base = stem

            if children:
                # This entry becomes a directory
                if file_key:
                    # Convert the file as README
                    src = archive_dir / "MD" / Path(file_key).name
                    out = space_dir / rel_base / "README.md"
                    if src.exists():
                        convert_file(src, archive_name, out, space_dir, space_assets_dir)
                    else:
                        QA_ISSUES.append({"type": "missing_source_md", "file": str(src)})
                        _make_container_readme(out, title, [])
                else:
                    # Auto-generate container README
                    out = space_dir / rel_base / "README.md"
                    child_links = []
                    for c in children:
                        c_stem = Path(c["file"]).stem if c.get("file") else slugify(c.get("title",""))
                        child_links.append((c.get("title",""), c_stem + ".md"))
                    _make_container_readme(out, title, child_links)

                rel_path = f"{rel_base}/README.md"
                child_entries = walk(children, rel_base)
                result.append((title, rel_path, child_entries))
            else:
                # Leaf node
                if file_key:
                    src = archive_dir / "MD" / Path(file_key).name
                    out = space_dir / f"{rel_base}.md"
                    if src.exists():
                        convert_file(src, archive_name, out, space_dir, space_assets_dir)
                    else:
                        QA_ISSUES.append({"type": "missing_source_md", "file": str(src)})
                        out.parent.mkdir(parents=True, exist_ok=True)
                        out.write_text(f"# {title}\n\n> ⚠️ Source file not found.\n", encoding="utf-8")
                    rel_path = f"{rel_base}.md"
                else:
                    # TOC entry with no file and no children – shouldn't happen but handle
                    rel_path = f"{rel_base}.md"
                    out = space_dir / rel_path
                    out.parent.mkdir(parents=True, exist_ok=True)
                    out.write_text(f"# {title}\n", encoding="utf-8")
                result.append((title, rel_path, []))
        return result

    return walk(toc_entries, prefix)


def _make_container_readme(out: Path, title: str, child_links: list[tuple[str, str]]) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {title}", ""]
    for child_title, child_href in child_links:
        lines.append(f"* [{child_title}]({child_href})")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def entries_to_summary_lines(entries, indent=0) -> list[str]:
    lines = []
    pad = "  " * indent
    for title, rel_path, children in entries:
        lines.append(f"{pad}* [{title}]({rel_path})")
        if children:
            lines.extend(entries_to_summary_lines(children, indent + 1))
    return lines


# ============================================================
#  PHASE 5 – REDIRECTS
# ============================================================

def register_redirects(archive_name: str, space_name: str):
    """
    Register redirect rows for all known topics in this archive.
    Old URL: https://doc.apizee.com/articles/<archive_name>/<slug>
    New path: /<space_name>/<rel_path>
    """
    slug_map = ARCHIVE_SLUG_MAP.get(archive_name, {})
    for slug, rel_path in slug_map.items():
        old_url = f"https://doc.apizee.com/articles/{archive_name}/{slug}"
        new_path = f"/{space_name}/{rel_path}"
        REDIRECTS.append((old_url, new_path))


# ============================================================
#  PHASE 6 – ORPHAN DETECTION
# ============================================================

def find_orphans(archive_dir: Path, toc: list) -> list[str]:
    """Return list of MD files present but not referenced in TOC."""
    toc_flat = flatten_toc(toc)
    toc_files = {Path(e["file"]).stem for e in toc_flat if "file" in e}
    md_dir = archive_dir / "MD"
    orphans = []
    if md_dir.exists():
        for f in md_dir.glob("*.md"):
            if f.stem not in toc_files:
                orphans.append(f.name)
    return orphans


def find_missing_toc_files(archive_dir: Path, toc: list) -> list[str]:
    """Return list of TOC entries whose file doesn't exist."""
    toc_flat = flatten_toc(toc)
    missing = []
    for e in toc_flat:
        if "file" in e:
            src = archive_dir / "MD" / Path(e["file"]).name
            if not src.exists():
                missing.append(e["file"])
    return missing


# ============================================================
#  MAIN CONVERSION LOOP
# ============================================================

def convert_space(space_name: str, space_cfg: dict) -> dict:
    """Convert one space. Returns stats dict."""
    print(f"\n{'='*60}")
    print(f"  Converting space: {space_name}")
    print(f"{'='*60}")

    space_dir = OUTPUT_BASE / space_name
    space_dir.mkdir(parents=True, exist_ok=True)
    space_assets_dir = space_dir / ".gitbook" / "assets"
    space_assets_dir.mkdir(parents=True, exist_ok=True)

    is_hidden = space_cfg.get("hidden", False)
    summary_groups = []
    stats = {
        "space": space_name,
        "archives": [],
        "total_pages": 0,
        "orphans": [],
        "missing_files": [],
    }

    for group in space_cfg["groups"]:
        archive_name = group["archive"]
        group_title  = group.get("title")
        prefix       = group.get("prefix", "")

        archive_dir = SOURCE_BASE / f"{archive_name}-exported"
        if not archive_dir.exists():
            stats["archives"].append({"archive": archive_name, "status": "MISSING"})
            print(f"  [SKIP] Archive not found: {archive_name}-exported")
            continue

        print(f"  → Archive: {archive_name}  (prefix: '{prefix}')")

        toc = load_toc(archive_dir)
        orphans = find_orphans(archive_dir, toc)
        missing = find_missing_toc_files(archive_dir, toc)

        stats["orphans"] += [f"{archive_name}/{o}" for o in orphans]
        stats["missing_files"] += [f"{archive_name}/{m}" for m in missing]

        if orphans:
            print(f"    Orphans: {orphans}")
        if missing:
            print(f"    Missing TOC files: {missing}")

        # Convert TOC entries
        toc_entries = toc_to_file_tree(
            toc, archive_dir, archive_name,
            space_dir, space_assets_dir, prefix,
            archive_dir / "MD"
        )

        # Convert orphan files → place in "unsorted" group
        if orphans:
            unsorted_prefix = f"{prefix}/unsorted" if prefix else "unsorted"
            for orphan in orphans:
                src = archive_dir / "MD" / orphan
                stem = Path(orphan).stem
                out_rel = f"{unsorted_prefix}/{stem}.md"
                out = space_dir / out_rel
                convert_file(src, archive_name, out, space_dir, space_assets_dir)
                toc_entries.append((stem.replace("-", " ").title(), out_rel, []))

        # Register redirects
        register_redirects(archive_name, space_name)

        n_pages = len([e for e in flatten_toc(toc)])
        stats["total_pages"] += n_pages + len(orphans)
        stats["archives"].append({
            "archive": archive_name,
            "status": "OK",
            "toc_entries": n_pages,
            "orphans": len(orphans),
            "missing": len(missing),
        })

        if group_title:
            summary_groups.append((group_title, toc_entries))
        else:
            # Flat (no group header)
            summary_groups.append((None, toc_entries))

    # Generate SUMMARY.md
    _write_summary(space_dir, summary_groups, is_hidden)

    # Generate .gitbook.yaml
    _write_gitbook_yaml(space_dir)

    print(f"  Done: {stats['total_pages']} pages")
    return stats


def _write_summary(space_dir: Path, groups: list, hidden: bool):
    lines = ["# Summary", ""]

    if hidden:
        lines.append("{% hint style=\"warning\" %}")
        lines.append("These are contextual help pages (called by the application).")
        lines.append("{% endhint %}")
        lines.append("")

    for group_title, entries in groups:
        if group_title:
            lines.append(f"## {group_title}")
            lines.append("")
        lines.extend(entries_to_summary_lines(entries))
        lines.append("")

    (space_dir / "SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")


def _write_gitbook_yaml(space_dir: Path):
    content = (
        "root: ./\n"
        "structure:\n"
        "  summary: SUMMARY.md\n"
    )
    (space_dir / ".gitbook.yaml").write_text(content, encoding="utf-8")


# ============================================================
#  PHASE 7 – QA CHECKS
# ============================================================

def run_qa(spaces_to_check: list[str]) -> dict:
    print("\n[QA] Running post-conversion checks…")
    qa = {
        "broken_links": [],
        "missing_assets": [],
        "empty_files": [],
        "bom_remaining": [],
        "clickhelp_residue": [],
        "total_md_files": 0,
    }

    for space_name in spaces_to_check:
        space_dir = OUTPUT_BASE / space_name
        if not space_dir.exists():
            continue
        for md in space_dir.rglob("*.md"):
            qa["total_md_files"] += 1
            content = md.read_bytes()

            # BOM check
            if content.startswith(b"\xef\xbb\xbf"):
                qa["bom_remaining"].append(str(md))

            text = content.decode("utf-8", errors="replace")

            # Empty file
            if len(text.strip()) == 0:
                qa["empty_files"].append(str(md))

            # ClickHelp residue
            if "../Storage/" in text:
                qa["clickhelp_residue"].append({"file": str(md), "pattern": "../Storage/"})
            if "DXR.axd" in text:
                qa["clickhelp_residue"].append({"file": str(md), "pattern": "DXR.axd"})

    # Add issues from conversion
    for issue in QA_ISSUES:
        if issue["type"] in ("broken_internal_link",):
            qa["broken_links"].append(issue)
        elif issue["type"] in ("missing_asset",):
            qa["missing_assets"].append(issue)

    print(f"  {qa['total_md_files']} MD files checked")
    print(f"  Broken links: {len(qa['broken_links'])}")
    print(f"  Missing assets: {len(qa['missing_assets'])}")
    print(f"  Empty files: {len(qa['empty_files'])}")
    print(f"  BOM remaining: {len(qa['bom_remaining'])}")
    print(f"  ClickHelp residue: {len(qa['clickhelp_residue'])}")
    return qa


# ============================================================
#  PHASE 8 – WRITE REDIRECTS + DECISION + REPORT
# ============================================================

def write_redirects():
    out = OUTPUT_BASE / "redirects.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["source_url", "target_path"])
        for src, tgt in sorted(set(REDIRECTS)):
            w.writerow([src, tgt])
    print(f"\n[redirects] {len(REDIRECTS)} rows → redirects.csv")


def write_decision_md():
    content = """# Décisions de migration

## diag-help-desk-user

**Décision** : placé dans un espace GitBook dédié `diag-help-desk/`.

**Justification** : La publication contient 52 topics et constitue un guide utilisateur complet
pour le produit "Diag Help Desk", une variante hébergée/on-premise de la visio-assistance.
Elle a sa propre structure TOC (FAQ intégrée, section Tutoriels, gestion de tickets),
une terminologie distincte ("ticket" vs "invitation"), et n'appartient pas aux espaces
`video-assistance/` (qui ciblent le même produit en SaaS cloud). La séparer permet :
- de préserver les URLs de redirections `/articles/diag-help-desk-user/…`
- d'éviter des doublons de contenu sans fusion involontaire
- de laisser l'équipe décider ultérieurement d'une consolidation

---

## project-content-reuse (_appvisio-reuse-publication)

**Décision** : non publié comme espace GitBook.

**Justification** : Ce projet ne contient que des snippets partagés et des assets
(icônes, images génériques). Chaque archive exportée possède déjà sa propre copie
locale des assets dans `Storage/<pub>/project-content-reuse/`. Le script les copie
dans `.gitbook/assets/` de chaque espace cible avec déduplication par hash SHA-256.
Les snippets textuels (s'ils existent) sont inlinés dans les fichiers convertis.

---

## ok.png et prerequis.png

**Décision** : convertis en hints GitBook (success / info respectivement).

**Justification** : Ces icônes sont utilisées dans des tableaux 2-colonnes au même titre
que `info.png` et `warning.png`. Leur conversion en hints améliore la lisibilité dans GitBook
et élimine les références d'images parasites pour des éléments purement sémantiques.

---

## Ancres propriétaires ClickHelp (#h1__XXXXXXXX, #h2__XXXXXXXX)

**Décision** : supprimées lors de la conversion.

**Justification** : Ces ancres sont auto-générées par ClickHelp et ne correspondent pas à
des IDs d'en-têtes HTML standard. Elles ne fonctionneraient pas dans GitBook. Les liens
perdent leur cible précise mais restent valides au niveau page. Les ancres sémantiques
(ex. `#link-to-information-page`) sont conservées.

---

## validate.png dans les tableaux de compatibilité navigateurs

**Décision** : conservé comme image (non converti en hint).

**Justification** : Cette icône est utilisée comme cellule de donnée dans des tableaux
de compatibilité multi-lignes/multi-colonnes, pas comme indicateur de callout autonome.
"""
    out = OUTPUT_BASE / "decision.md"
    out.write_text(content, encoding="utf-8")


def write_report(all_stats: list[dict], qa: dict):
    lines = [
        "# Rapport de migration ClickHelp → GitBook",
        "",
        "## Volumétrie par espace",
        "",
        "| Espace | Archives | Pages converties | Orphelins | Fichiers manquants |",
        "| --- | --- | --- | --- | --- |",
    ]
    total_pages = 0
    for s in all_stats:
        archives = ", ".join(a["archive"] for a in s["archives"])
        pages = s["total_pages"]
        orphans = len(s["orphans"])
        missing = len(s["missing_files"])
        total_pages += pages
        lines.append(f"| `{s['space']}` | {archives} | {pages} | {orphans} | {missing} |")

    lines += [
        "",
        f"**Total** : {total_pages} pages converties",
        "",
        "## Archives manquantes (non exportées)",
        "",
    ]
    for m in MISSING_ARCHIVES:
        lines.append(f"- `{m}` — non disponible dans les exports")

    lines += [
        "",
        "## Résultats QA",
        "",
        f"- Fichiers .md vérifiés : **{qa['total_md_files']}**",
        f"- Liens internes cassés : **{len(qa['broken_links'])}**",
        f"- Assets manquants : **{len(qa['missing_assets'])}**",
        f"- Fichiers vides : **{len(qa['empty_files'])}**",
        f"- BOM UTF-8 résiduels : **{len(qa['bom_remaining'])}**",
        f"- Résidus syntaxe ClickHelp : **{len(qa['clickhelp_residue'])}**",
        "",
    ]

    if qa["broken_links"]:
        lines += ["### Liens cassés", ""]
        for bl in qa["broken_links"][:50]:
            lines.append(f"- `{bl.get('href','?')}` dans `{bl.get('file','?')}`")
        if len(qa["broken_links"]) > 50:
            lines.append(f"_(et {len(qa['broken_links']) - 50} autres)_")
        lines.append("")

    if qa["missing_assets"]:
        lines += ["### Assets manquants", ""]
        for ma in qa["missing_assets"][:30]:
            lines.append(f"- `{ma.get('ref','?')}` dans `{ma.get('file','?')}`")
        if len(qa["missing_assets"]) > 30:
            lines.append(f"_(et {len(qa['missing_assets']) - 30} autres)_")
        lines.append("")

    if qa["clickhelp_residue"]:
        lines += ["### Résidus ClickHelp", ""]
        for r in qa["clickhelp_residue"][:20]:
            lines.append(f"- Pattern `{r['pattern']}` dans `{r['file']}`")
        lines.append("")

    lines += [
        "## Doublons inter-espaces",
        "",
        "Les topics suivants apparaissent dans plusieurs archives avec le même slug.",
        "Ils ont été conservés séparément (pas de fusion automatique).",
        "",
    ]
    # Find duplicate slugs
    slug_counts: dict[str, list] = defaultdict(list)
    for arch, smap in ARCHIVE_SLUG_MAP.items():
        for slug in smap:
            slug_counts[slug].append(arch)
    dups = {s: archs for s, archs in slug_counts.items() if len(archs) > 1}
    if dups:
        lines.append("| Slug | Archives |")
        lines.append("| --- | --- |")
        for slug, archs in sorted(dups.items())[:40]:
            lines.append(f"| `{slug}` | {', '.join(archs)} |")
    else:
        lines.append("_(aucun doublon détecté)_")

    lines += [
        "",
        "## Redirections",
        "",
        f"Fichier généré : `redirects.csv` — {len(REDIRECTS)} URLs",
        "",
        "## Prochaines étapes",
        "",
        "1. Valider cet échantillon de pages converties (présenté séparément)",
        "2. Importer espace par espace dans GitBook via Git Sync",
        "3. Configurer le bloc `redirects:` dans chaque `.gitbook.yaml`",
        "4. Basculer le DNS/CDN de doc.apizee.com",
    ]

    out = OUTPUT_BASE / "RAPPORT-migration.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n[report] RAPPORT-migration.md written")


# ============================================================
#  ENTRY POINT
# ============================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--space", help="Convert only this space (e.g. faq)")
    parser.add_argument("--qa-only", action="store_true")
    args = parser.parse_args()

    if args.qa_only:
        qa = run_qa(list(SPACES.keys()))
        return

    # Reset global state for re-runs
    GLOBAL_SLUG_MAP.clear()
    for v in ARCHIVE_SLUG_MAP.values():
        v.clear()
    ARCHIVE_SLUG_MAP.clear()
    ASSET_HASH_MAP.clear()
    REDIRECTS.clear()
    QA_ISSUES.clear()

    # Note: we overwrite in place (Windows mount doesn't allow unlink after creation)
    OUTPUT_BASE.mkdir(parents=True, exist_ok=True)

    # Phase 1: build global slug map
    print("\n[Phase 1] Building global slug map…")
    build_global_slug_map()

    # Phase 2-6: convert spaces
    spaces_to_run = [args.space] if args.space else list(SPACES.keys())
    all_stats = []

    for space_name in spaces_to_run:
        if space_name not in SPACES:
            print(f"[ERROR] Unknown space: {space_name}")
            continue
        stats = convert_space(space_name, SPACES[space_name])
        all_stats.append(stats)

    # Write redirects
    write_redirects()

    # Write decision doc
    write_decision_md()

    # QA
    qa = run_qa(spaces_to_run)

    if not args.space:
        write_report(all_stats, qa)

    print("\n✓ Migration complete.")
    print(f"  Output: {OUTPUT_BASE}")


if __name__ == "__main__":
    main()
