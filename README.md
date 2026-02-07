# cointalk-archive

This repository is an archival static mirror of **cointalk.ca** (CoinTalk episodes + related WordPress content).

## Build a self-contained static site from Wayback

A reproducible builder is included which:
- resolves the closest Wayback snapshot for each URL,
- downloads HTML + page assets (CSS/JS/images/audio),
- rewrites internal links so the output contains **no web.archive.org / cointalk.ca dependencies**, and
- writes a tree suitable for static hosting.

### Quick start

```bash
cd cointalk-archive
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Build into ./docs (GitHub Pages compatible)
./scripts/wayback_build.py --verbose

# Preview locally
python3 -m http.server --directory docs 8000
```

Options:
- `--timestamp 20150328060609` sets the preferred capture date used when resolving closest snapshots.
- `--max-items N` is useful for quick/debug builds.
- `--clean` wipes the output directory before rebuilding.

The builder caches snapshot resolution + downloads under `.cache/wayback/`.
