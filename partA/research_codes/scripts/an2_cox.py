"""
AN-2: Cox proportional hazards regression (per cohort, low eCRF = reference)
Models (research plan §4.6):
  M1: unadjusted                              ~ ecrf_group
  M2: + age, sex                              ~ age + sex
  M3: + marital, education, smoking, drinking, SBP   (HbA1c/TC dropped per D2)
Covariate coding:
  ecrf_group: 1=low(ref), 2=middle, 3=high (entered as dummy; reference=low)
  sex: 2=female ref? We keep as-is with interpretation (code 1 male, 2 female); use male=1 ref -> female=2
  educ: 3-tier (1=below HS ref, 2=HS, 3=college+)
  smoke_status: 0=never(ref), 1=former, 2=current
  marital: 0=other ref, 1=married/partnered
  drink: 0=no ref, 1=yes
  sbp: continuous
Ties: efron. Schoenfeld residuals tested for all covariates in M3.
Outputs: an2_cox_<cohort>.csv (HR/CI/p per term), an2_schoenfeld.csv, an2_cox_report.md
"""
from pathlib import Path
import pandas as pd
import numpy as np
from lifelines import CoxPHFitter

OUT = str(Path(__file__).resolve().parents[1] / "output")

df = pd.read_csv(OUT + r"\final_analysis_pooled.csv")
df = df[df["ecrf_group"].notna()].copy()
df["ecrf_group"] = df["ecrf_group"].astype(int)
for c in ["age","sex","educ","marital","bmi","waist","rhr","sbp","mvpa","smoke_status","drink"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
df["followup_years"] = pd.to_numeric(df["followup_years"], errors="coerce")
df["mobility_event"] = pd.to_numeric(df["mobility_event"], errors="coerce").fillna(0).astype(int)

cohort_order = ["CHARLS", "ELSA", "HRS"]

def prep(dfc):
    d = dfc.copy()
    d["group_mid"] = (d["ecrf_group"] == 2).astype(int)
    d["group_high"] = (d["ecrf_group"] == 3).astype(int)
    d["educ_hs"] = (d["educ"] == 2).astype(int)
    d["educ_college"] = (d["educ"] == 3).astype(int)
    d["smk_former"] = (d["smoke_status"] == 1).astype(int)
    d["smk_current"] = (d["smoke_status"] == 2).astype(int)
    # sex: 2=female -> female indicator (ref=male)
    d["female"] = (d["sex"] == 2).astype(int)
    return d

def run_model(d, cols, name, cohort):
    dfm = d[["followup_years", "mobility_event"] + cols].dropna()
    if len(dfm) < len(cols) + 2:
        return None, dfm
    cph = CoxPHFitter(penalizer=0)
    cph.fit(dfm, duration_col="followup_years", event_col="mobility_event")
    r = cph.summary.reset_index()
    r = r.rename(columns={r.columns[0]: "term"})
    r["cohort"] = cohort
    r["model"] = name
    r["n"] = len(dfm)
    return r, dfm

out_rows = []
schoen = []
for cohort in cohort_order:
    d = prep(df[df["cohort"] == cohort])
    # M1
    r1, m1 = run_model(d, ["group_mid","group_high"], "M1", cohort)
    if r1 is not None: out_rows.append(r1)
    # M2
    r2, m2 = run_model(d, ["group_mid","group_high","age","female"], "M2", cohort)
    if r2 is not None: out_rows.append(r2)
    # M3
    cols3 = ["group_mid","group_high","age","female","marital","educ_hs","educ_college",
             "smk_former","smk_current","drink","sbp"]
    r3, m3 = run_model(d, cols3, "M3", cohort)
    if r3 is not None: out_rows.append(r3)

res = pd.concat(out_rows, ignore_index=True)
res.to_csv(OUT + r"\an2_cox.csv", index=False, encoding="utf-8-sig")

# Schoenfeld: run separate chi2 test per model per cohort M3
sch_rows = []
for cohort in cohort_order:
    d = prep(df[df["cohort"] == cohort])
    cols3 = ["group_mid","group_high","age","female","marital","educ_hs","educ_college",
             "smk_former","smk_current","drink","sbp"]
    dfm = d[["followup_years","mobility_event"]+cols3].dropna()
    if len(dfm) < 30:
        continue
    cph3 = CoxPHFitter()
    cph3.fit(dfm, duration_col="followup_years", event_col="mobility_event")
    resids = cph3.compute_residuals(dfm, kind="scaled_schoenfeld")
    for term in cols3:
        if term in resids.columns:
            v = resids[term].dropna()
            # scaled Schoenfeld residuals rows are indexed by event time
            if len(v) > 2:
                import scipy.stats as st
                t = v.index.astype(float)  # index holds follow-up time of events
                rho, p = st.spearmanr(t, v)
                sch_rows.append({"cohort":cohort,"term":term,"spearman_rho":rho,"p":p})
sch_df = pd.DataFrame(sch_rows)
sch_df.to_csv(OUT + r"\an2_schoenfeld.csv", index=False, encoding="utf-8-sig")

# build report
def fmt_hr(row):
    hr = row["exp(coef)"]; lo = row["exp(coef) lower 95%"]; hi = row["exp(coef) upper 95%"]
    p = row["p"] if "p" in row.index else row["p-value"] if "p-value" in row.index else np.nan
    return f"{hr:.3f} ({lo:.3f}-{hi:.3f})"

rep = ["# AN-2 Cox 回归报告（按库，模型1/2/3，低eCRF参照）", ""]
for cohort in cohort_order:
    rep.append(f"## {cohort}")
    sub = res[res["cohort"]==cohort]
    for model in ["M1","M2","M3"]:
        sm = sub[sub["model"]==model]
        if not len(sm):
            rep.append(f"- {model}: 数据不足/未运行")
            continue
        n = sm["n"].iloc[0]
        rep.append(f"### {model} (n={n})")
        for _, row in sm.iterrows():
            term = row["term"]
            hr = fmt_hr(row)
            p = row.get("p", np.nan) if "p" in row.index else row.get("p-value", np.nan)
            rep.append(f"- {term}: HR {hr}, p={float(p):.4f}" if pd.notna(p) else f"- {term}: HR {hr}")
    rep.append("")
rep.append("## Schoenfeld 残差检验（M3，Spearman 对时间）")
rep.append("- 若 p<0.05 提示该协变量违反比例风险假设")
rep.append(sch_df.to_string() if len(sch_df) else "(n/a)")

with open(OUT + r"\an2_cox_report.md", "w", encoding="utf-8") as f:
    f.write("\n".join(rep))
print("\n".join(rep[:40]))
print("saved an2_cox.csv, an2_schoenfeld.csv")