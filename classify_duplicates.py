import json
import re
import os

def extract_space_from_path(path):
    parts = path.split('/')
    try:
        idx = parts.index('gitbook-export')
        return parts[idx + 1]
    except (ValueError, IndexError):
        return 'unknown'

def strip_frontmatter(text):
    if text.startswith('---'):
        end_frontmatter = text.find('---', 3)
        if end_frontmatter != -1:
            return text[end_frontmatter + 3:].strip()
    return text.strip()

def classify_group(group):
    first_file = group['file_paths'][0]
    with open(first_file, 'r', encoding='utf-8') as f:
        actual = f.read()
    
    content = strip_frontmatter(actual)
    
    # 1. stub-include: only {% include "..." %} (possibly multiple, with whitespace)
    include_only_pattern = re.compile(r'^(\s*\{\%\s*include\s+"[^"]+"\s*\%\}\s*)+$', re.MULTILINE)
    if include_only_pattern.match(content):
        return 'stub-include'
    
    # 2. stub-content-ref: only heading(s) + content-ref blocks (+ includes/whitespace)
    temp = re.sub(r'\{\%\s*content-ref[^\%]*\%\}.*?\{\%\s*endcontent-ref\s*\%\}', '', content, flags=re.DOTALL)
    temp = re.sub(r'\{\%\s*include\s+"[^"]+"\s*\%\}', '', temp)
    temp = temp.strip()
    lines = temp.splitlines()
    only_headings_and_empty = True
    for line in lines:
        stripped = line.strip()
        if stripped == '':
            continue
        if not re.match(r'^#{1,6}\s+', stripped):
            only_headings_and_empty = False
            break
    
    has_content_ref = bool(re.search(r'\{\%\s*content-ref', content))
    if only_headings_and_empty and has_content_ref:
        return 'stub-content-ref'
    
    return 'real-content'


def generate_include_name(group):
    """Derive a kebab-case name from the first heading in content, falling back to file names."""
    first_file = group['file_paths'][0]
    with open(first_file, 'r', encoding='utf-8') as f:
        raw = f.read()
    content = strip_frontmatter(raw)
    # Find first heading
    m = re.search(r'^#{1,6}\s+(.+)$', content, re.MULTILINE)
    if m:
        heading = m.group(1).strip()
        # Remove markdown formatting, links, etc.
        heading = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', heading)  # remove links
        heading = re.sub(r'[^\w\s-]', '', heading).strip().lower()
        heading = re.sub(r'[-\s]+', '-', heading)
        if len(heading) > 60:
            heading = heading[:60].rstrip('-')
        if heading:
            return heading
    
    # Fallback to file names
    names = [os.path.splitext(os.path.basename(p))[0] for p in group['file_paths']]
    from os.path import commonprefix
    common = commonprefix(names).strip('-_')
    if common:
        name = common.strip('-_')
    else:
        name = min(names, key=len)
    name = re.sub(r'[^\w\s-]', '', name).strip().lower()
    name = re.sub(r'[-\s]+', '-', name)
    if len(name) > 60:
        name = name[:60].rstrip('-')
    return name


def main():
    with open('/home/romain/code/documentation-migration/duplicate_hashes_report.json', 'r') as f:
        data = json.load(f)
    
    stub_includes = []
    stub_content_refs = []
    real_contents = []
    
    for group in data['exact_duplicate_groups']:
        category = classify_group(group)
        spaces = sorted(set(extract_space_from_path(p) for p in group['file_paths']))
        
        if category == 'stub-include':
            stub_includes.append({
                'hash': group['hash'],
                'file_count': len(group['file_paths']),
                'content_preview': group['content_preview'][:100],
                'spaces_affected': spaces
            })
        elif category == 'stub-content-ref':
            stub_content_refs.append({
                'hash': group['hash'],
                'file_count': len(group['file_paths']),
                'content_preview': group['content_preview'][:100],
                'spaces_affected': spaces
            })
        else:
            first_file = group['file_paths'][0]
            with open(first_file, 'r') as f:
                raw = f.read()
            content = strip_frontmatter(raw)
            preview = content[:100]
            suggested_name = generate_include_name(group)
            real_contents.append({
                'hash': group['hash'],
                'file_count': len(group['file_paths']),
                'suggested_include_name': suggested_name,
                'content_preview': preview,
                'spaces_affected': spaces
            })
    
    output = {
        'stub_include_summary': {
            'count': len(stub_includes),
            'top_5_examples': stub_includes[:5]
        },
        'stub_content_ref_summary': {
            'count': len(stub_content_refs),
            'top_5_examples': stub_content_refs[:5]
        },
        'real_content_groups': real_contents,
        'totals': {
            'stub_include': len(stub_includes),
            'stub_content_ref': len(stub_content_refs),
            'real_content': len(real_contents)
        }
    }
    
    with open('/home/romain/code/documentation-migration/duplicates_categorized.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"Done. stub-include: {len(stub_includes)}, stub-content-ref: {len(stub_content_refs)}, real-content: {len(real_contents)}")

if __name__ == '__main__':
    main()
