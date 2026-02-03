#!/usr/bin/env python3
"""Build a static mirror of cointalk.ca from the Internet Archive (Wayback).

Goals:
- Download HTML/CSS/JS/images/audio from Wayback snapshots
- Rewrite internal links so the site is self-contained (no web.archive.org, no cointalk.ca)
- Output a tree suitable for static hosting (default: ./docs)

This script is intentionally conservative:
- It never deletes output unless you pass --clean
- It caches snapshot lookups and downloads for repeatable runs

NOTE: Wayback availability varies by URL; we resolve the closest snapshot per URL.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse, urlunparse, parse_qsl, quote

import requests
from bs4 import BeautifulSoup


WAYBACK_AVAILABLE = "https://archive.org/wayback/available"
WAYBACK_CDX = "https://web.archive.org/cdx/search/cdx"

# Keep this small & explicit.
ASSET_EXTENSIONS = {
    ".css",
    ".js",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".webp",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".otf",
    ".mp3",
    ".m4a",
    ".mp4",
    ".pdf",
    ".xml",
    ".txt",
}

HTML_LIKE_EXTENSIONS = {".html", ".htm", ""}


@dataclass(frozen=True)
class Snapshot:
    original: str
    timestamp: str
    wayback_url: str


def _safe_query_fragment(query: str) -> str:
    """Turn a query string into a filename-safe fragment.

    Example: "ver=3.7.3&foo=bar" -> "ver=3.7.3_foo=bar"
    """
    if not query:
        return ""
    # Preserve common delimiters but avoid path separators.
    q = quote(query, safe="=&@,.-_")
    return q.replace("&", "_")


def _canonical_host(hostname: str) -> str:
    h = (hostname or "").lower()
    if h.startswith("www."):
        h = h[4:]
    return h


def _normalize_original_url(original_url: str) -> str:
    """Normalize an original URL for consistent snapshot lookup.

    CDX often returns URLs with explicit :80; Wayback availability is inconsistent
    about that, so we strip default ports.
    """
    u = _safe_urlparse(original_url)
    if not u:
        return original_url
    netloc = u.netloc
    if netloc.endswith(":80") and u.scheme == "http":
        netloc = netloc[: -len(":80")]
    if netloc.endswith(":443") and u.scheme == "https":
        netloc = netloc[: -len(":443")]
    return urlunparse((u.scheme, netloc, u.path, u.params, u.query, u.fragment))


def _local_path_for_original(original_url: str, out_dir: Path, *, treat_as_html: bool) -> Path:
    u = _safe_urlparse(original_url)
    if not u:
        # Fall back to a deterministic junk path; caller should generally avoid
        # feeding invalid URLs here.
        digest = hashlib.sha256(original_url.encode("utf-8", errors="ignore")).hexdigest()[:16]
        return out_dir / "invalid_urls" / f"{digest}.bin"

    host = _canonical_host(u.hostname or "")
    path = u.path or "/"

    # Keep the primary site at the web root. Put third-party assets under a prefix
    # to avoid collisions (e.g. fonts.googleapis.com/css).
    prefix = ""
    if host and host not in {"cointalk.ca"}:
        prefix = f"third_party/{host}"

    # Decide local path.
    if treat_as_html:
        if path.endswith("/"):
            path = path + "index.html"
        else:
            ext = Path(path).suffix.lower()
            # WordPress pretty permalinks are extensionless.
            if ext == "":
                path = path + "/index.html"
            elif ext in {".php"}:
                # Keep it as HTML content.
                path = path + "/index.html"
    else:
        # Assets are kept at their original paths; query string becomes part of filename.
        if host == "fonts.googleapis.com" and path.rstrip("/") == "/css":
            path = "/css.css"

    # Encode query into filename.
    query = u.query
    if query:
        p = Path(path)
        qfrag = _safe_query_fragment(query)
        if p.suffix:
            new_name = f"{p.stem}@{qfrag}{p.suffix}"
        else:
            new_name = f"{p.name}@{qfrag}"
        path = str(p.with_name(new_name))

    if prefix:
        return out_dir / prefix / path.lstrip("/")
    return out_dir / path.lstrip("/")


def _href_for_local_file(local_file: Path, out_dir: Path, *, from_path: Optional[Path] = None) -> str:
    """Return an href suitable for static hosting under a subpath.

    We intentionally avoid leading-slash root-relative URLs because they break when
    hosted under a subdirectory (e.g. GitHub Pages / raw.githack previews).

    If from_path is provided, the href is made relative to from_path's directory.
    Otherwise it is relative to out_dir root.
    """
    target = local_file
    # Prefer directory-style links for HTML content.
    if str(target).endswith(str(Path("index.html"))):
        # We'll strip "index.html" after computing the relative path below.
        pass

    if from_path is not None:
        base_dir = from_path.parent
        rel = os.path.relpath(target, base_dir)
    else:
        rel = str(target.relative_to(out_dir))

    rel = rel.replace(os.sep, "/")

    if rel.endswith("/index.html"):
        rel = rel[: -len("index.html")]
    return rel


def _strip_wayback_wrappers_html(soup: BeautifulSoup) -> None:
    # Remove Wayback toolbar and injected scripts/styles.
    for el in soup.select("#wm-ipp"):
        el.decompose()

    # Remove common Wayback injected resources.
    for tag in soup.find_all(["script", "link"]):
        src = tag.get("src") or ""
        href = tag.get("href") or ""
        blob = src + " " + href
        if "web-static.archive.org/_static/" in blob:
            tag.decompose()
        if "archive.org/includes/athena.js" in blob:
            tag.decompose()

    # Remove inline __wm.* blocks
    for script in soup.find_all("script"):
        if script.string and "__wm." in script.string:
            script.decompose()


_WAYBACK_PREFIX_RE = re.compile(r"^https?://web\.archive\.org/web/(\d+)([a-z_]{0,6})?/(https?://.+)$")


def _unwrap_wayback_url(url: str) -> str:
    """If passed a Wayback URL, return the original URL; else return unchanged."""
    m = _WAYBACK_PREFIX_RE.match(url)
    if not m:
        return url
    return m.group(3)


def _safe_urlparse(url: str):
    """Like urllib.parse.urlparse, but never throws.

    Wayback-captured HTML occasionally contains malformed URLs (notably broken
    IPv6-ish bracket syntax) which would otherwise crash the whole build.
    """
    try:
        return urlparse(url)
    except ValueError:
        return None


def _is_internal(url: str, allowed_hosts: Set[str]) -> bool:
    u = _safe_urlparse(url)
    if not u or u.scheme not in ("http", "https"):
        return False
    host = _canonical_host(u.hostname or "")
    allowed = {_canonical_host(h) for h in allowed_hosts}
    return host in allowed


def _looks_like_asset(url: str) -> bool:
    u = _safe_urlparse(url)
    if not u:
        return False
    host = _canonical_host(u.hostname or "")
    ext = Path(u.path).suffix.lower()
    if ext in ASSET_EXTENSIONS:
        return True
    # Heuristics for common extensionless assets.
    if host == "fonts.googleapis.com" and u.path.rstrip("/") == "/css":
        return True
    return False


def _looks_like_html(url: str) -> bool:
    u = _safe_urlparse(url)
    if not u:
        return False
    ext = Path(u.path).suffix.lower()
    return ext in HTML_LIKE_EXTENSIONS


def cdx_list_urls(session: requests.Session, *, host: str, from_ts: str = "19900101000000", to_ts: str = "20500101000000") -> List[str]:
    """List archived original URLs for a host via the Wayback CDX API.

    Returns a de-duplicated list (collapse=urlkey) of original URLs.
    """
    params = {
        "url": f"{host}/*",
        "from": from_ts,
        "to": to_ts,
        "output": "json",
        "fl": "original",
        "filter": "statuscode:200",
        "collapse": "urlkey",
    }
    r = session.get(WAYBACK_CDX, params=params, timeout=120)
    r.raise_for_status()
    data = r.json()
    # First row is header.
    urls: List[str] = []
    for row in data[1:]:
        if not row:
            continue
        u = row[0]
        if isinstance(u, str) and u.startswith("http"):
            urls.append(u)
    return urls


class Builder:
    def __init__(
        self,
        out_dir: Path,
        *,
        allowed_hosts: Set[str],
        desired_timestamp: str,
        max_items: Optional[int],
        sleep_s: float,
        cache_dir: Path,
        verbose: bool,
        html_only: bool = False,
    ) -> None:
        self.out_dir = out_dir
        self.allowed_hosts = allowed_hosts
        self.desired_timestamp = desired_timestamp
        self.max_items = max_items
        self.sleep_s = sleep_s
        self.cache_dir = cache_dir
        self.verbose = verbose
        self.html_only = html_only

        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "cointalk-archive-rebuilder/1.0 (https://github.com/bobsummerwill/cointalk-archive)",
            }
        )

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.snapshot_cache_path = self.cache_dir / "snapshot_cache.json"
        self.download_cache_path = self.cache_dir / "download_cache.json"

        self.snapshot_cache: Dict[str, Snapshot] = {}
        self.download_cache: Dict[str, Dict[str, str]] = {}
        self._load_caches()

        # Map of local file -> original URL (used for rewriting relative CSS urls).
        self.local_to_original: Dict[Path, str] = {}

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(msg, file=sys.stderr)

    def _load_caches(self) -> None:
        if self.snapshot_cache_path.exists():
            data = json.loads(self.snapshot_cache_path.read_text("utf-8"))
            for k, v in data.items():
                self.snapshot_cache[k] = Snapshot(
                    original=v["original"], timestamp=v["timestamp"], wayback_url=v["wayback_url"]
                )
        if self.download_cache_path.exists():
            self.download_cache = json.loads(self.download_cache_path.read_text("utf-8"))

    def _save_caches(self) -> None:
        self.snapshot_cache_path.write_text(
            json.dumps(
                {k: {"original": v.original, "timestamp": v.timestamp, "wayback_url": v.wayback_url} for k, v in self.snapshot_cache.items()},
                indent=2,
                sort_keys=True,
            ),
            "utf-8",
        )
        self.download_cache_path.write_text(json.dumps(self.download_cache, indent=2, sort_keys=True), "utf-8")

    def resolve_snapshot(self, original_url: str) -> Optional[Snapshot]:
        original_url = _normalize_original_url(_unwrap_wayback_url(original_url))
        if original_url in self.snapshot_cache:
            return self.snapshot_cache[original_url]

        def lookup(u: str) -> Optional[dict]:
            params = {"url": u, "timestamp": self.desired_timestamp}
            # Wayback's availability endpoint can be a bit flaky; retry a few times.
            for attempt in range(3):
                r = self.session.get(WAYBACK_AVAILABLE, params=params, timeout=60)
                r.raise_for_status()
                data = r.json()
                closest = data.get("archived_snapshots", {}).get("closest")
                if closest:
                    return closest
                if attempt < 2:
                    time.sleep(1.0 + attempt)
            return None

        closest = lookup(original_url)
        if not closest:
            # Many assets were archived without their cache-busting query string.
            u = urlparse(original_url)
            if u.query:
                stripped = urlunparse((u.scheme, u.netloc, u.path, u.params, "", u.fragment))
                closest = lookup(stripped)
            if not closest:
                self._log(f"No snapshot found: {original_url}")
                return None
        snap = Snapshot(original=original_url, timestamp=closest["timestamp"], wayback_url=closest["url"])
        self.snapshot_cache[original_url] = snap
        self._save_caches()
        if self.sleep_s:
            time.sleep(self.sleep_s)
        return snap

    def _wayback_identity_url(self, wayback_url: str, timestamp: str) -> str:
        # Convert .../web/<ts>/http://... -> .../web/<ts>id_/http://...
        # This generally removes Wayback toolbar injections.
        needle = f"/web/{timestamp}/"
        if needle in wayback_url:
            return wayback_url.replace(needle, f"/web/{timestamp}id_/")
        return wayback_url

    def _externalize_url_if_needed(self, original_url: str) -> Optional[str]:
        """Return a Wayback URL for resources we intentionally do *not* vendor locally.

        Currently used to omit specific large/problematic files from the repo (e.g. Audio/015.mp3).
        """
        try:
            u = urlparse(_unwrap_wayback_url(original_url))
        except Exception:
            return None
        if (u.path or "") in {"/Audio/010.mp3", "/Audio/015.mp3"}:
            snap = self.resolve_snapshot(original_url)
            if not snap:
                return None
            return self._wayback_identity_url(snap.wayback_url, snap.timestamp)
        return None

    def download(self, original_url: str, *, treat_as_html: bool) -> Optional[Path]:
        original_url = _normalize_original_url(_unwrap_wayback_url(original_url))

        # Intentionally do not download certain resources; they should remain hosted on Wayback.
        if self._externalize_url_if_needed(original_url) is not None:
            return None

        snap = self.resolve_snapshot(original_url)
        if not snap:
            return None

        local_path = _local_path_for_original(original_url, self.out_dir, treat_as_html=treat_as_html)
        local_path.parent.mkdir(parents=True, exist_ok=True)

        cache_key = original_url
        cached = self.download_cache.get(cache_key)
        if cached and local_path.exists():
            # Fast path: already downloaded.
            self.local_to_original[local_path] = original_url
            return local_path

        fetch_url = self._wayback_identity_url(snap.wayback_url, snap.timestamp)

        self._log(f"GET {original_url}  <-  {fetch_url}")

        tmp_path = local_path.with_suffix(local_path.suffix + ".part")

        # Wayback can be flaky for large files; retry a few times.
        for attempt in range(3):
            last_err: Optional[BaseException] = None
            for url_to_fetch in [fetch_url, snap.wayback_url]:
                try:
                    resp = self.session.get(url_to_fetch, timeout=120, stream=True)
                    resp.raise_for_status()

                    h = hashlib.sha256()
                    with tmp_path.open("wb") as f:
                        for chunk in resp.iter_content(chunk_size=1024 * 1024):
                            if not chunk:
                                continue
                            f.write(chunk)
                            h.update(chunk)
                    resp.close()

                    tmp_path.replace(local_path)
                    sha256 = h.hexdigest()
                    self.download_cache[cache_key] = {"local": str(local_path), "sha256": sha256, "timestamp": snap.timestamp}
                    self._save_caches()
                    last_err = None
                    break
                except (requests.exceptions.ChunkedEncodingError, requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout) as e:
                    last_err = e
                    try:
                        resp.close()  # type: ignore[name-defined]
                    except Exception:
                        pass
                    if tmp_path.exists():
                        try:
                            tmp_path.unlink()
                        except Exception:
                            pass
                    continue

            if last_err is None:
                break

            if attempt < 2:
                self._log(f"Retry {attempt+1}/3 after download error for {original_url}: {last_err}")
                time.sleep(1.0 + attempt)
                continue

            self._log(f"Giving up downloading {original_url} after retries: {last_err}")
            return None

        self.local_to_original[local_path] = original_url

        if self.sleep_s:
            time.sleep(self.sleep_s)

        return local_path

    def rewrite_html_in_place(self, html_path: Path) -> Tuple[Set[str], Set[str]]:
        """Rewrite HTML links to local, returning (discovered_html_urls, discovered_asset_urls)."""
        original_url = self.local_to_original.get(html_path)
        if not original_url:
            return set(), set()

        html = html_path.read_text("utf-8", errors="replace")
        soup = BeautifulSoup(html, "lxml")
        _strip_wayback_wrappers_html(soup)

        discovered_html: Set[str] = set()
        discovered_assets: Set[str] = set()

        # Attributes that can contain URLs.
        candidates: Iterable[Tuple[str, str]] = [
            ("a", "href"),
            ("link", "href"),
            ("script", "src"),
            ("img", "src"),
            ("img", "srcset"),
            ("source", "src"),
            ("source", "srcset"),
            ("audio", "src"),
            ("video", "src"),
            ("iframe", "src"),
            ("form", "action"),
            # RSS/Atom
            ("enclosure", "url"),
        ]

        for tag_name, attr in candidates:
            for tag in soup.find_all(tag_name):
                val = tag.get(attr)
                if not val:
                    continue

                if attr == "srcset":
                    # srcset is a comma-separated list.
                    parts = [p.strip() for p in val.split(",") if p.strip()]
                    new_parts = []
                    for part in parts:
                        bits = part.split()
                        url_part = bits[0]
                        descriptor = " ".join(bits[1:])
                        abs_url = urljoin(original_url, _unwrap_wayback_url(url_part))
                        if _is_internal(abs_url, self.allowed_hosts):
                            treat_asset = _looks_like_asset(abs_url)
                            if self.html_only and treat_asset:
                                ext = Path(urlparse(abs_url).path).suffix.lower()
                                if ext in {".mp3", ".m4a", ".mp4"}:
                                    snap = self.resolve_snapshot(abs_url)
                                    if snap:
                                        new_url = self._wayback_identity_url(snap.wayback_url, snap.timestamp)
                                    else:
                                        new_url = url_part
                                    if descriptor:
                                        new_parts.append(f"{new_url} {descriptor}")
                                    else:
                                        new_parts.append(new_url)
                                    continue
                            local_file = _local_path_for_original(
                                abs_url,
                                self.out_dir,
                                treat_as_html=(not treat_asset),
                            )
                            new_url = _href_for_local_file(local_file, self.out_dir, from_path=html_path)
                            if descriptor:
                                new_parts.append(f"{new_url} {descriptor}")
                            else:
                                new_parts.append(new_url)
                            if treat_asset:
                                discovered_assets.add(abs_url)
                            else:
                                discovered_html.add(abs_url)
                        else:
                            new_parts.append(part)
                    tag[attr] = ", ".join(new_parts)
                    continue

                abs_url = urljoin(original_url, _unwrap_wayback_url(val))
                if not _is_internal(abs_url, self.allowed_hosts):
                    continue

                # Some resources are intentionally left on Wayback (not vendored locally).
                external = self._externalize_url_if_needed(abs_url)
                if external is not None:
                    tag[attr] = external
                    continue

                treat_asset = _looks_like_asset(abs_url)
                if self.html_only and treat_asset:
                    ext = Path(urlparse(abs_url).path).suffix.lower()
                    if ext in {".mp3", ".m4a", ".mp4"}:
                        snap = self.resolve_snapshot(abs_url)
                        if snap:
                            tag[attr] = self._wayback_identity_url(snap.wayback_url, snap.timestamp)
                        continue
                local_file = _local_path_for_original(abs_url, self.out_dir, treat_as_html=(not treat_asset))
                tag[attr] = _href_for_local_file(local_file, self.out_dir, from_path=html_path)

                if treat_asset:
                    discovered_assets.add(abs_url)
                else:
                    discovered_html.add(abs_url)

        html_text = str(soup)

        # Second pass: catch URLs inside conditional comments, inline <style> blocks,
        # and other places BeautifulSoup doesn't reliably expose as tag attributes.
        embedded_re = re.compile(r"(?P<url>(?:https?:)?//[^\"'\s<>\)]+)")

        def embedded_repl(m: re.Match) -> str:
            raw = m.group("url")
            abs_url = raw
            if raw.startswith("//"):
                abs_url = "http:" + raw
            abs_url = _unwrap_wayback_url(abs_url)
            if not _is_internal(abs_url, self.allowed_hosts):
                return raw

            # Some resources are intentionally left on Wayback (not vendored locally).
            external = self._externalize_url_if_needed(abs_url)
            if external is not None:
                return external

            u = urlparse(abs_url)
            path = u.path or "/"
            treat_asset = _looks_like_asset(abs_url) or path.startswith(("/wp-content/", "/wp-includes/", "/Audio/"))
            if self.html_only and treat_asset:
                ext = Path(urlparse(abs_url).path).suffix.lower()
                if ext in {".mp3", ".m4a", ".mp4"}:
                    snap = self.resolve_snapshot(abs_url)
                    if snap:
                        return self._wayback_identity_url(snap.wayback_url, snap.timestamp)
                    return raw
            if not treat_asset:
                # Avoid rewriting URLs embedded in JS or metadata (e.g. powerpress_pinw),
                # since they are not required for a self-contained static render.
                return raw

            local_file = _local_path_for_original(abs_url, self.out_dir, treat_as_html=False)
            discovered_assets.add(abs_url)
            return _href_for_local_file(local_file, self.out_dir, from_path=html_path)

        html_text = embedded_re.sub(embedded_repl, html_text)

        html_path.write_text(html_text, "utf-8")
        return discovered_html, discovered_assets

    _CSS_URL_RE = re.compile(r"url\(\s*(['\"]?)([^'\")]+)\1\s*\)")
    _CSS_IMPORT_RE = re.compile(r"@import\s+(?:url\()?\s*(['\"])([^'\"]+)\1\s*\)?")

    def rewrite_css_in_place(self, css_path: Path) -> Set[str]:
        original_url = self.local_to_original.get(css_path)
        if not original_url:
            return set()

        text = css_path.read_text("utf-8", errors="replace")
        discovered_assets: Set[str] = set()

        def repl_url(m: re.Match) -> str:
            raw = m.group(2).strip()
            if raw.startswith("data:"):
                return m.group(0)
            abs_url = urljoin(original_url, _unwrap_wayback_url(raw))
            if not _is_internal(abs_url, self.allowed_hosts):
                return m.group(0)
            local_file = _local_path_for_original(abs_url, self.out_dir, treat_as_html=False)
            discovered_assets.add(abs_url)
            return f"url({_href_for_local_file(local_file, self.out_dir, from_path=css_path)})"

        text = self._CSS_URL_RE.sub(repl_url, text)

        def repl_import(m: re.Match) -> str:
            raw = m.group(2).strip()
            abs_url = urljoin(original_url, _unwrap_wayback_url(raw))
            if not _is_internal(abs_url, self.allowed_hosts):
                return m.group(0)
            local_file = _local_path_for_original(abs_url, self.out_dir, treat_as_html=False)
            discovered_assets.add(abs_url)
            return f"@import url({_href_for_local_file(local_file, self.out_dir, from_path=css_path)})"

        text = self._CSS_IMPORT_RE.sub(repl_import, text)

        css_path.write_text(text, "utf-8")
        return discovered_assets

    def build(self, seeds: Iterable[str]) -> None:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        (self.out_dir / ".nojekyll").write_text("", "utf-8")

        q: deque[Tuple[str, bool]] = deque()
        seen: Set[str] = set()
        count = 0

        for s in seeds:
            q.append((s, True))

        while q:
            original_url, treat_as_html = q.popleft()
            original_url = _unwrap_wayback_url(original_url)
            if original_url in seen:
                continue
            seen.add(original_url)

            if self.max_items is not None and count >= self.max_items:
                self._log("Reached --max-items limit")
                break

            local = self.download(original_url, treat_as_html=treat_as_html)
            if not local:
                continue

            count += 1

            # Post-process.
            if treat_as_html:
                discovered_html, discovered_assets = self.rewrite_html_in_place(local)
                for u in sorted(discovered_assets):
                    q.append((u, False))
                for u in sorted(discovered_html):
                    q.append((u, True))
            else:
                if local.suffix.lower() == ".css":
                    discovered_assets = self.rewrite_css_in_place(local)
                    for u in sorted(discovered_assets):
                        q.append((u, False))

        self._log(f"Done. Downloaded/reused {count} items into {self.out_dir}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs", help="Output directory (default: docs)")
    ap.add_argument("--timestamp", default="20150328060609", help="Preferred timestamp to resolve closest snapshots")
    ap.add_argument("--seed", action="append", default=["http://cointalk.ca/"], help="Seed URL(s) (repeatable)")
    ap.add_argument("--seed-file", default=None, help="Path to text file with one seed URL per line")
    ap.add_argument(
        "--seed-cdx",
        action="store_true",
        help="Use Wayback CDX to enumerate URLs for cointalk.ca + www.cointalk.ca and use them as seeds (inventory-driven build)",
    )
    ap.add_argument("--max-items", type=int, default=None, help="Limit total downloaded items (debug)")
    ap.add_argument(
        "--html-only",
        action="store_true",
        help="Only download/seed HTML-like pages (and required assets discovered from them). Skips CDX Audio/wp-content/wp-includes seeding.",
    )
    ap.add_argument("--sleep", type=float, default=0.0, help="Sleep between requests (politeness)")
    ap.add_argument("--cache-dir", default=".cache/wayback", help="Cache directory")
    ap.add_argument("--clean", action="store_true", help="Delete output directory before building")
    ap.add_argument("-v", "--verbose", action="store_true")

    args = ap.parse_args()

    out_dir = Path(args.out)
    cache_dir = Path(args.cache_dir)

    if args.clean and out_dir.exists():
        shutil.rmtree(out_dir)

    b = Builder(
        out_dir,
        allowed_hosts={
            "cointalk.ca",
            "www.cointalk.ca",
            # Third-party dependencies we want to vendor locally.
            "fonts.googleapis.com",
            "themes.googleusercontent.com",
        },
        desired_timestamp=args.timestamp,
        max_items=args.max_items,
        sleep_s=args.sleep,
        cache_dir=cache_dir,
        verbose=args.verbose,
        html_only=args.html_only,
    )

    seeds: List[str] = list(args.seed or [])
    if args.seed_file:
        p = Path(args.seed_file)
        if p.exists():
            for line in p.read_text("utf-8", errors="ignore").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    seeds.append(line)

    if args.seed_cdx:
        # Inventory-driven: enumerate URLs from CDX and build them.
        # We intentionally cap the time range to avoid later domain-takeover spam content.
        # cointalk.ca's relevant archive content is primarily 2013-2014.
        urls: List[str] = []
        for host in ["cointalk.ca", "www.cointalk.ca"]:
            try:
                urls.extend(cdx_list_urls(b.session, host=host, to_ts="20151231235959"))
            except Exception as e:
                print(f"CDX failed for {host}: {e}", file=sys.stderr)

        def include(u: str) -> bool:
            try:
                p = urlparse(_normalize_original_url(u)).path or "/"
            except Exception:
                return False
            if p == "/" or p == "":
                return True

            # HTML-first mode: only seed HTML-ish navigational pages.
            if args.html_only:
                prefixes = [
                    "/2013/",
                    "/2014/",
                    "/category/",
                    "/author/",
                    "/tag/",
                    "/page/",
                    "/about-",
                    "/contact-",
                    "/events",
                    "/the-crew",
                    "/policy",
                    "/cointalk-",
                    "/feed",
                    "/comments/",
                ]
                return any(p.startswith(pre) for pre in prefixes)

            # Full mode (includes assets + audio seeding)
            prefixes = [
                "/2013/",
                "/2014/",
                "/category/",
                "/author/",
                "/tag/",
                "/page/",
                "/feed",
                "/comments/",
                "/about-",
                "/contact-",
                "/events",
                "/the-crew",
                "/policy",
                "/cointalk-",
                "/wp-content/",
                "/wp-includes/",
                "/Audio/",
            ]
            return any(p.startswith(pre) for pre in prefixes)

        seeds.extend([u for u in urls if include(u)])

    # De-dupe while preserving order.
    seen = set()
    uniq_seeds: List[str] = []
    for s in seeds:
        if s in seen:
            continue
        seen.add(s)
        uniq_seeds.append(s)

    b.build(uniq_seeds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
