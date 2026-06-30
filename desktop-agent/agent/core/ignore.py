"""
System / shell / lock-screen surfaces that should never count as usage.

These are OS UI processes, not user activity. The ML name map tends to label them
"work", so without filtering they inflate productive time -- e.g. the lock screen
(``LockApp.exe``) showing 14 minutes of "100% work" while the machine was actually idle
and locked. We drop their segments entirely (treated as away/break time).

``LockApp`` / ``LogonUI`` are the strongest signal that the workstation is locked: while
on the secure desktop the global idle counter can stop advancing, so time-based idle
detection alone won't catch it -- hence an explicit name check.
"""

from __future__ import annotations

import os

# Lowercased exe basenames to ignore.
_IGNORE_EXE = {
    # Lock / sign-in (machine is away).
    "lockapp.exe",
    "logonui.exe",
    "credentialuibroker.exe",
    # Shell / desktop chrome surfaces.
    "shellexperiencehost.exe",
    "startmenuexperiencehost.exe",
    "searchhost.exe",
    "searchapp.exe",
    "searchui.exe",
    "widgets.exe",
    "widgetboard.exe",
    "textinputhost.exe",
    "applicationframehost.exe",
    "systemsettings.exe",
    "shellhost.exe",
    "dwm.exe",
    "sihost.exe",
    "ctfmon.exe",
    "lsass.exe",
    "rundll32.exe",
    "openwith.exe",
}

# Window titles that indicate a transient OS surface even when the exe isn't matched.
_IGNORE_TITLE_EXACT = {
    "",
    "windows default lock screen",
    "task switching",
    "start",
    "search",
}


def _basename(path: str | None) -> str:
    if not path:
        return ""
    return os.path.basename(str(path).replace("/", "\\")).strip().lower()


def should_ignore(exe_path: str | None, window_title: str | None = None) -> bool:
    """True if this foreground window is a system/lock surface we must not record."""
    if _basename(exe_path) in _IGNORE_EXE:
        return True
    if window_title is not None and window_title.strip().lower() in _IGNORE_TITLE_EXACT:
        # Only ignore an empty/again-system title when there's also no usable exe name.
        if not _basename(exe_path):
            return True
    return False
