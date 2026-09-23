"""
p3_step01_ml_components.py  (PartB / eCRF 组分分析)

依据与研究者 2026-09-19 讨论确定：
  - eCRF 是复合指标；预测因子只用其组分：age, bmi, waist, rhr, mvpa, smoke_now。
  - eCRF 分性别 → 纳入 sex；并**分性别(男/女)各自评估**。
  - 不纳入共病（共病留给亚组分析）。
  - 目标：mobility_event；5 个 ML；200 次重复；另算**变量重要性**（置换重要性, RF）。
数据集命名： <cohort>_<fs>[_M|_F]
  fs: compsex = 6 组分 + sex；comp = 6 组分（分性别时用）
用法：
  py p3_step01_ml_components.py one CHARLS_compsex
  py p3_step01_ml_components.py one ALL_comp_M ALL_comp_F
输出：output/p3_ml_results.csv、output/p3_ml_importance.csv
"""
from pathlib import Path
import os
import sys
import json
import time
import warnings
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, GridSearchCV, StratifiedKFold
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.inspection import permutation_importance
from sklearn.metrics import (accuracy_score, recall_score, precision_score,
                             roc_auc_score, brier_score_loss)
from xgboost import XGBClassifier
from scipy.special import expit

warnings.filterwarnings("ignore")

DATA = str(Path(__file__).resolve().parents[2] / "data")
OUT = str(Path(__file__).resolve().parents[1] / "output")
COMP = ["age", "bmi", "waist", "rhr", "mvpa", "smoke_now"]
CAT = ["sex", "mvpa", "smoke_now"]


def scaled(est):
    return Pipeline([("sc", StandardScaler()), ("m", est)])


MODELS = {
    "RF": (RandomForestClassifier(n_estimators=300, n_jobs=-1, random_state=1),
           {"n_estimators": [300], "max_depth": [None, 8], "min_samples_leaf": [1, 5]}),
    "XGBoost": (XGBClassifier(random_state=1, n_jobs=-1, eval_metric="logloss"),
                {"n_estimators": [300], "max_depth": [3, 6], "learning_rate": [0.05, 0.1]}),
    "SVM": (scaled(SVC(probability=False, random_state=1)), {"m__C": [1, 10]}),
    "KNN": (scaled(KNeighborsClassifier()), {"m__n_neighbors": [5, 15, 31]}),
    "MLP": (scaled(MLPClassifier(random_state=1, max_iter=200, early_stopping=True)),
            {"m__hidden_layer_sizes": [(64,), (128,)], "m__alpha": [1e-4]}),
}


def get_proba(est, X):
    if hasattr(est, "predict_proba"):
        return est.predict_proba(X)[:, 1]
    return expit(est.decision_function(X))


def impute(train, test, feats):
    tr, te = train.copy(), test.copy()
    for c in feats:
        fill = tr[c].mode().iloc[0] if c in CAT else tr[c].median()
        tr[c] = tr[c].fillna(fill)
        te[c] = te[c].fillna(fill)
    return tr, te


def metrics(y, p):
    pred = (p >= 0.5).astype(int)
    return {"accuracy": accuracy_score(y, pred),
            "sensitivity": recall_score(y, pred, zero_division=0),
            "PPV": precision_score(y, pred, zero_division=0),
            "AUC": roc_auc_score(y, p), "Brier": brier_score_loss(y, p)}


def run_dataset(dname, df, feats, repeats=200, save_cb=None, done_models=None, seed0=2026):
    done_models = done_models or set()
    X = df[feats].copy()
    y = df["mobility_event"].astype(int)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, stratify=y, random_state=seed0)
    tr, te = impute(Xtr, Xte, feats)
    rows, best_params = [], {}
    tuned = {}
    for mname, (est, grid) in MODELS.items():
        if mname in done_models:
            continue
        t0 = time.time()
        gs = GridSearchCV(est, grid, scoring="roc_auc",
                          cv=StratifiedKFold(3, shuffle=True, random_state=1), n_jobs=-1)
        gs.fit(tr, ytr)
        best_params[mname] = gs.best_params_
        tuned[mname] = gs.best_estimator_
        res = []
        for r in range(repeats):
            Xtr2, Xte2, ytr2, yte2 = train_test_split(X, y, test_size=0.3, stratify=y, random_state=1000 + r)
            tr2, te2 = impute(Xtr2, Xte2, feats)
            e = gs.best_estimator_
            e.fit(tr2, ytr2)
            res.append(metrics(yte2, get_proba(e, te2)))
        agg = {"dataset": dname, "model": mname, "n": len(y), "repeats": repeats,
               "auc": np.mean([r["AUC"] for r in res]), "auc_sd": np.std([r["AUC"] for r in res]),
               "acc": np.mean([r["accuracy"] for r in res]),
               "sens": np.mean([r["sensitivity"] for r in res]),
               "ppv": np.mean([r["PPV"] for r in res]),
               "brier": np.mean([r["Brier"] for r in res])}
        rows.append(agg)
        print("   %-20s %-8s AUC=%.3f(+-%.3f) acc=%.3f sens=%.3f ppv=%.3f  %.1fs" %
              (dname, mname, agg["auc"], agg["auc_sd"], agg["acc"], agg["sens"], agg["ppv"], time.time() - t0), flush=True)
        if save_cb:
            save_cb(agg, best_params, mname)
    return rows, best_params


def importance_rows(dname, df, feats):
    """RF 置换重要性：5 次 70/30，测试集 AUC 下降为重要性。"""
    X = df[feats].copy(); y = df["mobility_event"].astype(int)
    acc = np.zeros(len(feats))
    for s in range(5):
        Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, stratify=y, random_state=500 + s)
        tr, te = impute(Xtr, Xte, feats)
        m = RandomForestClassifier(n_estimators=300, n_jobs=-1, random_state=1).fit(tr, ytr)
        pi = permutation_importance(m, te, yte, scoring="roc_auc", n_repeats=5, random_state=1, n_jobs=-1)
        acc += pi.importances_mean
    acc /= 5
    return [{"dataset": dname, "feature": f, "importance": acc[i]} for i, f in enumerate(feats)]


def build(name):
    pool = pd.read_csv(os.path.join(DATA, "final_analysis_pooled.csv"))
    coh = name.split("_comp")[0]
    d = pool.copy() if coh == "ALL" else pool[pool["cohort"] == coh].copy()
    if name.endswith("_M"):
        d = d[d["sex"] == 1]
    elif name.endswith("_F"):
        d = d[d["sex"] == 2]
    return d


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "list"
    if stage == "list":
        jobs = ["CHARLS_compsex", "ELSA_compsex", "HRS_compsex", "ALL_compsex",
                "ALL_comp_M", "ALL_comp_F",
                "CHARLS_comp_M", "CHARLS_comp_F", "ELSA_comp_M", "ELSA_comp_F",
                "HRS_comp_M", "HRS_comp_F"]
    else:
        jobs = sys.argv[2:]
    resfile = os.path.join(OUT, "p3_ml_results.csv")
    impfile = os.path.join(OUT, "p3_ml_importance.csv")
    allrows = pd.read_csv(resfile).to_dict("records") if os.path.exists(resfile) else []
    impr = pd.read_csv(impfile).to_dict("records") if os.path.exists(impfile) else []
    done_pairs = {(r["dataset"], r["model"]) for r in allrows}
    for dname in jobs:
        d = build(dname)
        if dname.endswith("_M") or dname.endswith("_F"):
            feats = COMP
        else:
            feats = COMP + ["sex"]
        done_models = {m for (ds, m) in done_pairs if ds == dname}
        if len(done_models) >= len(MODELS):
            print("skip", dname, flush=True); continue
        print("== %s n=%d feats=%s" % (dname, len(d), feats), flush=True)

        def saver(agg, bp, mname, _dn=dname):
            allrows.append(agg)
            pd.DataFrame(allrows).to_csv(resfile, index=False, encoding="utf-8-sig")

        run_dataset(dname, d, feats, 200, save_cb=saver, done_models=done_models)
        if dname not in {r["dataset"] for r in impr}:
            impr += importance_rows(dname, d, feats)
            pd.DataFrame(impr).to_csv(impfile, index=False, encoding="utf-8-sig")
            print("   importance saved for", dname, flush=True)
    print("DONE")
