#!/usr/bin/env python3
"""
Runner for convert.py that works around the __main__ stdout suppression in this sandbox.
Usage:
    python3 scripts/run_migration.py [--space SPACE] [--qa-only]
"""
import sys
import importlib.util
import argparse
from pathlib import Path

def load_convert():
    spec = importlib.util.spec_from_file_location(
        "convert",
        Path(__file__).parent / "convert.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--space", help="Convert only this space (e.g. faq)")
    parser.add_argument("--qa-only", action="store_true")
    args = parser.parse_args()

    conv = load_convert()

    # Reset global state
    conv.GLOBAL_SLUG_MAP.clear()
    conv.ARCHIVE_SLUG_MAP.clear()
    conv.ASSET_HASH_MAP.clear()
    conv.REDIRECTS.clear()
    conv.QA_ISSUES.clear()

    conv.OUTPUT_BASE.mkdir(parents=True, exist_ok=True)

    if args.qa_only:
        qa = conv.run_qa(list(conv.SPACES.keys()))
        conv.write_report([], qa)
        return

    # Phase 1: build slug map
    print("\n[Phase 1] Building global slug map…")
    conv.build_global_slug_map()

    spaces_to_run = [args.space] if args.space else list(conv.SPACES.keys())
    all_stats = []

    for space_name in spaces_to_run:
        if space_name not in conv.SPACES:
            print(f"[ERROR] Unknown space: {space_name}")
            continue
        stats = conv.convert_space(space_name, conv.SPACES[space_name])
        all_stats.append(stats)

    conv.write_redirects()
    conv.write_decision_md()

    qa = conv.run_qa(spaces_to_run)

    if not args.space:
        conv.write_report(all_stats, qa)

    print("\n✓ Migration complete.")
    print(f"  Output: {conv.OUTPUT_BASE}")

if __name__ == "__main__":
    main()
