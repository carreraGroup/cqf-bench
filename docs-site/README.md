# CQF Bench documentation site

Public documentation for [CQF Bench](https://github.com/carreraGroup/cqf-bench) in the
[Carrera Group](https://github.com/carreraGroup) GitHub organization. Built with
[Astro](https://astro.build/) and [Starlight](https://starlight.astro.build/).

**Published site:** [https://carreraGroup.github.io/cqf-bench/](https://carreraGroup.github.io/cqf-bench/)

## Why `docs-site/` instead of `docs/`?

| Location | Purpose |
| --- | --- |
| [`docs/`](../docs/) | Code-level and maintainer-facing notes (preserve separately from this site). |
| **`docs-site/`** | Public website — guides, concepts, reference, and engine setup. |

The Astro project must not live under `docs/` so internal notes and the published site can evolve independently.

## Local development

Requires **Node.js ≥ 22.12** (Astro 6). With [nvm](https://github.com/nvm-sh/nvm):

```bash
cd docs-site
nvm use    # reads .nvmrc
npm install
npm run dev
```

Open [http://localhost:4321/cqf-bench/](http://localhost:4321/cqf-bench/) (matches the GitHub Pages `base` path).

| Command | Action |
| --- | --- |
| `npm run dev` | Dev server with hot reload |
| `npm run build` | Production build → `docs-site/dist/` |
| `npm run preview` | Serve the production build locally |

```bash
npm run build && npm run preview
```

## GitHub Pages (Carrera Group)

The site deploys automatically from this repository via GitHub Actions — not from a
`gh-pages` branch.

| Item | Value |
| --- | --- |
| Organization | [carreraGroup](https://github.com/carreraGroup) |
| Repository | [carreraGroup/cqf-bench](https://github.com/carreraGroup/cqf-bench) |
| Public URL | **https://carreraGroup.github.io/cqf-bench/** |
| Workflow | [`.github/workflows/deploy-docs-site.yml`](../.github/workflows/deploy-docs-site.yml) |
| Astro `site` | `https://carreraGroup.github.io` |
| Astro `base` | `/cqf-bench/` |

### One-time repository setup

In **carreraGroup/cqf-bench** on GitHub:

1. **Settings → Pages**
2. **Build and deployment → Source:** select **GitHub Actions** (not “Deploy from a branch”).
3. Ensure the default branch is **`main`** (the workflow runs on pushes to `main`).

After the first successful workflow run, the site is live at the URL above. Re-runs
happen on every push to `main` that triggers the workflow, or manually via
**Actions → Deploy documentation site → Run workflow**.

### What the workflow does

1. `actions/checkout@v4`
2. `actions/setup-node@v4` — `npm ci` in `docs-site/`
3. `actions/configure-pages@v5` — `npm run build`
4. `actions/upload-pages-artifact@v3` — uploads `docs-site/dist`
5. `actions/deploy-pages@v4` — publishes to GitHub Pages

Permissions: `contents: read`, `pages: write`, `id-token: write`.

## Project layout

```
docs-site/
  astro.config.mjs              # site URL, base path, sidebar
  src/
    content.config.ts
    content/docs/               # pages (Markdown / MDX)
    styles/landing.css          # home landing page styles
  public/                       # favicon, static assets
```

## Diagrams (Mermaid)

The [Diagrams](https://carreraGroup.github.io/cqf-bench/diagrams/) page uses
[`@pasqal-io/starlight-client-mermaid`](https://pasqal-io.github.io/starlight-client-mermaid/).
Enable it in `astro.config.mjs`; use ` ```mermaid ` blocks in any doc page.

## Adding a page

1. Create a `.md` or `.mdx` file under `src/content/docs/`.
2. Add front matter with at least a `title`.
3. Register the page in the `sidebar` array in `astro.config.mjs`.
4. Use `/cqf-bench/...` prefixes in internal links (required for project-site hosting).
