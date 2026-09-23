"""p5_step08_traj_plot.py —— 移动障碍轨迹图（LCGA 最终类别，论文用）"""
from pathlib import Path
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DATA = str(Path(__file__).resolve().parents[2] / "data")
OUT = str(Path(__file__).resolve().parents[1] / "output")
FIG = str(Path(__file__).resolve().parents[2] / "figures")
os.makedirs(FIG, exist_ok=True)
BASE = {"CHARLS": 2011, "ELSA": 2004, "HRS": 2006}
TITLE = {"CHARLS": "CHARLS (China)", "ELSA": "ELSA (England)", "HRS": "HRS (USA)"}
NAME = {
    "CHARLS": {1: "High-declining", 2: "Increasing", 3: "Low-stable"},
    "ELSA": {1: "Late-increasing", 2: "Early-high", 3: "Low-stable"},
    "HRS": {1: "Rapid-increasing", 2: "Low-slowly-increasing"},
}
COL = {1: "#C44E52", 2: "#4C72B0", 3: "#55A868", 4: "#DD8452"}

fig, axes = plt.subplots(1, 3, figsize=(14, 4.3))
for ax, coh in zip(axes, ["CHARLS", "ELSA", "HRS"]):
    d = pd.read_csv(os.path.join(DATA, "mobility_long_%s.csv" % coh))
    d["year"] = d["wave_year"]
    d = d[d["year"] > BASE[coh]]                       # 只画随访波
    cc = pd.read_csv(os.path.join(OUT, "p5_final_class_%s.csv" % coh))
    m = d.merge(cc[["pid", "class"]], on="pid", how="inner")
    tot = m["pid"].nunique()
    for c in sorted(m["class"].unique()):
        s = m[m["class"] == c].groupby("year")["mobilsev"]
        mean, se = s.mean(), s.std() / np.sqrt(s.count())
        n = m[m["class"] == c]["pid"].nunique()
        pct = 100 * n / tot
        ax.errorbar(mean.index, mean.values, yerr=se.values, marker="o", ms=4, lw=1.9,
                    capsize=2.5, color=COL.get(c, "gray"),
                    label="%s (%.1f%%)" % (NAME[coh].get(c, "Class %d" % c), pct))
    ax.set_title(TITLE[coh], fontsize=11)
    ax.set_xlabel("Year of follow-up")
    ax.set_ylabel("Mobility limitation score (0–7)")
    ax.set_ylim(-0.3, 7)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8, frameon=False, loc="upper left")
fig.suptitle("Latent trajectories of incident mobility limitation (LCGA)", fontsize=12)
fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(os.path.join(FIG, "p5_mobility_traj.png"), dpi=300)
fig.savefig(os.path.join(FIG, "p5_mobility_traj.pdf"))
print("saved", os.path.join(FIG, "p5_mobility_traj.png"))
