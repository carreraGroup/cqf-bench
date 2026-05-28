// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

/**
 * GitHub Pages project-site settings.
 *
 * Published URL: https://carreragroup.github.io/cqf-bench/
 *
 * To change the base path (repo rename) or move to a custom domain:
 * - Set `site` to your canonical origin (e.g. https://docs.example.org).
 * - Set `base` to `/` for a root site, or `/<repo-name>/` for a project site.
 * - Update internal doc links that use the `/cqf-bench/` prefix.
 *
 * Optional overrides for CI or local experiments:
 * - ASTRO_SITE  (default: https://carreragroup.github.io)
 * - ASTRO_BASE  (default: /cqf-bench/)
 */
const site = process.env.ASTRO_SITE ?? 'https://carreragroup.github.io';
const base = process.env.ASTRO_BASE ?? '/cqf-bench/';

export default defineConfig({
  output: 'static',
  site,
  base,
  integrations: [
    starlight({
      title: 'CQF Bench',
      description:
        'Open benchmark harness for comparing CQF / Clinical Reasoning endpoint behavior and performance across engines.',
      logo: {
        src: './src/assets/logo.png',
        alt: 'CQF Bench',
        replacesTitle: false,
      },
      favicon: '/favicon.png',
      social: [
        {
          icon: 'github',
          label: 'GitHub',
          href: 'https://github.com/carreraGroup/cqf-bench',
        },
      ],
      editLink: {
        baseUrl: 'https://github.com/carreraGroup/cqf-bench/edit/main/docs-site/',
      },
      sidebar: [
        {
          label: 'Start Here',
          items: [
            { label: 'Overview', slug: 'overview' },
            { label: 'Getting Started', slug: 'getting-started' },
            { label: 'Installation', slug: 'installation' },
          ],
        },
        {
          label: 'Concepts',
          items: [
            { label: 'Core Concepts', slug: 'concepts' },
            { label: 'Benchmark Suites', slug: 'concepts/benchmark-suites' },
            { label: 'Test Cases', slug: 'concepts/test-cases' },
            { label: 'Engine Adapters', slug: 'concepts/engine-adapters' },
            { label: 'Results', slug: 'concepts/results' },
          ],
        },
        {
          label: 'Guides',
          items: [
            { label: 'Run Your First Benchmark', slug: 'guides/run-your-first-benchmark' },
            { label: 'Compare Engines', slug: 'guides/compare-engines' },
            { label: 'Publish Results', slug: 'guides/publish-results' },
          ],
        },
        {
          label: 'Reference',
          items: [
            { label: 'CLI', slug: 'reference/cli' },
            { label: 'Configuration', slug: 'reference/configuration' },
            { label: 'Output Format', slug: 'reference/output-format' },
            { label: 'Scenario Catalog', slug: 'reference/scenario-catalog' },
          ],
        },
        {
          label: 'Project',
          items: [
            { label: 'Contributing', slug: 'contributing' },
            { label: 'Suggested Diagrams', slug: 'diagrams' },
          ],
        },
      ],
    }),
  ],
});
