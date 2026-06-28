"""
Retrain the SmartAgile activity classifiers from the cleaned CSVs.

Produces three artifacts that `continous_task.py` loads at runtime:
  * app_vectorizer.pkl  - CountVectorizer over exe basenames
  * rf_model.pkl        - RandomForest predicting app category (work/entertainment/...)
  * svm_pipeline.pkl    - TfidfVectorizer + linear SVC predicting browser-title category

Design notes (train == serve):
  * RF: production calls
        pd.DataFrame(vect.transform([basename]).toarray(), columns=vect.get_feature_names_out())
        rf.predict(df)
    so we fit the RF on a *named* DataFrame with identical columns.
  * SVM: production calls `svm_pipeline.predict([raw_window_title])` with RAW text,
    so we train the pipeline on raw keywords (TF-IDF does its own lowercasing/tokenizing).
    No NLTK preprocessing -> no train/serve skew and no extra dependencies.

Existing .pkl files are backed up to <name>.bak.pkl (only if no backup exists yet).
Run:  python train_models.py
"""
from __future__ import annotations

import os
import shutil

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.svm import SVC

HERE = os.path.dirname(os.path.realpath(__file__))
APPS_CSV = os.path.join(HERE, "applications.csv")
BROWSER_CSV = os.path.join(HERE, "browsertasks.csv")
SEED = 42


def backup(name: str) -> None:
    src = os.path.join(HERE, name)
    bak = os.path.join(HERE, os.path.splitext(name)[0] + ".bak.pkl")
    if os.path.exists(src) and not os.path.exists(bak):
        shutil.copy2(src, bak)
        print(f"  backup -> {os.path.basename(bak)}")


def basename_of(path: str) -> str:
    return os.path.basename(str(path).replace("/", "\\").strip())


def train_app_rf():
    print("\n=== RandomForest: application categories ===")
    df = pd.read_csv(APPS_CSV).dropna(subset=["file_path", "category"])
    df["app_token"] = df["file_path"].map(basename_of)
    df = df[df["app_token"].str.len() > 0]

    vect = CountVectorizer()  # lowercase=True by default (matches serve)
    X_sparse = vect.fit_transform(df["app_token"])
    feature_names = vect.get_feature_names_out()
    X = pd.DataFrame(X_sparse.toarray(), columns=feature_names)
    y = df["category"].reset_index(drop=True)

    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, random_state=SEED, stratify=y
    )
    rf_eval = RandomForestClassifier(n_estimators=300, random_state=SEED, class_weight="balanced")
    rf_eval.fit(X_tr, y_tr)
    pred = rf_eval.predict(X_te)
    print(f"  rows: {len(df)}  features: {len(feature_names)}")
    print(f"  holdout accuracy: {accuracy_score(y_te, pred):.3f}")
    print(classification_report(y_te, pred, zero_division=0))

    # Final model: refit on ALL data with named columns (production passes a named DataFrame).
    rf = RandomForestClassifier(n_estimators=300, random_state=SEED, class_weight="balanced")
    rf.fit(X, y)

    backup("app_vectorizer.pkl")
    backup("rf_model.pkl")
    joblib.dump(vect, os.path.join(HERE, "app_vectorizer.pkl"))
    joblib.dump(rf, os.path.join(HERE, "rf_model.pkl"))
    print("  saved app_vectorizer.pkl + rf_model.pkl")

    # Serve-path sanity check.
    sample = "chrome.exe"
    sv = pd.DataFrame(vect.transform([sample]).toarray(), columns=vect.get_feature_names_out())
    print(f"  sanity: {sample!r} -> {rf.predict(sv)[0]}")


def train_browser_svm():
    print("\n=== SVM: browser-title categories ===")
    df = pd.read_csv(BROWSER_CSV).dropna(subset=["keyword", "category"])
    df["keyword"] = df["keyword"].astype(str).str.strip()
    df = df[df["keyword"].str.len() > 0]
    X, y = df["keyword"], df["category"]

    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, random_state=SEED, stratify=y
    )
    pipeline = Pipeline(
        [
            ("tfidf", TfidfVectorizer(sublinear_tf=True)),
            ("svm", SVC(kernel="linear", random_state=SEED, class_weight="balanced")),
        ]
    )
    grid = {
        "tfidf__ngram_range": [(1, 1), (1, 2)],
        "tfidf__min_df": [1, 2],
        "svm__C": [1, 10],
    }
    search = GridSearchCV(pipeline, grid, cv=3, scoring="accuracy", n_jobs=-1)
    search.fit(X_tr, y_tr)
    print(f"  rows: {len(df)}  best params: {search.best_params_}")
    pred = search.best_estimator_.predict(X_te)
    print(f"  holdout accuracy: {accuracy_score(y_te, pred):.3f}")
    print(classification_report(y_te, pred, zero_division=0))

    # Final pipeline: same best params, refit on ALL data, save.
    final = Pipeline(
        [
            ("tfidf", TfidfVectorizer(sublinear_tf=True,
                                      ngram_range=search.best_params_["tfidf__ngram_range"],
                                      min_df=search.best_params_["tfidf__min_df"])),
            ("svm", SVC(kernel="linear", random_state=SEED, class_weight="balanced",
                        C=search.best_params_["svm__C"])),
        ]
    )
    final.fit(X, y)

    backup("svm_pipeline.pkl")
    joblib.dump(final, os.path.join(HERE, "svm_pipeline.pkl"))
    print("  saved svm_pipeline.pkl")

    for s in ["ChatGPT", "Premier League Highlights - YouTube", "Online Banking - HDFC"]:
        print(f"  sanity: {s!r} -> {final.predict([s])[0]}")


if __name__ == "__main__":
    train_app_rf()
    train_browser_svm()
    print("\nDone. Restart the desktop agent to load the new models.")
