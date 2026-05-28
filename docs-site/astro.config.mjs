// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import starlightClientMermaid from '@pasqal-io/starlight-client-mermaid';

/**
 * Carrera Group GitHub Pages (project site).
 * Published at: https://carreraGroup.github.io/cqf-bench/
 *
 * Change these two values if the org, repo name, or domain changes.
 */
const site = 'https://carreraGroup.github.io';
const base = '/cqf-bench/';

export default defineConfig({
  output: 'static',
  site,
  base,
  integrations: [
    starlight({
      plugins: [starlightClientMermaid({})],
      customCss: ['./src/styles/landing.css'],
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
        baseUrl: 'https://github.com/carreraGroup/cqf-bench/edit/master/docs-site/',
      },
      sidebar: [
        {
          label: 'Start Here',
          items: [
            { label: 'Home', slug: 'index' },
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
            { label: 'Golden Validation', slug: 'concepts/golden-validation' },
            { label: 'Engine Adapters', slug: 'concepts/engine-adapters' },
            { label: 'Results', slug: 'concepts/results' },
          ],
        },
        {
          label: 'Guides',
          items: [
            { label: 'Run Your First Benchmark', slug: 'guides/run-your-first-benchmark' },
            { label: 'Add an Engine', slug: 'guides/add-an-engine' },
            { label: 'Compare Engines', slug: 'guides/compare-engines' },
            { label: 'Publish Results', slug: 'guides/publish-results' },
          ],
        },
        {
          label: 'Engines',
          items: [
            { label: 'Engine guides', slug: 'engines' },
            { label: 'HAPI CQF Ruler', slug: 'engines/hapi-cqf-ruler' },
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
            { label: 'Diagrams', slug: 'diagrams' },
          ],
        },
      ],
    }),
  ],
});
