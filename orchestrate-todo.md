# Documentation Improvement — Orchestrated Tasks

> Adapted for GitBook Markdown project (gitbook-export/ submodule).
> **Validation script**: `python3 scripts/validate-gitbook.py`
> Run `python3 scripts/validate-gitbook.py --help` for options.

## tasks

- [x] 1. Create a proper help center homepage
  branch: docs/homepage-hero
  files: gitbook-export/README.md, gitbook-export/.gitbook/
  done-when: python3 scripts/validate-gitbook.py --allow-cross-space && grep -q "How can we help" gitbook-export/README.md

- [ ] 2. Fix garbled FAQ product name "Diag Help Des****k"
  branch: docs/fix-faq-title
  files: gitbook-export/faq/**/*.md, gitbook-export/faq/SUMMARY.md
  done-when: python3 scripts/validate-gitbook.py --allow-cross-space && ! grep -ri "Diag Help Des" gitbook-export/faq/

- [ ] 3. Add legacy domain banner and version clarification
  branch: docs/legacy-banner
  files: gitbook-export/**/README.md
  done-when: python3 scripts/validate-gitbook.py --allow-cross-space && grep -r "apizeelegacy" gitbook-export/ | grep -v "legacy-banner" | grep -v "apizeelegacy.gitbook.io" | wc -l | grep -q "^0$"

- [ ] 4. Delete "Untitled" section and "Page" stub placeholders
  branch: docs/cleanup-placeholders
  files: gitbook-export/**/SUMMARY.md, gitbook-export/_unassigned/**
  done-when: python3 scripts/validate-gitbook.py --allow-cross-space && ! grep -r "## Untitled" gitbook-export/ && ! grep -r '^\s*\*\s*\[Page\]\s*$' gitbook-export/

- [ ] 5. Rename persona-based navigation to task-oriented labels
  branch: docs/rename-persona-nav
  files: gitbook-export/**/SUMMARY.md
  done-when: python3 scripts/validate-gitbook.py --allow-cross-space && ! grep -r "for-administrators\|for-agents\|for-guests" gitbook-export/

- [ ] 6. Create a top-level "Troubleshooting" section
  branch: docs/create-troubleshooting
  files: gitbook-export/troubleshooting/README.md, gitbook-export/**/SUMMARY.md
  done-when: python3 scripts/validate-gitbook.py --allow-cross-space && test -f gitbook-export/troubleshooting/README.md && grep -c "##" gitbook-export/troubleshooting/README.md | grep -q "[5-9]\|1[0-9]"

- [ ] 7. Create a top-level "Billing & Plans" section
  branch: docs/create-billing
  files: gitbook-export/billing-plans/README.md, gitbook-export/**/SUMMARY.md
  done-when: python3 scripts/validate-gitbook.py --allow-cross-space && test -f gitbook-export/billing-plans/README.md

- [ ] 8. Standardize all URLs to English (remove French slugs)
  branch: docs/standardize-urls
  files: gitbook-export/video-assistance-multi/**, gitbook-export/**/.gitbook.yaml
  done-when: python3 scripts/validate-gitbook.py --allow-cross-space && ! find gitbook-export -path '*pour-les-administrateurs*' -o -path '*pour-les-agents*' | grep -q .

- [ ] 9. Flatten URL hierarchy to 3 levels max
  branch: docs/flatten-urls
  files: gitbook-export/**/SUMMARY.md
  done-when: python3 scripts/validate-gitbook.py --allow-cross-space && python3 -c "import re, sys, pathlib; errs=[]; [errs.append(f'{s}: >3 levels') for s in pathlib.Path('gitbook-export').rglob('SUMMARY.md') if max([len(re.findall(r'  ', l)) for l in s.read_text().splitlines() if l.startswith('*')]+[0]) > 2]; sys.exit(len(errs))"

- [ ] 10. Embed tutorial videos inline (not external links)
  branch: docs/inline-videos
  files: gitbook-export/**
  done-when: python3 scripts/validate-gitbook.py --allow-cross-space && ! grep -ri "Watch the tutorial" gitbook-export/ | grep -v "{%"

- [ ] 11. Enable "Last updated" dates on all articles
  branch: docs/last-updated
  files: gitbook-export/**/.gitbook.yaml
  done-when: python3 scripts/validate-gitbook.py --allow-cross-space && grep -r "lastUpdated\|last_updated" gitbook-export/ | wc -l | grep -q "[1-9]"

- [ ] 12. Add "Related articles" footer template to all articles
  branch: docs/related-articles
  files: gitbook-export/**/README.md, gitbook-export/**/*.md
  done-when: python3 scripts/validate-gitbook.py --allow-cross-space && test -f gitbook-export/shared/.gitbook/includes/related-articles.md && grep -r "{% include.*related-articles" gitbook-export/ | wc -l | grep -q "[5-9]\|1[0-9]"

- [ ] 13. Standardize FAQ titles to second person / imperative
  branch: docs/standardize-faq-titles
  files: gitbook-export/faq/**/*.md
  done-when: python3 scripts/validate-gitbook.py --allow-cross-space && ! grep -ri "^# .*I do not" gitbook-export/faq/ && ! grep -ri "^# .*I forgot" gitbook-export/faq/ && ! grep -ri "^# .*I cannot" gitbook-export/faq/

- [ ] 14. Build unified "Getting Started" track
  branch: docs/getting-started-track
  files: gitbook-export/getting-started/**/*.md, gitbook-export/**/SUMMARY.md
  done-when: python3 scripts/validate-gitbook.py --allow-cross-space && test -d gitbook-export/getting-started && test -f gitbook-export/getting-started/README.md && grep -q "getting-started" gitbook-export/faq/SUMMARY.md

- [ ] 15. Add status page link to site header / homepage
  branch: docs/status-page-link
  files: gitbook-export/**/README.md
  done-when: python3 scripts/validate-gitbook.py --allow-cross-space && grep -ri "status page\|system status\|service status" gitbook-export/ | wc -l | grep -q "[1-9]"

- [ ] 16. Create annotated diagrams for key conceptual topics
  branch: docs/concept-diagrams
  files: gitbook-export/.gitbook/assets/diagrams/
  done-when: python3 scripts/validate-gitbook.py --allow-cross-space && test $(find gitbook-export -path "*/diagrams/*" -name "*.png" -o -path "*/diagrams/*" -name "*.svg" | wc -l) -ge 3

- [ ] 17. Publish a public changelog / release notes page
  branch: docs/changelog
  files: gitbook-export/changelog/README.md, gitbook-export/**/SUMMARY.md
  done-when: python3 scripts/validate-gitbook.py --allow-cross-space && test -f gitbook-export/changelog/README.md

- [ ] 18. Add system requirements / compatibility article review
  branch: docs/compatibility-update
  files: gitbook-export/**/compatibility*.md, gitbook-export/**/browser*.md
  done-when: python3 scripts/validate-gitbook.py --allow-cross-space && ! grep -ri "chrome.*v4[0-9]\|firefox.*v4[0-9]" gitbook-export/

- [ ] 19. Add FAQ schema markup (JSON-LD) to FAQ articles
  branch: docs/faq-schema
  files: gitbook-export/faq/**/*.md
  done-when: python3 scripts/validate-gitbook.py --allow-cross-space && grep -ri "faqpage\|json+ld\|application/ld+json" gitbook-export/faq/ | wc -l | grep -q "[1-9]"

- [ ] 20. Conduct native-English copyedit pass on titles and headings

## Run Summary — 2026-06-16

- ✅ Done: docs/homepage-hero
- ⏳ Pending: docs/fix-faq-title, docs/legacy-banner, docs/cleanup-placeholders, docs/rename-persona-nav, docs/create-troubleshooting, docs/create-billing, docs/standardize-urls, docs/flatten-urls, docs/inline-videos, docs/last-updated, docs/related-articles, docs/standardize-faq-titles, docs/getting-started-track, docs/status-page-link, docs/concept-diagrams, docs/changelog, docs/compatibility-update, docs/faq-schema, docs/copyedit-titles
- ⚠️ Blocked: (none yet)
- Baseline validation: ✅ Clean (0 hard errors). The 7 pre-existing broken image refs were fixed in commit `962123c`.
- Commits on master: 1 new (`0ec9fa2` — homepage hero)
- Pushed to GitHub: no
  branch: docs/copyedit-titles
  files: gitbook-export/**/*.md
  done-when: python3 scripts/validate-gitbook.py --allow-cross-space && ! grep -ri "Website\|Web browser\|I do not manage to" gitbook-export/ | grep "^gitbook-export" | grep ".md:" | wc -l | grep -q "^0$"
