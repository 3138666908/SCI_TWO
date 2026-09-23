"""
AN-7b: Sensitivity analysis 4 - Multiple Imputation by Chained Equations (MICE), m=20
Goal: address selection bias from missing eCRF inputs by imputing and using the full
      baseline cohort with observed follow-up (main analysis used only eCRF-complete 7,885).
Procedure per cohort:
  1. Keep baseline cohort (age>=45, baseline mobilsev==0) with observed followup_years.
  2. Impute missing: bmi, waist, rhr, sbp, mvpa, educ, marital, smoke_status, drink
     (predictors include age, sex, outcome, followup_years, cohort-irrelevant).
  3. Round categorical/binary imputed values.
  4. Recompute eCRF (sex-specific), sex-stratified quintiles -> ecrf_group.
  5. Fit Cox M3; store beta & SE for group_mid/group_high.
  6. Pool m=20 by Rubin's rules.
Output: an7_mice_report.md + an7_mice_results.csv
"""
from pathlib import Path
import pandas as pd
import numpy as np
import scipy.stats as st
from sklearn.experimental import enable_iterative_imputer  # noqa
from sklearn.impute import IterativeImputer
from lifelines import CoxPHFitter

OUT = str(Path(__file__).resolve().parents[1] / "output")
df = pd.read_csv(OUT + r"\final_analysis_pooled.csv")
for c in ["age","sex","educ","marital","bmi","waist","rhr","sbp","mvpa","smoke_status","drink"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
df["followup_years"] = pd.to_numeric(df["followup_years"], errors="coerce")
df["mobility_event"] = pd.to_numeric(df["mobility_event"], errors="coerce").fillna(0).astype(int)

# baseline cohort with observed follow-up
base = df[df["followup_years"].notna()].copy()
n_total = len(base)
impute_vars = ["age","sex","educ","marital","bmi","waist","rhr","sbp","mvpa","smoke_status","drink"]
pred_vars = impute_vars + ["mobility_event","followup_years"]

def ecrf_calc(sex, age, bmi, waist, rhr, mvpa, smoke_now):
    male = sex == 1
    e = np.full(len(sex), np.nan, dtype=float)
    am = male.values
    e[am] = (21.2870 + age[am]*0.1654 - (age[am]**2)*0.0023 - bmi[am]*0.2318
             - waist[am]*0.0337 - rhr[am]*0.0390 + mvpa[am]*0.6351 - smoke_now[am]*0.4263)
    af = (~male).values
    e[af] = (14.7873 + age[af]*0.1159 - (age[af]**2)*0.0017 - bmi[af]*0.1534
             - waist[af]*0.0085 - rhr[af]*0.0364 + mvpa[af]*0.5987 - smoke_now[af]*0.2994)
    return e

cohort_order = ["CHARLS","ELSA","HRS"]
m = 20
results = []
per_imp_hr = {co: [] for co in cohort_order}

for imp in range(m):
    for co in cohort_order:
        sub = base[base["cohort"] == co].copy().reset_index(drop=True)
        X = sub[pred_vars].copy()
        ii = IterativeImputer(max_iter=10, random_state=1000+imp, sample_posterior=True)
        Ximp = pd.DataFrame(ii.fit_transform(X), columns=pred_vars)
        # round categorical/binary
        Ximp["sex"] = Ximp["sex"].round().clip(1,2)
        Ximp["educ"] = Ximp["educ"].round().clip(1,3)
        Ximp["marital"] = Ximp["marital"].round().clip(0,1)
        Ximp["mvpa"] = Ximp["mvpa"].round().clip(0,1)
        Ximp["drink"] = Ximp["drink"].round().clip(0,1)
        Ximp["smoke_status"] = Ximp["smoke_status"].round().clip(0,2)
        d = sub.copy()
        for c in impute_vars:
            d[c] = Ximp[c].values
        smoke_now = (d["smoke_status"] == 2).astype(float)
        d["ecrf"] = ecrf_calc(d["sex"], d["age"], d["bmi"], d["waist"], d["rhr"], d["mvpa"], smoke_now)
        # sex-stratified quintiles -> group 1/2/3
        grp = pd.Series(pd.NA, index=d.index, dtype="Int64")
        for s in [1,2]:
            vals = d.loc[d["sex"]==s, "ecrf"].dropna()
            if len(vals) < 5:
                continue
            q = np.nanpercentile(vals, [20,40,60,80])
            g = pd.cut(vals, [-np.inf, q[0], q[2], np.inf], labels=[1,2,3], right=False)
            idx = vals.index
            grp.loc[idx] = pd.Series(g.values, index=idx).astype("Int64")
        d["ecrf_group_s"] = grp
        d = d.dropna(subset=["ecrf_group_s"]).copy()
        d["group_mid"] = (d["ecrf_group_s"]==2).astype(int)
        d["group_high"] = (d["ecrf_group_s"]==3).astype(int)
        d["female"] = (d["sex"]==2).astype(int)
        d["educ_hs"] = (d["educ"]==2).astype(int)
        d["educ_college"] = (d["educ"]==3).astype(int)
        d["smk_former"] = (d["smoke_status"]==1).astype(int)
        d["smk_current"] = (d["smoke_status"]==2).astype(int)
        cols = ["group_mid","group_high","age","female","marital","educ_hs","educ_college",
                "smk_former","smk_current","drink","sbp"]
        dfm = d[["followup_years","mobility_event"]+cols].dropna()
        try:
            cph = CoxPHFitter(penalizer=0)
            cph.fit(dfm, duration_col="followup_years", event_col="mobility_event")
            for term, tl in [("group_mid","mid"),("group_high","high")]:
                beta = cph.params_[term]; se = cph.standard_errors_[term]
                per_imp_hr[co].append({"term":tl,"beta":beta,"se":se,"n":len(dfm)})
        except Exception as e:
            print(f"[{co} imp{imp}] fit failed: {e}")

def rubin(est):
    betas = np.array([e["beta"] for e in est])
    ses = np.array([e["se"] for e in est])
    Ub = ses**2
    Qbar = betas.mean()
    Ubar = Ub.mean()
    B = betas.var(ddof=1)
    T = Ubar + (1 + 1/len(betas))*B
    se = np.sqrt(T)
    return Qbar, se, len(betas)

rep = ["# AN-7b 敏感性分析 SEN-4：MICE 多重插补（m=20）", "",
       f"- 用于插补的基线队列（有随访时间）: {n_total}（其中主分析 eCRF 完整 7,885）",
       "- 插补变量: bmi, waist, rhr, sbp, mvpa, educ, marital, smoke_status, drink",
       "- 每次插补后按性别分层重算 eCRF 五分位分组；Rubin 规则合并。",
       ""]
for co in cohort_order:
    est = per_imp_hr[co]
    if not est:
        rep.append(f"## {co}: 无有效插补结果")
        continue
    rep.append(f"## {co}  (有效插补 {len(est)//2}×2 项, 中位 n={int(np.median([e['n'] for e in est]))})")
    for term, lab in [("mid","中 eCRF vs 低"),("high","高 eCRF vs 低")]:
        sub = [e for e in est if e["term"]==term]
        Qbar, se, mm = rubin(sub)
        hr = np.exp(Qbar); lo = np.exp(Qbar-1.96*se); hi = np.exp(Qbar+1.96*se)
        p = 2*(1-st.norm.cdf(abs(Qbar/se)))
        rep.append(f"- {lab}: HR {hr:.3f} ({lo:.3f}-{hi:.3f}), p={p:.4f}")
        results.append({"cohort":co,"term":lab,"HR":hr,"lo":lo,"hi":hi,"p":p,"m":mm})
    rep.append("")
rep.append("## 备注")
rep.append("- 3,180 例无任何随访观测者（无生存时间）未纳入插补，与主分析的随访定义一致。")

pd.DataFrame(results).to_csv(OUT + r"\an7_mice_results.csv", index=False, encoding="utf-8-sig")
with open(OUT + r"\an7_mice_report.md", "w", encoding="utf-8") as f:
    f.write("\n".join(rep))
print("\n".join(rep))