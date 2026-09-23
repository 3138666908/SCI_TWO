"""
p4_step01_decomposition.py  (PartB / eCRF 组分的贡献分解)

目的（2026-09-19 与研究者确定）：
  eCRF 是 6 个组分的确定性函数，故不做"预测 eCRF"；改为**分解 eCRF 的差异/下降**：
  ① 变化分解：ΔeCRF = Σ b_k·Δx_k   （谁造成了随访期的下降）
  ② 方差分解：Var(eCRF) = Σ b_k·Cov(x_k, eCRF)  （谁造成了人群间差异）
  系数用 eCRF 公式原值（男女分式），不改变 eCRF 定义。

输入：data/ecrf_long_{CHARLS,ELSA,HRS}.xlsx（含组分列）
分析波次：CHARLS W1/W2/W3（11/13/15）；ELSA W2/W4/W6（04/08/12）；HRS 偶数波 W8/W10/W12/W14
输出：output/p4_change_decomposition.csv、output/p4_variance_decomposition.csv、p4_report.md
"""
from pathlib import Path
import os
import numpy as np
import pandas as pd

DATA = str(Path(__file__).resolve().parents[2] / "data")
OUT = str(Path(__file__).resolve().parents[1] / "output")
WAVES = {"CHARLS": [1, 2, 3], "ELSA": [2, 4, 6], "HRS": [8, 10, 12, 14]}
BASE = {"CHARLS": 2011, "ELSA": 2004, "HRS": 2006}
# eCRF 系数（男 sex=1 / 女 sex=2）
COEF = {
    1: {"age": 0.1654, "age2": -0.0023, "bmi": -0.2318, "waist": -0.0337, "rhr": -0.0390, "mvpa": 0.6351, "smoke": -0.4263},
    2: {"age": 0.1159, "age2": -0.0017, "bmi": -0.1534, "waist": -0.0085, "rhr": -0.0364, "mvpa": 0.5987, "smoke": -0.2994},
}
LAB = {"age": "age(+age^2)", "bmi": "BMI", "waist": "waist", "rhr": "resting HR", "mvpa": "MVPA", "smoke": "current smoking"}

chg_rows, var_rows = [], []
report = ["# p4 eCRF 组分贡献分解报告", ""]

for coh, waves in WAVES.items():
    d = pd.read_excel(os.path.join(DATA, "ecrf_long_%s.xlsx" % coh))
    d = d[d["wave"].isin(waves)].copy()
    d = d.dropna(subset=["ecrf", "age", "bmi", "waist", "rhr", "mvpa", "smoke_now"])
    # ---------- ② 方差分解（横断面，用基线波） ----------
    b = d[d["wave"] == waves[0]].copy()
    for sx in [1, 2]:
        s = b[b["sex"] == sx]
        if len(s) < 30:
            continue
        c = COEF[sx]
        e = s["ecrf"] - s["ecrf"].mean()
        var_e = e.var(ddof=0)
        contrib = {
            "age": c["age"] * ((s["age"] - s["age"].mean()) * e).mean() + c["age2"] * ((s["age"] ** 2 - (s["age"] ** 2).mean()) * e).mean(),
            "bmi": c["bmi"] * ((s["bmi"] - s["bmi"].mean()) * e).mean(),
            "waist": c["waist"] * ((s["waist"] - s["waist"].mean()) * e).mean(),
            "rhr": c["rhr"] * ((s["rhr"] - s["rhr"].mean()) * e).mean(),
            "mvpa": c["mvpa"] * ((s["mvpa"] - s["mvpa"].mean()) * e).mean(),
            "smoke": c["smoke"] * ((s["smoke_now"] - s["smoke_now"].mean()) * e).mean(),
        }
        tot = sum(contrib.values())
        for k, v in contrib.items():
            var_rows.append({"cohort": coh, "sex": "M" if sx == 1 else "F", "n": len(s),
                             "component": LAB[k], "contribution": v, "share_pct": 100 * v / tot})

    # ---------- ① 变化分解（首次→末次） ----------
    d = d.sort_values(["pid", "wave_year"])
    g = d.groupby("pid")
    first = g.first()
    last = g.last()
    m = first.index.intersection(last.index)
    # 需要有 >=2 次测量（wave 数>=2）
    cnt = g.size()
    m = [p for p in m if cnt[p] >= 2]
    F = first.loc[m]; L = last.loc[m]
    for sx in [1, 2]:
        sel = [p for p in m if F.loc[p, "sex"] == sx]
        if len(sel) < 30:
            continue
        c = COEF[sx]
        dage = (L.loc[sel, "age"] - F.loc[sel, "age"])
        dage2 = (L.loc[sel, "age"] ** 2 - F.loc[sel, "age"] ** 2)
        contrib = {
            "age": (c["age"] * dage + c["age2"] * dage2).mean(),
            "bmi": (c["bmi"] * (L.loc[sel, "bmi"] - F.loc[sel, "bmi"])).mean(),
            "waist": (c["waist"] * (L.loc[sel, "waist"] - F.loc[sel, "waist"])).mean(),
            "rhr": (c["rhr"] * (L.loc[sel, "rhr"] - F.loc[sel, "rhr"])).mean(),
            "mvpa": (c["mvpa"] * (L.loc[sel, "mvpa"] - F.loc[sel, "mvpa"])).mean(),
            "smoke": (c["smoke"] * (L.loc[sel, "smoke_now"] - F.loc[sel, "smoke_now"])).mean(),
        }
        de = (L.loc[sel, "ecrf"] - F.loc[sel, "ecrf"]).mean()
        for k, v in contrib.items():
            chg_rows.append({"cohort": coh, "sex": "M" if sx == 1 else "F", "n": len(sel),
                             "component": LAB[k], "mean_contribution": v,
                             "share_pct": 100 * v / de if de != 0 else np.nan})
        chg_rows.append({"cohort": coh, "sex": "M" if sx == 1 else "F", "n": len(sel),
                         "component": "TOTAL ΔeCRF", "mean_contribution": de, "share_pct": 100.0})

pd.DataFrame(var_rows).to_csv(OUT + r"\p4_variance_decomposition.csv", index=False, encoding="utf-8-sig")
pd.DataFrame(chg_rows).to_csv(OUT + r"\p4_change_decomposition.csv", index=False, encoding="utf-8-sig")

for name, rows, key in [("方差分解 Var(eCRF) 份额(%)", var_rows, "share_pct"),
                        ("变化分解 ΔeCRF 份额(%)", chg_rows, "share_pct")]:
    report.append("## " + name)
    t = pd.DataFrame(rows).pivot_table(index="component", columns=["cohort", "sex"], values=key)
    report.append(t.round(1).to_string())
    report.append("")
with open(OUT + r"\p4_report.md", "w", encoding="utf-8") as f:
    f.write("\n".join(report))
print("\n".join(report))
print("DONE")
