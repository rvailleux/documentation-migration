import os
import re
import shutil

BASE = "/home/romain/code/documentation-migration/gitbook-export"
SHARED_INCLUDES = os.path.join(BASE, "shared", ".gitbook", "includes")

def find_images(content):
    return re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', content)

def resolve_image_from_space(space, img_rel):
    """Resolve image path from space root given a relative path from a file inside it."""
    # img_rel like ../../.gitbook/assets/foo.png from a file 2-3 levels deep
    # We need to find where it lands inside the space.
    # Heuristic: check if path contains .gitbook/assets/
    if ".gitbook/assets/" in img_rel:
        basename = os.path.basename(img_rel)
        return os.path.join(BASE, space, ".gitbook", "assets", basename)
    return None

def main():
    for fname in os.listdir(SHARED_INCLUDES):
        if not fname.endswith('.md'):
            continue
        include_path = os.path.join(SHARED_INCLUDES, fname)
        with open(include_path, 'r', encoding='utf-8') as f:
            content = f.read()
        images = find_images(content)
        if not images:
            continue
        # Find which spaces use this include by scanning files
        spaces_using = set()
        for root, dirs, files in os.walk(BASE):
            for file in files:
                if file.endswith('.md') and file != fname:
                    fp = os.path.join(root, file)
                    with open(fp, 'r', encoding='utf-8') as f:
                        txt = f.read(500)
                    if fname in txt and '{% include' in txt:
                        rel = os.path.relpath(fp, BASE)
                        space = rel.split(os.sep)[0]
                        spaces_using.add(space)
        if not spaces_using:
            continue
        for alt, img_rel in images:
            if img_rel.startswith('http'):
                continue
            basename = os.path.basename(img_rel)
            # find source image somewhere in any space
            source = None
            for space in spaces_using:
                candidate = os.path.join(BASE, space, ".gitbook", "assets", basename)
                if os.path.exists(candidate):
                    source = candidate
                    break
            if not source:
                # search all spaces
                for space in os.listdir(BASE):
                    candidate = os.path.join(BASE, space, ".gitbook", "assets", basename)
                    if os.path.exists(candidate):
                        source = candidate
                        break
            if not source:
                print(f"SKIP {fname}: cannot find source for {basename}")
                continue
            for space in spaces_using:
                target = os.path.join(BASE, space, ".gitbook", "assets", basename)
                if not os.path.exists(target):
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    shutil.copy2(source, target)
                    print(f"COPIED {basename} -> {space}/.gitbook/assets/")

if __name__ == "__main__":
    main()
