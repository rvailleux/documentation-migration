# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The ClickHelp→GitBook migration is **complete** (1,096 pages converted, 0 broken links, 0 missing assets). This repository now manages the live GitBook mono-repo under `gitbook-export/`. The day-to-day work is editorial — fixing content, improving cross-references, updating screenshots, and syncing changes to GitBook via GitHub.

- **Do not rerun the migration script** (`scripts/convert.py`) unless the user explicitly requests it.
- **Do not commit `.env`** — it contains live API keys and tokens.

## Repository Layout

| Path | Purpose |
|------|---------|
| `gitbook-export/` | **GitBook mono-repo** (git-tracked, pushed to GitHub for Git Sync) |
| `gitbook-export/.gitbook/` | Per-space config (`assets/`, `includes/`) |
| `gitbook-export/shared/` | Shared includes and assets referenced by multiple spaces |
| `gitbook-export/_unassigned/` | Orphaned content not assigned to a published space |
| `.env` | GitBook API key + GitHub PAT (**repo root; DO NOT COMMIT**) |
| `scripts/convert.py` | Legacy migration script (frozen unless explicitly asked) |
| `PROMPT-migration-gitbook.md` | Original migration specification (French) |
| `gitbook-export/decision.md` | Editorial decisions taken during migration |
| `gitbook-export/RAPPORT-migration.md` | Last-run QA report and volumetrics |
| `gitbook-export/README.md` | Human-facing repo intro for contributors |

## Git Workflow (`gitbook-export/`)

All git operations happen **inside** `gitbook-export/` (the `.git/` directory is there, not at the repo root).

```bash
cd gitbook-export/

# Daily workflow
git status
git add -A
git commit -m "fix: ..."
git push origin master
```

- **Remote:** `git@github.com:rvailleux/docs.git`
- **Branch:** `master`
- **Git Sync:** Configured on all spaces but awaiting the GitBook GitHub app installation (one-click manual step, see `.env`). After the app is installed, pushes will automatically sync to GitBook.

> **Never `rm -rf gitbook-export/`** — it lives on a Windows-mounted CIFS share; Linux cannot delete Windows-created files. Overwrite files in place instead.

## GitBook API & GitHub CLI

Credentials live in `.env` at the repo root. Load them before API or CLI calls:

```bash
# From inside gitbook-export/
export $(grep -v '^#' ../.env | xargs)
```

### GitBook API

Authenticate requests with the header `Authorization: Bearer $GITBOOK_API_KEY`. Use `$GITBOOK_ORG_ID` for organization-scoped operations and individual `$SPACE_ID` values (see mapping below) for space-scoped operations.

### GitHub CLI (`gh`)

The `gh` CLI uses `$GITHUB_FINE_GRAINED_PAT` or `$GITHUB_OAUTH_TOKEN`. Target repo is `rvailleux/docs`.

```bash
gh auth status
gh repo view rvailleux/docs
gh pr list
gh pr create --title "..." --body "..."
```

## Space-to-Directory Mapping

| Space | `gitbook-export/` folder | Space ID (for API calls) |
|-------|--------------------------|--------------------------|
| FAQ | `faq/` | `1VOp8peyy1K4iSCkmeAM` |
| Video Assistance | `video-assistance/` | `uuE6D1BWLXQZZvYIYyYC` |
| Embed | `embed/` | `XH6kwaH8vDkuYEnwhsAF` |
| Multi-participant Assistance | `video-assistance-multi/` | `j0vKAXamawxejMo2xtpP` |
| Meetings | `meetings/` | `QvcFlXIvB4rm9rWnMUoF` |
| Telehealth | `telehealth/` | `XMurrUZVH5WAKckcJRRd` |
| Salesforce | `salesforce/` | `3Q0H4t76pLjcJWctIBRd` |
| Genesys | `genesys/` | `KgZ8sXCpeG85FPndOp2q` |
| ServiceNow | `servicenow/` | `UxiBx7vA0tJuSlEVazhl` |

## Content Editing Conventions

### Hints

Four styles are supported: `info`, `success`, `warning`, `danger`.

```markdown
{% hint style="info" %}
This is an info block.
{% endhint %}
```

### Includes (reusable content)

Place shared blocks in a space's `.gitbook/includes/` directory. Reference them with a path **relative to the current `.md` file** (not the repo root).

```markdown
{% include "../../.gitbook/includes/my-block.md" %}
```

Limitation: included content does **not** appear in search results of spaces that reference it (only in the parent space where the file lives). This is acceptable for short onboarding topics but unsuitable for long FAQ pages.

Shared includes live at `shared/.gitbook/includes/` and can be referenced cross-space with relative paths such as `../../shared/.gitbook/includes/foo.md`.

### Content-refs (page embeds)

Use `content-ref` to embed a reference to another page:

```markdown
{% content-ref url="../../faq/platform/forgot-password.md" %}
[Reset your password](../../faq/platform/forgot-password.md)
{% endcontent-ref %}
```

The inner link text and the `url` parameter are both required and must point to the same target.

### `.gitbook.yaml` (per-space config)

```yaml
root: ./
structure:
  readme: README.md
  summary: SUMMARY.md
redirects:
  old-page-slug: new-folder/page.md
```

- `root` is relative to the space folder.
- Redirect keys are **without leading slashes** (e.g. `previous/page: new-folder/page.md`).
- GitBook resolves redirects in this order: auto-generated → space-level (`.gitbook.yaml`) → site-level.

### `SUMMARY.md`

Standard GitBook summary file using Markdown headings and bullet lists:

```markdown
# Summary

## For agents
* [About video assistance](agents/about-apizee-video-assistance.md)
  * [Quick invitation](agents/create-a-ticket-quick-invitation.md)
```

### Content blocks (tabs, etc.)

```markdown
{% tabs %}
{% tab title="Tab A" %}
Content for tab A
{% endtab %}
{% tab title="Tab B" %}
Content for tab B
{% endtab %}
{% endtabs %}
```

### Cross-space links

Links between spaces in the same monorepo use **relative file paths** from the current `.md` file. For example, a page in `video-assistance/agents/foo.md` linking to a FAQ topic uses `../../faq/platform/bar.md`.

### Page frontmatter (YAML metadata)

GitBook reads YAML frontmatter at the very top of `.md` files. The `---` block must appear before any markdown content.

Supported fields:
- **`description`** — SEO text and preview snippets.
- **`icon`** — Font Awesome icon name (e.g. `book-open`, `bolt`).
- **`hidden`** — Set to `true` to exclude the page from the sidebar.
- **`layout`** — Controls page chrome visibility (`width`, `title.visible`, `tableOfContents.visible`, etc.).
- **`tags`** — YAML list of strings; `primary: true` marks the primary tag.
- **`vars`** — Key-value pairs for page-specific template variables.

Example:
```markdown
---
description: "Reset your Apizee account password"
icon: key
hidden: false
layout:
  tableOfContents:
    visible: true
---
```

## Folder & File Organization (per space)

- **Folders become collapsible sections** in the sidebar. GitBook recommends **capping nesting at 3 levels**.
- **`README.md` inside a folder** becomes the **index/landing page** for that folder.
- **`SUMMARY.md`** defines the explicit sidebar order. If omitted, GitBook infers structure from the filesystem (not recommended for production).
- **Hidden pages** — pages with `hidden: true` in frontmatter are reachable by direct URL but do not appear in the sidebar. Used for `contextual-help/`.
- **`.gitbook/assets/`** — Images placed here are referenced with relative paths from the current `.md` file.
- **`.gitbook/includes/`** — Files here are pulled into pages via `{% include %}` and should generally be excluded from `SUMMARY.md`.
- **URL slugs** — Derived from the file path relative to `root`. `agents/start-a-session.md` becomes `/agents/start-a-session`.

## CIFS / Windows-Mount Constraints

`gitbook-export/` and `scripts/` live on a Windows SMB share mounted into the Linux sandbox.

### 1. Linux cannot delete Windows-created files
`rm -rf gitbook-export` will fail with "Operation not permitted". The correct strategy is **overwrite in place**.

### 2. CIFS dentry cache: newly-created directories are invisible to `open()`
After `mkdir()`, the Linux VFS dentry cache for the *parent* directory can be stale. `convert.py` works around this with `_safe_write()`, which flushes ancestors via `os.listdir()` before retrying a write. If writing files from scratch (not via `convert.py`), you may need a similar flush step.

### 3. Page-cache split between Windows tools and Linux bash
The Windows-side file tools (Read / Write / Edit) and the Linux bash process maintain **separate page caches**. After the Windows side writes a file, bash may read a stale version.

**Mitigation**: always verify the actual on-disk state from bash (`wc -l`, `tail`, `cat`) rather than trusting the Read tool's view. To fix a stale bash cache, write the corrected content **from bash** using Python or `echo`.

## Legacy Migration

The conversion pipeline in `scripts/convert.py` is idempotent and can technically be rerun, but **doing so without explicit user approval risks overwriting manual editorial fixes** that have been made directly in `gitbook-export/`. If the user asks to re-run it, verify they understand this trade-off. `PROMPT-migration-gitbook.md` retains the full original specification.
