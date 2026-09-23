"""
p1_step02_prepare_traj.py  (PartB / 阶段一 - 轨迹建模数据准备)

依据 handbook §5.1（方案 2：轨迹建模仅 HRS 主 / ELSA 辅；CHARLS 不做轨迹）。
输入：data\\ecrf_long_HRS.xlsx、ecrf_long_ELSA.xlsx
处理：
  - time = wave_year - 基线年（HRS 基线 2006；ELSA 基线 2004）
  - 仅保留 eCRF 已观测（非缺失）的记录
  - 主分析样本：观测到 >=2 个波次者；敏感性样本：>=3 个波次者
  - 长格式：pid, cohort, wave, wave_year, time, ecrf（供 lcmm 使用）
输出：
  output\\p1_traj_HRS.csv / p1_traj_ELSA.csv           （>=2 波，主分析）
  output\\p1_traj_HRS_ge3.csv / p1_traj_ELSA_ge3.csv   （>=3 波，敏感性）
  output\\p1_step02_prepare_report.md
"""
from pathlib import Path
import pandas as pd

DATA = str(Path(__file__).resolve().parents[2] / "data")
OUT = str(Path(__file__).resolve().parents[1] / "output")
BASE_YEAR = {"HRS": 2006, "ELSA": 2004}

rep = ["# p1_step02 轨迹建模数据准备报告", ""]
rep.append("| 队列 | 样本 | 人数 | 观测记录数 | 平均观测波次 |")
rep.append("|---|---|---|---|---|")

for cohort in ["HRS", "ELSA"]:
    d = pd.read_excel(DATA + r"\ecrf_long_%s.xlsx" % cohort)
    d = d[d["ecrf"].notna()].copy()
    d["time"] = d["wave_year"] - BASE_YEAR[cohort]
    d = d[["pid", "cohort", "wave", "wave_year", "time", "ecrf"]]

    obs = d.groupby("pid")["ecrf"].size()
    for label, thr, suffix in [(">=2波(主)", 2, ""), (">=3波(敏感性)", 3, "_ge3")]:
        keep = obs[obs >= thr].index
        sub = d[d["pid"].isin(keep)].sort_values(["pid", "time"]).reset_index(drop=True)
        sub.to_csv(OUT + r"\p1_traj_%s%s.csv" % (cohort, suffix), index=False,
                   encoding="utf-8-sig")
        rep.append("| %s | %s | %d | %d | %.2f |" %
                   (cohort, label, sub["pid"].nunique(), len(sub),
                    sub.groupby("pid").size().mean()))
    rep.append("")

rep.append("> time 单位：年（相对基线）；HRS: 0,2,4,...,12；ELSA: 0,4,8。")
with open(OUT + r"\p1_step02_prepare_report.md", "w", encoding="utf-8") as f:
    f.write("\n".join(rep))
print("DONE")
