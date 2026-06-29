"""
Plugin manager: holds the registered plugins and picks one per window.

Plugins are tried in ``priority`` order (lowest first); the default app plugin has the
highest number so it always wins last. ``match`` is called on every poll, so plugin
``matches`` methods must stay cheap. Set ``SMARTAGILE_PLUGINS=off`` to disable all the
specialised enrichers and fall back to the default (original) behaviour.
"""

from __future__ import annotations

import logging
import os

from .app_plugin import DefaultAppPlugin
from .base import Plugin, RawWindow
from .browser_plugin import BrowserPlugin
from .outlook_plugin import OutlookPlugin
from .vscode_plugin import VSCodePlugin

logger = logging.getLogger(__name__)


def _plugins_enabled() -> bool:
    return str(os.environ.get("SMARTAGILE_PLUGINS", "")).strip().lower() not in ("off", "0", "false", "no")


class PluginManager:
    def __init__(self, classifier) -> None:
        self.classifier = classifier
        plugins: list[Plugin] = []
        if _plugins_enabled():
            plugins = [
                BrowserPlugin(classifier),
                VSCodePlugin(classifier),
                OutlookPlugin(classifier),
            ]
        else:
            logger.info("Specialised plugins disabled (SMARTAGILE_PLUGINS=off); using default behaviour.")
        # Default catch-all always present and always last.
        plugins.append(DefaultAppPlugin(classifier))
        self.plugins = sorted(plugins, key=lambda p: p.priority)
        logger.info("Plugins active: %s", ", ".join(p.name for p in self.plugins))

    def match(self, raw: RawWindow) -> Plugin:
        for plugin in self.plugins:
            try:
                if plugin.matches(raw):
                    return plugin
            except Exception as exc:  # noqa: BLE001
                logger.debug("plugin %s.matches errored: %s", plugin.name, exc)
        return self.plugins[-1]
