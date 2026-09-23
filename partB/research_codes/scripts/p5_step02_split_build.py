"""
p5_step02_split_build.py  (PartB 修订版 / 第一步：划分 + 构建轨迹建模宽表)

依据 handbook §5.4 与研究者确认：
  - 分析样本 = 基线 eCRF 可得者（mobile_long 已按此提取）。
  - 先按队列分层 30/70（以"是否曾出现移动障碍 ever_limited"为分层变量）；
  - **只在 70% 训练集上建轨迹**；30% 测试集留待后续按后验概率归类。
输出：
  output/p5_split_<cohort>_{train,test}.csv   （pid 列表）
  research_codes/mplus_p5/data/<cohort>_train.dat （宽表，缺失 -999）
  research_codes/mplus_p5/times_<cohort>.json      （时间分数，供 Mplus）
  报告 output/p5_step02_split_report.md
"""
from pathlib import Path
import os, json
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

DATA = str(Path(__file__).resolve().parents[2] / "data")
OUT = str(Path(__file__).resolve().parents[1] / "output")
MP = str(Path(__file__).resolve().parents[1] / "mplus_p5")
os.makedirs(os.path.join(MP, "data"), exist_ok=True)

BASE = {"CHARLS": 2011, "ELSA": 2004, "HRS": 2006}
SEED = 2026
rep = ["# p5_step02 划分与宽表构建报告", ""]

for coh in ["CHARLS", "ELSA", "HRS"]:
    d = pd.read_csv(os.path.join(DATA, "mobility_long_%s.csv" % coh))
    d["time"] = d["wave_year"] - BASE[coh]
    ever = (d.groupby("pid")["mobilsev"].max() >= 1).astype(int)
    pid = ever.index.values
    tr_idx, te_idx = train_test_split(np.arange(len(pid)), test_size=0.3,
                                      stratify=ever.values, random_state=SEED)
    tr_pid, te_pid = pid[tr_idx], pid[te_idx]
    pd.DataFrame({"pid": tr_pid}).to_csv(os.path.join(OUT, "p5_split_%s_train.csv" % coh), index=False)
    pd.DataFrame({"pid": te_pid}).to_csv(os.path.join(OUT, "p5_split_%s_test.csv" % coh), index=False)

    # 基线波(0)所有人为 0（纳入标准），不能再进轨迹模型 → 只用首个随访波起
    fu = [t for t in sorted(d["time"].unique()) if t > 0]
    t0 = fu[0]
    times_rc = [int(t - t0) for t in fu]          # 重中心：首个随访波=0
    dt = d[d["pid"].isin(tr_pid)]
    wide = dt.pivot_table(index="pid", columns="time", values="mobilsev", aggfunc="first")
    wide = wide.reindex(columns=fu).sort_index()
    nvar = len(fu)
    wide.columns = ["y%d" % (i + 1) for i in range(nvar)]
    times = times_rc
    mat = wide.reset_index().rename(columns={"pid": "id"}).fillna(-999)
    mat.to_csv(os.path.join(MP, "data", "%s_train.dat" % coh), sep=" ", index=False, header=False)
    with open(os.path.join(MP, "times_%s.json" % coh), "w") as jf:
        json.dump({"times": [int(t) for t in times]}, jf)

    rep.append("## %s" % coh)
    rep.append("- 总样本 %d；训练 %d / 测试 %d（曾出现移动障碍占比：train %.3f / test %.3f）" %
               (len(pid), len(tr_pid), len(te_pid), ever.loc[tr_pid].mean(), ever.loc[te_pid].mean()))
    rep.append("- 时间分数：%s" % times)
    rep.append("- 训练宽表：%d 行 × %d 列" % (len(wide), nvar))
    rep.append("")

with open(os.path.join(OUT, "p5_step02_split_report.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(rep))
print("\n".join(rep))
print("DONE")
