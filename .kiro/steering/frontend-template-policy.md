---
inclusion: always
---

# Frontend Template Policy

## `.frontend-template` Folder — Read-Only Design Reference

The `.frontend-template` folder contains the original React + Tailwind CSS dashboard template used as the visual and structural foundation for `frontend-app/`. It is the single source of truth for UI patterns, component design, and visual consistency.

## Rules

- **NEVER modify any file inside `.frontend-template`** — it is strictly read-only
- **NEVER delete or move files** inside `.frontend-template`
- **NEVER create new files** inside `.frontend-template`
- The `.frontend-template` folder may be read and consulted at any time to understand component structure, styling patterns, and layout conventions

## Purpose

The `.frontend-template` folder exists to:
- Serve as the canonical reference for all UI component design and styling
- Ensure visual consistency across `frontend-app/` by providing proven patterns to follow
- Provide ready-to-use components, icons, and page layouts that can be adapted into `frontend-app/`
- Prevent visual drift by giving agents a clear baseline to compare against

## How to Use the Template

When implementing or modifying UI in `frontend-app/`:

1. **Check the template first** — before creating a new component or page, look for an existing implementation in `.frontend-template/src/` that solves the same problem
2. **Copy and adapt** — copy the relevant component from `.frontend-template/` into `frontend-app/src/` and adapt it to the project's needs (API integration, routing, auth, etc.)
3. **Preserve visual patterns** — maintain the same Tailwind CSS classes, spacing, color schemes, and responsive breakpoints used in the template
4. **Reuse UI primitives** — the template's `components/ui/` folder contains buttons, modals, tables, badges, dropdowns, and other primitives that define the design system — always prefer these over custom implementations
5. **Follow layout conventions** — sidebar, header, and page layout patterns in `.frontend-template/src/layout/` define the application shell — respect their structure
6. **Use template icons** — when a new icon is needed, check `.frontend-template/src/icons/` first before adding external icons

## Template Structure Reference

| Path | Description |
|---|---|
| `src/components/ui/` | Design system primitives (Button, Modal, Table, Badge, Dropdown, etc.) |
| `src/components/form/` | Form elements (Input, TextArea, Select, Switch, Checkbox, etc.) |
| `src/components/charts/` | Chart components (Bar, Line) using ApexCharts |
| `src/components/tables/` | Table layout examples |
| `src/components/common/` | Shared utilities (PageMeta, Breadcrumb, ComponentCard, etc.) |
| `src/components/header/` | Header with notifications, user dropdown, and theme toggle |
| `src/layout/` | Application shell (Sidebar, Header, Layout, Backdrop) |
| `src/pages/` | Full page examples (Dashboard, Auth, Forms, Charts, Tables, UI Elements) |
| `src/icons/` | SVG icon library with React component exports |
| `src/context/` | Theme and Sidebar context providers |
| `src/index.css` | Global styles and Tailwind CSS configuration |

## Summary

| Action | Allowed |
|---|---|
| Read files in `.frontend-template` | ✅ Yes |
| Copy and adapt components to `frontend-app` | ✅ Yes |
| Use as visual reference for styling decisions | ✅ Yes |
| Modify files in `.frontend-template` | ❌ No |
| Delete files in `.frontend-template` | ❌ No |
| Create files in `.frontend-template` | ❌ No |
| Ignore template patterns when building UI | ❌ No |
