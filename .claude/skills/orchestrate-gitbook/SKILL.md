---
name: orchestrate-gitbook
description: This skill should be used when the user runs "/orchestrate-gitbook <file>" for a GitBook / Markdown documentation project. Works through a todo file sequentially, one task at a time, dispatching sub-agents in git worktrees for branch-based changes or implementing inline for simple edits. Validates with content checks (grep, file existence, link integrity, markdown lint) instead of npm/tsc. Supports GitHub PR workflow.
---

# Orchestrate (GitBook / Markdown Edition)

Work through a todo file sequentially — one task at a time — dispatching a sub-agent (or implementing directly) per task, merging results, and looping until all tasks are done. No human intervention needed. Designed for pure Markdown/GitBook documentation projects.

## Invocation

```
/orchestrate-gitbook <path-to-todo-file>
```

Example: `/orchestrate-gitbook orchestrate-todo.md`

## Todo File Format

The todo file is the single source of truth. Read it at start, update it continuously.

```markdown
# Documentation Sprint

## merge-order
gitbook-export/README.md, gitbook-export/**/SUMMARY.md, gitbook-export/**/.gitbook.yaml

## tasks

- [ ] Create a proper help center homepage
  branch: docs/homepage-hero
  files: gitbook-export/README.md, gitbook-export/.gitbook/
  done-when: grep -q "How can we help" gitbook-export/README.md

- [ ] Fix garbled FAQ product name
  branch: docs/fix-faq-title
  files: gitbook-export/faq/**/*.md
  done-when: grep -ri "Diag Help Des" gitbook-export/faq/ returns empty
```

### Status Markers

| Marker | Meaning |
|--------|---------|
| `- [ ]` | Pending — not started |
| `- [~]` | WIP — agent dispatched |
| `- [x]` | Done — branch merged |
| `- [!]` | Blocked — failed after retries |

Update the marker in the file immediately when status changes.

## Orchestrator Workflow

```
Read todo file → Pre-flight check → Pick next pending task
    → Mark [~] → Run task (sub-agent or inline)
    → Validate → Valid? → Merge → Mark [x] → /clear context → Any pending? → loop back
                        ↓ no
                    Retries left? → retry
                        ↓ no
                    Mark [!] → /clear context → Any pending? → loop back
                                                      ↓ no
                                              Final integration test → Write summary
```

**Key rules:**
- One task at a time. Never dispatch the next task until the current one is merged or marked blocked.
- Clear context between every task. Run `/clear` after marking a task `[x]` or `[!]`, before picking the next `- [ ]` task. This prevents context window bloat over long runs.

## Step-by-Step

### 1. Read the todo file

Parse the file passed as argument. Extract:
- `merge-order` section (optional glob patterns for merge sequencing)
- All tasks with their `branch`, `files`, and `done-when` criteria

### 2. Pre-flight check

Before dispatching anything, run inside `gitbook-export/`:

```bash
cd gitbook-export/
git status --short          # must be clean — no uncommitted changes
```

Then run the documentation baseline validation:

```bash
python3 ../scripts/validate-gitbook.py --allow-cross-space
```

This validates: unclosed GitBook tags, broken images, broken content-refs, broken includes, invalid YAML frontmatter, and SUMMARY link integrity.

If **errors** are found, stop and report. Do not proceed with a broken base. Cross-space image warnings (`--allow-cross-space`) are expected on legacy migration projects and do not block the pipeline.

### 3. Pick next task + mark WIP

Read the todo file (re-read it fresh each iteration — do not rely on memory). Find the **first** `- [ ]` task.

1. Update its marker to `- [~]` in the file immediately
2. Execute the task (sub-agent or inline — see §4)
3. Do not pick the next task until this one is merged (`- [x]`) or blocked (`- [!]`)

**Loop**: after resolving a task, go back to step 3 and pick the next `- [ ]` task. Keep looping until no `- [ ]` tasks remain.

### 4. Sub-agent vs inline execution

**Use a sub-agent** when the task has a `branch:` field (requires isolated worktree work).

**Implement inline** (directly in the main context) when the task has no `branch:` field or is a simple scripting/config task.

#### Sub-agent prompt template

```
You are working in the gitbook-export/ directory of a GitBook documentation project.

## Task
<paste task block from todo file>

## Constraint
Only touch files listed in `files:`. Do not modify any other files in gitbook-export/.

## Execution
1. invoke the `write-for-gitbook` skill first to load the full GitBook syntax and editorial conventions.
2. Read the current state of all files in `files:`.
3. Plan the edit(s) needed to fulfill the task, following write-for-gitbook conventions (frontmatter, custom blocks, SUMMARY links, includes, content-refs, etc.).
4. Implement using Write, Edit, or Bash tools. Edit Markdown files in-place.
   - Ensure all GitBook custom blocks are properly opened and closed.
   - Use correct frontmatter (description, icon, hidden, layout, vars).
   - Use relative paths for internal links and images.
   - If new files are needed, create them with correct GitBook syntax.
   - If moving/renaming files, use `git mv` and update SUMMARY.md / cross-links.
5. After edits, run `cd gitbook-export/ && git add -A && git commit -m "<task description>"` to create the branch commit.

## Report
When done, output exactly:
---RESULT---
status: success|failure
branch: <branch name>
files_modified: <comma-separated list>
validation: <pass|fail>
error_summary: <if failure, concise description>
---END---
```

**Inline execution for simple edits:**
When no `branch:` is specified, directly edit the file(s) in the main context. This is suitable for:
- Global search/replace operations (command `sed`)
- Frontmatter additions across files
- Simple content insertions
- `gitbook-export/` file moves and renames

After inline edits, commit directly on master: `cd gitbook-export/ && git add -A && git commit -m "docs: <task description>"`

### 5. Validate each result

When an agent returns, do NOT trust its self-report. Re-verify inside `gitbook-export/`:

```bash
cd gitbook-export/

# Run the task's done-when criterion (exact command from todo file)
# Then validate GitBook syntax integrity
python3 ../scripts/validate-gitbook.py --allow-cross-space
```

Pass = `done-when` returns success AND validation script exits 0. Anything else = failure.

### 6. Retry logic (max 2 retries per task)

On failure, dispatch again with:
```
Previous attempt failed.
Error: <exact error output from validation>
Focus on fixing these specific errors. Do not rewrite working parts.
Retry budget: this is attempt <N> of 2.
```

After 2 retries: mark `- [!]` in file, move on.

### 7. Merge

Merge immediately after a task passes validation — do not accumulate completed branches.

```bash
cd gitbook-export/
git merge --no-ff <branch> -m "merge: <task description>"
```

After each merge, re-run the full syntax validation (same as §5). If new syntax errors appear, fix them before the next merge.

Mark `- [x]` in file immediately after successful merge.

**After marking `- [x]`, immediately re-read the todo file and loop back to §3** to pick the next `- [ ]` task. Keep going until no `- [ ]` tasks remain.

For inline tasks (no branch), skip the merge step — just mark `- [x]` after successful done-when validation.

### 7b. Context reset (mandatory between tasks)

After marking a task `- [x]` or `- [!]`, **always clear the context before starting the next task**:

```
/clear
```

Then re-read the todo file fresh and continue from §3. This is non-negotiable — skipping it causes context window overflow on long todo lists and pollutes sub-agent prompts with stale task details.

### 8. Final integration test

After all branches are merged or marked blocked:

```bash
cd gitbook-export/

# Ensure working tree is clean after all merges
git status --short

# Run full content validation
python3 ../scripts/validate-gitbook.py --allow-cross-space --report-json

# Optionally push to GitHub
git push origin master
```

### 9. Write summary to todo file

Append to the bottom of the todo file:

```markdown
## Run Summary — <date>

- ✅ Done: docs/homepage-hero, docs/fix-faq-title, ...
- ⚠️ Blocked: docs/flatten-urls — content-ref unclosed in embed/README.md (line 42)
- Final validation: <N> syntax issues, <M> broken links
- Commits on master: <count>
- Pushed to GitHub: yes|no
```

## GitHub PR Workflow (Optional)

If the project uses GitHub for Git Sync with GitBook, create a PR instead of direct merge:

After a task passes validation (step 5), instead of `git merge`:

```bash
cd gitbook-export/

# Ensure GitHub CLI is authenticated
gh auth status

# Push the branch
git push origin <branch>

# Create PR
gh pr create --title "<task description>" --body "Automated documentation task from orchestrate-gitbook" --base master

# The PR is then merged manually or via gh merge
# Mark task - [x] only after PR is merged
```

This is useful when GitBook GitHub Sync is active — pushing to master triggers automatic GitBook sync.

## Resilience Rules

**Never hang.** If stuck: document and move on.

**Never trust self-reports.** Always re-run validation yourself.

**Never merge a failing branch.** A single bad merge can introduce syntax errors across the entire GitBook site.

**File is ground truth.** Any state you hold in memory is secondary to what's written in the todo file. Re-read it if context is unclear.

**Retry budget is per-task.** 2 retries max. Burning retries on a lost cause blocks everything else.

## Worktree Setup (required)

Ensure `.claude/settings.json` has:
```json
{
  "worktree": {
    "symlinkDirectories": [".gitbook/assets", "shared"]
  }
}
```

This prevents each worktree from duplicating shared assets and includes directories.

## Done-When Validation Patterns

For Markdown/GitBook projects, use these patterns in `done-when`:

| Check | Command |
|-------|---------|
| File exists | `test -f <path>` |
| File contains text | `grep -q "text" <path>` |
| File does NOT contain | `! grep -q "text" <path>` |
| No broken relative images | All `![](...)` resolve from `.md` location |
| SUMMARY references exist | All `* [Title](path)` files exist |
| `.gitbook.yaml` valid | `python3 -c "import yaml; yaml.safe_load(open('<path>'))"` |

## Example Todo File

See format above. Minimum required per task: `branch` or `inline`, `files`, `done-when`.
The `merge-order` section is optional but recommended when tasks share editable boundaries (e.g., multiple articles whose SUMMARY ordering matters).
