"""
p5_step01_extract_mobility_waves.py  (PartB 修订版 / 第一步数据准备)

目的：提取三队列 eCRF 可得者(7,885)在**各波次**的移动障碍得分 `r{N}mobilsev`（0–7 连续）。
输入：partB/data/final_analysis_pooled.csv（pid, cohort, ecrf）
      源数据：data 下三库 harmonized 文件
匹配键：CHARLS=ID(12位含前导零) ↔ pooled.pid(int)；ELSA=idauniq；HRS=hhidpn
校验：pooled.mobilsev_base 与源数据 r{baseline}mobilsev 对拍（应全为 0）
输出：partB/data/mobility_long_<cohort>.xlsx / .csv
      output/p5_step01_mobility_report.md
"""
from pathlib import Path
import os
import numpy as np
import pandas as pd
import pyreadstat

DATA = str(Path(__file__).resolve().parents[2] / "data")
OUT = str(Path(__file__).resolve().parents[1] / "output")
SRC = str(Path(__file__).resolve().parents[3] / "data")
FILES = {
    "CHARLS": dict(path=SRC + r"\Harmonized CHARLS\H_CHARLS_D_Data.dta", kind="dta",
                   key="ID", waves=[1, 2, 3, 4],
                   years={1: 2011, 2: 2013, 3: 2015, 4: 2018}, base_col="r1mobilsev"),
    "ELSA": dict(path=SRC + r"\Harmonized ELSA\gh_elsa_h.sav", kind="sav",
                 key="idauniq", waves=list(range(2, 10)),
                 years={2: 2004, 3: 2006, 4: 2008, 5: 2010, 6: 2012, 7: 2014, 8: 2016, 9: 2018},
                 base_col="r2mobilsev"),
    "HRS": dict(path=SRC + r"\Harmonized HRS\H_HRS_d.dta", kind="dta",
                key="hhidpn", waves=list(range(8, 15)),
                years={8: 2006, 9: 2008, 10: 2010, 11: 2012, 12: 2014, 13: 2016, 14: 2018},
                base_col="r8mobilsev"),
}

pool = pd.read_csv(os.path.join(DATA, "final_analysis_pooled.csv"),
                   usecols=["pid", "cohort", "ecrf", "mobilsev_base"])
rep = ["# p5_step01 逐波次移动障碍得分提取报告", ""]

for coh, sp in FILES.items():
    sub = pool[(pool["cohort"] == coh) & (pool["ecrf"].notna())].copy()
    sub["pid"] = pd.to_numeric(sub["pid"], errors="coerce").astype("Int64")
    cols = [sp["key"]] + ["r%dmobilsev" % w for w in sp["waves"]]
    if sp["kind"] == "dta":
        df, _ = pyreadstat.read_dta(sp["path"], usecols=cols)
    else:
        df, _ = pyreadstat.read_sav(sp["path"], usecols=cols)
    df["pid"] = pd.to_numeric(df[sp["key"]], errors="coerce").astype("Int64")
    df = df.drop(columns=[sp["key"]])
    df = df.dropna(subset=["pid"]).drop_duplicates(subset=["pid"])
    df["_found"] = 1

    m = sub.merge(df, on="pid", how="left")
    matched = int(m["_found"].notna().sum())
    # 校验：基线 mobilsev 对拍
    chk = pd.to_numeric(m[sp["base_col"]], errors="coerce")
    agree = int((chk == m["mobilsev_base"]).sum())
    rep.append("## %s" % coh)
    rep.append("- eCRF 可得者：%d；源数据匹配到：%d" % (len(sub), matched))
    rep.append("- 基线 mobilsev 对拍一致：%d/%d（池化 mobilsev_base 应全为 0）" % (agree, int(chk.notna().sum())))

    frames = []
    for w in sp["waves"]:
        c = "r%dmobilsev" % w
        frames.append(pd.DataFrame({"pid": m["pid"], "cohort": coh, "wave": w,
                                    "wave_year": sp["years"][w],
                                    "mobilsev": pd.to_numeric(m[c], errors="coerce")}))
    long = pd.concat(frames, ignore_index=True)
    long = long[long["mobilsev"].notna()].copy()
    long["mobilsev"] = long["mobilsev"].clip(0, 7)

    path = os.path.join(DATA, "mobility_long_%s" % coh)
    long.to_excel(path + ".xlsx", index=False)
    long.to_csv(path + ".csv", index=False, encoding="utf-8-sig")

    obs = long.groupby("pid")["mobilsev"].size()
    rep.append("- 长表行数：%d；非零得分占比：%.1f%%；得分范围：%g–%g" %
               (len(long), 100 * (long["mobilsev"] > 0).mean(), long["mobilsev"].min(), long["mobilsev"].max()))
    rep.append("- 各波非缺失：%s" % (dict(long.groupby("wave")["mobilsev"].size())))
    rep.append("- 每人均值观测波次：%.2f；观测>=2 波人数：%d；>=3 波：%d；全波：%d" %
               (obs.mean(), int((obs >= 2).sum()), int((obs >= 3).sum()), int((obs == len(sp["waves"])).sum())))
    rep.append("")

with open(OUT + r"\p5_step01_mobility_report.md", "w", encoding="utf-8") as f:
    f.write("\n".join(rep))
print("\n".join(rep))
print("DONE")
