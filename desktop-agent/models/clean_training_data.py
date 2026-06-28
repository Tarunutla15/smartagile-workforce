"""
Clean the SmartAgile training CSVs (browsertasks.csv + applications.csv).

Fixes applied (idempotent — safe to re-run):
  browsertasks.csv
    * strip whitespace on `keyword` and `category`
    * reverse a botched find/replace that turned "Education" -> "Educational-related"
      inside the KEYWORD column (category label "Educational-related" is preserved)
    * normalize category labels: any "X related" -> "X-related", collapse
      whitespace/case variants so phantom duplicate classes merge
    * drop rows with empty keyword/category
    * de-duplicate by (case-insensitive) keyword, keeping the first occurrence;
      report keywords that had conflicting categories
  applications.csv
    * strip whitespace, lower-case the category, de-duplicate app rows

Originals are backed up to <name>.bak.csv (only if a backup does not already exist).
A summary is written to _clean_report.txt next to this script.

Usage:  python clean_training_data.py
"""
from __future__ import annotations

import csv
import os
import shutil
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.realpath(__file__))
BACKEND = os.path.normpath(os.path.join(HERE, "..", "..", "backend", "smartagile", "models"))

BROWSER_FILES = [
    os.path.join(HERE, "browsertasks.csv"),
    os.path.join(BACKEND, "browsertasks.csv"),
]
APP_FILES = [
    os.path.join(HERE, "applications.csv"),
    os.path.join(BACKEND, "applications.csv"),
]

# Canonical category names for the browser dataset.
CANON_BROWSER = {
    "work-related": "Work-related",
    "educational-related": "Educational-related",
    "entertainment-related": "Entertainment-related",
    "personal": "Personal",
    "gaming-related": "Gaming-related",
    "finance-related": "Finance-related",
    "health": "Health",
}

report: list[str] = []


def log(*a):
    line = " ".join(str(x) for x in a)
    report.append(line)
    print(line)


def _collapse_ws(s: str) -> str:
    return " ".join((s or "").split())


def normalize_category(raw: str) -> str:
    c = _collapse_ws(raw)
    if not c:
        return ""
    # "Entertainment related" -> "Entertainment-related" (space-before-"related" bug)
    low = c.lower()
    if low.endswith(" related"):
        low = low[: -len(" related")] + "-related"
    return CANON_BROWSER.get(low, c)


def fix_keyword(raw: str) -> str:
    k = _collapse_ws(raw)
    # Reverse "Education" -> "Educational-related" corruption inside keyword text.
    k = k.replace("Educational-related", "Education")
    return k


def _backup(path: str) -> None:
    bak = os.path.splitext(path)[0] + ".bak.csv"
    if os.path.exists(path) and not os.path.exists(bak):
        shutil.copy2(path, bak)
        log(f"  backup -> {bak}")


def clean_browser(path: str) -> None:
    log(f"\n===== browsertasks: {path} =====")
    if not os.path.exists(path):
        log("  (missing, skipped)")
        return

    rows: list[tuple[str, str]] = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        next(reader, None)  # header
        for r in reader:
            if not r:
                continue
            keyword = ",".join(r[:-1]) if len(r) > 2 else (r[0] if len(r) == 1 else r[0])
            category = r[-1] if len(r) >= 2 else ""
            rows.append((keyword, category))

    before = len(rows)
    cleaned: list[tuple[str, str]] = []
    dropped_empty = 0
    seen: dict[str, str] = {}
    conflicts: dict[str, set] = defaultdict(set)
    dup_skipped = 0

    for kw_raw, cat_raw in rows:
        kw = fix_keyword(kw_raw)
        cat = normalize_category(cat_raw)
        if not kw or not cat:
            dropped_empty += 1
            continue
        key = kw.lower()
        if key in seen:
            dup_skipped += 1
            if seen[key] != cat:
                conflicts[kw].add(seen[key])
                conflicts[kw].add(cat)
            continue
        seen[key] = cat
        cleaned.append((kw, cat))

    _backup(path)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["keyword", "category"])
        w.writerows(cleaned)

    log(f"  rows: {before} -> {len(cleaned)}  (dropped empty: {dropped_empty}, dup removed: {dup_skipped})")
    cats = Counter(c for _, c in cleaned)
    log("  final categories:")
    for c, n in sorted(cats.items(), key=lambda x: -x[1]):
        log(f"    {c:24} {n}")
    if conflicts:
        log(f"  WARNING: {len(conflicts)} keyword(s) had conflicting categories (kept first):")
        for k, cs in list(conflicts.items())[:20]:
            log(f"    {k!r}: {sorted(cs)}")


def clean_apps(path: str) -> None:
    log(f"\n===== applications: {path} =====")
    if not os.path.exists(path):
        log("  (missing, skipped)")
        return
    rows: list[list[str]] = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        next(reader, None)
        for r in reader:
            if len(r) < 3:
                continue
            rows.append(r)

    before = len(rows)
    cleaned: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    dup = 0
    for r in rows:
        app = _collapse_ws(r[0])
        fpath = r[1].strip()
        cat = _collapse_ws(r[-1]).lower()
        if not app or not cat:
            continue
        key = (app.lower(), fpath.lower())
        if key in seen:
            dup += 1
            continue
        seen.add(key)
        cleaned.append((app, fpath, cat))

    _backup(path)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["app_name", "file_path", "category"])
        w.writerows(cleaned)

    log(f"  rows: {before} -> {len(cleaned)}  (dup removed: {dup})")
    cats = Counter(c for *_, c in cleaned)
    log("  final categories:")
    for c, n in sorted(cats.items(), key=lambda x: -x[1]):
        log(f"    {c:18} {n}")


def main():
    for p in BROWSER_FILES:
        clean_browser(p)
    for p in APP_FILES:
        clean_apps(p)
    out = os.path.join(HERE, "_clean_report.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(report))
    print("\nwrote", out)


if __name__ == "__main__":
    main()
