"""
AN-6: Subgroup analysis of eCRF -> mobility limitation (M3, pooled cohorts + cohort adjust)
Subgroups (research plan):
  age: <60 / 60-<70 / >=70
  sex: male / female
  education: belowHS / HS / college+
  smoking: never / former / current
  drinking: no / yes
  PA: no MVPA / MVPA>=2wk
  BMI: normal(<25) / overweight(25-<30) / obese(>=30)
For each subgroup variable:
  1. Fit M3 within each stratum; report HR(high vs low) and HR(mid vs low).
  2. Interaction test: eCRF group (ordinal 1/2/3) x subgroup variable (Wald).
Output: an6_subgroup_results.csv + an6_subgroup_report.md
Note: 'cohort' is included as model covariate (pooled); event is mobility_event.
"""
from pathlib import Path
import pandas as pd
import numpy as np
import scipy.stats as st
from lifelines import CoxPHFitter

OUT = str(Path(__file__).resolve().parents[1] / "output")
df = pd.read_csv(OUT + r"\final_analysis_pooled.csv")
df = df[df["ecrf_group"].notna()].copy()
# cohort as dummies (string) for pooled model
df["cohort"] = df["cohort"].astype(str)
df = pd.get_dummies(df, columns=["cohort"], prefix="coh").astype({c: int for c in df.columns if c.startswith("coh_")})
for c in ["age","sex","educ","marital","bmi","smoke_status","drink","sbp"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
df["followup_years"] = pd.to_numeric(df["followup_years"], errors="coerce")
df["mobility_event"] = pd.to_numeric(df["mobility_event"], errors="coerce").fillna(0).astype(int)
df["ecrf_group"] = df["ecrf_group"].astype(int)

# recodes
df["female"] = (df["sex"] == 2).astype(int)
df["educ_hs"] = (df["educ"] == 2).astype(int)
df["educ_college"] = (df["educ"] == 3).astype(int)
df["smk_former"] = (df["smoke_status"] == 1).astype(int)
df["smk_current"] = (df["smoke_status"] == 2).astype(int)
df["mvpa"] = pd.to_numeric(df["mvpa"], errors="coerce")
# subgroup factor variables
df["age_cat"] = pd.cut(df["age"], [0, 60, 70, 200], labels=[1, 2, 3])  # <60=1,60-70=2,>=70=3
df["educ_cat"] = df["educ"]                                      # 1/2/3
df["smk_cat"] = df["smoke_status"]                               # 0/1/2
df["drink_cat"] = df["drink"]                                    # 0/1
df["pa_cat"] = df["mvpa"]                                        # 0/1
# BMI 3-group: normal(<25)=1, overweight(25-<30)=2, obese(>=30)=3
bmi = pd.to_numeric(df["bmi"], errors="coerce")
df["bmi_cat3"] = np.select([bmi < 25, (bmi >= 25) & (bmi < 30), bmi >= 30], [1, 2, 3], default=np.nan)

M3_COLS = ["age","female","marital","educ_hs","educ_college","smk_former","smk_current",
           "drink","sbp","coh_ELSA","coh_HRS"]
STRATA = {
    "Age": ("age_cat", {1: "<60", 2: "60-70", 3: ">=70"}),
    "Sex": ("sex", {1: "Male", 2: "Female"}),
    "Education": ("educ_cat", {1: "Below HS", 2: "HS", 3: "College+"}),
    "Smoking": ("smk_cat", {0: "Never", 1: "Former", 2: "Current"}),
    "Drinking": ("drink_cat", {0: "No", 1: "Yes"}),
    "PA": ("pa_cat", {0: "No MVPA", 1: "MVPA>=2/wk"}),
    "BMI": ("bmi_cat3", {1: "Normal<25", 2: "Overweight25-<30", 3: "Obese>=30"}),
}

rows = []
rep = ["# AN-6 亚组分析报告（合并队列，Cox M3 + cohort 调整；低 eCRF 参照）", ""]

def run_stratum(sub, cohort_lbl, subgroup_col=None):
    sub = sub.copy()
    sub["group_mid"] = (sub["ecrf_group"] == 2).astype(int)
    sub["group_high"] = (sub["ecrf_group"] == 3).astype(int)
    cols = ["group_mid","group_high"] + [c for c in M3_COLS if c in sub.columns]
    dfm = sub[["followup_years","mobility_event"] + cols].dropna()
    if len(dfm) < 20 or dfm["mobility_event"].sum() < 5:
        return None
    # drop columns that are constant within stratum (cause convergence issues)
    keep = []
    for c in cols:
        v = dfm[c]
        if v.nunique() > 1:
            keep.append(c)
    dfm = dfm[["followup_years","mobility_event"] + keep].dropna()
    if len(dfm) < 20 or dfm["mobility_event"].sum() < 5:
        return None
    try:
        cph = CoxPHFitter(penalizer=0.01)
        cph.fit(dfm, duration_col="followup_years", event_col="mobility_event")
        return cph
    except Exception:
        try:
            cph = CoxPHFitter(penalizer=0.1)
            cph.fit(dfm, duration_col="followup_years", event_col="mobility_event")
            return cph
        except Exception:
            return None

for name, (var, labels) in STRATA.items():
    rep.append(f"## {name}")
    for val, lab in labels.items():
        sub = df[df[var] == val]
        cph = run_stratum(sub, name)
        if cph is None:
            rep.append(f"- {lab}: 样本不足")
            continue
        n = len(sub)
        ev = int(sub["mobility_event"].sum())
        rep.append(f"### {lab}  (n={n}, events={ev})")
        for term in ["group_mid","group_high"]:
            cc = cph.params_[term]; se = cph.standard_errors_[term]
            hr = np.exp(cc); lo = np.exp(cc - 1.96*se); hi = np.exp(cc + 1.96*se)
            p = 2*(1-st.norm.cdf(abs(cc/se)))
            lab_str = "中" if term == "group_mid" else "高"
            rep.append(f"- {lab_str} eCRF vs 低: HR {hr:.3f} ({lo:.3f}-{hi:.3f}), p={p:.4f}")
            rows.append({"subgroup": name, "stratum": lab, "n": n, "events": ev,
                         "term": lab_str, "HR": hr, "lo": lo, "hi": hi, "p": p})
    # interaction test (ordinal eCRF group x stratum)
    sub_all = df.dropna(subset=["age","sex","marital","educ","smoke_status","drink","sbp","bmi_cat3","followup_years"])
    if var == "bmi_cat3":
        sub_all = sub_all[sub_all["bmi_cat3"].notna()]
    sub_all = sub_all[sub_all[var].notna()]
    sub_all = sub_all.copy()
    sub_all["group_num"] = sub_all["ecrf_group"]  # 1/2/3 ordinal
    sub_all["var_num"] = pd.to_numeric(sub_all[var], errors="coerce")
    if sub_all["var_num"].nunique() < 2 or len(sub_all) < 40:
        rep.append("  （交互检验：亚组类别不足）")
        continue
    sub_all["inter"] = sub_all["group_num"] * sub_all["var_num"]
    sub_all["gmid"] = (sub_all["ecrf_group"] == 2).astype(int)
    sub_all["ghi"] = (sub_all["ecrf_group"] == 3).astype(int)
    colsA = ["gmid","ghi"] + [c for c in M3_COLS if c in sub_all.columns]
    dfm = sub_all[["followup_years","mobility_event"]+colsA+["var_num","group_num","inter"]].dropna()
    dfm = dfm[[c for c in dfm.columns if dfm[c].nunique() > 1]]
    try:
        cph2 = CoxPHFitter(penalizer=0.01)
        cph2.fit(dfm, duration_col="followup_years", event_col="mobility_event")
        cc = cph2.params_["inter"]; se = cph2.standard_errors_["inter"]
        p_int = 2*(1-st.norm.cdf(abs(cc/se)))
        rep.append(f"- 交互(eCRF组序数 × {name}) Wald p={p_int:.4f}")
        rows.append({"subgroup": name+"_interaction", "stratum": "ordinal-var",
                     "n": len(dfm), "events": int(dfm["mobility_event"].sum()),
                     "term": "interaction", "HR": np.exp(cc), "p": p_int})
    except Exception as e:
        rep.append(f"- 交互检验失败: {e}")
    rep.append("")

res = pd.DataFrame(rows)
res.to_csv(OUT + r"\an6_subgroup_results.csv", index=False, encoding="utf-8-sig")
with open(OUT + r"\an6_subgroup_report.md", "w", encoding="utf-8") as f:
    f.write("\n".join(rep))
print("\n".join(rep[:120]))