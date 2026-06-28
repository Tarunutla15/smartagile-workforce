import time
import os
import queue
import pywinctl
import threading
from pynput import mouse, keyboard
from datetime import datetime, timezone
import ctypes
import re
from ctypes import wintypes
import joblib
import logging
import pandas as pd
import json
import warnings

from sklearn.exceptions import DataConversionWarning

try:
    from sklearn.exceptions import InconsistentVersionWarning
except ImportError:
    InconsistentVersionWarning = None

warnings.filterwarnings("ignore", category=DataConversionWarning)
if InconsistentVersionWarning is not None:
    warnings.filterwarnings("ignore", category=InconsistentVersionWarning)

rf_model_path = os.path.join(os.path.dirname(__file__), "models", "rf_model.pkl")
rf_model = joblib.load(rf_model_path)
svm_model_path = os.path.join(os.path.dirname(__file__), "models", "svm_pipeline.pkl")
svm_model = joblib.load(svm_model_path)
app_vectorizer_model_path = os.path.join(os.path.dirname(__file__), "models", "app_vectorizer.pkl")
app_model = joblib.load(app_vectorizer_model_path)
json_file_path = os.path.join(os.path.dirname(__file__), "models", "exe_to_software.json")
with open(json_file_path, "r", encoding="utf-8") as _exe_json:
    exe_to_software = json.load(_exe_json)

from http_batch_writer import http_writer_loop
from local_pairing_server import pairing_port, start_pairing_server

running_flag = False
thread = None
User_global_id = 0

# Wake at least this often to refresh title (browser tabs), periodic DB flush, and 7pm logic.
TITLE_REFRESH_SEC = 2.0
# WinEvent foreground hook + message loop (see _foreground_hook_thread). If hook fails, we still refresh on TITLE_REFRESH_SEC.
EVENT_SYSTEM_FOREGROUND = 0x0003
WINEVENT_OUTOFCONTEXT = 0x0000
WM_QUIT = 0x0012
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
# DB writer batches: fewer commits, one transaction per flush.
top_100_browsers_list = [
    "chrome.exe",
    "safari.exe",
    "msedge.exe",
    "firefox.exe",
    "samsunginternet.exe",
    "opera.exe",
    "uc.exe",
    "brave.exe",
    "vivaldi.exe",
    "tor.exe",
    "maxthon.exe",
    "qqbrowser.exe",
    "yandex.exe",
    "baidu.exe",
    "avastsecure.exe",
    "epicprivacy.exe",
    "puffin.exe",
    "dolphin.exe",
    "duckduckgoprivacy.exe",
    "waterfox.exe",
    "palemoon.exe",
    "comododragon.exe",
    "slimbrowser.exe",
    "midori.exe",
    "falkon.exe",
    "gnuicecat.exe",
    "seamonkey.exe",
    "srwareiron.exe",
    "ghosteryprivacy.exe",
    "aloha.exe",
    "orion.exe",
    "opeaneon.exe",
    "sleipnir.exe",
    "konqueror.exe",
    "otter.exe",
    "polarity.exe",
    "cliqz.exe",
    "cent.exe",
    "librewolf.exe",
    "colibri.exe",
    "dooble.exe",
    "min.exe",
    "avirascout.exe",
    "blackhawk.exe",
    "basilisk.exe",
    "blisk.exe",
    "coowon.exe",
    "coccoc.exe",
    "qtebrowser.exe",
    "surf.exe",
    "uzbl.exe",
    "xb.exe",
    "smooz.exe",
    "tenta.exe",
    "iron.exe",
    "beaker.exe",
    "lucid.exe",
    "fennecfdroid.exe",
    "privacy.exe",
    "whale.exe",
    "kaios.exe",
    "smarttv.exe",
    "operagx.exe",
    "netscape.exe",
    "iexplore.exe",
    "nokia.exe",
    "blackberry.exe",
    "silk.exe",
    "bolt.exe",
    "skyfire.exe",
    "rockmelt.exe",
    "camino.exe",
    "shiira.exe",
    "avant.exe",
    "lunascape.exe",
    "k-meleon.exe",
    "slimjet.exe",
    "sputnik.exe",
    "chromium.exe",
    "msedgelegacy.exe",
    "epic.exe",
    "superbird.exe",
    "centaury.exe",
    "arcticfox.exe",
    "iceweasel.exe",
    "roccat.exe",
    "sunrise.exe",
    "wyzo.exe",
    "element.exe",
    "elinks.exe",
    "xombrero.exe",
    "neturf.exe",
    "galeon.exe",
    "amaya.exe",
    "arora.exe",
    "rekonq.exe",
    "jumanji.exe",
    "flock.exe",
    "phoenix.exe",
    "firewebnavigator.exe",
]

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

_user32.GetForegroundWindow.argtypes = ()
_user32.GetForegroundWindow.restype = wintypes.HWND
_user32.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
_user32.GetWindowThreadProcessId.restype = wintypes.DWORD
_user32.GetWindowTextLengthW.argtypes = (wintypes.HWND,)
_user32.GetWindowTextLengthW.restype = ctypes.c_int
_user32.GetWindowTextW.argtypes = (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
_user32.GetWindowTextW.restype = ctypes.c_int
_user32.GetMessageW.argtypes = (ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT)
_user32.GetMessageW.restype = wintypes.BOOL
_user32.TranslateMessage.argtypes = (ctypes.POINTER(wintypes.MSG),)
_user32.TranslateMessage.restype = wintypes.BOOL
_user32.DispatchMessageW.argtypes = (ctypes.POINTER(wintypes.MSG),)
_user32.DispatchMessageW.restype = ctypes.c_long
_user32.PostThreadMessageW.argtypes = (wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
_user32.PostThreadMessageW.restype = wintypes.BOOL
_user32.SetWinEventHook.argtypes = (
    wintypes.UINT,
    wintypes.UINT,
    wintypes.HMODULE,
    ctypes.c_void_p,
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.DWORD,
)
_user32.SetWinEventHook.restype = ctypes.c_void_p
_user32.UnhookWinEvent.argtypes = (ctypes.c_void_p,)
_user32.UnhookWinEvent.restype = wintypes.BOOL

_kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
_kernel32.OpenProcess.restype = wintypes.HANDLE
_kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
_kernel32.CloseHandle.restype = wintypes.BOOL
_kernel32.GetCurrentThreadId.restype = wintypes.DWORD
_kernel32.GetTickCount.restype = wintypes.DWORD

_kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.LPWSTR,
    ctypes.POINTER(wintypes.DWORD),
]
_kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]


_user32.GetLastInputInfo.argtypes = (ctypes.POINTER(LASTINPUTINFO),)
_user32.GetLastInputInfo.restype = wintypes.BOOL

_hook_callback_ref = []


def _seconds_since_last_input():
    """OS-wide idle: time since last keyboard/mouse input (GetLastInputInfo)."""
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if not _user32.GetLastInputInfo(ctypes.byref(lii)):
        return 0.0
    tick = _kernel32.GetTickCount()
    delta_ms = (tick - lii.dwTime) & 0xFFFFFFFF
    return delta_ms / 1000.0


def _get_window_text(hwnd):
    if not hwnd:
        return ""
    n = _user32.GetWindowTextLengthW(hwnd)
    if n <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(n + 1)
    _user32.GetWindowTextW(hwnd, buf, n + 1)
    return buf.value or ""


def _pid_for_hwnd(hwnd):
    pid = wintypes.DWORD(0)
    _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def _process_image_path(pid):
    if not pid:
        return ""
    h = _kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(4096)
        size = wintypes.DWORD(len(buf))
        if _kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            return buf.value or ""
    finally:
        _kernel32.CloseHandle(h)
    return ""


def _normalize_browser_title(title):
    """Strip common trailing ' - Browser' suffixes so the same page keys more stably."""
    if not title:
        return ""
    t = title.strip()
    t = re.sub(
        r"\s+-\s+(Google Chrome|Chromium|Mozilla Firefox|Microsoft Edge|Opera|Brave Browser|Brave|Vivaldi|Internet Explorer)\s*$",
        "",
        t,
        flags=re.IGNORECASE,
    )
    return t.strip()


def _app_id_for_ml(app_path_or_name):
    """Vectorizer was trained on short app strings; prefer basename for full paths."""
    if not app_path_or_name:
        return ""
    s = app_path_or_name.replace("/", "\\")
    if "\\" in s:
        return os.path.basename(s)
    return app_path_or_name


def _exe_lookup_key(app_path_or_name):
    if not app_path_or_name:
        return ""
    base = os.path.basename(app_path_or_name.replace("/", "\\")).lower()
    return base if base else app_path_or_name.lower()


def _is_browser_app(app_name):
    """Detect browsers from process path/title (pywinctl strings vary on Windows)."""
    if not app_name:
        return False
    an = app_name.lower().replace("\\", "/")
    if any(b.lower() in an for b in top_100_browsers_list):
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


def _stable_activity_key(active_window):
    """
    Same desktop app = same key even if the window title changes (file/tab captions).
    Browsers still use (app, title) so different sites/tabs are separate rows.
    """
    if active_window is None:
        return None
    title, app_name = active_window
    if app_name is None:
        return active_window
    if _is_browser_app(app_name):
        return (app_name, title or "")
    return (app_name, "")


def _task_column_value(title, app_name):
    """Non-browser: one aggregate row per app per day. Browser: page title as the site key."""
    if app_name and _is_browser_app(app_name):
        return title or ""
    return "(session)"


def get_window_info_from_foreground_hwnd(hwnd):
    """
    (title, exe_path_or_label) for foreground HWND.
    exe_path is used for browser detection and exe_to_software; stable across title changes for non-browser keys.
    """
    if not hwnd:
        return None, None
    title = _get_window_text(hwnd)
    pid = _pid_for_hwnd(hwnd)
    path = _process_image_path(pid)
    app_id = path if path else (f"pid:{pid}" if pid else "")
    if _is_browser_app(app_id):
        title = _normalize_browser_title(title)
    return title, app_id


def get_active_window_info():
    """Foreground window via Win32 (no per-call COM init). Falls back to pywinctl if needed."""
    hwnd = _user32.GetForegroundWindow()
    if hwnd:
        t, a = get_window_info_from_foreground_hwnd(hwnd)
        if a:
            return t, a
    try:
        ctypes.windll.ole32.CoInitialize(None)
        active_window = pywinctl.getActiveWindow()
        if active_window is not None:
            return active_window.title, active_window.getAppName()
        return None, None
    except Exception as e:
        print(f"Error getting active window info: {e}")
        return None, None
    finally:
        ctypes.windll.ole32.CoUninitialize()


def _win_event_proc_factory(fg_queue):
    def callback(_hook, event, hwnd, _id_object, _id_child, _tid, _time_ms):
        try:
            if hwnd and event == EVENT_SYSTEM_FOREGROUND:
                fg_queue.put_nowait(int(hwnd))
        except queue.Full:
            pass

    return ctypes.WINFUNCTYPE(
        None,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.HWND,
        wintypes.LONG,
        wintypes.LONG,
        wintypes.DWORD,
        wintypes.DWORD,
    )(callback)


def _foreground_hook_thread(fg_queue, hook_handle_box, thread_id_box):
    """
    SetWinEventHook for EVENT_SYSTEM_FOREGROUND; message pump required for OUTOFCONTEXT delivery.
    hook_handle_box[0] = hook handle; thread_id_box[0] = thread id for WM_QUIT.
    """
    global running_flag
    thread_id_box[0] = _kernel32.GetCurrentThreadId()
    proc = _win_event_proc_factory(fg_queue)
    _hook_callback_ref.append(proc)
    hook = _user32.SetWinEventHook(
        EVENT_SYSTEM_FOREGROUND,
        EVENT_SYSTEM_FOREGROUND,
        0,
        proc,
        0,
        0,
        WINEVENT_OUTOFCONTEXT,
    )
    hook_handle_box[0] = hook
    if not hook:
        logging.warning("SetWinEventHook failed; using timer-based foreground refresh only.")
        while running_flag:
            time.sleep(TITLE_REFRESH_SEC)
        return
    msg = wintypes.MSG()
    while running_flag:
        r = _user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
        if r == 0:
            break
        if r == -1:
            break
        _user32.TranslateMessage(ctypes.byref(msg))
        _user32.DispatchMessageW(ctypes.byref(msg))
    if hook_handle_box[0]:
        _user32.UnhookWinEvent(hook_handle_box[0])
        hook_handle_box[0] = None


counts_lock = threading.Lock()


def on_click(x, y, button, pressed):
    global click_count
    if pressed:
        with counts_lock:
            click_count += 1
    return True


def on_scroll(x, y, dx, dy):
    global scroll_count
    with counts_lock:
        scroll_count += 1
    return True


def on_press(key):
    global keystroke_count
    with counts_lock:
        keystroke_count += 1
    return True


click_count = 0
scroll_count = 0
keystroke_count = 0
idle_threshold = 120


def snapshot_and_reset_counts():
    global click_count, scroll_count, keystroke_count
    with counts_lock:
        ks = keystroke_count
        cl = click_count
        sc = scroll_count
        keystroke_count = 0
        click_count = 0
        scroll_count = 0
    return ks, cl, sc


PERIODIC_FLUSH_SEC = 60
# Idle inside a segment beyond this many seconds is treated as "away" and NOT counted.
# Active windows refresh input well within this, so normal usage is unaffected.
ACTIVE_IDLE_GRACE_SEC = 15
# A healthy loop flushes within ~PERIODIC_FLUSH_SEC. Anything much larger means the
# process was suspended/stalled (sleep, hibernate, thread starvation): clamp it so a
# multi-hour gap is never attributed to a single window.
MAX_SEGMENT_SEC = PERIODIC_FLUSH_SEC + 10
# Skip near-zero segments (rapid window flips / fully-idle periods) to avoid noise rows.
MIN_SEGMENT_SEC = 1.0


def _effective_duration(raw_spent, idle_seconds):
    """
    Convert raw foreground wall-time into *active* seconds:
    1) clamp runaway gaps (sleep/stall) to MAX_SEGMENT_SEC,
    2) drop idle time beyond ACTIVE_IDLE_GRACE_SEC ("away" time).
    """
    raw_spent = max(0.0, float(raw_spent))
    idle_in_seg = min(raw_spent, max(0.0, float(idle_seconds)))
    spent = min(raw_spent, MAX_SEGMENT_SEC)
    away = max(0.0, idle_in_seg - ACTIVE_IDLE_GRACE_SEC)
    return max(0.0, spent - away)


def _stable_app_name(app_name, task_raw):
    """
    Prefer a stable name from the executable (e.g. Cursor.exe -> "Cursor") so the same
    app never fragments across window-title variants. Fall back to the title suffix.
    """
    base = os.path.basename((app_name or "").replace("/", "\\"))
    stem = os.path.splitext(base)[0].strip()
    if stem and not stem.lower().startswith("pid:"):
        return stem
    return (task_raw or "").split("-")[-1].strip() or "Unknown"


def track_application_usage(user_id):
    uid = int(user_id)
    job_queue = queue.Queue()
    writer_thread = threading.Thread(
        target=http_writer_loop,
        args=(job_queue,),
        name="smartagile-http-writer",
        daemon=False,
    )
    writer_thread.start()

    previous_window = None
    previous_key = None
    start_time = time.time()
    mouse_listener = mouse.Listener(on_click=on_click, on_scroll=on_scroll)
    keyboard_listener = keyboard.Listener(on_press=on_press)

    mouse_listener.start()
    keyboard_listener.start()

    foreground_queue = queue.Queue()
    hook_handle_box = [None]
    hook_tid_box = [0]
    hook_thread = threading.Thread(
        target=_foreground_hook_thread,
        args=(foreground_queue, hook_handle_box, hook_tid_box),
        name="smartagile-foreground-hook",
        daemon=False,
    )
    hook_thread.start()

    logging.info(
        "Foreground WinEvent hook + GetLastInputInfo idle; HTTP batched writer to SmartAgile API."
    )

    def enqueue_usage_segment(prev_win, time_spent, idle_time, ks, cl, sc, with_openings_and_attendance):
        """time_spent is seconds; events POST to /api/usage-events/batch/."""
        _ = with_openings_and_attendance  # legacy flag; attendance is login/logout on server
        if prev_win is None:
            return
        task_raw, app_name = prev_win
        if app_name is None:
            return
        task_col = _task_column_value(task_raw, app_name)
        occurred_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
            "+00:00", "Z"
        )

        if _is_browser_app(app_name):
            an_low = app_name.lower()
            browser_name = next(
                (b for b in top_100_browsers_list if b.lower() in an_low),
                None,
            )
            if not browser_name:
                if "msedge" in an_low or "edge" in an_low:
                    browser_name = "msedge.exe"
                elif "firefox" in an_low:
                    browser_name = "firefox.exe"
                elif "chrome" in an_low or "chromium" in an_low:
                    browser_name = "chrome.exe"
                elif "brave" in an_low:
                    browser_name = "brave.exe"
                elif "opera" in an_low:
                    browser_name = "opera.exe"
                else:
                    browser_name = "browser.exe"
            software_name = exe_to_software.get(browser_name.lower(), "Unknown Software")
            predicted_category = svm_model.predict([task_raw])[0]
            if software_name == "Unknown Software":
                software_name = _stable_app_name(app_name, task_raw)
            software_name = (software_name or "").strip() or "Unknown"
            ev = {
                "source_type": "browser",
                "name": software_name,
                "context": task_raw,
                "category": str(predicted_category),
                "duration_seconds": float(time_spent),
                "idle_seconds": float(idle_time),
                "keystrokes": float(ks),
                "clicks": float(cl),
                "scrolls": float(sc),
                "occurred_at": occurred_iso,
            }
        else:
            ml_app = _app_id_for_ml(app_name)
            new_app_vectorized = app_model.transform([ml_app])
            input_data = pd.DataFrame(
                new_app_vectorized.toarray(),
                columns=app_model.get_feature_names_out(),
            )
            predicted_category = rf_model.predict(input_data)[0]
            software_name = exe_to_software.get(_exe_lookup_key(app_name), "Unknown Software")
            if software_name == "Unknown Software":
                software_name = _stable_app_name(app_name, task_raw)
            software_name = (software_name or "").strip() or "Unknown"
            ev = {
                "source_type": "application",
                "name": software_name,
                "context": task_col,
                "category": str(predicted_category),
                "duration_seconds": float(time_spent),
                "idle_seconds": float(idle_time),
                "keystrokes": float(ks),
                "clicks": float(cl),
                "scrolls": float(sc),
                "occurred_at": occurred_iso,
            }

        job_queue.put([ev])

    def compute_wait_timeout():
        if not running_flag:
            return 0.05
        t_refresh = TITLE_REFRESH_SEC
        if previous_window is None:
            return max(0.1, t_refresh)
        rem = PERIODIC_FLUSH_SEC - (time.time() - start_time)
        return max(0.15, min(t_refresh, rem))

    try:
        while running_flag:
            try:
                foreground_queue.get(timeout=compute_wait_timeout())
            except queue.Empty:
                pass
            while True:
                try:
                    foreground_queue.get_nowait()
                except queue.Empty:
                    break

            hwnd = _user32.GetForegroundWindow()
            active_window = get_window_info_from_foreground_hwnd(hwnd)
            if not active_window[1]:
                active_window = get_active_window_info()

            current_key = _stable_activity_key(active_window)

            if current_key != previous_key:
                if previous_window is not None:
                    raw_spent = time.time() - start_time
                    idle_raw = _seconds_since_last_input()
                    effective = _effective_duration(raw_spent, idle_raw)
                    ks, cl, sc = snapshot_and_reset_counts()  # always reset (don't bleed into next)
                    if effective >= MIN_SEGMENT_SEC:
                        enqueue_usage_segment(
                            previous_window,
                            effective,
                            min(effective, float(idle_raw)),
                            ks,
                            cl,
                            sc,
                            True,
                        )

                previous_window = active_window
                previous_key = current_key
                start_time = time.time()

            elif previous_window is not None and (time.time() - start_time) >= PERIODIC_FLUSH_SEC:
                raw_spent = time.time() - start_time
                idle_raw = _seconds_since_last_input()
                effective = _effective_duration(raw_spent, idle_raw)
                ks, cl, sc = snapshot_and_reset_counts()
                if effective >= MIN_SEGMENT_SEC:
                    enqueue_usage_segment(
                        previous_window,
                        effective,
                        min(effective, float(idle_raw)),
                        ks,
                        cl,
                        sc,
                        False,
                    )
                # Always advance the window so sustained idle does not keep growing one segment.
                start_time = time.time()

    except Exception as e:
        print(f"Exception occurred: {e}")
    finally:
        mouse_listener.stop()
        keyboard_listener.stop()
        if hook_tid_box[0]:
            _user32.PostThreadMessageW(hook_tid_box[0], WM_QUIT, 0, 0)
        hook_thread.join(timeout=15)
        job_queue.put(None)
        writer_thread.join(timeout=60)


def start_continous_task(user_id):
    global running_flag, thread, User_global_id
    # Localhost pairing for JWT (browser → Settings → Connect) + automatic refresh on disk
    start_pairing_server()
    User_global_id = user_id
    if not running_flag:
        running_flag = True
        thread = threading.Thread(target=track_application_usage, args=(user_id,))
        thread.start()
        print(f"Task started for user: {user_id}")


def stop_continous_task():
    global running_flag, thread
    if running_flag:
        running_flag = False
        if thread is not None:
            thread.join()
        print("Task stopped")


if __name__ == "__main__":
    import sys

    import auth_store

    logging.basicConfig(level=logging.INFO)
    # Optional; only for log context — default 1 without any env.
    _uid_raw = os.environ.get("SMARTAGILE_USER_ID", "").strip()
    if _uid_raw:
        try:
            uid = int(_uid_raw)
            if uid <= 0:
                uid = 1
        except ValueError:
            uid = 1
    else:
        uid = 1
    print("Starting desktop agent for user id", uid, "- Ctrl+C to stop")
    start_continous_task(uid)
    p = pairing_port()
    print(
        f"Pairing: http://127.0.0.1:{p}/health — SmartAgile → Settings → Connect desktop app — "
        f"tokens file: {auth_store.store_path()}"
    )
    has_auth = bool(
        os.environ.get("SMARTAGILE_ACCESS_TOKEN")
        or os.environ.get("SMARTAGILE_TAB_TOKEN")
        or auth_store.get_refresh()
    )
    if not has_auth:
        print("No auth yet: use Connect in Settings, or set SMARTAGILE_ACCESS_TOKEN for dev.")
    try:
        while running_flag:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_continous_task()
