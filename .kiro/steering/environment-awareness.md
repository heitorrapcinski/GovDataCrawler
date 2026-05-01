---
inclusion: always
---

# Environment Awareness

Before executing any shell commands, always detect the operating system and use the appropriate shell syntax.

## OS Detection

Check the system context provided in the conversation or use available tools to determine the OS:
- **Windows** → use PowerShell syntax
- **Linux / macOS** → use Bash syntax

## Command Reference

| Action | PowerShell (Windows) | Bash (Linux/macOS) |
|---|---|---|
| List files | `Get-ChildItem` | `ls -la` |
| Remove file | `Remove-Item file.txt` | `rm file.txt` |
| Remove directory | `Remove-Item -Recurse -Force dir` | `rm -rf dir` |
| Copy file | `Copy-Item src dst` | `cp src dst` |
| Create directory | `New-Item -ItemType Directory -Path dir` | `mkdir -p dir` |
| View file | `Get-Content file.txt` | `cat file.txt` |
| Find in files | `Select-String -Path *.txt -Pattern "x"` | `grep -r "x" .` |
| Command separator | `;` | `&&` |
| Environment variable | `$env:VAR` | `$VAR` |

## Rules

- **Never use `&&` on Windows** — use `;` instead
- **Never use `cd` in shell commands** — use the `cwd` parameter in tool calls
- **Always adapt commands** to the detected OS before executing
- When in doubt, prefer PowerShell-compatible syntax for Windows environments
