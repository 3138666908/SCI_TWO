"""
p1_step04_prepare_mplus_data.py  (PartB / 阶段一 - Mplus 宽表数据准备)

依据 handbook §5.1（方案 2）与研究者决定：
  - HRS：体格测量为交替半样本 → 只能用**偶数波** W8/W10/W12/W14
         （2006/2010/2014/2018；time=0/4/8/12）；
  - ELSA：W2/W4/W6（2004/2008/2012；time=0/4/8）；
  - CHARLS 不做轨迹。
样本：主 = 观测>=2 波；敏感性 = 观测>=3 波。
输出：mplus/data/{HRS,HRS_ge3,ELSA,ELSA_ge3}.dat（空格分隔，无表头，缺失=-999）
      mplus/mapping_<sample>.csv
"""
from pathlib import Path
import os
import pandas as pd

DATA = str(Path(__file__).resolve().parents[2] / "data")
MP = str(Path(__file__).resolve().parents[1] / "mplus")
DAT = os.path.join(MP, "data")
os.makedirs(DAT, exist_ok=True)

# label: (xlsx, waves, base_year)
SPEC = {
    "HRS": ("ecrf_long_HRS.xlsx", [8, 10, 12, 14], 2006),
    "HRS_ge3": ("ecrf_long_HRS.xlsx", [8, 10, 12, 14], 2006),
    "ELSA": ("ecrf_long_ELSA.xlsx", [2, 4, 6], 2004),
    "ELSA_ge3": ("ecrf_long_ELSA.xlsx", [2, 4, 6], 2004),
}
MINW = {"HRS": 2, "HRS_ge3": 3, "ELSA": 2, "ELSA_ge3": 3}

for label, (fx, waves, base) in SPEC.items():
    d = pd.read_excel(os.path.join(DATA, fx))
    d = d[d["wave"].isin(waves) & d["ecrf"].notna()].copy()
    d["time"] = d["wave_year"] - base
    obs = d.groupby("pid")["ecrf"].size()
    keep = obs[obs >= MINW[label]].index
    d = d[d["pid"].isin(keep)]
    wide = d.pivot_table(index="pid", columns="time", values="ecrf", aggfunc="first")
    times = sorted(d["time"].unique().tolist())
    wide = wide.reindex(columns=times).sort_index()
    nvar = len(times)
    wide.columns = ["y%d" % (i + 1) for i in range(nvar)]
    idf = wide.reset_index()[["pid"]].rename(columns={"pid": "id"})
    mat = pd.concat([idf.reset_index(drop=True), wide.reset_index(drop=True)], axis=1).fillna(-999)
    mat.to_csv(os.path.join(DAT, "%s.dat" % label), sep=" ", index=False, header=False)
    idf.to_csv(os.path.join(MP, "mapping_%s.csv" % label), index=False, encoding="utf-8-sig")
    print("%s: n=%d vars=%d times=%s" % (label, len(mat), nvar, times))
print("DONE")
