"""
p1_step07_parse_classes.py  (PartB / 阶段一 - 提取 LCGA k=4 的类别归属)

输入：mplus/final_lcga_<cohort>_k4_cprob.dat（SAVEDATA SAVE=CPROB）
     列 = [y1..yT] [cprob1..cprobK] [class] [id]
输出：output/p1_trajclass_<cohort>.csv（pid, class, cprob1..cprobK）
     以及合并轨迹均值表 output/p1_trajclass_means_<cohort>.csv（供画图）
"""
from pathlib import Path
import os
import numpy as np
import pandas as pd

MP = str(Path(__file__).resolve().parents[1] / "mplus")
OUT = str(Path(__file__).resolve().parents[1] / "output")
DATA = str(Path(__file__).resolve().parents[2] / "data")
SPEC = {"HRS": {"nvar": 4, "xlsx": "ecrf_long_HRS.xlsx", "waves": [8, 10, 12, 14], "base": 2006},
        "ELSA": {"nvar": 3, "xlsx": "ecrf_long_ELSA.xlsx", "waves": [2, 4, 6], "base": 2004}}
K = 4

for cohort, sp in SPEC.items():
    f = os.path.join(MP, "final_lcga_%s_k4_cprob.dat" % cohort)
    arr = pd.read_csv(f, sep=r"\s+", header=None)
    nvar, k = sp["nvar"], K
    assert arr.shape[1] == nvar + k + 2, (cohort, arr.shape)
    cls = arr.iloc[:, nvar + k].astype(int)
    pid = arr.iloc[:, -1].astype("int64")
    probs = arr.iloc[:, nvar:nvar + k]
    out = pd.DataFrame({"pid": pid, "class": cls})
    for j in range(k):
        out["cprob%d" % (j + 1)] = probs.iloc[:, j]
    out.to_csv(os.path.join(OUT, "p1_trajclass_%s.csv" % cohort), index=False, encoding="utf-8-sig")
    print("=== %s class counts:" % cohort, dict(out["class"].value_counts().sort_index()))

    d = pd.read_excel(os.path.join(DATA, sp["xlsx"]))
    d = d[d["wave"].isin(sp["waves"]) & d["ecrf"].notna()].copy()
    d["time"] = d["wave_year"] - sp["base"]
    d = d.merge(out[["pid", "class"]], on="pid", how="inner")
    means = d.groupby(["class", "time"])["ecrf"].agg(["mean", "std", "count"]).reset_index()
    means.to_csv(os.path.join(OUT, "p1_trajclass_means_%s.csv" % cohort),
                 index=False, encoding="utf-8-sig")
    print(means.to_string(index=False))
    print()
print("DONE")
