"""
Browser plugin: turns a browser window title (and, optionally, the real URL) into a
site + page.

    "React Tutorial - YouTube"          -> app="YouTube",       activity="React Tutorial"
    "asyncio in python - Stack Overflow" -> app="Stack Overflow", activity="asyncio in python"
    "Sprint Planning - Google Docs"      -> app="Google Docs",    activity="Sprint Planning"

URL capture (``SMARTAGILE_BROWSER_URL=1``) is additive: when a URL is read it improves the
site label (via its domain) and is attached to ``detail`` (``url`` / ``domain``) for the
event payload. Without it, the plugin still works from the title alone.
"""

from __future__ import annotations

import re

from ..core import browser_url
from .base import Enrichment, Plugin, RawWindow

# Registrable domain -> friendly site label.
_DOMAIN_SITES = {
    "youtube.com": "YouTube",
    "docs.google.com": "Google Docs",
    "drive.google.com": "Google Drive",
    "mail.google.com": "Gmail",
    "sheets.google.com": "Google Sheets",
    "slides.google.com": "Google Slides",
    "google.com": "Google",
    "github.com": "GitHub",
    "gitlab.com": "GitLab",
    "stackoverflow.com": "Stack Overflow",
    "stackexchange.com": "Stack Exchange",
    "reddit.com": "Reddit",
    "linkedin.com": "LinkedIn",
    "twitter.com": "Twitter",
    "x.com": "X",
    "notion.so": "Notion",
    "figma.com": "Figma",
    "atlassian.net": "Jira",
    "chatgpt.com": "ChatGPT",
    "openai.com": "OpenAI",
    "medium.com": "Medium",
    "netflix.com": "Netflix",
    "spotify.com": "Spotify",
}

# Site names that commonly appear as the trailing " - <Site>" segment in titles.
_KNOWN_SITE_NAMES = {
    "YouTube", "Google Docs", "Google Sheets", "Google Slides", "Google Drive", "Gmail",
    "Stack Overflow", "Stack Exchange", "GitHub", "GitLab", "Reddit", "LinkedIn",
    "Notion", "Figma", "Jira", "Confluence", "Medium", "Netflix", "Spotify", "Twitch",
    "ChatGPT", "Google Search", "Google",
}

_LEADING_COUNTER_RE = re.compile(r"^\(\d+\)\s*")  # "(12) Inbox" notification counts


def _prettify_domain(domain: str | None) -> str | None:
    if not domain:
        return None
    label = domain.split(".")[0]
    return label[:1].upper() + label[1:] if label else None


def _site_from_title(page: str) -> tuple[str | None, str]:
    """Split a 'Page - Site' style title into (site, page)."""
    if " - " not in page:
        return None, page
    head, _, tail = page.rpartition(" - ")
    tail_s = tail.strip()
    if tail_s in _KNOWN_SITE_NAMES and head.strip():
        return tail_s, head.strip()
    return None, page


class BrowserPlugin(Plugin):
    name = "browser"
    priority = 10
    source_type = "browser"
    splits_by_title = True

    def __init__(self, classifier) -> None:
        self.classifier = classifier

    def matches(self, raw: RawWindow) -> bool:
        return self.classifier.is_browser(raw.exe_path) or self.classifier.is_browser(raw.window_title)

    def segment_title(self, raw: RawWindow) -> str:
        return self.classifier.normalize_browser_title(raw.window_title)

    def enrich(self, raw: RawWindow) -> Enrichment:
        title_raw = self.classifier.normalize_browser_title(raw.window_title)
        category = self.classifier.predict_browser_category(title_raw)

        url = browser_url.get_active_url()
        domain = browser_url.registrable_domain(url) if url else None

        # Prefer a site label derived from the real domain; otherwise parse the title.
        site = _DOMAIN_SITES.get(domain) if domain else None
        page = _LEADING_COUNTER_RE.sub("", title_raw).strip() or title_raw
        title_site, title_page = _site_from_title(page)
        if title_site:
            page = title_page
            if not site:
                site = title_site
        if not site and domain:
            site = _DOMAIN_SITES.get(domain) or _prettify_domain(domain)

        # Fall back to the browser's own name (e.g. "Google Chrome") when no site is known,
        # preserving the original "top apps" semantics for unrecognised pages.
        app = site or self.classifier.browser_software_name(raw.exe_path, title_raw)
        activity = page or title_raw

        detail = None
        if url:
            detail = {"url": url, "domain": domain}

        return Enrichment(app=app, activity=activity, category=category, detail=detail)
