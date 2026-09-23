"""
p5_step06_final_classes.py —— LCGA 最终类别：训练集(来自70%拟合)+测试集(闭式后验打分)

思路：LCGA 每类 = 一条固定均值曲线 + 统一残差方差 σ²。给(未参与建模的)30%归类：
  posterior_c ∝ π_c * exp( -0.5 * Σ_观测t (y_t - μ_ct)² / σ² )
各类均值 μ_ct 与 σ²、π_c 由 70% 训练集的 cprob 直接经验估计（与参数化无关）。
输出：output/p5_final_class_<cohort>.csv（pid, role, class, 说明）
"""
from pathlib import Path
import os, json
import numpy as np
import pandas as pd

MP = str(Path(__file__).resolve().parents[1] / "mplus_p5")
OUT = str(Path(__file__).resolve().parents[1] / "output")
DATA = str(Path(__file__).resolve().parents[2] / "data")
K = {"CHARLS": 3, "ELSA": 3, "HRS": 2}
BASE = {"CHARLS": 2011, "ELSA": 2004, "HRS": 2006}


def read_cprob(tag, nvar, k):
    a = pd.read_csv(os.path.join(MP, tag + "_cprob.dat"), sep=r"\s+", header=None, engine="python")
    a = a.apply(pd.to_numeric, errors="coerce")
    ys = a.iloc[:, :nvar].replace(-999.0, np.nan).values
    cls = a.iloc[:, nvar + k].fillna(-1).astype(int).values
    pid = a.iloc[:, -1].round().astype("int64").values
    return ys, cls, pid


for coh in ["CHARLS", "ELSA", "HRS"]:
    times = json.load(open(os.path.join(MP, "times_%s.json" % coh)))["times"]
    nvar, k = len(times), K[coh]
    ys, cls, pid = read_cprob("cmp_lcga_%s" % coh, nvar, k)
    priors = np.array([(cls == c).mean() for c in range(1, k + 1)])
    mu = np.array([np.nanmean(ys[cls == c], axis=0) for c in range(1, k + 1)])  # k×nvar
    # 统一残差方差（类-时间上池化）
    vars_ = []
    for c in range(1, k + 1):
        sub = ys[cls == c]
        for j in range(nvar):
            col = sub[:, j]; col = col[~np.isnan(col)]
            if len(col) > 1:
                vars_.append(np.var(col, ddof=1))
    sigma2 = float(np.mean(vars_))
    print("%s: priors=%s  sigma2=%.3f" % (coh, np.round(priors, 3), sigma2))
    for c in range(k):
        print("   class%d mean traj:" % (c + 1), np.round(mu[c], 2))

    # ---- 测试集宽表 ----
    test_pids = set(pd.read_csv(os.path.join(OUT, "p5_split_%s_test.csv" % coh))["pid"].astype("int64"))
    d = pd.read_csv(os.path.join(DATA, "mobility_long_%s.csv" % coh))
    d["t"] = d["wave_year"] - BASE[coh]
    fu = [t for t in sorted(d["t"].unique()) if t > 0]
    t0 = fu[0]
    d = d[d["t"].isin(fu)]
    piv = d.pivot_table(index="pid", columns="t", values="mobilsev", aggfunc="first").reindex(columns=fu)
    piv.columns = list(range(nvar))

    rows = []
    for p, r in piv.iterrows():
        rows.append({"pid": p, "role": "train" if p not in test_pids else "test"})
    # 训练集标签（来自 70% 拟合）
    tr = pd.DataFrame({"pid": pid, "class": cls})
    te_rows = []
    for p, r in piv.iterrows():
        if p not in test_pids:
            continue
        y = r.values.astype(float)
        obs = ~np.isnan(y)
        if obs.sum() == 0:
            te_rows.append({"pid": p, "class": np.nan}); continue
        logp = np.log(priors)
        for c in range(k):
            ll = -0.5 * np.sum(((y[obs] - mu[c][obs]) ** 2) / sigma2)
            logp[c] += ll
        logp -= logp.max()
        post = np.exp(logp); post /= post.sum()
        te_rows.append({"pid": p, "class": int(np.argmax(post) + 1)})
    te = pd.DataFrame(te_rows)

    final = pd.concat([tr.assign(role="train"), te.assign(role="test")], ignore_index=True)
    # 只保留有类别者
    final = final[final["class"].notna()].copy()
    final["class"] = final["class"].astype(int)
    final.to_csv(os.path.join(OUT, "p5_final_class_%s.csv" % coh), index=False, encoding="utf-8-sig")
    tab = pd.crosstab(final["role"], final["class"])
    print("   final sizes by role:\n", tab.to_string())
print("DONE")
