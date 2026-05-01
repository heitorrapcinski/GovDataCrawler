---
inclusion: always
---

# Version Control Workflow

Every spec (feature or bugfix) follows a strict Git workflow. These rules apply to all spec-driven work — no exceptions.

## 1. Branch Creation (First Action)

Create and checkout a branch **before any code change**. Never commit directly to `main` or `master`.

Branch name format:
```
{type}-{year}.{sequential}
```
- `{type}`: `feature` or `bugfix`
- `{year}`: 4-digit year from the spec identifier
- `{sequential}`: 6-digit zero-padded number from the spec identifier

Example — for spec `2026.000001.[1.0.0-SNAPSHOT]-glpi-microservices-backend`:
```
git checkout -b feature-2026.000001
```

## 2. Version Bump to SNAPSHOT (Immediately After Branch Creation)

After creating the branch and before any implementation, bump the project version to the next SNAPSHOT version and commit it.

Version increment rules:
- **Feature**: increment **minor** version → `{major}.{minor+1}.0-SNAPSHOT`
- **Bugfix**: increment **patch** version → `{major}.{minor}.{patch+1}-SNAPSHOT`

Examples starting from `1.0.0`:
- Feature → `1.1.0-SNAPSHOT`
- Bugfix → `1.0.1-SNAPSHOT`

Search the entire codebase and replace **all** version references. Common files (non-exhaustive): `composer.json`, `package.json`, `pom.xml`, `build.gradle`, `build.gradle.kts`, `version.php`, `VERSION`, `.env`, any config or manifest file containing the version string.

Commit the version bump immediately:
```
git commit -m "chore: bump version to {new-version}-SNAPSHOT"
```

Example:
```
git commit -m "chore: bump version to 1.1.0-SNAPSHOT"
```

## 3. Commit Convention (Per Task)

After completing each task, commit using this message format:
```
{year}.{sequential}.{task-number}: <short description>
```
- `{task-number}`: the task number as-is from `tasks.md` (e.g., `1`, `2`, `3`)
- Description: imperative mood, lowercase, no period

Example:
```
git commit -m "2026.000001.1: scaffold project structure"
git commit -m "2026.000001.2: implement ticket entity and repository"
```

## 4. Version Control Task (Mandatory Last Task)

The **last task** in every `tasks.md` must be a version control and release task. Include it verbatim:

```markdown
- [ ] Version control and release
  - [ ] Ensure all previous tasks are complete and tests pass
  - [ ] Remove SNAPSHOT suffix from all version references in the codebase
  - [ ] Commit the version bump: "release: {version} - {short-description}"
  - [ ] Merge branch into main/master
  - [ ] Apply Git tag: {version} (without SNAPSHOT)
  - [ ] Push branch, merge, and tag to remote
```

Do not omit, reorder, or rename this task.

## 5. SNAPSHOT Removal (Before Merge)

Before merging into `main`, search the entire codebase and replace all occurrences of the SNAPSHOT version with the release version:
- `1.0.0-SNAPSHOT` → `1.0.0`
- `1.1.0-SNAPSHOT` → `1.1.0`
- `1.0.1-SNAPSHOT` → `1.0.1`

Files to check (non-exhaustive): `composer.json`, `package.json`, `pom.xml`, `build.gradle`, `version.php`, `VERSION`, `build.gradle.kts`, `.env`, any config or manifest file containing the version string.

Use a project-wide search to ensure no SNAPSHOT references remain.

## 6. Merge and Tag

Execute in this exact order:
```
git checkout main
git merge --no-ff {branch-name}
git tag -a "{version}" -m "release: {version} - {short-description}"
git push origin main --tags
```

- `{branch-name}`: the full branch name (e.g., `feature-2026.000001`)
- `{version}`: the final version without SNAPSHOT (e.g., `1.0.0`)
- `{short-description}`: kebab-case summary matching the spec directory name
- Always use `--no-ff` to preserve merge history

## Rules Summary

| Rule | Detail |
|---|---|
| No direct commits to main | Always work on a feature or bugfix branch |
| Branch first | Branch must be created before any code change |
| One commit per task | Each task gets its own commit using the task number as-is (not zero-padded) |
| SNAPSHOT removal is mandatory | All SNAPSHOT suffixes must be removed before merge |
| Tag matches release version | Tag must be the clean version (no SNAPSHOT) |
| Version control task is mandatory | Must be the last task in every `tasks.md` |
| Merge uses `--no-ff` | Preserve branch history in the merge commit |
