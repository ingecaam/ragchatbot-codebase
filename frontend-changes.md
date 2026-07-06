# Frontend Code Quality Changes

## Overview

Added Prettier as the automatic code formatter for the frontend, applied
consistent formatting across all source files, and created npm scripts for
running quality checks.

---

## New Files

### `frontend/package.json`
Defines the frontend as a Node package and wires up Prettier with three npm
scripts:
- `npm run format` — formats all files in place
- `npm run format:check` — checks formatting without writing (CI-safe)
- `npm run quality` — alias for `format:check`

### `frontend/.prettierrc`
Prettier configuration enforcing consistent style across HTML, CSS, and JS:
- 2-space indentation
- Single quotes in JS/CSS
- Trailing commas where valid in ES5 (objects, arrays, function params)
- 80-character print width
- CSS-sensitive HTML whitespace handling

### `frontend/.prettierignore`
Excludes `node_modules/` from formatting.

---

## Modified Files

All three source files were reformatted to match the Prettier configuration.
No logic was changed — only whitespace and style.

### `frontend/index.html`
- Indentation: 4 spaces → 2 spaces throughout
- Long attribute lines (e.g. `data-question`, SVG attributes) wrapped to one
  attribute per line per Prettier's HTML formatter
- Void elements self-closed (`<meta ... />`, `<input ... />`, `<link ... />`)
- `<!DOCTYPE html>` lowercased to `<!doctype html>` (Prettier default)

### `frontend/script.js`
- Indentation: 4 spaces → 2 spaces throughout
- String literals changed from double quotes to single quotes
- Trailing commas added to multi-line object literals and function arguments
- Double blank lines collapsed to single blank lines
- Stale comment `// Removed removeMessage function...` removed
- Stale `console.log` debug calls in `loadCourseStats` removed
- Long lines broken at 80 characters (e.g. `addMessage(...)` call in
  `createNewSession`, `fetch(...).catch(...)` chain in `handleNewChat`)

### `frontend/style.css`
- Indentation: 4 spaces → 2 spaces throughout (including inside `@media` blocks)
- `transition` shorthand with multiple values expanded to multi-value format
  (Prettier puts each value on its own line for readability)
- `@keyframes bounce` selector list `0%, 80%, 100%` placed on separate lines
- Stale inline comment `/* Remove max-height... */` removed from `.course-titles`
- Single-line heading rules (`h1 { font-size: 1.5rem; }`) expanded to block form

---

## How to Use

Install dev dependencies (one-time):
```bash
cd frontend
npm install
```

Check formatting (no writes — safe for CI):
```bash
npm run quality
```

Auto-fix all formatting:
```bash
npm run format
```
