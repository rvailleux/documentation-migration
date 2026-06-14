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
import argparse
from pathlib import Path
from collections import defaultdict
from html import unescape as html_unescape
from urllib.parse import unquote

# ============================================================
#  PATHS
# ============================================================
SCRIPTS_DIR = Path(__file__).parent.resolve()
SOURCE_BASE = SCRIPTS_DIR.parent
OUTPUT_BASE = SOURCE_BASE / "gitbook-export"

# ============================================================
#  SPACE / ARCHIVE MAPPING
# ============================================================
SPACES = {
    "video-assistance": {
        "groups": [
            {"archive": "video-assistance-user-en",  "title": "For agents",         "prefix": "agents"},
            {"archive": "video-assistance-guest-en", "title": "For guests",         "prefix": "guests"},
            {"archive": "video-assistance-admin-en", "title": "For administrators", "prefix": "admins"},
            {"archive": "diag-help-desk-user",         "title": "Help Desk",          "prefix": "help-desk"},
            {"archive": "agents-tab-set-the-call-distribution-mode",         "title": None, "prefix": "contextual-help", "hidden": True},
            {"archive": "ticket-advanced-option-scan-the-guest-video-tooltip", "title": None, "prefix": "contextual-help", "hidden": True},
        ]
    },
    "embed": {
        "groups": [
            {"archive": "apizee-embed-for-agents",   "title": "For agents",     "prefix": "agents"},
            {"archive": "apizee-embed-for-guests",  "title": "For guests",     "prefix": "guests"},
            {"archive": "apizee-embed-for-admins",  "title": "For admins",     "prefix": "admins"},
            {"archive": "apizee-embed-for-it-operators", "title": "For IT operators", "prefix": "it-operators"},
        ]
    },
    "video-assistance-multi": {
        "groups": [
            {"archive": "assistance-multi-participants-user",  "title": "Pour les agents",           "prefix": "agents"},
            {"archive": "assistance-multi-participants-guest", "title": "Pour les invités",          "prefix": "guests"},
            {"archive": "assistance-multi-participants-admin", "title": "Pour les administrateurs", "prefix": "admins"},
        ]
    },
    "meetings": {
        "groups": [
            {"archive": "apizee-meeting-user-en",  "title": "For users",        "prefix": "users"},
            {"archive": "apizee-meeting-guest-en", "title": "For guests",       "prefix": "guests"},
            {"archive": "apizee-meeting-admin-en", "title": "For administrators", "prefix": "admins"},
        ]
    },
    "telehealth": {
        "groups": [
            {"archive": "health-user",  "title": "For practitioners", "prefix": "practitioners"},
            {"archive": "health-guest", "title": "For patients",      "prefix": "patients"},
            {"archive": "health-admin", "title": "For administrators","prefix": "admins"},
        ]
    },
    "salesforce": {
        "groups": [{"archive": "apizee-for-salesforce", "title": None, "prefix": ""}]
    },
    "genesys": {
        "groups": [{"archive": "apizee-for-genesys-admin", "title": None, "prefix": ""}]
    },
    "servicenow": {
        "groups": [{"archive": "apizee-for-servicenow-publication", "title": None, "prefix": ""}]
    },
    "faq": {
        "groups": [
            {"archive": "faq", "title": "General", "prefix": "general"},
            {"archive": "legal-information", "title": "Legal", "prefix": "legal"},
        ]
    },
}

SKIP_ARCHIVES = {"_appvisio-reuse-publication", "customer-engagement-admin-en"}

MISSING_ARCHIVES = [
    "apizee-for-salesforce-publication-admin",
    "customer-engagement-user-en",
    "agents-tab-prioritize-agents-availability",
    "apizee-meeting-user-fr",
    "apizee-meeting-guest-fr",
    "apizee-meeting-admin-fr",
]

# ============================================================
#  CATEGORY DEFINITIONS
# ============================================================
CATEGORY_A_SLUGS = {
    "i-forgot-my-password-can-i-reset-it",
    "where-are-the-servers",
    "i-want-to-change-my-subscription",
    "i-cannot-add-a-new-user-to-my-company",
    "how-to-contact-the-support-team-and-follow-my-requests",
    "change-language",
    "what-language-is-available",
    "how-can-i-switch-from-dark-to-light-mode",
}

CATEGORY_B_SLUGS = {
    "log-in-to-the-apizee-portal-for-the-first-time",
    "user-roles",
    "choose-my-portal-dashboard",
    "allow-the-web-browser-to-access-the-camera-and-the-microphone-on-my-computer",
    "audio-video-settings",
    "bandwidth-resolution-settings",
}

# ============================================================
#  CALLOUT ICONS → GitBook hint style
# ============================================================
CALLOUT_ICONS = {
    "info.png":     "info",
    "warning.png":  "warning",
    "alert.png":    "danger",
    "danger.png":   "danger",
    "tip.png":      "success",
    "ok.png":       "success",
    "prerequis.png": "info",
}

# ============================================================
#  GLOBAL STATE
# ============================================================
GLOBAL_SLUG_MAP: dict[str, tuple[str, str]] = {}
ARCHIVE_SLUG_MAP: dict[str, dict[str, str]] = defaultdict(dict)
ASSET_HASH_MAP: dict[str, str] = {}
REDIRECTS: list[tuple[str, str]] = []
QA_ISSUES: list[dict] = []

# ============================================================
#  HELPERS
# ============================================================
def slugify(text: str) -> str:
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
    toc_path = archive_dir / "toc.yaml"
    if not toc_path.exists():
        return []
    raw = toc_path.read_text(encoding="utf-8-sig")
    return yaml.safe_load(raw) or []


def flatten_toc(entries: list) -> list[dict]:
    result = []
    def _walk(items, parent_slug_path):
        for item in items:
            slug = Path(item["file"]).stem if "file" in item else slugify(item.get("title", "untitled"))
            path = f"{parent_slug_path}/{slug}" if parent_slug_path else slug
            result.append({**item, "_slug": slug, "_path": path})
            if "children" in item:
                _walk(item["children"], path)
    _walk(entries, "")
    return result


def get_assigned_archives() -> set[str]:
    assigned = set()
    for space_cfg in SPACES.values():
        for group in space_cfg["groups"]:
            assigned.add(group["archive"])
    return assigned


def get_all_exported_archives() -> list[str]:
    result = []
    for item in SOURCE_BASE.iterdir():
        if item.is_dir() and item.name.endswith("-exported"):
            name = item.name[:-9]
            if name not in SKIP_ARCHIVES:
                result.append(name)
    return sorted(result)


# ============================================================
#  INVENTORY
# ============================================================
def build_inventory() -> list[dict]:
    inventory: list[dict] = []
    assigned = get_assigned_archives()
    archive_target: dict[str, tuple[str, dict]] = {}
    for space_name, space_cfg in SPACES.items():
        for group in space_cfg["groups"]:
            archive_target[group["archive"]] = (space_name, group)

    for archive_name in get_all_exported_archives():
        archive_dir = SOURCE_BASE / f"{archive_name}-exported"
        md_dir = archive_dir / "MD"
        toc = load_toc(archive_dir)
        flat = flatten_toc(toc)
        toc_slugs = {Path(e["file"]).stem for e in flat if "file" in e}
        toc_title_map = {Path(e["file"]).stem: e.get("title", "") for e in flat if "file" in e}
        if not md_dir.exists():
            continue
        for md_file in md_dir.glob("*.md"):
            slug = md_file.stem
            size = md_file.stat().st_size
            title = toc_title_map.get(slug, slug.replace("-", " ").title())
            is_orphan = slug not in toc_slugs
            category = "-"
            if slug in CATEGORY_A_SLUGS:
                category = "A"
            elif slug in CATEGORY_B_SLUGS:
                category = "B"
            target_space, target_prefix = "", ""
            if archive_name in archive_target:
                space_name, group = archive_target[archive_name]
                target_space = space_name
                target_prefix = group.get("prefix", "")
            inventory.append({
                "archive": archive_name, "slug": slug, "title": title,
                "md_path": str(md_file), "category": category,
                "orphan": is_orphan, "file_size": size,
                "target_space": target_space, "target_prefix": target_prefix,
                "assigned": archive_name in assigned,
            })
    return inventory


def write_inventory(inventory: list[dict]):
    path = OUTPUT_BASE / "INVENTAIRE.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["archive", "slug", "title", "md_path", "category", "orphan",
                    "file_size", "target_space", "target_prefix", "assigned"])
        for row in sorted(inventory, key=lambda r: (r["archive"], r["slug"])):
            w.writerow([row["archive"], row["slug"], row["title"], row["md_path"],
                        row["category"], row["orphan"], row["file_size"],
                        row["target_space"], row["target_prefix"], row["assigned"]])
    print(f"[inventory] {len(inventory)} rows → {path}")


# ============================================================
#  CATEGORY ANALYSIS
# ============================================================
def analyze_categories(inventory: list[dict]) -> tuple[dict, dict, set]:
    cat_a = {}
    cat_b = {}
    slug_locations: dict[str, list[dict]] = defaultdict(list)
    for row in inventory:
        slug_locations[row["slug"]].append(row)
    for slug in CATEGORY_A_SLUGS:
        rows = [r for r in slug_locations.get(slug, []) if r["assigned"]]
        if rows:
            best = max(rows, key=lambda r: r["file_size"])
            cat_a[slug] = {"source_path": Path(best["md_path"]), "title": best["title"]}
    for slug in CATEGORY_B_SLUGS:
        rows = [r for r in slug_locations.get(slug, []) if r["assigned"]]
        if rows:
            best = max(rows, key=lambda r: r["file_size"])
            cat_b[slug] = {"source_path": Path(best["md_path"]), "title": best["title"]}
    cat_c = set()
    for slug, rows in slug_locations.items():
        assigned = [r for r in rows if r["assigned"]]
        if len(assigned) > 1 and slug not in CATEGORY_A_SLUGS and slug not in CATEGORY_B_SLUGS:
            cat_c.add(slug)
    print(f"[categories] A={len(cat_a)}, B={len(cat_b)}, C={len(cat_c)}")
    return cat_a, cat_b, cat_c


# ============================================================
#  SLUG MAP
# ============================================================
def build_global_slug_map(cat_a_canonical: dict):
    for space_name, space_cfg in SPACES.items():
        for group in space_cfg["groups"]:
            archive_name = group["archive"]
            prefix = group["prefix"]
            archive_dir = SOURCE_BASE / f"{archive_name}-exported"
            if not archive_dir.exists():
                continue
            toc = load_toc(archive_dir)
            flat = flatten_toc(toc)
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
                target = f"{prefix}/{entry['_path']}" if prefix else entry["_path"]
                has_children = bool(entry.get("children"))
                if has_children:
                    target_rel = f"{target}/README.md"
                else:
                    target_rel = f"{target}.md"
                if slug in CATEGORY_A_SLUGS and archive_name == "faq":
                    target_rel = f"platform/{slug}.md"
                ARCHIVE_SLUG_MAP[archive_name][slug] = target_rel
                GLOBAL_SLUG_MAP[slug] = (space_name, target_rel)
    for slug in CATEGORY_A_SLUGS:
        if "faq" in ARCHIVE_SLUG_MAP and slug in ARCHIVE_SLUG_MAP["faq"]:
            GLOBAL_SLUG_MAP[slug] = ("faq", ARCHIVE_SLUG_MAP["faq"][slug])
    print(f"[slug-map] {len(GLOBAL_SLUG_MAP)} unique slugs")


# ============================================================
#  ASSET HANDLING
# ============================================================
def copy_asset(src_path: Path, space_assets_dir: Path) -> str:
    if not src_path.exists():
        return src_path.name
    h = file_hash(src_path)
    if h in ASSET_HASH_MAP:
        return ASSET_HASH_MAP[h]
    dest_name = src_path.name
    dest_path = space_assets_dir / dest_name
    if dest_path.exists():
        if file_hash(dest_path) == h:
            ASSET_HASH_MAP[h] = dest_name
            return dest_name
        ext = src_path.suffix
        dest_name = f"{src_path.stem}-{h[:8]}{ext}"
        dest_path = space_assets_dir / dest_name
    space_assets_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_path, dest_path)
    ASSET_HASH_MAP[h] = dest_name
    return dest_name


def resolve_asset_path(img_ref: str, md_file: Path) -> Path:
    decoded = html_unescape(unquote(img_ref))
    p = (md_file.parent / decoded).resolve()
    if p.exists():
        return p
    def ascii_key(s):
        return re.sub(r'[^a-z0-9.\-_]', '', s.lower())
    target_key = ascii_key(p.name)
    parent_dir = p.parent
    if parent_dir.is_dir():
        for candidate in parent_dir.iterdir():
            if ascii_key(candidate.name) == target_key:
                return candidate
    return p


def rewrite_assets(content: str, md_src_path: Path, space_assets_dir: Path,
                   output_md_path: Path) -> str:
    def _copy_and_rel(abs_src: Path) -> str:
        dest_name = copy_asset(abs_src, space_assets_dir)
        assets_abs = space_assets_dir / dest_name
        return os.path.relpath(assets_abs, output_md_path.parent)

    def is_bogus_src(src: str) -> bool:
        if not src or src.startswith("http") or src.startswith("data:"):
            return True  # empty src is bogus
        name = Path(src).name
        return name.startswith(".") and not Path(src).suffixes

    def replace_img(m):
        alt, src = m.group(1), m.group(2)
        if src.startswith("http") or src.startswith("data:"):
            return m.group(0)
        if is_bogus_src(src):
            return ""
        abs_src = resolve_asset_path(src, md_src_path)
        if not abs_src.exists():
            QA_ISSUES.append({"type": "missing_asset", "file": str(output_md_path), "ref": src})
            return m.group(0)
        return f"![{alt}]({_copy_and_rel(abs_src)})"

    IMG_RE = r"!\[([^\]]*)\]\(((?:[^()]+|\([^()]*\))+)\)"
    content = re.sub(IMG_RE, replace_img, content)
    content = re.sub(r"\n{3,}", "\n\n", content)

    def replace_html_img(m):
        src = m.group(1)
        if src.startswith("http") or src.startswith("data:"):
            return m.group(0)
        if is_bogus_src(src):
            return ""
        abs_src = resolve_asset_path(src, md_src_path)
        if not abs_src.exists():
            QA_ISSUES.append({"type": "missing_asset", "file": str(output_md_path), "ref": src})
            return m.group(0)
        return f'<img src="{_copy_and_rel(abs_src)}"'

    content = re.sub(r'<img\s[^>]*src="([^"]+)"', replace_html_img, content)

    # Image inside a link text: [![alt](src)](href)
    def replace_img_in_link(m):
        alt = m.group(1)
        src = m.group(2)
        href = m.group(3)
        if src.startswith("http") or src.startswith("data:"):
            return m.group(0)
        if is_bogus_src(src):
            return ""
        abs_src = resolve_asset_path(src, md_src_path)
        if not abs_src.exists():
            QA_ISSUES.append({"type": "missing_asset", "file": str(output_md_path), "ref": src})
            return m.group(0)
        return f"[![{alt}]({_copy_and_rel(abs_src)})]({href})"

    IMG_IN_LINK_RE = r"\[!\[([^\]]*)\]\(((?:[^()]+|\([^()]*\))+)\)\]\(((?:[^()]+|\([^()]*\))+)\)"
    content = re.sub(IMG_IN_LINK_RE, replace_img_in_link, content)
    return content


# ============================================================
#  CONTENT CONVERSION
# ============================================================
def convert_callout_table(content: str) -> str:
    lines = content.split("\n")
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(
            r"^\s*\|\s*(?:\[)?!\[[^\]]*\]\(([^)]+)\)(?:\]\([^)]+\))?\s*\|\s*(.*?)\s*\|?\s*$", line)
        if m:
            icon_name = Path(m.group(1)).name
            style = CALLOUT_ICONS.get(icon_name)
            next_is_sep = (i + 1 < len(lines) and
                           re.match(r"^\s*\|\s*[-:]+\s*\|\s*[-:]+\s*\|", lines[i + 1]))
            if style is not None:
                cell_text = re.sub(r"<br\s*/?>", "\n", m.group(2)).strip()
                out.append(f'{{% hint style="{style}" %}}')
                out.append(cell_text)
                out.append("{% endhint %}")
                i += 2 if next_is_sep else 1
                continue
        if re.match(r"^\s*\|\s*[-:]+\s*\|\s*[-:]+\s*\|", line):
            if i + 1 < len(lines):
                m2 = re.match(
                    r"^\s*\|\s*(?:\[)?!\[[^\]]*\]\(([^)]+)\)(?:\]\([^)]+\))?\s*\|\s*(.*?)\s*\|?\s*$", lines[i + 1])
                if m2:
                    icon_name = Path(m2.group(1)).name
                    style = CALLOUT_ICONS.get(icon_name)
                    if style is not None:
                        cell_text = re.sub(r"<br\s*/?>", "\n", m2.group(2)).strip()
                        out.append(f'{{% hint style="{style}" %}}')
                        out.append(cell_text)
                        out.append("{% endhint %}")
                        i += 2
                        continue
        out.append(line)
        i += 1
    return "\n".join(out)


def convert_html(content: str) -> str:
    content = re.sub(r"<br\s*/?>", "\n", content)
    def strip_html_attrs(m):
        tag = m.group(0)
        tag = re.sub(r'\s+style="[^"]*"', "", tag)
        tag = re.sub(r"\s+style='[^']*'", "", tag)
        tag = re.sub(r'\s+loading="[^"]*"', "", tag)
        return tag
    content = re.sub(r"<[a-zA-Z][^>]*>", strip_html_attrs, content)
    content = re.sub(r"<(?:b|strong)>(.*?)</(?:b|strong)>", r"**\1**", content, flags=re.DOTALL)
    content = re.sub(r"<(?:i|em)>(.*?)</(?:i|em)>", r"*\1*", content, flags=re.DOTALL)
    content = re.sub(r"<span[^>]*>(.*?)</span>", r"\1", content, flags=re.DOTALL)
    content = re.sub(r"<ul[^>]*>", "", content)
    content = re.sub(r"</ul>", "", content)
    content = re.sub(r"<ol[^>]*>", "", content)
    content = re.sub(r"</ol>", "", content)
    content = re.sub(r"<li>(.*?)</li>", r"- \1", content, flags=re.DOTALL)
    for tag in ["p", "div", "section", "article"]:
        content = re.sub(rf"<{tag}[^>]*>", "", content)
        content = re.sub(rf"</{tag}>", "\n", content)
    content = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)
    content = re.sub(r"\n{3,}", "\n\n", content)
    return content


def strip_proprietary_anchors(href: str) -> str:
    return re.sub(r"#h[123]_+\d+$", "", href)


def rewrite_links(content: str, archive_name: str, output_md_path: Path,
                  space_dir: Path) -> str:
    def replace_link(m):
        text = m.group(1)
        href = m.group(2)
        href = strip_proprietary_anchors(href)
        if href.startswith("http://") or href.startswith("https://"):
            da = re.match(
                r"https://doc\.apizee\.com/(?:smart|articles)/([^/]+)/([^/#?]+)(.*)?",
                href)
            if da:
                slug = da.group(2)
                anchor = strip_proprietary_anchors(da.group(3) or "")
                for arch, smap in ARCHIVE_SLUG_MAP.items():
                    if slug in smap:
                        target_slug_map = smap[slug]
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
        if href.endswith(".md") or ".md#" in href:
            parts = href.split("#", 1)
            md_part = parts[0]
            anchor = "#" + strip_proprietary_anchors("#" + parts[1]).lstrip("#") if len(parts) > 1 else ""
            anchor = re.sub(r"^#+", "#", anchor)
            if anchor == "#":
                anchor = ""
            stem = Path(md_part).stem
            if stem in ARCHIVE_SLUG_MAP.get(archive_name, {}):
                new_rel = ARCHIVE_SLUG_MAP[archive_name][stem]
            elif stem in GLOBAL_SLUG_MAP:
                new_rel = GLOBAL_SLUG_MAP[stem][1]
            else:
                QA_ISSUES.append({"type": "broken_internal_link", "file": str(output_md_path), "href": href})
                return m.group(0)
            target_abs = space_dir / new_rel
            try:
                rel = os.path.relpath(target_abs, output_md_path.parent)
            except ValueError:
                rel = str(target_abs)
            return f"[{text}]({rel}{anchor})"
        return m.group(0)
    content = re.sub(r"\[([^\]]*)\]\(([^)]+)\)", replace_link, content)
    return content


def convert_content(src_md: Path, archive_name: str, out_path: Path,
                    space_dir: Path, space_assets_dir: Path) -> str:
    raw = src_md.read_text(encoding="utf-8-sig")
    # Strip common Markdown escapes so callouts/images match correctly
    raw = raw.replace(r"\[", "[").replace(r"\]", "]")
    raw = convert_callout_table(raw)
    raw = convert_html(raw)
    raw = rewrite_assets(raw, src_md, space_assets_dir, out_path)
    raw = rewrite_links(raw, archive_name, out_path, space_dir)
    raw = re.sub(r"\n{3,}", "\n\n", raw).strip() + "\n"
    return raw


# ============================================================
#  CATEGORY PAGE GENERATORS
# ============================================================
def make_category_a_redirect(title: str, platform_rel_path: str) -> str:
    return f'''---
description: See the platform FAQ for this topic.
---
# {title}

{{% content-ref url="{platform_rel_path}" %}}
[{title}]({platform_rel_path})
{{% endcontent-ref %}}
'''


def make_category_b_include(rel_include_path: str) -> str:
    return f'{{% include "{rel_include_path}" %}}\n'


# ============================================================
#  TOC → FILE TREE
# ============================================================
def _safe_write(path: Path, text: str) -> None:
    """Write text to path, bypassing CIFS dentry cache via openat (dir_fd).

    On Windows-mounted CIFS (SMB) shares, a freshly-created directory may not
    appear in its parent's cached listing, causing path.write_text() to fail
    with ENOENT even though the directory exists.  Using os.open() with
    dir_fd=<parent_fd> bypasses the parent-directory dentry cache entirely:
    the kernel resolves the file relative to the already-open parent fd.
    """
    import os
    parent_fd = os.open(str(path.parent), os.O_RDONLY | os.O_DIRECTORY)
    try:
        fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644,
                     dir_fd=parent_fd)
        try:
            os.write(fd, text.encode("utf-8"))
        finally:
            os.close(fd)
    finally:
        os.close(parent_fd)

def convert_topic(src_md: Path, archive_name: str, out_path: Path, slug: str,
                  space_dir: Path, space_assets_dir: Path,
                  cat_a_canonical: dict, cat_b_canonical: dict,
                  shared_dir: Path, shared_assets_dir: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Determine canonical source flags
    is_canonical_b = slug in cat_b_canonical and str(src_md) == str(cat_b_canonical[slug]["source_path"])
    is_canonical_a = slug in cat_a_canonical and str(src_md) == str(cat_a_canonical[slug]["source_path"])

    # 1. Category A canonical → write to faq/platform/ and redirect at out_path
    if slug in CATEGORY_A_SLUGS and is_canonical_a:
        faq_dir = OUTPUT_BASE / "faq"
        faq_assets = faq_dir / ".gitbook" / "assets"
        faq_assets.mkdir(parents=True, exist_ok=True)
        platform_out = faq_dir / "platform" / f"{slug}.md"
        platform_out.parent.mkdir(parents=True, exist_ok=True)
        converted = convert_content(src_md, archive_name, platform_out, faq_dir, faq_assets)
        platform_out.write_text(converted, encoding="utf-8")
        # Redirect at normal out_path
        try:
            rel = os.path.relpath(platform_out, out_path.parent)
        except ValueError:
            rel = str(platform_out)
        raw = make_category_a_redirect(
            cat_a_canonical.get(slug, {}).get("title", slug.replace("-", " ").title()), rel)
        _safe_write(out_path, raw)
        return

    # 2. Category B canonical → write to shared/ and include at out_path
    if slug in CATEGORY_B_SLUGS and is_canonical_b:
        include_out = shared_dir / ".gitbook" / "includes" / f"{slug}.md"
        include_out.parent.mkdir(parents=True, exist_ok=True)
        converted = convert_content(src_md, archive_name, include_out, shared_dir, shared_assets_dir)
        include_out.write_text(converted, encoding="utf-8")
        try:
            rel = os.path.relpath(include_out, out_path.parent)
        except ValueError:
            rel = str(include_out)
        _safe_write(out_path, make_category_b_include(rel))
        return

    # 3. Category A redirect (non-canonical)
    if slug in CATEGORY_A_SLUGS:
        target = OUTPUT_BASE / "faq" / "platform" / f"{slug}.md"
        try:
            rel = os.path.relpath(target, out_path.parent)
        except ValueError:
            rel = str(target)
        raw = make_category_a_redirect(
            cat_a_canonical.get(slug, {}).get("title", slug.replace("-", " ").title()), rel)
        _safe_write(out_path, raw)
        return

    # 4. Category B include (non-canonical)
    if slug in CATEGORY_B_SLUGS:
        target = shared_dir / ".gitbook" / "includes" / f"{slug}.md"
        try:
            rel = os.path.relpath(target, out_path.parent)
        except ValueError:
            rel = str(target)
        _safe_write(out_path, make_category_b_include(rel))
        return

    # 5. Default
    converted = convert_content(src_md, archive_name, out_path, space_dir, space_assets_dir)
    _safe_write(out_path, converted)


def toc_to_file_tree(toc_entries, archive_dir, archive_name, space_dir, space_assets_dir,
                     prefix, cat_a_canonical, cat_b_canonical, shared_dir, shared_assets_dir):
    def walk(entries, parent_rel_prefix):
        result = []
        for entry in entries:
            title = entry.get("title", "Untitled").strip()
            file_key = entry.get("file")
            children = entry.get("children", [])
            stem = Path(file_key).stem if file_key else slugify(title)
            rel_base = f"{parent_rel_prefix}/{stem}" if parent_rel_prefix else stem
            if children:
                if file_key:
                    src = archive_dir / "MD" / Path(file_key).name
                    out = space_dir / rel_base / "README.md"
                    if src.exists():
                        convert_topic(src, archive_name, out, stem, space_dir, space_assets_dir,
                                      cat_a_canonical, cat_b_canonical, shared_dir, shared_assets_dir)
                    else:
                        QA_ISSUES.append({"type": "missing_source_md", "file": str(src)})
                        _make_container_readme(out, title, [])
                else:
                    out = space_dir / rel_base / "README.md"
                    child_links = [(c.get("title", ""), (Path(c["file"]).stem if c.get("file") else slugify(c.get("title", ""))) + ".md") for c in children]
                    _make_container_readme(out, title, child_links)
                rel_path = f"{rel_base}/README.md"
                child_entries = walk(children, rel_base)
                result.append((title, rel_path, child_entries))
            else:
                if file_key:
                    src = archive_dir / "MD" / Path(file_key).name
                    out = space_dir / f"{rel_base}.md"
                    if src.exists():
                        convert_topic(src, archive_name, out, stem, space_dir, space_assets_dir,
                                      cat_a_canonical, cat_b_canonical, shared_dir, shared_assets_dir)
                    else:
                        QA_ISSUES.append({"type": "missing_source_md", "file": str(src)})
                        out.parent.mkdir(parents=True, exist_ok=True)
                        _safe_write(out, f"# {title}\n\n> ⚠️ Source file not found.\n")
                    rel_path = f"{rel_base}.md"
                else:
                    rel_path = f"{rel_base}.md"
                    out = space_dir / rel_path
                    out.parent.mkdir(parents=True, exist_ok=True)
                    _safe_write(out, f"# {title}\n")
                result.append((title, rel_path, []))
        return result
    return walk(toc_entries, prefix)


def _make_container_readme(out, title, child_links):
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {title}", ""]
    for child_title, child_href in child_links:
        lines.append(f"* [{child_title}]({child_href})")
    _safe_write(out, "\n".join(lines) + "\n")


def entries_to_summary_lines(entries, indent=0):
    lines = []
    pad = "  " * indent
    for title, rel_path, children in entries:
        lines.append(f"{pad}* [{title}]({rel_path})")
        if children:
            lines.extend(entries_to_summary_lines(children, indent + 1))
    return lines


# ============================================================
#  SPACE CONVERSION
# ============================================================
def convert_space(space_name, space_cfg, cat_a_canonical, cat_b_canonical,
                  shared_dir, shared_assets_dir):
    print(f"\n{'='*60}")
    print(f"  Converting space: {space_name}")
    print(f"{'='*60}")
    space_dir = OUTPUT_BASE / space_name
    space_dir.mkdir(parents=True, exist_ok=True)
    space_assets_dir = space_dir / ".gitbook" / "assets"
    space_assets_dir.mkdir(parents=True, exist_ok=True)

    prefix_groups = defaultdict(list)
    for group in space_cfg["groups"]:
        prefix_groups[group["prefix"]].append(group)

    total_pages = 0
    all_orphans = []
    all_missing = []
    summary_sections = []

    for prefix in sorted(prefix_groups.keys(), key=lambda p: (p == "", p)):
        groups = prefix_groups[prefix]
        group_title = None
        for g in groups:
            if g.get("title"):
                group_title = g["title"]
                break
        is_hidden = any(g.get("hidden") for g in groups)
        combined_entries = []

        for group in groups:
            archive_name = group["archive"]
            archive_dir = SOURCE_BASE / f"{archive_name}-exported"
            if not archive_dir.exists():
                print(f"  [MISSING] {archive_name}-exported")
                continue
            print(f"  → Archive: {archive_name} (prefix: '{prefix}')")
            toc = load_toc(archive_dir)
            orphans = find_orphans(archive_dir, toc)
            missing = find_missing_toc_files(archive_dir, toc)
            all_orphans += [f"{archive_name}/{o}" for o in orphans]
            all_missing += [f"{archive_name}/{m}" for m in missing]
            toc_entries = toc_to_file_tree(
                toc, archive_dir, archive_name, space_dir, space_assets_dir, prefix,
                                      cat_a_canonical, cat_b_canonical, shared_dir, shared_assets_dir)
            combined_entries.extend(toc_entries)
            if orphans:
                unsorted_prefix = f"{prefix}/_unsorted" if prefix else "_unsorted"
                for orphan in orphans:
                    src = archive_dir / "MD" / orphan
                    stem = Path(orphan).stem
                    out_rel = f"{unsorted_prefix}/{stem}.md"
                    out = space_dir / out_rel
                    convert_topic(src, archive_name, out, stem, space_dir, space_assets_dir,
                                      cat_a_canonical, cat_b_canonical, shared_dir, shared_assets_dir)
                    combined_entries.append((stem.replace("-", " ").title(), out_rel, []))
                total_pages += len(orphans)
            total_pages += len([e for e in flatten_toc(toc)])
            register_redirects(archive_name, space_name)

        if not is_hidden:
            summary_sections.append((group_title, combined_entries))

    _write_summary(space_dir, summary_sections)
    _write_gitbook_yaml(space_dir)
    print(f"  Done: {total_pages} pages")
    return {"space": space_name, "total_pages": total_pages,
            "orphans": all_orphans, "missing_files": all_missing}


def find_orphans(archive_dir, toc):
    toc_flat = flatten_toc(toc)
    toc_files = {Path(e["file"]).stem for e in toc_flat if "file" in e}
    md_dir = archive_dir / "MD"
    orphans = []
    if md_dir.exists():
        for f in md_dir.glob("*.md"):
            if f.stem not in toc_files:
                orphans.append(f.name)
    return orphans


def find_missing_toc_files(archive_dir, toc):
    toc_flat = flatten_toc(toc)
    missing = []
    for e in toc_flat:
        if "file" in e:
            src = archive_dir / "MD" / Path(e["file"]).name
            if not src.exists():
                missing.append(e["file"])
    return missing


def register_redirects(archive_name, space_name):
    slug_map = ARCHIVE_SLUG_MAP.get(archive_name, {})
    for slug, rel_path in slug_map.items():
        old_url = f"https://doc.apizee.com/articles/{archive_name}/{slug}"
        new_path = f"/{space_name}/{rel_path}"
        REDIRECTS.append((old_url, new_path))


def _write_summary(space_dir, sections):
    lines = ["# Summary", ""]
    for group_title, entries in sections:
        if group_title:
            lines.append(f"## {group_title}")
            lines.append("")
        lines.extend(entries_to_summary_lines(entries))
        lines.append("")
    (space_dir / "SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")


def _write_gitbook_yaml(space_dir):
    content = "root: ./\nstructure:\n  summary: SUMMARY.md\n"
    (space_dir / ".gitbook.yaml").write_text(content, encoding="utf-8")


# ============================================================
#  UNASSIGNED
# ============================================================
def copy_unassigned(assigned):
    unassigned_dir = OUTPUT_BASE / "_unassigned"
    count = 0
    for archive_name in get_all_exported_archives():
        if archive_name in assigned:
            continue
        src = SOURCE_BASE / f"{archive_name}-exported"
        dst = unassigned_dir / archive_name
        if src.exists():
            print(f"  [unassigned] {archive_name}")
            shutil.copytree(src, dst, dirs_exist_ok=True)
            count += 1
    print(f"\n[unassigned] {count} archives copied")
    return count


# ============================================================
#  WRITERS
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

## Archives non assignées

**Décision** : placées dans `_unassigned/` (non publiées comme espaces GitBook).

**Archives concernées** :
- `customer-engagement-user-en` (19 topics)
- `apizee-for-salesforce-publication-admin` (22 topics)

**Archives ignorées (ni migrées ni copiées)** :
- `customer-engagement-admin-en` — exclu explicitement de la migration.

---

## diag-help-desk-user

**Décision** : intégré dans l'espace `video-assistance` sous le groupe `Help Desk` (préfixe `help-desk/`).

**Justification** : Le contenu Diag Help Desk est complémentaire à la visio-assistance. Il n'a pas assez de volume pour justifier un espace GitBook autonome.

---

## Catégories de doublons (A / B / C)

- **Catégorie A** : topics plateforme → page canonique unique dans `faq/platform/`, redirect `content-ref` dans les sections produit.
- **Catégorie B** : onboarding commun → bloc partagé dans `shared/.gitbook/includes/`, appelé via `{% include %}` dans chaque section.
- **Catégorie C** : features produit-spécifiques → copie distincte par section, intentionnellement non fusionnée.

---

## Ancres propriétaires ClickHelp

**Décision** : supprimées lors de la conversion.

**Justification** : Auto-générées par ClickHelp, ne fonctionnent pas dans GitBook. Les liens perdent leur cible précise mais restent valides au niveau page.

---

## project-content-reuse

**Décision** : non migré comme espace GitBook.

**Justification** : Ce projet ne contient que des snippets partagés et des assets génériques. Les assets sont gérés via le mécanisme de déduplication SHA-256 de chaque espace.
"""
    out = OUTPUT_BASE / "decision.md"
    _safe_write(out, content)


def write_report(all_stats, qa, cat_a_canonical, cat_b_canonical, cat_c):
    lines = [
        "# Rapport de migration ClickHelp → GitBook",
        "",
        "## Volumétrie par espace",
        "",
        "| Espace | Pages converties | Orphelins | Fichiers manquants |",
        "| --- | --- | --- | --- |",
    ]
    total = 0
    for s in all_stats:
        total += s["total_pages"]
        lines.append(f"| `{s['space']}` | {s['total_pages']} | {len(s['orphans'])} | {len(s['missing_files'])} |")
    lines.append(f"| **Total** | **{total}** | | |")
    lines += [
        "",
        "## Catégories de doublons",
        "",
        f"- **Catégorie A** (plateforme) : {len(cat_a_canonical)} topics canoniques dans `faq/platform/`",
    ]
    for slug in sorted(cat_a_canonical):
        lines.append(f"  - `{slug}`")
    lines.append(f"- **Catégorie B** (onboarding) : {len(cat_b_canonical)} blocs partagés dans `shared/.gitbook/includes/`")
    for slug in sorted(cat_b_canonical):
        lines.append(f"  - `{slug}`")
    lines.append(f"- **Catégorie C** (produit-spécifiques) : {len(cat_c)} slugs dupliqués conservés séparément")
    lines += [
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
    if qa["broken_links"][:20]:
        lines += ["### Liens cassés (top 20)", ""]
        for bl in qa["broken_links"][:20]:
            lines.append(f"- `{bl.get('href','?')}` dans `{bl.get('file','?')}`")
        lines.append("")
    if qa["missing_assets"][:20]:
        lines += ["### Assets manquants (top 20)", ""]
        for ma in qa["missing_assets"][:20]:
            lines.append(f"- `{ma.get('ref','?')}` dans `{ma.get('file','?')}`")
        lines.append("")
    if qa["clickhelp_residue"][:20]:
        lines += ["### Résidus ClickHelp (top 20)", ""]
        for r in qa["clickhelp_residue"][:20]:
            lines.append(f"- Pattern `{r['pattern']}` dans `{r['file']}`")
        lines.append("")
    lines += [
        "",
        "## Prochaines étapes",
        "",
        "1. Valider l'échantillon de pages converties",
        "2. Importer espace par espace dans GitBook via Git Sync",
        "3. Configurer les redirections dans chaque `.gitbook.yaml`",
        "4. Basculer le DNS/CDN de doc.apizee.com",
    ]
    out = OUTPUT_BASE / "RAPPORT-migration.md"
    _safe_write(out, "\n".join(lines) + "\n")
    print(f"\n[report] RAPPORT-migration.md written")


# ============================================================
#  QA
# ============================================================
def run_qa(spaces_to_check):
    print("\n[QA] Running post-conversion checks...")
    qa = {
        "broken_links": [], "missing_assets": [], "empty_files": [],
        "bom_remaining": [], "clickhelp_residue": [], "total_md_files": 0,
    }
    dirs_to_check = []
    shared_dir = OUTPUT_BASE / "shared"
    if shared_dir.exists():
        dirs_to_check.append(shared_dir)
    for space_name in spaces_to_check:
        space_dir = OUTPUT_BASE / space_name
        if space_dir.exists():
            dirs_to_check.append(space_dir)
    for base_dir in dirs_to_check:
        for md in base_dir.rglob("*.md"):
            qa["total_md_files"] += 1
            content = md.read_bytes()
            if content.startswith(b"\xef\xbb\xbf"):
                qa["bom_remaining"].append(str(md))
            text = content.decode("utf-8", errors="replace")
            if len(text.strip()) == 0:
                qa["empty_files"].append(str(md))
            # Skip raw _unassigned/ copies for ClickHelp residue check
            is_unassigned = "_unassigned" in str(md)
            if not is_unassigned and "../Storage/" in text:
                qa["clickhelp_residue"].append({"file": str(md), "pattern": "../Storage/"})
            if not is_unassigned and "DXR.axd" in text:
                qa["clickhelp_residue"].append({"file": str(md), "pattern": "DXR.axd"})
            for m in re.finditer(r'{%\s*include\s+"([^"]+)"\s*%}', text):
                include_path = m.group(1)
                abs_path = (md.parent / include_path).resolve()
                if not abs_path.exists():
                    qa["broken_links"].append({"file": str(md), "href": include_path})
            for m in re.finditer(r'{%\s*content-ref\s+url="([^"]+)"\s*%}', text):
                ref_path = m.group(1)
                abs_path = (md.parent / ref_path).resolve()
                if not abs_path.exists():
                    qa["broken_links"].append({"file": str(md), "href": ref_path})
    for issue in QA_ISSUES:
        if issue["type"] == "broken_internal_link":
            qa["broken_links"].append(issue)
        elif issue["type"] == "missing_asset":
            qa["missing_assets"].append(issue)
    print(f"  {qa['total_md_files']} MD files checked")
    print(f"  Broken links: {len(qa['broken_links'])}")
    print(f"  Missing assets: {len(qa['missing_assets'])}")
    print(f"  Empty files: {len(qa['empty_files'])}")
    print(f"  BOM remaining: {len(qa['bom_remaining'])}")
    print(f"  ClickHelp residue: {len(qa['clickhelp_residue'])}")
    return qa


# ============================================================
#  MAIN
# ============================================================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--space", help="Convert only this space (e.g. faq)")
    parser.add_argument("--qa-only", action="store_true")
    args = parser.parse_args()

    GLOBAL_SLUG_MAP.clear()
    for v in ARCHIVE_SLUG_MAP.values():
        v.clear()
    ARCHIVE_SLUG_MAP.clear()
    ASSET_HASH_MAP.clear()
    REDIRECTS.clear()
    QA_ISSUES.clear()

    OUTPUT_BASE.mkdir(parents=True, exist_ok=True)

    if args.qa_only:
        qa = run_qa(list(SPACES.keys()))
        return

    print("\n[Phase 1] Building inventory...")
    inventory = build_inventory()
    write_inventory(inventory)

    print("\n[Phase 2] Analyzing categories A/B/C...")
    cat_a_canonical, cat_b_canonical, cat_c = analyze_categories(inventory)

    print("\n[Phase 3] Building global slug map...")
    build_global_slug_map(cat_a_canonical)

    shared_dir = OUTPUT_BASE / "shared"
    shared_assets_dir = shared_dir / ".gitbook" / "assets"
    shared_assets_dir.mkdir(parents=True, exist_ok=True)

    spaces_to_run = [args.space] if args.space else list(SPACES.keys())
    all_stats = []
    for space_name in spaces_to_run:
        if space_name not in SPACES:
            print(f"[ERROR] Unknown space: {space_name}")
            continue
        stats = convert_space(space_name, SPACES[space_name], cat_a_canonical, cat_b_canonical,
                              shared_dir, shared_assets_dir)
        all_stats.append(stats)

    print("\n[Phase 5] Copying unassigned archives...")
    assigned = get_assigned_archives()
    copy_unassigned(assigned)

    write_redirects()
    write_decision_md()
    qa = run_qa(spaces_to_run)
    if not args.space:
        write_report(all_stats, qa, cat_a_canonical, cat_b_canonical, cat_c)

    print("\n[done] Migration complete.")
    print(f"  Output: {OUTPUT_BASE}")

if __name__ == "__main__":
    main()
