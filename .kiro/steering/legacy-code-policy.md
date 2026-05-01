---
inclusion: always
---

# Legacy Code Policy

## `.legacy` Folder — Read-Only Reference

Whenever the workspace contains a `.legacy` folder, it means this project originated from a **fork of an upstream project**. The `.legacy` folder holds the original source code for **reference purposes only**.

## Rules

- **NEVER modify any file inside `.legacy`** — it is strictly read-only
- **NEVER delete or move files** inside `.legacy`
- **NEVER create new files** inside `.legacy`
- The `.legacy` folder may be read and consulted to understand original behavior, logic, or structure
- All new code must be written **outside** of `.legacy`
- When migrating or adapting logic from `.legacy`, copy and adapt it to the appropriate location in the project — do not edit the original

## Purpose

The `.legacy` folder exists to:
- Preserve the original upstream code as a reference baseline
- Allow comparison between the fork's evolution and the original
- Serve as documentation of the starting point of the project

## Summary

| Action | Allowed |
|---|---|
| Read files in `.legacy` | ✅ Yes |
| Copy logic from `.legacy` to new location | ✅ Yes |
| Modify files in `.legacy` | ❌ No |
| Delete files in `.legacy` | ❌ No |
| Create files in `.legacy` | ❌ No |
