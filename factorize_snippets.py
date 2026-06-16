import json
import os
import re
import shutil
import sys

BASE = "/home/romain/code/documentation-migration/gitbook-export"
SHARED_INCLUDES = os.path.join(BASE, "shared", ".gitbook", "includes")
SHARED_ASSETS = os.path.join(BASE, "shared", ".gitbook", "assets")

def rel_path(from_file, to_file):
    """Return relative path from from_file's directory to to_file."""
    from_dir = os.path.dirname(from_file)
    return os.path.relpath(to_file, from_dir)

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def find_images(content):
    # Match ![](path) or ![alt](path)
    return re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', content)

def resolve_image_path(md_file, img_rel):
    """Resolve relative image path from md_file to absolute."""
    md_dir = os.path.dirname(md_file)
    return os.path.normpath(os.path.join(md_dir, img_rel))

def space_from_path(rel_path_from_base):
    parts = rel_path_from_base.split(os.sep)
    if len(parts) > 0:
        return parts[0]
    return None

def spaces_for_group(group):
    return set(group.get("spaces_affected", []))

def main():
    with open("/home/romain/code/documentation-migration/duplicates_categorized.json", 'r', encoding='utf-8') as f:
        data = json.load(f)

    groups = data.get("real_content_groups", [])
    # Filter: cross-space (>=2 spaces) and >=6 files
    target_groups = [
        g for g in groups
        if len(g.get("spaces_affected", [])) >= 2 and g.get("file_count", 0) >= 6
    ]
    print(f"Target groups to factorize: {len(target_groups)}")
    for g in target_groups:
        print(f"  - {g['suggested_include_name']} ({g['file_count']} files, spaces: {g['spaces_affected']})")

    # Also include some high-value groups with 4-5 files cross-space if they impact many spaces
    extra = [
        g for g in groups
        if len(g.get("spaces_affected", [])) >= 3 and g.get("file_count", 0) >= 4
        and g not in target_groups
    ]
    print(f"Extra high-space groups: {len(extra)}")
    for g in extra:
        print(f"  - {g['suggested_include_name']} ({g['file_count']} files, spaces: {g['spaces_affected']})")

    all_targets = target_groups + extra
    print(f"\nTotal to process: {len(all_targets)}")

    processed = 0
    skipped = []
    for group in all_targets:
        hash_val = group["hash"]
        with open("/home/romain/code/documentation-migration/duplicate_hashes_report.json", 'r', encoding='utf-8') as f:
            report = json.load(f)
        # find matching group in report
        file_paths = []
        for dup_group in report.get("exact_duplicate_groups", []):
            if dup_group["hash"] == hash_val:
                file_paths = dup_group["file_paths"]
                break
        if not file_paths:
            skipped.append((group, "No file paths found in report"))
            continue

        # Choose canonical file (first in list)
        canonical = file_paths[0]
        content = read_file(canonical)
        include_name = group["suggested_include_name"] + ".md"
        include_path = os.path.join(SHARED_INCLUDES, include_name)

        # Avoid collisions
        counter = 1
        original_include_name = include_name
        while os.path.exists(include_path):
            include_name = f"{group['suggested_include_name']}-{counter}.md"
            include_path = os.path.join(SHARED_INCLUDES, include_name)
            counter += 1

        # Analyze images
        images = find_images(content)
        missing_images = []
        for alt, img_rel in images:
            if img_rel.startswith("http"):
                continue
            abs_img = resolve_image_path(canonical, img_rel)
            if not os.path.exists(abs_img):
                print(f"  WARN: Image not found in canonical: {abs_img}")
                continue
            # Check in all target spaces
            target_spaces = spaces_for_group(group)
            for space in target_spaces:
                space_img = os.path.join(BASE, space, ".gitbook", "assets", os.path.basename(img_rel))
                if not os.path.exists(space_img):
                    missing_images.append((abs_img, space_img, space, os.path.basename(img_rel)))

        if missing_images:
            print(f"  Group {group['suggested_include_name']} has {len(missing_images)} missing image copies. Will copy them.")
            for src, dst, space, basename in missing_images:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                print(f"    Copied {basename} to {space}/.gitbook/assets/")

        # Write include
        write_file(include_path, content)
        print(f"  Created include: {include_path}")

        # Replace each duplicated file
        for fp in file_paths:
            rel = rel_path(fp, include_path)
            # Check if file has frontmatter that differs from canonical? They are identical per hash.
            # We replace with just the include
            include_line = f'{{% include "{rel}" %}}\n'
            write_file(fp, include_line)
            print(f"    Replaced: {fp}")

        processed += 1

    print(f"\nDone. Processed {processed} groups. Skipped {len(skipped)}.")
    if skipped:
        for g, reason in skipped:
            print(f"  SKIPPED {g['suggested_include_name']}: {reason}")

if __name__ == "__main__":
    main()
