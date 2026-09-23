"""
AN-9: Sensitivity - exclude samples beyond eCRF formula applicable range
       (female age>78, male age>86, BMI<=18.5) per researcher decision.
Compare against main Cox M3 (per cohort, pooled analysis sample = eCRF-complete).
Output: an9_range_sensitivity_report.md + an9_range_sensitivity.csv
"""
from pathlib import Path
import pandas as pd
import numpy as np
import scipy.stats as st
from lifelines import CoxPHFitter

OUT = str(Path(__file__).resolve().parents[1] / "output")
df = pd.read_csv(OUT + r"\final_analysis_pooled.csv")
df = df[df["ecrf_group"].notna()].copy()
for c in ["age","sex","bmi","educ","marital","sbp","smoke_status","drink"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
df["followup_years"] = pd.to_numeric(df["followup_years"], errors="coerce")
df["mobility_event"] = pd.to_numeric(df["mobility_event"], errors="coerce").fillna(0).astype(int)
df["ecrf_group"] = df["ecrf_group"].astype(int)

# out-of-range flags
out_range = ((df["sex"]==2) & (df["age"]>78)) | ((df["sex"]==1) & (df["age"]>86)) | (df["bmi"]<=18.5)
unkrange = out_range.isna()  # BMI missing -> cannot judge; treat as in-range (not excluded)
excl_flag = out_range.fillna(False)

def prep(d):
    d = d.copy()
    d["group_mid"] = (d["ecrf_group"]==2).astype(int)
    d["group_high"] = (d["ecrf_group"]==3).astype(int)
    d["female"] = (d["sex"]==2).astype(int)
    d["educ_hs"] = (d["educ"]==2).astype(int)
    d["educ_college"] = (d["educ"]==3).astype(int)
    d["smk_former"] = (d["smoke_status"]==1).astype(int)
    d["smk_current"] = (d["smoke_status"]==2).astype(int)
    return d

M3 = ["group_mid","group_high","age","female","marital","educ_hs","educ_college",
      "smk_former","smk_current","drink","sbp"]

def fit_report(d, cohort, label):
    dfm = d[["followup_years","mobility_event"]+M3].dropna()
    rows = []
    if len(dfm) < 30:
        return rows, dfm
    cph = CoxPHFitter(penalizer=0)
    cph.fit(dfm, duration_col="followup_years", event_col="mobility_event")
    for term, lab in [("group_mid","mid"),("group_high","high")]:
        cc=cph.params_[term]; se=cph.standard_errors_[term]
        hr=np.exp(cc); lo=np.exp(cc-1.96*se); hi=np.exp(cc+1.96*se); p=2*(1-st.norm.cdf(abs(cc/se)))
        rows.append({"analysis":label,"cohort":cohort,"term":lab,"n":len(dfm),
                     "events":int(dfm["mobility_event"].sum()),"HR":hr,"lo":lo,"hi":hi,"p":p})
    return rows, dfm

all_rows = []
rep = ["# AN-9 超 eCRF 公式适用范围样本敏感性分析", "",
       "- 超范围定义：女>78岁 / 男>86岁 / BMI≤18.5", ""]
for co in ["CHARLS","ELSA","HRS"]:
    d_all = df[df["cohort"]==co]
    n_total = len(d_all)
    n_excl = int(excl_flag[df["cohort"]==co].sum())
    d_keep = d_all[~excl_flag[df["cohort"]==co].to_numpy()]
    d_keep = prep(d_keep)
    rows, dfm = fit_report(d_keep, co, "excl-out-of-range")
    all_rows += rows
    rep.append(f"## {co}: 分析样本 n={n_total}, 剔除超范围={n_excl}, 保留 n={len(d_keep)}")
    for r in rows:
        rep.append(f"- {r['term']} eCRF vs 低: HR {r['HR']:.3f} ({r['lo']:.3f}-{r['hi']:.3f}), p={r['p']:.4f} (n={r['n']})")
    rep.append("")
rep.append("## 与主分析 M3 对比（高 vs 低 eCRF HR）")
main = pd.read_csv(OUT + r"\an2_cox.csv")
for co in ["CHARLS","ELSA","HRS"]:
    r0 = main[(main["cohort"]==co)&(main["model"]=="M3")&(main["term"]=="group_high")].iloc[0]
    r1 = [r for r in all_rows if r["cohort"]==co and r["term"]=="high"]
    if r1:
        r1 = r1[0]
        rep.append(f"- {co}: 主分析 {r0['exp(coef)']:.3f} ({r0['exp(coef) lower 95%']:.3f}-{r0['exp(coef) upper 95%']:.3f}) "
                   f"→ 剔除超范围后 {r1['HR']:.3f} ({r1['lo']:.3f}-{r1['hi']:.3f})")
rep.append("")
rep.append("## 结论")
rep.append("- 若剔除超范围样本后 HR 与主分析一致，则表明外推样本不改变结论；否则需在下文中说明影响。")

pd.DataFrame(all_rows).to_csv(OUT + r"\an9_range_sensitivity.csv", index=False, encoding="utf-8-sig")
with open(OUT + r"\an9_range_sensitivity_report.md", "w", encoding="utf-8") as f:
    f.write("\n".join(rep))
print("\n".join(rep))