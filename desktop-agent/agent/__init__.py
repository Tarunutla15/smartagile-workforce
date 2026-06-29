"""SmartAgile desktop agent package.

Modular tracker split out of the old monolithic ``continous_task.py``:

    agent/
      core/      Window / Input / Idle trackers, ML classifier, uploader, auth, engine
      plugins/   Per-app context enrichers (browser, vscode, outlook, ...)

``continous_task.py`` stays as the thin entrypoint (so existing docs and the
front-end "Connect" flow keep working) and just wires these together.
"""

__all__ = ["__version__"]

__version__ = "2.0.0"
