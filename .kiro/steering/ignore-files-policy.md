# Ignore Files Policy

## Always Keep `.gitignore` and `.dockerignore` Up to Date

Whenever an agent creates, moves, deletes, or modifies files or directories in the project, it must evaluate whether `.gitignore` and `.dockerignore` need to be updated accordingly.

## When to Update

Update `.gitignore` when:
- New build output directories are introduced (e.g., `dist/`, `build/`, `out/`)
- New dependency directories are added (e.g., `node_modules/`, `vendor/`)
- New environment or secret files are created (e.g., `.env`, `.env.local`, `*.key`, `*.pem`)
- New cache or temp directories appear (e.g., `.cache/`, `tmp/`, `*.log`)
- New IDE or tool-specific files are generated (e.g., `.idea/`, `.vscode/`, `*.swp`)
- New test coverage or report directories are created (e.g., `coverage/`, `.nyc_output/`)
- Any file or folder that should not be tracked by version control is introduced

Update `.dockerignore` when:
- New directories exist that should not be copied into Docker images (e.g., `node_modules/`, `vendor/`, `.git/`, `tests/`, `docs/`)
- New build artifacts or local config files are added that are irrelevant inside containers
- New secret or environment files are created that must never be baked into images
- The project structure changes in a way that affects what Docker needs to copy

## Rules

- **Never leave untracked sensitive files without a `.gitignore` entry** — secrets, credentials, and local config must always be ignored
- **Never copy unnecessary files into Docker images** — keep images lean by updating `.dockerignore` proactively
- **Both files must be reviewed together** — a change that affects one usually affects the other
- **If `.dockerignore` does not exist** and Docker-related files are present in the project, create it
- **If `.gitignore` does not exist**, create it before committing any new files

## File Locations

Both files must live at the project root (or at the root of each relevant Docker build context):

```
.gitignore
.dockerignore
```

## Example Entries

### `.gitignore`
```
# Dependencies
node_modules/
vendor/

# Build output
dist/
build/

# Environment
.env
.env.*
!.env.example

# Logs
*.log
logs/

# Cache
.cache/
tmp/
```

### `.dockerignore`
```
.git/
.kiro/
node_modules/
vendor/
dist/
tests/
*.log
.env
.env.*
README.md
CHANGELOG.md
```

## Summary

| Trigger | Action |
|---|---|
| New dependency folder added | Add to both `.gitignore` and `.dockerignore` |
| New build output created | Add to both |
| New secret/env file created | Add to `.gitignore` immediately |
| New test/docs folder added | Add to `.dockerignore` |
| File moved to new location | Re-evaluate both files |
| Docker build context changes | Update `.dockerignore` |
