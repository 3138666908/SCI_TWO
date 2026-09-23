"""p5_step05_cmp.py —— LCGA vs GMM 轨迹与归属对照"""
from pathlib import Path
import os, json
import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score

MP = str(Path(__file__).resolve().parents[1] / "mplus_p5")
OUT = str(Path(__file__).resolve().parents[1] / "output")
K = {"CHARLS": 3, "ELSA": 3, "HRS": 2}
rep = ["# p5_step05 LCGA vs GMM 对照（70% 训练集）", ""]


def read_cprob(tag, nvar, k):
    arr = pd.read_csv(os.path.join(MP, tag + "_cprob.dat"), sep=r"\s+", header=None, engine="python")
    arr = arr.apply(pd.to_numeric, errors="coerce")
    cls = arr.iloc[:, nvar + k].fillna(-1).astype(int)
    pid = arr.iloc[:, -1].round().astype("int64")
    ys = arr.iloc[:, :nvar].replace(-999, np.nan)
    return ys.reset_index(drop=True), cls.reset_index(drop=True), pid.reset_index(drop=True)


for coh in ["CHARLS", "ELSA", "HRS"]:
    times = json.load(open(os.path.join(MP, "times_%s.json" % coh)))["times"]
    nvar, k = len(times), K[coh]
    yl, cl, pl = read_cprob("cmp_lcga_%s" % coh, nvar, k)
    yg, cg, pg = read_cprob("cmp_gmm_%s" % coh, nvar, k)

    rep.append("## %s（%d 波，k=%d）" % (coh, nvar, k))
    rep.append("- LCGA 类人数：%s" % dict(cl.value_counts().sort_index()))
    rep.append("- GMM  类人数：%s" % dict(cg.value_counts().sort_index()))
    # 归属一致率
    m = pd.merge(pd.DataFrame({"pid": pl, "lcga": cl}), pd.DataFrame({"pid": pg, "gmm": cg}), on="pid")
    ari = adjusted_rand_score(m["lcga"], m["gmm"])
    agree = (m["lcga"].values == m["gmm"].values).mean()
    rep.append("- 归属完全一致比例：%.1f%%；调整兰德指数 ARI=%.3f" % (100 * agree, ari))
    rep.append("- 交叉表（行=LCGA, 列=GMM）：")
    ct = pd.crosstab(m["lcga"], m["gmm"])
    rep.append(ct.to_string())
    rep.append("")
    rep.append("- 各类**经验均值轨迹**（行=类, 列=时间 %s）：" % times)
    for name, ys, cs in [("LCGA", yl, cl), ("GMM", yg, cg)]:
        tab = ys.groupby(cs.values).mean().round(2)
        tab.columns = times
        rep.append("  [%s]" % name)
        rep.append("  " + tab.to_string().replace("\n", "\n  "))
    rep.append("")

with open(os.path.join(OUT, "p5_step05_cmp_report.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(rep))
print("\n".join(rep))
print("DONE")
