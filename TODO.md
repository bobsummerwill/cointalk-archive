# TODO (WIP)

This is a temporary working checklist to keep the PR on track. Delete before merge if desired.

## Goal
- Produce a self-contained static mirror of cointalk.ca that works when hosted under a subpath (GitHub Pages / githack), i.e. no root-absolute URLs like `/wp-content/...`.

## Current focus
- Fix root-absolute URLs in generated HTML/CSS so assets/links work under subpath.

## Next steps
- [ ] Identify remaining root-absolute patterns in `docs/` (HTML + CSS):
  - [ ] `href="/wp-content/..."`, `src="/wp-includes/..."`
  - [ ] CSS `url(/wp-content/...)`, `url(/wp-includes/...)`
  - [ ] Any other `href="/..."` that should be local
- [ ] Implement systematic rewrite in builder (preferred) so rebuilds are reproducible.
- [ ] Rebuild `docs/` and validate locally (incl. subpath-like serving) and via githack.

## Follow-ups
- [ ] Ensure no unexpected MP3 downloads in HTML-first mode; keep file-size constraints in mind.
- [ ] Add/expand README notes about subpath hosting if needed.

## Reporting
- Hourly status updates to Bob (Signal).
- Make incremental commits (script changes + docs updates) so review is easy.
