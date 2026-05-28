# CQF Bench documentation site

Public documentation for [CQF Bench](https://github.com/carreraGroup/cqf-bench), built with [Astro](https://astro.build/) and [Starlight](https://starlight.astro.build/) and published to GitHub Pages.

## Why `docs-site/` instead of `docs/`?

This repository keeps two kinds of documentation separate:

| Location | Purpose |
| --- | --- |
| [`docs/`](../docs/) | Code-level and maintainer-facing notes that live next to the harness (when present). |
| **`docs-site/`** (this directory) | The public website — guides, concepts, and reference for users and contributors. |

The Astro project must not live under `docs/` so internal notes and the published site can evolve independently.

## Local development

```bash
cd docs-site
npm install
npm run dev
```

Open [http://localhost:4321/cqf-bench/](http://localhost:4321/cqf-bench/) (the dev server respects the `base` path in `astro.config.mjs`).

| Command | Action |
| --- | --- |
| `npm run dev` | Start the dev server with hot reload |
| `npm run build` | Production build into `docs-site/dist/` |
| `npm run preview` | Serve the production build locally |

To preview a production build:

```bash
npm run build && npm run preview
```

Then open the URL printed by `astro preview` (typically `http://localhost:4321/cqf-bench/`).

## Project layout

```
docs-site/
  astro.config.mjs              # site URL, base path, sidebar
  src/
    content.config.ts           # Starlight content collection
    content/docs/               # documentation pages (Markdown / MDX)
      engines/                  # product-specific engine setup (HAPI CQF Ruler, …)
      guides/                   # task-oriented walkthroughs (incl. add-an-engine)
    assets/                     # images referenced from content
  public/                       # static files (favicon, etc.)
```

## GitHub Pages deployment

Pushes to `main` or `master` run [`.github/workflows/deploy-docs-site.yml`](../.github/workflows/deploy-docs-site.yml), which:

1. Installs npm dependencies in `docs-site/`
2. Runs `npm run build`
3. Uploads `docs-site/dist` as a Pages artifact
4. Deploys with the official `configure-pages` / `upload-pages-artifact` / `deploy-pages` actions

**One-time repo setup:** Settings → Pages → Build and deployment → **Source: GitHub Actions**.

The site is configured as a **project site** at `https://carreragroup.github.io/cqf-bench/` (`base: '/cqf-bench/'` in `astro.config.mjs`). Doc links in content use that prefix. For a custom domain, set `ASTRO_SITE` / `ASTRO_BASE` (or edit `astro.config.mjs`) and update those links.

## Diagrams (Mermaid)

The [Diagrams](/cqf-bench/diagrams/) page uses
[`@pasqal-io/starlight-client-mermaid`](https://pasqal-io.github.io/starlight-client-mermaid/)
(client-side rendering). Add a ` ```mermaid ` fenced block in any doc page; the
plugin is enabled in `astro.config.mjs`.

## Adding a page

1. Create a `.md` or `.mdx` file under `src/content/docs/`.
2. Add front matter with at least a `title`.
3. Register the page in the `sidebar` array in `astro.config.mjs`.
