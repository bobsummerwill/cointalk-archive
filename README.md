# cointalk-archive

A complete archival static mirror of **[cointalk.ca](https://cointalk.ca)** — a Canadian cryptocurrency podcast that ran from 2013–2014, featuring early discussions of Bitcoin, Ethereum, and the Canadian crypto community.

**Live site:** [cointalk-archive.ca](https://cointalk-archive.ca) · [bobsummerwill.github.io/cointalk-archive](https://bobsummerwill.github.io/cointalk-archive/)

## What's archived

- **20 podcast episodes** (004–020 + Ethereum specials + bonus episodes) with MP3 audio
- **18 additional pages** (About, Events, Sponsors, blog posts, category archives)
- **Full WordPress theme** (Twenty Thirteen) with CSS, JS, images, and fonts
- **112 HTML files** total, all self-contained with no external dependencies

Episodes 015 and coinfest2014 exceed GitHub's 100 MB file limit and link to the [Internet Archive](https://web.archive.org/) instead.

## Rebuilding from Wayback Machine

A reproducible builder script is included at `scripts/wayback_build.py`. It downloads pages and assets from the Wayback Machine, rewrites all URLs to be relative (no `web.archive.org` or `cointalk.ca` dependencies), and outputs a static site to `docs/`.

### Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Build

```bash
# Full build into docs/ (GitHub Pages compatible)
./scripts/wayback_build.py --verbose

# Preview locally
python3 -m http.server --directory docs 8000
```

### Options

| Flag | Description |
|------|-------------|
| `--timestamp YYYYMMDDHHMMSS` | Preferred Wayback capture date for snapshot resolution |
| `--max-items N` | Limit number of pages to build (useful for debugging) |
| `--clean` | Wipe output directory before rebuilding |
| `--no-resume` | Ignore cached progress and rebuild from scratch |

The builder caches snapshot resolution and downloads under `.cache/wayback/`.

### Known issues

- Wayback Machine can be intermittent — some downloads may return HTML error pages instead of actual assets. The builder retries with multiple timestamps, but manual re-runs may be needed.
- CSS files downloaded from Wayback may be HTML-wrapped (containing `&gt;` instead of `>` in selectors). The builder handles this, but verify CSS after a fresh build.

## Hosting

The site is hosted via GitHub Pages, serving static files directly from the `docs/` directory (no Jekyll processing). A `.nojekyll` file is included to prevent Jekyll from interfering.

To configure for your own fork:
1. Go to **Settings → Pages**
2. Set Source to **Deploy from a branch**
3. Select branch **main**, folder **/docs**

## License

See [LICENSE](LICENSE).
