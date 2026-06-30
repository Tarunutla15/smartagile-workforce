"""
Browser plugin: keeps the browser as one app (Digital-Wellbeing style) and puts the site
+ page in the activity/context, so all tabs roll up under "Google Chrome" / "Microsoft
Edge" instead of fragmenting into many per-site cards.

    "React Tutorial - YouTube"           -> app="Google Chrome",  activity="YouTube - React Tutorial"
    "asyncio in python - Stack Overflow" -> app="Google Chrome",  activity="Stack Overflow - asyncio in python"

URL capture (``SMARTAGILE_BROWSER_URL``) is additive: when a URL is read, its domain sets
a deterministic category and labels the site in the context, and ``url`` / ``domain`` are
attached to ``detail`` for the event payload. Without it, the plugin still works from the
title alone.
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

# Registrable domain -> deterministic category. When a real URL is captured this overrides
# the noisy title-based ML guess (e.g. a "SmartAgile" tab no longer reads as entertainment).
# Labels match the backend's canonical categories ("work" / "entertainment").
_DOMAIN_CATEGORY = {
    "github.com": "work",
    "gitlab.com": "work",
    "stackoverflow.com": "work",
    "stackexchange.com": "work",
    "docs.google.com": "work",
    "sheets.google.com": "work",
    "slides.google.com": "work",
    "drive.google.com": "work",
    "mail.google.com": "work",
    "atlassian.net": "work",
    "notion.so": "work",
    "figma.com": "work",
    "chatgpt.com": "work",
    "openai.com": "work",
    "youtube.com": "entertainment",
    "netflix.com": "entertainment",
    "spotify.com": "entertainment",
    "reddit.com": "entertainment",
    "twitter.com": "entertainment",
    "x.com": "entertainment",
    "instagram.com": "entertainment",
    "facebook.com": "entertainment",
    "twitch.tv": "entertainment",
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

        # A known domain is a far stronger signal than the title; let it set the category.
        if domain and domain in _DOMAIN_CATEGORY:
            category = _DOMAIN_CATEGORY[domain]

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

        # Group everything under the browser (one card per browser); the site + page live
        # in the activity/context so tabs are visible inside that card.
        app = self.classifier.browser_software_name(raw.exe_path, title_raw)
        if site and page and site.lower() not in page.lower():
            activity = f"{site} - {page}"
        else:
            activity = site or page or title_raw

        detail = None
        if url:
            detail = {"url": url, "domain": domain}

        return Enrichment(app=app, activity=activity, category=category, detail=detail)
