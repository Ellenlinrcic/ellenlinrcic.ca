# ellenlinrcic.ca
Official website for Jie "Ellen" Lin, RCIC
Website updated on July 18, 2026.

## Publishing validation

- `npm run build`: original Eleventy generation followed by mandatory offline validation; exits nonzero on a critical failure. Cloudflare Pages must use this command and `_site` output. No network or browser dependency is added to this build.
- `npm run check:publish`: rebuild once, then run the same offline validator.
- `npm run check:publish -- --live`: rebuild/validate locally, then check production HTTP only if offline validation passes. Do this after deployment; do not compare unpublished routes to production.
- `npm run test:seo`: regression tests, including isolated build gate tests. Requires a generated `_site` (even a failed checked build generates it).
- `npm run build:raw`: internal generation only, not approved for deployment.
- `python3 scripts/check-seo.py --skip-build`: validation of an already generated output, used by the checked build. Do not use stale output for publishing decisions.

Runtime requirements remain Node/npm/Eleventy 3.1.6 plus Python 3.9+ standard library. No Python packages are required. Missing Python or validator failures intentionally stop the build. Verify the actual Cloudflare dashboard build command and Python availability before approving rollout; repository scripts alone cannot prove remote settings.

Missing/empty titles or descriptions and multiple metadata elements are critical. Duplicate titles and description similarity (normalized text, SequenceMatcher ratio >= 0.92) are advisory SEO review warnings, not extra exceptions. Review them without automatically changing content. The six existing exception occurrences are printed separately on every validation report. Protected hashes are never refreshed by the checker.

Desktop/mobile visual review is a separate required publishing step in AGENTS.md. The offline command explicitly reports it as NOT RUN; it does not pretend to measure browser layout. Live HTTP checks likewise do not establish Google indexing.

Deployment prerequisite (owner-confirmed current setting): production currently uses `npx @11ty/eleventy`, which bypasses validation. After deployment approval, change the Cloudflare Pages production Build command to `npm run build`, retain `_site` output, and verify Python 3.9+ availability before the approved push/deployment. Do not claim automatic enforcement on Cloudflare until this setting is changed and verified. No cloud settings have been changed locally.

Owner verified before rollout: Build system Version 3, no `PYTHON_VERSION` or `NODE_VERSION` overrides, production branch `main`, output `_site`; the default Python runtime is compatible. The Build command change to `npm run build` is still pending owner coordination. After that setting is saved, obtain approval to commit/push, inspect the deployment log for validation execution, and run `npm run check:publish -- --live` after deployment succeeds.
