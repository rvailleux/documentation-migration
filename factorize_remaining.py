import json
import os
import re
import shutil
import hashlib

BASE = "/home/romain/code/documentation-migration/gitbook-export"
SHARED_INCLUDES = os.path.join(BASE, "shared", ".gitbook", "includes")

def file_hash(path):
    with open(path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

def rel_path(from_file, to_file):
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
    return re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', content)

def resolve_image_path(md_file, img_rel):
    md_dir = os.path.dirname(md_file)
    return os.path.normpath(os.path.join(md_dir, img_rel))

def space_from_path(rel_path_from_base):
    parts = rel_path_from_base.split(os.sep)
    if len(parts) > 0:
        return parts[0]
    return None

def already_factorized(file_paths):
    """Check if all files in group are already just an include."""
    for fp in file_paths:
        with open(fp, 'r', encoding='utf-8') as f:
            txt = f.read().strip()
        if not txt.startswith('{% include'):
            return False
    return True

def main():
    with open("/home/romain/code/documentation-migration/duplicates_categorized.json", 'r', encoding='utf-8') as f:
        data = json.load(f)

    with open("/home/romain/code/documentation-migration/duplicate_hashes_report.json", 'r', encoding='utf-8') as f:
        report = json.load(f)

    groups = data.get("real_content_groups", [])
    # Process all remaining groups with >= 2 files, excluding already processed
    target_groups = []
    for g in groups:
        if g.get("file_count", 0) < 2:
            continue
        # find file paths via hash
        hash_val = g["hash"]
        file_paths = []
        for dup_group in report.get("exact_duplicate_groups", []):
            if dup_group["hash"] == hash_val:
                file_paths = dup_group["file_paths"]
                break
        if not file_paths:
            continue
        if already_factorized(file_paths):
            continue
        target_groups.append((g, file_paths))

    print(f"Remaining groups to factorize: {len(target_groups)}")
    for g, fps in target_groups[:10]:
        print(f"  - {g['suggested_include_name']} ({len(fps)} files)")

    processed = 0
    for g, file_paths in target_groups:
        canonical = file_paths[0]
        content = read_file(canonical)
        include_name = g["suggested_include_name"] + ".md"
        include_path = os.path.join(SHARED_INCLUDES, include_name)

        counter = 1
        while os.path.exists(include_path):
            include_name = f"{g['suggested_include_name']}-{counter}.md"
            include_path = os.path.join(SHARED_INCLUDES, include_name)
            counter += 1

        images = find_images(content)
        missing_images = []
        target_spaces = set()
        for fp in file_paths:
            rel = os.path.relpath(fp, BASE)
            sp = rel.split(os.sep)[0] if rel else None
            if sp:
                target_spaces.add(sp)

        for alt, img_rel in images:
            if img_rel.startswith("http"):
                continue
            abs_img = resolve_image_path(canonical, img_rel)
            if not os.path.exists(abs_img):
                print(f"  WARN: Image not found in canonical: {abs_img}")
                continue
            basename = os.path.basename(img_rel)
            for space in target_spaces:
                space_img = os.path.join(BASE, space, ".gitbook", "assets", basename)
                if not os.path.exists(space_img):
                    missing_images.append((abs_img, space_img, space, basename))

        if missing_images:
            for src, dst, space, basename in missing_images:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                print(f"    Copied {basename} -> {space}/.gitbook/assets/")

        write_file(include_path, content)
        print(f"  Created include: {include_name}")

        for fp in file_paths:
            rel = rel_path(fp, include_path)
            include_line = f'{{% include "{rel}" %}}\n'
            write_file(fp, include_line)
            print(f"    Replaced: {os.path.relpath(fp, BASE)}")
        processed += 1

    print(f"\nDone. Processed {processed} groups.")

if __name__ == "__main__":
    main()
