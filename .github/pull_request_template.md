## Summary

<!-- What changed and why (1–3 sentences). -->

## Changes

<!-- Bullet list or short description. -->

## Validation

Run locally before requesting review:

- [ ] `python -m pip install -e .`
- [ ] `python -m compileall scripts`
- [ ] `python scripts/validate_scenarios.py --suite bench/scenarios/tpcqf/suite.yaml`
- [ ] `python -m unittest discover -s tests -v`
- [ ] `cd docs-site && npm ci && npm run build` (if docs-site changed)

CI must pass: **`python`** and **`docs`** ([workflow](.github/workflows/ci.yml)).

## Checklist

- [ ] Docs updated if behavior changed (`docs-site/` and/or root `.md` files)
- [ ] Scenario files updated/validated if applicable
- [ ] No secrets or local config committed (`local.engines.yaml`, `.env`, tokens)

## Public release safety

- [ ] No real tokens, API keys, bearer tokens, cookies, or credentials
- [ ] No private engine endpoints, customer names, or proprietary URLs
- [ ] No generated data derived from real patient/customer data (all data is synthetic)
- [ ] No benchmark results for private/commercial engines unless approved for publication
- [ ] No local Docker images or private registry references unless clearly marked example-only
