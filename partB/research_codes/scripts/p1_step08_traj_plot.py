"""
p1_step08_traj_plot.py  (PartB / 阶段一 - 轨迹图)

输入：output/p1_trajclass_means_<cohort>.csv
输出：figures/p1_traj_<cohort>.png / .pdf  和合并图 p1_traj_all.png
说明：LCGA k=4（最终解）；点为各类均值，误差棒为均值的标准误(SE=SD/sqrt(n))。
"""
from pathlib import Path
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = str(Path(__file__).resolve().parents[1] / "output")
FIG = str(Path(__file__).resolve().parents[2] / "figures")
os.makedirs(FIG, exist_ok=True)

COL = {1: "#4C72B0", 2: "#DD8452", 3: "#55A868", 4: "#C44E52"}
LAB = {1: "Class 1", 2: "Class 2", 3: "Class 3", 4: "Class 4"}
TITLES = {"HRS": "HRS (even waves, 2006-2018)", "ELSA": "ELSA (2004-2012)"}

fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
for ax, cohort in zip(axes, ["HRS", "ELSA"]):
    m = pd.read_csv(os.path.join(OUT, "p1_trajclass_means_%s.csv" % cohort))
    cc = pd.read_csv(os.path.join(OUT, "p1_trajclass_%s.csv" % cohort))["class"].value_counts()
    for c in sorted(m["class"].unique()):
        s = m[m["class"] == c].sort_values("time")
        se = s["std"] / np.sqrt(s["count"])
        n = int(cc.get(c, 0))
        ax.errorbar(s["time"], s["mean"], yerr=se, marker="o", ms=5, lw=1.8,
                    capsize=3, color=COL[c], label="%s (n=%d)" % (LAB[c], n))
    ax.set_title(TITLES[cohort], fontsize=11)
    ax.set_xlabel("Years from baseline")
    ax.set_ylabel("eCRF (METs)")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8, frameon=False)
fig.suptitle("Latent eCRF trajectories (LCGA, k=4)", fontsize=12)
fig.tight_layout(rect=[0, 0, 1, 0.96])
fig.savefig(os.path.join(FIG, "p1_traj_all.png"), dpi=300)
fig.savefig(os.path.join(FIG, "p1_traj_all.pdf"))
print("saved", os.path.join(FIG, "p1_traj_all.png"))
