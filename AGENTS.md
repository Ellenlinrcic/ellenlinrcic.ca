# ellenlinrcic.ca — durable article publishing rules

Applies to this repository; obey any more specific AGENTS.md. `src/` is the active Eleventy input; root-level legacy copies are not publication sources. Build with `npm run build`; Cloudflare Pages uses `_site`. Preserve the existing Eleventy 3.1.6 pipeline and templates.

- Inspect git status, applicable rules, existing article front matter and category collections before changes. Preserve unrelated work.
- Publishing normally adds one Markdown article under `src/articles/` and its resources. Use `article.njk`, English lowercase hyphenated filename/slug, explicit `permalink: articles/<slug>.html`, `tags: articles`, publication date, approved category, title/titleEn, description and the existing bilingual fields. Read a current article for its full schema. Chinese content is allowed; public slugs remain English.
- Keep public article URL `/articles/<slug>`; do not rename old routes. Use the existing `canonicalUrl` filter, exactly one absolute self canonical, and existing automatic sitemap collection. Do not hand-add Markdown sitemap entries. Internal href/src/action use root-relative paths. Never emit `/articles/articles/`.
- Preserve all existing article bytes, routes, legacy HTML, permanent redirects, design, forms, analytics and templates unless the user explicitly authorizes a specific change. Do not remove known broken links by guessing destinations. Do not submit test forms.
- Run `npm run check:publish` before proposing publication. It rebuilds and checks sources/output and protected file hashes. Run `npm run test:seo` after changing the checker. Report failures and exact documented exceptions; do not conceal them by broadening an allowlist.
- `scripts/seo-baseline.json` protects current source files. Never regenerate hashes automatically to make a failure pass. After an explicitly approved edit, review the diff then update only the approved entries. After publishing new articles, add their source/resource hashes to this same manifest so they become protected. Preserve existing entries.
- The offline check cannot verify Cloudflare HTTP statuses or Google indexing. Never call it live verification. A generated top-level 404 is necessary; deployment must still be tested.
- Do not commit, push or deploy without explicit user confirmation. Git pushes to main may trigger Cloudflare automatically, so push permission must include deployment permission.
- After an authorized deployment completes, run `npm run check:publish -- --live`. It verifies production URLs against the local build: 200, article canonicals, sitemap equality, robots/noindex, nonexistent URLs 404, and existing `.html`/`index.html` redirects exactly 308 with correct Location. It does not follow redirects when checking statuses. Report network/incomplete checks as failures, never as passes. HTTP success does not establish Google indexing.

## Required provincial Insights publishing step

For every provincial nominee article, Codex MUST identify its province(s) and synchronize the existing provincial Insights directory in the same local publishing task, without waiting for a separate user reminder. A homepage, policy category, or sitemap entry does not satisfy this requirement.

- `scripts/province-insights.json` is the explicit association registry. Its `topics` map lists only existing directories: BC, Alberta, Manitoba, Ontario, PEI, Newfoundland and Labrador, Saskatchewan, New Brunswick, and Northwest Territories. Do not create a new page merely to satisfy this check.
- Use the article's substantive program scope and authoritative sources to identify the province; never infer membership solely from a title, filename, or free-text `categoryLabel`. If the association or publication date is unclear, report it and obtain confirmation before finalizing classification. Cross-province articles may belong to multiple existing topics.
- Every NEW article must have an `articles` registry entry with its extensionless route, explicit `topics` list, and verified `published` date. Use `topics: []` only after confirming that it is not a provincial-topic article. `legacy_unclassified` is a fixed migration list of pre-existing articles awaiting review; NEVER put a new article there to bypass classification. Do not reclassify these historical articles without confirmation.
- Before synchronizing, provide reviewed `title`, `title_en`, and `description` in the registry for any new card. Preserve the article's existing approved front matter, category, route, content, canonical, and sitemap behavior. Provincial membership is separate from the broad policy/case/client category.
- Run `python3 scripts/province_insights.py --write` automatically as part of the authorized LOCAL publishing task. It updates existing lists, preserves existing cards and links, inserts new cards exactly once, and orders by verified publication date, newest first. It refuses unknown topics, duplicate/unconfirmed entries, and missing reviewed card metadata. It does not update protection hashes or publish anything.
- Review directory diffs; update ONLY the approved directory/article hashes in `scripts/seo-baseline.json`. Preserve other hashes, layouts, URLs, existing cards, exceptions, unrelated files, and user changes. Never regenerate the baseline wholesale.
- Then run `npm run check:publish` and `npm run test:seo`. The checked build requires a corresponding directory entry for every registered provincial article and rejects missing entries, duplicates, incorrect ordering, unresolved new articles, and unconfirmed directory associations. Do not add an exception or remove a registry association to make a failure pass.
- Report directory membership and ordering results. Commit, push, and deployment still require separate explicit authorization. The synchronization command is not run by builds: builds validate and fail rather than silently repairing protected source files.

## Mandatory publishing workflow

These rules apply to every future article. Preserve previously published URLs unless the user explicitly approves a route change. Use English lowercase hyphenated source filenames and slugs. Every article must have exactly one absolute self canonical matching its final extensionless public URL and its automatic sitemap entry. Sitemap entries must be unique, existing pages; include every published article. Never add another `/articles/` prefix.

Internal navigation, image and asset references must be root-relative (same-page `#anchors` are allowed). Verify targets and appropriate static homepage/category discovery links in generated HTML, not only JavaScript-rendered links. Require nonempty SEO titles and descriptions. Report duplicate titles and duplicate/highly similar descriptions separately for editorial review; do not rewrite existing articles automatically. Missing, empty or multiple conflicting metadata tags are critical errors.

1. Inspect status, rules, a working article and category collections before editing.
2. Run `npm run check:publish` before offering a preview or proposing publication. `npm run build` also enforces the same offline checks automatically after Eleventy; `build:raw` is an internal build primitive, never the deployment command. Critical failures stop publication. Do not bypass failures with `--skip-build` on stale output, changed baselines, or new exceptions.
3. For every new or visually changed article, inspect desktop (1440px) and mobile (375px and 390px) widths in a browser. Compare with a working article. Check page overflow, heading/paragraph wrapping, tables, image loading and natural aspect ratios, buttons and consultation links. Capture screenshots and review them; do not submit forms. Static checks do not establish visual correctness. No browser check means NOT RUN, never PASS. Avoid shared template/CSS changes unless necessary and explicitly within scope.
4. Run `npm run test:seo` whenever validation code changes. Preserve all existing protected hashes and documented exception entries and reviewed occurrences; never silently expand exceptions. Newly discovered defects must be reported, not hidden.
5. Obtain explicit commit/push/deployment approval. Confirm the actual Cloudflare Pages build command invokes `npm run build` (or the fully checked `npm run check:publish`) with `_site` output. Dashboard settings cannot be proven from package.json alone. If access is unavailable, report verification as incomplete. Do not change cloud settings without authorization.
6. After authorized deployment, run `npm run check:publish -- --live`. Verify live 200 responses, canonical, sitemap, robots/meta/header directives, old URL permanent redirects and nonexistent URL 404 responses. Never use a homepage fallback for invalid articles. Local 404 files do not prove server status. Network errors or incomplete checks are failures/incomplete, not PASS.
7. Report results using the table below. Add scope/evidence and list exceptions separately. Use NOT RUN where the check was not performed and NOT DEPLOYED before approval. Deployment success never guarantees Google indexing; monitor Search Console separately, and do not claim access or monitoring unless actually performed.

| Check | Result |
| --- | --- |
| Article URL | PASS / FAIL / NOT RUN |
| Canonical URL | PASS / FAIL / NOT RUN |
| Sitemap inclusion | PASS / FAIL / NOT RUN |
| Internal links | PASS / FAIL / NOT RUN |
| HTTP status | PASS / FAIL / NOT RUN |
| Robots / Noindex | PASS / FAIL / NOT RUN |
| Mobile display | PASS / FAIL / NOT RUN |
| Desktop display | PASS / FAIL / NOT RUN |
| Existing redirects | PASS / FAIL / NOT RUN |
| Deployment | SUCCESS / FAILED / NOT DEPLOYED |
