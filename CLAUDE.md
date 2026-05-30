# CLAUDE.md — Project Rules

---

## Epic Plan Implementation Notes

Keep these clean and concise. Bullet points as needed for changes or decisions made. 

## Frontend HTML IDs

Add a **unique, descriptive `id`** to **every** HTML element in the frontend so that:
- Changes can be directed to specific elements in the future.
- E2E tests and automation can target elements reliably.
- ARIA relationships (e.g. `aria-labelledby`, `aria-controls`) stay consistent.

### Requirement: IDs on every element

**Every** HTML element must have an `id`. No exceptions. This includes:

- **Landmarks**: `main`, `header`, `nav`, `footer`, `section` (e.g. `id="app-main"`, `id="site-header"`, `id="bottom-nav"`).
- **Interactive elements**: buttons, submit inputs, toggles, links (e.g. `id="login-submit"`, `id="mobile-menu-toggle"`).
- **Form controls**: inputs, selects, textareas (match `htmlFor` on labels).
- **Key sections**: cards, lists, dialogs, banners (e.g. `id="connection-card"`, `id="verification-banner"`).
- **Regions targeted by `aria-controls` or `aria-describedby`**: the controlled region must have the matching `id`.
- **Wrappers and layout**: every `div`, `span`, and other container (e.g. `id="login-form-wrapper"`, `id="card-inner"`, `id="hero-text"`).
- **Headings, paragraphs, lists, list items**: e.g. `id="page-title"`, `id="intro-paragraph"`, `id="feature-list"`, `id="feature-item-0"`.
- **Images, icons, SVGs**: e.g. `id="hero-image"`, `id="nav-home-icon"`.

If it's in the DOM and you render it, it gets an `id`.

---

## React Philosophy

**When in doubt, split into smaller components to keep things clean and tight.** A
component that is getting long, juggling several responsibilities, or hard to read
at a glance is a signal to break it apart. Prefer many small, focused, well-named
components over a few large ones — they are easier to read, test, reuse, and reason
about.

---

## Naming Conventions

> Applies to: all source files

Names — classes, variables, functions, methods — must be **immediately understandable** to someone reading the code for the first time. Follow these rules:

### Be descriptive, not abbreviated

Write the full word. Never shorten unless the abbreviation is universally understood (e.g. `url`, `id`, `api`).

| Avoid | Prefer |
|---|---|
| `usr` | `user` |
| `cfg` | `config` |
| `btn` | `button` |
| `mgr` | `manager` |
| `idx` | `index` |
| `val` | `value` |
| `e` (in catch blocks) | `error` |
| `cb` | `callback` |
| `fn` | `function` |
| `req`, `res` | `request`, `response` |

### Use natural human language over technical jargon

Prefer words a non-engineer would recognise. When two words mean roughly the same thing, pick the more natural one.

| Avoid | Prefer |
|---|---|
| `resolve` | `get` |
| `hydrate` | `fill`, `load`, `populate` |
| `mutate` | `change`, `update` |
| `invoke` | `call`, `run` |
| `instantiate` | `create` |
| `consume` | `use`, `read`, `process` |
| `emit` | `send`, `trigger` |
| `propagate` | `pass`, `forward` |
| `traverse` | `walk`, `loop through` |

### Name things after what they are, not what they do technically

A function that loads a user's profile should be `getUserProfile`, not `resolveUserEntity`. A variable holding the selected brand should be `selectedBrand`, not `activeBrandInstance`.

### Boolean names should read as a yes/no question

Prefix booleans with `is`, `has`, `can`, `should`, or `did`.

| Avoid | Prefer |
|---|---|
| `loading` | `isLoading` |
| `error` (boolean) | `hasError` |
| `visible` | `isVisible` |
| `userLoggedIn` | `isUserLoggedIn` |

---

## UI/UX Design Guide

Follow the project's design conventions (visual style, color palette, typography, layout, components, and UX flow) defined in [LinkShrink UI/UX Design Guide](../.development-docs/LinkShrink_UI_UX_Guide.md). Consult it before adding or changing frontend UI.
