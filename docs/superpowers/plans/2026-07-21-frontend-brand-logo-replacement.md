# Frontend Brand Logo Replacement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the supplied Zhuque brand image into a real SVG and display that one Logo in the browser favicon, the application top bar, and the history sidebar without changing the existing brand text or behavior.

**Architecture:** Store one static, self-contained SVG in Vite's `public/` directory and reference it by its stable absolute public URL (`/brand-logo.svg`). The browser's favicon link, top-bar `<img>`, and sidebar `<img>` will all consume that exact URL, eliminating the existing duplicated favicon/source SVG files and raw-SVG runtime injection.

**Tech Stack:** Vue 3 SFCs, Vite 5 public assets, Vitest 2, pnpm.

## Global Constraints

- The SVG must be a genuine vector drawing; do not embed the provided PNG by base64 data, an `<image>` element, or another raster mechanism.
- Keep `朱雀投研智能体` text, existing application routing, API behavior, Pinia state, and interactions unchanged.
- Use `/brand-logo.svg` as the single visual source in the favicon, top bar, and sidebar.
- Preserve the dark-first XC visual system; do not introduce new dependencies.
- Do not start a browser or take screenshots; the user performs visual acceptance manually.
- Run only `pnpm` commands for the frontend.
- Do not run `git add`, `git commit`, `git push`, or other Git write operations.

---

## File Structure

| File | Change | Responsibility |
| --- | --- | --- |
| `agent-frontend/public/brand-logo.svg` | Create | One portable vector source for favicon and in-app branding. |
| `agent-frontend/public/favicon.svg` | Delete | Remove the superseded duplicate favicon artwork. |
| `agent-frontend/src/assets/logo.svg` | Delete | Remove the superseded component-only duplicate artwork. |
| `agent-frontend/index.html` | Modify | Point the browser favicon to the common public Logo. |
| `agent-frontend/src/layout/index.vue` | Modify | Replace the CSS-only gradient brand square in the top bar with the shared Logo image. |
| `agent-frontend/src/layout/components/AppSidebar.vue` | Modify | Replace raw SVG injection with the shared Logo image while retaining the sidebar title and collapse behavior. |
| `agent-frontend/tests/logo-mask.spec.js` | Modify | Guard the single-source asset contract and the three required integration points. |

### Task 1: Establish the single vector Logo asset

**Files:**
- Create: `agent-frontend/public/brand-logo.svg`
- Delete: `agent-frontend/public/favicon.svg`
- Delete: `agent-frontend/src/assets/logo.svg`
- Modify: `agent-frontend/tests/logo-mask.spec.js:5-33`

**Interfaces:**
- Consumes: the supplied brand image at `C:\Users\JDPC0200\Downloads\image-1784596267230.png` as the visual reference only.
- Produces: the public URL `/brand-logo.svg`, a standalone `viewBox="0 0 64 64"` SVG with no raster embedding, suitable for `<link rel="icon">` and `<img>` consumers.

- [ ] **Step 1: Replace the logo-source contract test with a failing test**

Replace `agent-frontend/tests/logo-mask.spec.js` with the following test. It intentionally expects the new asset before it exists.

```js
import { describe, expect, it } from 'vitest'
import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const frontendRoot = process.cwd()
const logoPath = resolve(frontendRoot, 'public/brand-logo.svg')
const indexHtml = readFileSync(resolve(frontendRoot, 'index.html'), 'utf8')
const layout = readFileSync(resolve(frontendRoot, 'src/layout/index.vue'), 'utf8')
const sidebar = readFileSync(resolve(frontendRoot, 'src/layout/components/AppSidebar.vue'), 'utf8')

describe('brand logo rendering', () => {
  it('uses one real SVG source for the favicon, top bar, and sidebar', () => {
    expect(existsSync(logoPath)).toBe(true)

    const logoSvg = readFileSync(logoPath, 'utf8')
    expect(logoSvg).toContain('<svg')
    expect(logoSvg).toContain('viewBox="0 0 64 64"')
    expect(logoSvg).not.toContain('<image')
    expect(logoSvg).not.toMatch(/data:image\//i)

    expect(indexHtml).toContain('href="/brand-logo.svg"')
    expect(layout).toContain('src="/brand-logo.svg"')
    expect(sidebar).toContain('src="/brand-logo.svg"')
    expect(sidebar).not.toContain("import logoSvg from '@/assets/logo.svg?raw'")

    expect(existsSync(resolve(frontendRoot, 'public/favicon.svg'))).toBe(false)
    expect(existsSync(resolve(frontendRoot, 'src/assets/logo.svg'))).toBe(false)
  })

  it('keeps the welcome orb independent from the brand logo', () => {
    const home = readFileSync(resolve(frontendRoot, 'src/views/home/index.vue'), 'utf8')
    expect(home).toContain("import orbSrc from '@/assets/ai-sphere.png'")
    expect(home).toContain('<img class="ir-welcome__orb" :src="orbSrc" alt="" aria-hidden="true" />')
  })
})
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run:

```bash
cd agent-frontend && pnpm vitest run tests/logo-mask.spec.js
```

Expected: FAIL because `public/brand-logo.svg` does not exist and the application still refers to the prior assets.

- [ ] **Step 3: Create the vector Logo and remove both prior duplicated assets**

Create `agent-frontend/public/brand-logo.svg` with this complete SVG. It uses only vector primitives and a transparent background, while retaining a dark cyan/purple investment-research visual language that remains legible at favicon size.

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-labelledby="title desc">
  <title id="title">朱雀投研智能体</title>
  <desc id="desc">抽象朱雀与上升数据曲线标志</desc>
  <defs>
    <linearGradient id="feather" x1="12" y1="50" x2="52" y2="12" gradientUnits="userSpaceOnUse">
      <stop stop-color="#22d3ee"/>
      <stop offset="1" stop-color="#8b5cf6"/>
    </linearGradient>
    <linearGradient id="wing" x1="18" y1="46" x2="47" y2="18" gradientUnits="userSpaceOnUse">
      <stop stop-color="#0e7490"/>
      <stop offset="1" stop-color="#4f46e5"/>
    </linearGradient>
  </defs>
  <path fill="url(#wing)" d="M11 47c8-2 13-7 17-15 3-6 7-11 15-14-4 5-5 9-4 13 2-4 6-8 12-10-5 6-7 12-7 19 0 8-6 14-15 14-8 0-14-3-18-7Z"/>
  <path fill="url(#feather)" d="M14 46c10-6 15-13 20-27 1-3 4-5 7-5 0 8-1 14-5 20 4-4 8-6 14-6-7 5-12 11-15 19-8 1-14 1-21-1Z"/>
  <path fill="#e2e8f0" d="M42 15c5 1 8 4 10 8-4-1-7 0-10 3-1-4-1-7 0-11Z"/>
  <circle cx="46.5" cy="20" r="1.5" fill="#020617"/>
  <path d="M17 51h31" fill="none" stroke="#22d3ee" stroke-linecap="round" stroke-width="3"/>
  <path d="m18 44 8-7 7 4 12-15" fill="none" stroke="#f8fafc" stroke-linecap="round" stroke-linejoin="round" stroke-width="3"/>
  <path d="m40 26 5-1-1 5" fill="none" stroke="#f8fafc" stroke-linecap="round" stroke-linejoin="round" stroke-width="3"/>
</svg>
```

Delete these files, rather than keeping alternate copies:

```text
agent-frontend/public/favicon.svg
agent-frontend/src/assets/logo.svg
```

- [ ] **Step 4: Run the focused test and verify the asset contract passes**

Run:

```bash
cd agent-frontend && pnpm vitest run tests/logo-mask.spec.js
```

Expected: FAIL only for the remaining integration assertions in `index.html`, `src/layout/index.vue`, and `AppSidebar.vue`; the SVG existence/raster-embedding assertions pass.

- [ ] **Step 5: Do not commit**

The repository rules explicitly prohibit Git write operations without a separate user request. Leave the successful asset and test changes unstaged.

### Task 2: Wire the common Logo into all three brand entry points

**Files:**
- Modify: `agent-frontend/index.html:5`
- Modify: `agent-frontend/src/layout/index.vue:5-8,117-123`
- Modify: `agent-frontend/src/layout/components/AppSidebar.vue:14,81-84,222-236`
- Modify: `agent-frontend/tests/logo-mask.spec.js:16-20`

**Interfaces:**
- Consumes: `/brand-logo.svg` created in Task 1.
- Produces: favicon and both in-app brand locations that use the exact same public URL; no raw SVG module import or `v-html` injection remains.

- [ ] **Step 1: Extend the currently failing test with semantic image assertions**

In the first test in `agent-frontend/tests/logo-mask.spec.js`, immediately after the three `src="/brand-logo.svg"` assertions, add:

```js
expect(layout).toContain('<img class="ir-brand__mark" src="/brand-logo.svg" alt="" aria-hidden="true" />')
expect(sidebar).toContain('<img class="ir-sider__logo" src="/brand-logo.svg" alt="" aria-hidden="true" />')
expect(layout).toContain('<span class="ir-brand__name">{{ title }}</span>')
expect(sidebar).toContain('<span class="ir-sider__brand">朱雀投研智能体</span>')
```

- [ ] **Step 2: Run the focused test and verify it still fails**

Run:

```bash
cd agent-frontend && pnpm vitest run tests/logo-mask.spec.js
```

Expected: FAIL because the favicon still points at `/favicon.svg`, the top bar is a CSS-only `<span>`, and the sidebar uses `v-html`.

- [ ] **Step 3: Update the favicon URL**

In `agent-frontend/index.html`, replace the current favicon line with:

```html
<link rel="icon" href="/brand-logo.svg" type="image/svg+xml" />
```

- [ ] **Step 4: Replace the top-bar CSS square with the shared Logo image**

In `agent-frontend/src/layout/index.vue`, replace:

```vue
<span class="ir-brand__mark" aria-hidden="true" />
```

with:

```vue
<img class="ir-brand__mark" src="/brand-logo.svg" alt="" aria-hidden="true" />
```

Replace the `.ir-brand__mark` rule with:

```css
.ir-brand__mark {
  width: 22px;
  height: 22px;
  flex: 0 0 auto;
  object-fit: contain;
}
```

Do not change `.ir-brand__name`, `.ir-brand__sub`, or their surrounding layout.

- [ ] **Step 5: Replace sidebar raw-SVG injection with the shared Logo image**

In `agent-frontend/src/layout/components/AppSidebar.vue`, replace:

```vue
<span class="ir-sider__logo" aria-hidden="true" v-html="logoSvg" />
```

with:

```vue
<img class="ir-sider__logo" src="/brand-logo.svg" alt="" aria-hidden="true" />
```

Delete this script import:

```js
import logoSvg from '@/assets/logo.svg?raw'
```

Replace the existing `.ir-sider__logo` and `.ir-sider__logo :deep(svg)` rules with this image-specific styling, preserving the existing size values from the deleted rule:

```css
.ir-sider__logo {
  width: 24px;
  height: 24px;
  flex: 0 0 auto;
  object-fit: contain;
}
```

Delete the `--zra-icon-bg`, `--zra-icon-border`, `--zra-icon-mark`, and `--zra-icon-accent` declarations that only existed to recolor the old inlined SVG. Do not alter the neighboring `.ir-sider__brand` rule or any collapse/hover event handlers.

- [ ] **Step 6: Run the focused Logo test**

Run:

```bash
cd agent-frontend && pnpm vitest run tests/logo-mask.spec.js
```

Expected: PASS with two passing assertions.

- [ ] **Step 7: Do not commit**

The repository rules explicitly prohibit Git write operations without a separate user request. Leave the successful integration changes unstaged.

### Task 3: Verify no behavior regression and package the public asset

**Files:**
- Verify only: `agent-frontend/tests/logo-mask.spec.js`
- Verify only: `agent-frontend/package.json`
- Verify only: `agent-frontend/dist/`

**Interfaces:**
- Consumes: the complete single-source asset and component wiring from Tasks 1–2.
- Produces: test/build evidence that Vite can package the SVG and existing frontend behavior remains unaffected.

- [ ] **Step 1: Run the complete frontend test suite**

Run:

```bash
cd agent-frontend && pnpm test
```

Expected: PASS. If a test fails because it asserts the removed `src/assets/logo.svg`, update only that assertion to expect `/brand-logo.svg`; do not alter business-flow expectations.

- [ ] **Step 2: Build the production frontend**

Run:

```bash
cd agent-frontend && pnpm build
```

Expected: command exits with code `0` and reports the production build output under `dist/`.

- [ ] **Step 3: Verify the packaged public Logo exists**

Run:

```bash
cd agent-frontend && test -f dist/brand-logo.svg
```

Expected: exit code `0`, confirming the Vite public asset was copied into the production package.

- [ ] **Step 4: Do not run browser validation or commit**

Do not run `pnpm dev`, browser automation, screenshots, or Git write commands. The user manually confirms the favicon, top bar, and sidebar rendering.

## Self-Review

- **Spec coverage:** Task 1 produces a true vector SVG with no raster embedding and removes duplicate sources. Task 2 applies that one URL to the favicon, title bar, and navigation/sidebar while preserving text and behavior. Task 3 covers the requested automated build/test validation and explicitly excludes browser verification.
- **Placeholder scan:** No TBD/TODO markers, implicit error-handling instructions, or unspecified code changes remain.
- **Type and naming consistency:** All consumers use the exact public URL `/brand-logo.svg`; all component classes and assertions match the template snippets in Task 2.
- **Project-constraint review:** The plan uses no dependencies, makes no API/business changes, uses pnpm exclusively, and omits the skill template’s Git commits because the repository instructions prohibit Git writes.
