"""
AN-10: True complete-case sensitivity analysis (SEN-5)
从【全量基线队列】(age>=45 && 基线 mobilsev==0) 出发，剔除任何缺失：
  - eCRF 成分：age, sex, bmi, waist, rhr, mvpa, smoke_now
  - 协变量：educ, marital, drink, sbp
  - 结局：followup_years, mobility_event
  完整病例内重算 eCRF -> 性别分层五分位 -> Cox M3（低 eCRF 参照，分库）
  与主分析（eCRF 可算 7,885）对比。
Output: an10_completecase_report.md + an10_completecase.csv
"""
from pathlib import Path
import pandas as pd
import numpy as np
import scipy.stats as st
from lifelines import CoxPHFitter

OUT = str(Path(__file__).resolve().parents[1] / "output")

def ecrf_calc(sex, age, bmi, waist, rhr, mvpa, smoke_now):
    arr_sex = np.asarray(sex); age=np.asarray(age); bmi=np.asarray(bmi)
    waist=np.asarray(waist); rhr=np.asarray(rhr); mvpa=np.asarray(mvpa); smk=np.asarray(smoke_now)
    e = np.full(len(arr_sex), np.nan, float)
    m = arr_sex == 1
    e[m] = 21.2870 + age[m]*0.1654 - (age[m]**2)*0.0023 - bmi[m]*0.2318 - waist[m]*0.0337 \
           - rhr[m]*0.0390 + mvpa[m]*0.6351 - smk[m]*0.4263
    f = arr_sex == 2
    e[f] = 14.7873 + age[f]*0.1159 - (age[f]**2)*0.0017 - bmi[f]*0.1534 - waist[f]*0.0085 \
           - rhr[f]*0.0364 + mvpa[f]*0.5987 - smk[f]*0.2994
    return e

REQ = ["age","sex","educ","marital","bmi","waist","rhr","sbp","mvpa",
       "smoke_ever","smoke_now","drink","followup_years","mobility_event"]

cohort_order = ["CHARLS","ELSA","HRS"]
report_rows = []
rep = ["# AN-10 真·完整病例敏感性分析（SEN-5）", "",
       "- 定义：从全量基线队列（age≥45 且基线 mobilsev=0）剔除任意 eCRF 成分/协变量/结局缺失者",
       "- eCRF 成分：age, sex, bmi, waist, rhr, mvpa, smoke_now；协变量：educ, marital, drink, sbp",
       "- 完整病例内重算 eCRF → 性别分层五分位 → 低 eCRF 参照 Cox M3（分库）", ""]

main = pd.read_csv(OUT + r"\an2_cox.csv")

for co in cohort_order:
    if co == "CHARLS":
        src = OUT + r"\step05_CHARLS_outcome.csv"
    elif co == "ELSA":
        src = OUT + r"\step05_ELSA_outcome.csv"
    else:
        src = OUT + r"\step05_HRS_outcome.csv"
    d = pd.read_csv(src)
    for c in REQ + ["age_ge45"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["mobility_event"] = d["mobility_event"].fillna(0).astype(int)
    n_base = len(d)
    # complete-case filter
    cc = d.dropna(subset=REQ).copy()
    n_keep = len(cc)
    n_drop = n_base - n_keep
    # recompute eCRF
    cc["ecrf"] = ecrf_calc(cc["sex"], cc["age"], cc["bmi"], cc["waist"], cc["rhr"],
                           cc["mvpa"], cc["smoke_now"])
    # sex-stratified quintiles -> 1/2/3
    grp = pd.Series(pd.NA, index=cc.index, dtype="Int64")
    for s in [1,2]:
        vals = cc.loc[cc["sex"]==s, "ecrf"].dropna()
        if len(vals) < 5: continue
        q = np.nanpercentile(vals, [20,40,60,80])
        g = pd.cut(vals, [-np.inf,q[0],q[2],np.inf], labels=[1,2,3], right=False)
        idx = vals.index
        grp.loc[idx] = pd.Series(g.values, index=idx).astype("Int64")
    cc["ecrf_group_cc"] = grp
    cc = cc.dropna(subset=["ecrf_group_cc"]).copy()
    cc["group_mid"] = (cc["ecrf_group_cc"]==2).astype(int)
    cc["group_high"] = (cc["ecrf_group_cc"]==3).astype(int)
    cc["female"] = (cc["sex"]==2).astype(int)
    cc["educ_hs"] = (cc["educ"]==2).astype(int)
    cc["educ_college"] = (cc["educ"]==3).astype(int)
    # smoking 3-category from ever/now
    smoke = pd.Series(pd.NA, index=cc.index, dtype="Int64")
    smoke[cc["smoke_ever"]==0] = 0
    smoke[(cc["smoke_ever"]==1)&(cc["smoke_now"]==1)] = 2
    smoke[(cc["smoke_ever"]==1)&(cc["smoke_now"]==0)] = 1
    cc["smk_status"] = smoke
    cc["smk_former"] = (cc["smk_status"]==1).astype(int)
    cc["smk_current"] = (cc["smk_status"]==2).astype(int)

    M3 = ["group_mid","group_high","age","female","marital","educ_hs","educ_college",
          "smk_former","smk_current","drink","sbp"]
    dfm = cc[["followup_years","mobility_event"]+M3].dropna()
    rep.append(f"## {co}")
    rep.append(f"- 基线队列 n={n_base}；剔除缺失 {n_drop}；完整病例 n={n_keep}（{100*n_keep/n_base:.1f}%）")
    rep.append(f"- Cox M3 有效样本 n={len(dfm)}, events={int(dfm['mobility_event'].sum())}")
    cph = CoxPHFitter(penalizer=0)
    cph.fit(dfm, duration_col="followup_years", event_col="mobility_event")
    for term, lab in [("group_mid","中"),("group_high","高")]:
        cc_ = cph.params_[term]; se = cph.standard_errors_[term]
        hr=np.exp(cc_); lo=np.exp(cc_-1.96*se); hi=np.exp(cc_+1.96*se); p=2*(1-st.norm.cdf(abs(cc_/se)))
        rep.append(f"- {lab} eCRF vs 低: HR {hr:.3f} ({lo:.3f}-{hi:.3f}), p={p:.4f}")
        report_rows.append({"analysis":"SEN-5 complete-case","cohort":co,"term":"mid" if term=="group_mid" else "high",
                            "n":len(dfm),"events":int(dfm["mobility_event"].sum()),"HR":hr,"lo":lo,"hi":hi,"p":p})
    # contrast with main
    for term, lab in [("group_mid","mid"),("group_high","high")]:
        r0 = main[(main["cohort"]==co)&(main["model"]=="M3")&(main["term"]==term)]
        if len(r0):
            r0=r0.iloc[0]
            rep.append(f"  [对比 主分析 M3 {lab}] HR {r0['exp(coef)']:.3f} ({r0['exp(coef) lower 95%']:.3f}-{r0['exp(coef) upper 95%']:.3f})")
    rep.append("")

rep.append("## 结论")
rep.append("- 与主分析 M3 对比：完整病例（SEN-5）与主分析的 HR 若接近，则缺失排除策略不改变结论。")

pd.DataFrame(report_rows).to_csv(OUT + r"\an10_completecase.csv", index=False, encoding="utf-8-sig")
with open(OUT + r"\an10_completecase_report.md","w",encoding="utf-8") as f:
    f.write("\n".join(rep))
print("\n".join(rep))