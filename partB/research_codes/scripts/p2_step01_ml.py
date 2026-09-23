"""
p2_step01_ml.py  (PartB / 阶段二 - 机器学习预测新发移动障碍)

依据 handbook §5 阶段二 与研究者 2026-09-19 决定：
  - 目标：mobility_event（新发移动障碍）
  - 数据集：CHARLS / ELSA / HRS 各自 + 合并(ALL, 含 cohort)
  - 两套特征：
      (i)  noecrf = 全协变量(不含 eCRF)，全部样本
      (ii) ecrf   = 含 eCRF（仅 eCRF 可得的 7,885 人），剔除与 eCRF 同为其输入且精确共线的
                    bmi/waist/rhr/mvpa/smoke_now（保留 age, sex, educ, marital, sbp, drink, 各慢病, adl_base）
  - 缺失：分类=众数；连续=中位数；**插补参数只在训练集估计**（不插补 eCRF）
  - 划分：按结局分层 70/30；调参一次（固定训练集内 3 折 CV）；随后固定超参做 REPEATS 次随机划分评估
  - 指标：accuracy / sensitivity / PPV / AUC / Brier
用法：
  py p2_step01_ml.py pilot     # HRS+noecrf，5 模型，10 次（验证与计时）
  py p2_step01_ml.py full      # 全部 8 个数据集 × 5 模型 × 1000 次
输出：output/p2_ml_results.csv、output/p2_ml_bestparams.json
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
from sklearn.metrics import (accuracy_score, recall_score, precision_score,
                             roc_auc_score, brier_score_loss)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier
from scipy.special import expit


def scaled(est):
    return Pipeline([("sc", StandardScaler()), ("m", est)])

warnings.filterwarnings("ignore")


def get_proba(est, X):
    if hasattr(est, "predict_proba"):
        return est.predict_proba(X)[:, 1]
    return expit(est.decision_function(X))

DATA = str(Path(__file__).resolve().parents[2] / "data")
OUT = str(Path(__file__).resolve().parents[1] / "output")

TAU = 0.5
CAT = ["sex", "educ", "marital", "mvpa", "drink", "smoke_status",
       "hibp", "diab", "cancer", "lung", "heart", "stroke", "adl_base", "cohort"]
CONT = ["age", "bmi", "waist", "sbp", "rhr", "ecrf"]

FS_NOECRF = ["age", "sex", "educ", "marital", "bmi", "waist", "sbp", "rhr", "mvpa",
             "drink", "smoke_status", "hibp", "diab", "cancer", "lung", "heart",
             "stroke", "adl_base"]
FS_ECRF = ["ecrf", "age", "sex", "educ", "marital", "sbp", "drink",
           "hibp", "diab", "cancer", "lung", "heart", "stroke", "adl_base"]

MODELS = {
    "RF": (RandomForestClassifier(random_state=1, n_jobs=-1),
           {"n_estimators": [300], "max_depth": [None, 8], "min_samples_leaf": [1, 5]}),
    "XGBoost": (XGBClassifier(random_state=1, n_jobs=-1, eval_metric="logloss"),
                {"n_estimators": [300], "max_depth": [3, 6], "learning_rate": [0.05, 0.1]}),
    "SVM": (scaled(SVC(probability=False, random_state=1)),
            {"m__C": [1, 10], "m__gamma": ["scale"]}),
    "KNN": (scaled(KNeighborsClassifier()), {"m__n_neighbors": [5, 15, 31]}),
    "MLP": (scaled(MLPClassifier(random_state=1, max_iter=200, early_stopping=True)),
            {"m__hidden_layer_sizes": [(64,), (128,)], "m__alpha": [1e-4]}),
}


def impute(train, test, feats):
    tr = train.copy()
    te = test.copy()
    for c in feats:
        if c in CAT:
            v = tr[c].mode()
            fill = v.iloc[0] if len(v) else 0
        else:
            fill = tr[c].median()
        tr[c] = tr[c].fillna(fill)
        te[c] = te[c].fillna(fill)
    return tr, te


def metrics(y, p):
    pred = (p >= TAU).astype(int)
    return {"accuracy": accuracy_score(y, pred),
            "sensitivity": recall_score(y, pred, zero_division=0),
            "PPV": precision_score(y, pred, zero_division=0),
            "AUC": roc_auc_score(y, p),
            "Brier": brier_score_loss(y, p)}


def run_dataset(dname, df, feats, repeats, save_cb=None, done_models=None, seed0=2026):
    done_models = done_models or set()
    X = df[feats].copy()
    y = df["mobility_event"].astype(int)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, stratify=y, random_state=seed0)
    tr, te = impute(Xtr, Xte, feats)
    rows, best_params = [], {}
    for mname, (est, grid) in MODELS.items():
        if mname in done_models:
            print("   skip (done): %s %s" % (dname, mname), flush=True)
            continue
        t0 = time.time()
        gs = GridSearchCV(est, grid, scoring="roc_auc", cv=StratifiedKFold(3, shuffle=True, random_state=1), n_jobs=-1)
        gs.fit(tr, ytr)
        best_params[mname] = gs.best_params_
        res = []
        for r in range(repeats):
            Xtr2, Xte2, ytr2, yte2 = train_test_split(X, y, test_size=0.3, stratify=y, random_state=1000 + r)
            tr2, te2 = impute(Xtr2, Xte2, feats)
            est2 = gs.best_estimator_
            est2.fit(tr2, ytr2)
            p = get_proba(est2, te2)
            res.append(metrics(yte2, p))
        agg = {"dataset": dname, "model": mname, "n": len(y), "repeats": repeats,
               "auc": np.mean([r["AUC"] for r in res]),
               "auc_sd": np.std([r["AUC"] for r in res]),
               "acc": np.mean([r["accuracy"] for r in res]),
               "sens": np.mean([r["sensitivity"] for r in res]),
               "ppv": np.mean([r["PPV"] for r in res]),
               "brier": np.mean([r["Brier"] for r in res])}
        rows.append(agg)
        print("   %-22s %-8s AUC=%.3f(+-%.3f) acc=%.3f sens=%.3f ppv=%.3f brier=%.3f  %.1fs" %
              (dname, mname, agg["auc"], agg["auc_sd"], agg["acc"], agg["sens"], agg["ppv"], agg["brier"], time.time() - t0),
              flush=True)
        if save_cb:
            save_cb(agg, best_params)
    return rows, best_params


def build(name):
    pool = pd.read_csv(os.path.join(DATA, "final_analysis_pooled.csv"))
    if name == "ALL":
        d = pool.copy()
    else:
        d = pool[pool["cohort"] == name].copy()
    d["cohort"] = d["cohort"].map({"CHARLS": 0, "ELSA": 1, "HRS": 2})
    return d


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "pilot"
    resfile = os.path.join(OUT, "p2_ml_results_%s.csv" % ("pilot" if stage == "pilot" else "full"))
    parfile = os.path.join(OUT, "p2_ml_bestparams_%s.json" % ("pilot" if stage == "pilot" else "full"))
    if stage == "pilot":
        jobs = [("HRS", FS_NOECRF, "noecrf", 10)]
    else:
        jobs = [(coh, sf, sn, 200)
                for coh in ["CHARLS", "ELSA", "HRS", "ALL"]
                for sn, sf in [("noecrf", FS_NOECRF), ("ecrf", FS_ECRF)]]
        if stage == "one":
            want = set(sys.argv[2:])
            jobs = [j for j in jobs if ("%s_%s" % (j[0], j[2])) in want]
    allrows = []
    done_pairs = set()
    if os.path.exists(resfile):
        prev = pd.read_csv(resfile)
        allrows = prev.to_dict("records")
        done_pairs = set(zip(prev["dataset"], prev["model"]))
    allparams = json.load(open(parfile, encoding="utf-8")) if os.path.exists(parfile) else {}
    for coh, feats, sname, reps in jobs:
        dname = "%s_%s" % (coh, sname)
        done_models = {m for (ds, m) in done_pairs if ds == dname}
        if len(done_models) >= len(MODELS):
            print("skip (all done):", dname, flush=True)
            continue
        d = build(coh)
        if sname == "ecrf":
            d = d[d["ecrf"].notna()].copy()
        use_feats = feats + (["cohort"] if coh == "ALL" else [])
        print("== %s  n=%d  feats=%d  reps=%d ..." % (dname, len(d), len(use_feats), reps), flush=True)

        def saver(agg, bp_dict, _dn=dname):
            allrows.append(agg)
            allparams[_dn] = bp_dict
            pd.DataFrame(allrows).to_csv(resfile, index=False, encoding="utf-8-sig")
            with open(parfile, "w", encoding="utf-8") as f:
                json.dump(allparams, f, indent=1)

        run_dataset(dname, d, use_feats, reps, save_cb=saver, done_models=done_models)
    print(pd.DataFrame(allrows).to_string())
    print("DONE", stage)
