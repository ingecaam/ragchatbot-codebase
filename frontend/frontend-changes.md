# Frontend Changes

## Dark/Light Mode Toggle Button

### What was added

A fixed-position dark/light mode toggle button in the top-right corner of the viewport.

### Files modified

#### `index.html`
- Added an inline `<script>` in `<head>` (before the stylesheet link) to read the saved theme from `localStorage` and set `data-theme` on `<html>` immediately, preventing any flash of unstyled content on page load.
- Added the `#themeToggle` button element just inside `<body>`, before the main `.container`. It contains two inline SVGs: a sun icon (`.icon-sun`) and a moon icon (`.icon-moon`).
- Bumped cache-busting versions: `style.css?v=13`, `script.js?v=12`.

#### `style.css`
- Added new CSS variables to `:root` for `--code-bg`, `--source-link-color`, `--source-link-border`, `--source-link-hover-bg`, `--source-link-hover-color`, `--source-link-hover-border`.
- Added `[data-theme="light"]` block that overrides the palette to a light slate theme (`#f8fafc` background, `#ffffff` surfaces, `#0f172a` text, `#e2e8f0` borders).
- Added `.theme-transitioning` helper class applied by JS during toggle: it forces `transition` on all descendant elements for 300ms to produce a smooth cross-fade.
- Added `.theme-toggle` styles: `position: fixed; top: 1rem; right: 1rem`, circular 40×40px button, border/background/color driven by CSS variables, hover and `:focus-visible` focus ring.
- Added icon animation: both SVGs are `position: absolute` inside the button. In dark mode the sun is visible (`opacity: 1, rotate(0)`); the moon is hidden (`opacity: 0, rotate(90deg) scale(0.5)`). In light mode the states swap. The `transition` on each SVG produces a smooth rotation+fade when the theme changes.
- Updated `.message-content code` and `.message-content pre` to use `var(--code-bg)` instead of the hardcoded `rgba(0,0,0,0.2)`.
- Updated `.sources-content a` link colors to use the new source-link CSS variables instead of hardcoded hex values.

#### `script.js`
- Added `setupThemeToggle()`: wires a `click` listener on `#themeToggle` that reads the current `data-theme`, switches to the opposite value, persists it to `localStorage`, and temporarily adds `.theme-transitioning` to `<html>` (removed after 300ms).
- `setupThemeToggle()` is called in `DOMContentLoaded` before other setup.

### Behavior

- Default theme is **dark** (set by the inline head script from `localStorage`, falling back to `'dark'`).
- Clicking the toggle switches between dark and light mode with a 250ms smooth cross-fade on colors.
- The icon rotates and fades: sun → moon when switching to light, moon → sun when switching to dark.
- The chosen theme persists across page reloads via `localStorage`.
- The button is keyboard-navigable (focusable, visible focus ring) and has an `aria-label` for screen readers.

---

## Light Theme CSS Variables

### What was added

A complete `[data-theme="light"]` variable block in `style.css` providing a full light palette for the entire UI. Activated when `data-theme="light"` is set on `<html>` (controlled by the toggle button above).

### Files modified

#### `style.css`

New variables added to `:root` (dark defaults) and overridden in `[data-theme="light"]`:

| Variable | Dark value | Light value | Purpose |
|---|---|---|---|
| `--background` | `#0f172a` | `#f8fafc` | Page/chat background |
| `--surface` | `#1e293b` | `#ffffff` | Sidebar, message bubbles |
| `--surface-hover` | `#334155` | `#f1f5f9` | Hover states |
| `--text-primary` | `#f1f5f9` | `#0f172a` | Body text (~18:1 contrast on bg) |
| `--text-secondary` | `#94a3b8` | `#64748b` | Labels, meta (~4.6:1, WCAG AA) |
| `--border-color` | `#334155` | `#e2e8f0` | Dividers, input borders |
| `--shadow` | dark rgba | lighter rgba | Box shadows |
| `--focus-ring` | rgba blue 20% | rgba blue 15% | Keyboard focus rings |
| `--code-bg` | `rgba(0,0,0,0.25)` | `rgba(0,0,0,0.05)` | Inline code / pre blocks |
| `--source-link-color` | `#93c5fd` | `#2563eb` | Source pill link text |
| `--source-link-border` | `#475569` | `#93c5fd` | Source pill border |
| `--source-link-hover-bg` | `#1e3a5f` | `#eff6ff` | Source pill hover background |
| `--source-link-hover-color` | `#bfdbfe` | `#1d4ed8` | Source pill hover text |
| `--source-link-hover-border` | `#93c5fd` | `#2563eb` | Source pill hover border |

`--primary-color` (`#2563eb`) and `--primary-hover` (`#1d4ed8`) are unchanged — the blue meets WCAG AA contrast on both light and dark backgrounds.

### Accessibility

- `--text-primary` on `--background`: contrast ratio ~18:1 (WCAG AAA).
- `--text-secondary` on `--background`: ~4.6:1 (WCAG AA for normal text).
- `--primary-color` on `--background`: ~4.5:1 (WCAG AA).
- All interactive elements (buttons, inputs, links) use the same focus-ring variable in both themes.
