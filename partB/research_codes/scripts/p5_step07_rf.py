"""
p5_step07_rf.py —— 第二步：RF 以基线 eCRF 预测 LCGA 轨迹类别（队列内 70/30）

输入：output/p5_final_class_<cohort>.csv（pid, role, class）
      partB/data/final_analysis_pooled.csv（基线 eCRF）
输出：output/p5_ml_results.csv、output/p5_confusion_<cohort>.csv、报告
"""
from pathlib import Path
import os
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, confusion_matrix, recall_score,
                             precision_score, roc_auc_score)

OUT = str(Path(__file__).resolve().parents[1] / "output")
DATA = str(Path(__file__).resolve().parents[2] / "data")
NAME = {
    "CHARLS": {"1": "高位下降型", "2": "进展型", "3": "低稳定型"},
    "ELSA": {"1": "晚期进展型", "2": "早期高位型", "3": "低稳定型"},
    "HRS": {"1": "快速发展型", "2": "低缓升型"},
}
pool = pd.read_csv(os.path.join(DATA, "final_analysis_pooled.csv"), usecols=["pid", "ecrf"])
pool["pid"] = pd.to_numeric(pool["pid"], errors="coerce").astype("Int64")

rows, rep = [], ["# p5 第二步 RF（基线 eCRF → LCGA 轨迹类别）", ""]
for coh in ["CHARLS", "ELSA", "HRS"]:
    f = pd.read_csv(os.path.join(OUT, "p5_final_class_%s.csv" % coh))
    d = f.merge(pool, on="pid", how="left").dropna(subset=["ecrf", "class"])
    tr = d[d["role"] == "train"]; te = d[d["role"] == "test"]
    Xtr, ytr = tr[["ecrf"]].values, tr["class"].astype(int).values
    Xte, yte = te[["ecrf"]].values, te["class"].astype(int).values
    rf = RandomForestClassifier(n_estimators=500, random_state=1, n_jobs=-1).fit(Xtr, ytr)
    proba = rf.predict_proba(Xte)
    pred = rf.classes_[np.argmax(proba, axis=1)]
    classes = sorted(set(ytr))
    acc = accuracy_score(yte, pred)
    bal_acc = recall_score(yte, pred, labels=classes, average="macro", zero_division=0)
    if len(classes) == 2:
        auc = roc_auc_score((yte == classes[1]).astype(int), proba[:, 1])
    else:
        try:
            auc = roc_auc_score(yte, proba, multi_class="ovr", average="macro", labels=rf.classes_)
        except Exception:
            auc = np.nan
    sens = recall_score(yte, pred, labels=classes, average=None, zero_division=0)
    ppv = precision_score(yte, pred, labels=classes, average=None, zero_division=0)
    cm = confusion_matrix(yte, pred, labels=classes)
    rows.append({"cohort": coh, "n_train": len(tr), "n_test": len(te),
                 "n_class": len(classes), "accuracy": acc, "balanced_accuracy": bal_acc, "AUC": auc,
                 "test_class_dist": dict(zip(classes, np.bincount(yte, minlength=max(classes) + 1)[classes]))})
    nm = NAME[coh]
    rep.append("## %s（训练 %d / 测试 %d，%d 类）" % (coh, len(tr), len(te), len(classes)))
    rep.append("- 准确率 = **%.3f**；平衡准确率 = **%.3f**；AUC = **%.3f**" % (acc, bal_acc, auc))
    rep.append("- 各类（按类别）：")
    for i, c in enumerate(classes):
        rep.append("  - %s：灵敏度 %.3f，PPV %.3f（测试集 n=%d）" % (nm.get(str(c), c), sens[i], ppv[i], cm[i].sum()))
    rep.append("- 混淆矩阵（行=真实, 列=预测）：")
    rep.append(pd.DataFrame(cm, index=[nm.get(str(c), c) for c in classes],
                            columns=[nm.get(str(c), c) for c in classes]).to_string())
    pd.DataFrame(cm, index=classes, columns=classes).to_csv(
        os.path.join(OUT, "p5_confusion_%s.csv" % coh), encoding="utf-8-sig")
    rep.append("")

pd.DataFrame(rows).to_csv(os.path.join(OUT, "p5_ml_results.csv"), index=False, encoding="utf-8-sig")
with open(os.path.join(OUT, "p5_step07_rf_report.md"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(rep))
print("\n".join(rep))
print("DONE")
