"""
ML classifier + name resolution.

Owns the bundled scikit-learn models and the ``exe -> friendly software name`` map,
plus browser detection. Kept separate from the engine so inference and naming live in
one place.

Model files are resolved in a PyInstaller-safe way: when frozen, they are read from
``sys._MEIPASS`` (the one-file bundle's temp dir); otherwise from ``desktop-agent/models``.
"""

from __future__ import annotations

import json
import os
import re
import sys
import warnings
from pathlib import Path

import joblib
import pandas as pd
from sklearn.exceptions import DataConversionWarning

try:
    from sklearn.exceptions import InconsistentVersionWarning
except ImportError:  # older scikit-learn
    InconsistentVersionWarning = None

warnings.filterwarnings("ignore", category=DataConversionWarning)
if InconsistentVersionWarning is not None:
    warnings.filterwarnings("ignore", category=InconsistentVersionWarning)


def _models_dir() -> Path:
    """Locate the bundled ``models/`` directory (dev tree or PyInstaller bundle)."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass) / "models"
    # core/ -> agent/ -> desktop-agent/
    return Path(__file__).resolve().parents[2] / "models"


# Browser executables we recognise (lowercased basenames). Used for detection and to
# resolve a canonical browser key for the exe -> software map.
TOP_BROWSERS = [
    "chrome.exe", "safari.exe", "msedge.exe", "firefox.exe", "samsunginternet.exe",
    "opera.exe", "uc.exe", "brave.exe", "vivaldi.exe", "tor.exe", "maxthon.exe",
    "qqbrowser.exe", "yandex.exe", "baidu.exe", "avastsecure.exe", "epicprivacy.exe",
    "puffin.exe", "dolphin.exe", "duckduckgoprivacy.exe", "waterfox.exe", "palemoon.exe",
    "comododragon.exe", "slimbrowser.exe", "midori.exe", "falkon.exe", "gnuicecat.exe",
    "seamonkey.exe", "srwareiron.exe", "ghosteryprivacy.exe", "aloha.exe", "orion.exe",
    "opeaneon.exe", "sleipnir.exe", "konqueror.exe", "otter.exe", "polarity.exe",
    "cliqz.exe", "cent.exe", "librewolf.exe", "colibri.exe", "dooble.exe", "min.exe",
    "avirascout.exe", "blackhawk.exe", "basilisk.exe", "blisk.exe", "coowon.exe",
    "coccoc.exe", "qtebrowser.exe", "surf.exe", "uzbl.exe", "xb.exe", "smooz.exe",
    "tenta.exe", "iron.exe", "beaker.exe", "lucid.exe", "fennecfdroid.exe", "privacy.exe",
    "whale.exe", "kaios.exe", "smarttv.exe", "operagx.exe", "netscape.exe", "iexplore.exe",
    "nokia.exe", "blackberry.exe", "silk.exe", "bolt.exe", "skyfire.exe", "rockmelt.exe",
    "camino.exe", "shiira.exe", "avant.exe", "lunascape.exe", "k-meleon.exe", "slimjet.exe",
    "sputnik.exe", "chromium.exe", "msedgelegacy.exe", "epic.exe", "superbird.exe",
    "centaury.exe", "arcticfox.exe", "iceweasel.exe", "roccat.exe", "sunrise.exe",
    "wyzo.exe", "element.exe", "elinks.exe", "xombrero.exe", "neturf.exe", "galeon.exe",
    "amaya.exe", "arora.exe", "rekonq.exe", "jumanji.exe", "flock.exe", "phoenix.exe",
    "firewebnavigator.exe",
]

_BROWSER_TITLE_SUFFIX_RE = re.compile(
    r"\s+-\s+(Google Chrome|Chromium|Mozilla Firefox|Microsoft Edge|Opera|Brave Browser|Brave|Vivaldi|Internet Explorer)\s*$",
    flags=re.IGNORECASE,
)


class Classifier:
    def __init__(self) -> None:
        d = _models_dir()
        self.rf_model = joblib.load(d / "rf_model.pkl")
        self.svm_model = joblib.load(d / "svm_pipeline.pkl")
        self.app_model = joblib.load(d / "app_vectorizer.pkl")
        with open(d / "exe_to_software.json", "r", encoding="utf-8") as f:
            self.exe_to_software: dict[str, str] = json.load(f)

    # -- browser detection / naming -------------------------------------
    def is_browser(self, app_name: str | None) -> bool:
        if not app_name:
            return False
        an = app_name.lower().replace("\\", "/")
        if any(b.lower() in an for b in TOP_BROWSERS):
            return True
        if "chrome" in an and ("google" in an or "chromium" in an or an.endswith("chrome")):
            return True
        if "firefox" in an or "mozilla" in an:
            return True
        if "microsoft edge" in an or "msedge" in an or an.strip().endswith("edge"):
            return True
        if "brave" in an:
            return True
        if "opera" in an:
            return True
        if "vivaldi" in an:
            return True
        if "safari" in an and "apple" in an:
            return True
        return False

    def normalize_browser_title(self, title: str | None) -> str:
        """Strip common trailing ' - Browser' suffixes so the same page keys more stably."""
        if not title:
            return ""
        return _BROWSER_TITLE_SUFFIX_RE.sub("", title.strip()).strip()

    def resolve_browser_key(self, app_name: str) -> str:
        """Canonical browser exe key (e.g. 'chrome.exe') for the exe -> software map."""
        an_low = (app_name or "").lower()
        for b in TOP_BROWSERS:
            if b.lower() in an_low:
                return b
        if "msedge" in an_low or "edge" in an_low:
            return "msedge.exe"
        if "firefox" in an_low:
            return "firefox.exe"
        if "chrome" in an_low or "chromium" in an_low:
            return "chrome.exe"
        if "brave" in an_low:
            return "brave.exe"
        if "opera" in an_low:
            return "opera.exe"
        return "browser.exe"

    def browser_software_name(self, app_name: str, title_raw: str = "") -> str:
        key = self.resolve_browser_key(app_name)
        name = self.exe_to_software.get(key.lower(), "Unknown Software")
        if name == "Unknown Software":
            name = self.stable_app_name(app_name, title_raw)
        return (name or "").strip() or "Unknown"

    # -- application naming ---------------------------------------------
    def app_id_for_ml(self, app_path_or_name: str) -> str:
        """Vectorizer was trained on short app strings; prefer basename for full paths."""
        if not app_path_or_name:
            return ""
        s = app_path_or_name.replace("/", "\\")
        if "\\" in s:
            return os.path.basename(s)
        return app_path_or_name

    def _exe_lookup_key(self, app_path_or_name: str) -> str:
        if not app_path_or_name:
            return ""
        base = os.path.basename(app_path_or_name.replace("/", "\\")).lower()
        return base if base else app_path_or_name.lower()

    def app_software_name(self, app_name: str, title_raw: str = "") -> str:
        name = self.exe_to_software.get(self._exe_lookup_key(app_name), "Unknown Software")
        if name == "Unknown Software":
            name = self.stable_app_name(app_name, title_raw)
        return (name or "").strip() or "Unknown"

    def stable_app_name(self, app_name: str | None, task_raw: str | None) -> str:
        """
        Prefer a stable name from the executable (e.g. Cursor.exe -> "Cursor") so the same
        app never fragments across window-title variants. Fall back to the title suffix.
        """
        base = os.path.basename((app_name or "").replace("/", "\\"))
        stem = os.path.splitext(base)[0].strip()
        if stem and not stem.lower().startswith("pid:"):
            return stem
        return (task_raw or "").split("-")[-1].strip() or "Unknown"

    # -- category prediction --------------------------------------------
    def predict_browser_category(self, title_raw: str) -> str:
        return str(self.svm_model.predict([title_raw])[0])

    def predict_app_category(self, app_name: str) -> str:
        ml_app = self.app_id_for_ml(app_name)
        vec = self.app_model.transform([ml_app])
        frame = pd.DataFrame(vec.toarray(), columns=self.app_model.get_feature_names_out())
        return str(self.rf_model.predict(frame)[0])
