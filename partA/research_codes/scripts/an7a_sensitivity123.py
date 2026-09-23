"""
AN-7a: Sensitivity analyses 1-3 (Cox M3, per cohort, low eCRF ref)
SEN-1: exclude baseline mobility limitation -> identical to main cohort (baseline mobilsev==0 already)
       -> rerun explicitly for the record.
SEN-2: additionally exclude baseline cancer / lung / CVD (=heart OR stroke).
SEN-3: complete-case analysis (drop rows with any missing model variable) -> equals main M3 sample.
Output: an7_sensitivity123_report.md + an7_sensitivity123.csv
"""
from pathlib import Path
import pandas as pd
import numpy as np
import scipy.stats as st
from lifelines import CoxPHFitter

OUT = str(Path(__file__).resolve().parents[1] / "output")
df = pd.read_csv(OUT + r"\final_analysis_pooled.csv")
df = df[df["ecrf_group"].notna()].copy()
for c in ["age","sex","educ","marital","sbp","smoke_status","drink","bmi","waist","rhr",
          "cancer","lung","heart","stroke"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
df["followup_years"] = pd.to_numeric(df["followup_years"], errors="coerce")
df["mobility_event"] = pd.to_numeric(df["mobility_event"], errors="coerce").fillna(0).astype(int)
df["ecrf_group"] = df["ecrf_group"].astype(int)

def prep(d):
    d = d.copy()
    d["group_mid"] = (d["ecrf_group"] == 2).astype(int)
    d["group_high"] = (d["ecrf_group"] == 3).astype(int)
    d["female"] = (d["sex"] == 2).astype(int)
    d["educ_hs"] = (d["educ"] == 2).astype(int)
    d["educ_college"] = (d["educ"] == 3).astype(int)
    d["smk_former"] = (d["smoke_status"] == 1).astype(int)
    d["smk_current"] = (d["smoke_status"] == 2).astype(int)
    return d

M3 = ["group_mid","group_high","age","female","marital","educ_hs","educ_college",
      "smk_former","smk_current","drink","sbp"]

def fit(dfc):
    dfm = dfc[["followup_years","mobility_event"] + M3].dropna()
    if len(dfm) < 30:
        return None, dfm
    cph = CoxPHFitter(penalizer=0)
    cph.fit(dfm, duration_col="followup_years", event_col="mobility_event")
    return cph, dfm

def extract(cph, dfm, label, cohort):
    out = []
    for term in ["group_mid","group_high"]:
        cc = cph.params_[term]; se = cph.standard_errors_[term]
        hr = np.exp(cc); lo = np.exp(cc-1.96*se); hi = np.exp(cc+1.96*se)
        p = 2*(1-st.norm.cdf(abs(cc/se)))
        out.append({"analysis":label,"cohort":cohort,"term":("mid" if term=="group_mid" else "high"),
                    "n":len(dfm),"events":int(dfm["mobility_event"].sum()),
                    "HR":hr,"lo":lo,"hi":hi,"p":p})
    return out

rows = []
rep = ["# AN-7a 敏感性分析（SEN-1/2/3，Cox M3，分库，低 eCRF 参照）", ""]

cohort_order = ["CHARLS","ELSA","HRS"]
# SEN-1 (explicit; main cohort already excludes baseline mobility)
rep.append("## SEN-1 排除基线移动障碍者（= 主分析队列定义，重跑确认）")
for co in cohort_order:
    d = prep(df[df["cohort"] == co])
    cph, dfm = fit(d)
    if cph is not None:
        rows += extract(cph, dfm, "SEN-1", co)
        rep.append(f"- {co}: n={len(dfm)}, events={int(dfm['mobility_event'].sum())}")
rep.append("")

# SEN-2 exclude baseline cancer/lung/CVD
rep.append("## SEN-2 排除基线癌症/肺病/CVD（CVD=heart 或 stroke）")
for co in cohort_order:
    d = df[df["cohort"] == co].copy()
    excl = (d["cancer"] == 1) | (d["lung"] == 1) | (d["heart"] == 1) | (d["stroke"] == 1)
    d = prep(d[~excl])
    cph, dfm = fit(d)
    if cph is not None:
        rows += extract(cph, dfm, "SEN-2", co)
        rep.append(f"- {co}: n={len(dfm)}, events={int(dfm['mobility_event'].sum())}, 排除病人数={int(excl.sum())}")
rep.append("")

# SEN-3 complete case
rep.append("## SEN-3 完整病例分析（模型变量无缺失）")
for co in cohort_order:
    d = prep(df[df["cohort"] == co])
    cph, dfm = fit(d)
    if cph is not None:
        rows += extract(cph, dfm, "SEN-3", co)
        rep.append(f"- {co}: complete-case n={len(dfm)}, events={int(dfm['mobility_event'].sum())}")
rep.append("")

res = pd.DataFrame(rows)
res.to_csv(OUT + r"\an7_sensitivity123.csv", index=False, encoding="utf-8-sig")

rep.append("## 结果表（HR 高/中 eCRF vs 低）")
for lab in ["SEN-1","SEN-2","SEN-3"]:
    rep.append(f"### {lab}")
    for co in cohort_order:
        sub = res[(res["analysis"]==lab)&(res["cohort"]==co)]
        for _,r in sub.iterrows():
            rep.append(f"- {co} {r['term']}: HR {r['HR']:.3f} ({r['lo']:.3f}-{r['hi']:.3f}), p={r['p']:.4f} (n={r['n']})")
with open(OUT + r"\an7_sensitivity123_report.md", "w", encoding="utf-8") as f:
    f.write("\n".join(rep))
print("\n".join(rep))