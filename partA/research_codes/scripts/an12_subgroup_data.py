"""
AN-12 generic: subgroup forest plot data (Model 3 complete-case) for any cohort.
Exposure: eCRF per 1 SD (z-scored within the cohort's eCRF-complete sample).
Within each stratum: Cox M3 (drop constant columns within stratum), HR (95% CI), events/n
  on the M3 complete-case sample.
P-interaction: full-cohort M3 with ecrf_sd * subgroup_var (numeric) interaction.
Usage: python an12_subgroup_data.py <COHORT>   (COHORT in CHARLS/ELSA/HRS)
Output: output/an12_<COHORT>_subgroup.csv
"""
from pathlib import Path
import sys
import pandas as pd
import numpy as np
import scipy.stats as st
from lifelines import CoxPHFitter

COHORT = sys.argv[1]
OUT = str(Path(__file__).resolve().parents[1] / "output")

df = pd.read_csv(OUT + r"\final_analysis_pooled.csv")
df = df[df["ecrf_group"].notna()].copy()
df = df[df["cohort"] == COHORT].copy()
for c in ["age","sex","educ","marital","sbp","smoke_status","drink","ecrf","followup_years","mobility_event","bmi"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
df["mobility_event"] = df["mobility_event"].fillna(0).astype(int)

d = df.copy()
d["female"] = (d["sex"] == 2).astype(int)
d["educ_hs"] = (d["educ"] == 2).astype(int)
d["educ_college"] = (d["educ"] == 3).astype(int)
d["smk_former"] = (d["smoke_status"] == 1).astype(int)
d["smk_current"] = (d["smoke_status"] == 2).astype(int)
d["ecrf_sd"] = (d["ecrf"] - d["ecrf"].mean()) / d["ecrf"].std()
d["age_cat"] = pd.cut(d["age"], [0,60,70,200], labels=[1,2,3])
d["sex_num"] = (d["sex"] == 2).astype(int)
d["educ_num"] = d["educ"]
d["smk_num"] = d["smoke_status"]
d["drink_num"] = d["drink"]
d["pa_num"] = d["mvpa"]
bmi = pd.to_numeric(d["bmi"], errors="coerce")
d["bmi_cat3"] = np.select([bmi<25, (bmi>=25)&(bmi<30), bmi>=30], [1,2,3], default=np.nan)

M3 = ["age","female","marital","educ_hs","educ_college","smk_former","smk_current","drink","sbp"]

SUBGROUPS = [
    ("Age, years",        "age_cat",    {1:"<60",         2:"60-70",             3:">=70"}),
    ("Sex",               "sex_num",    {0:"Male",         1:"Female"}),
    ("Education",         "educ_num",   {1:"Below HS",     2:"High school",       3:"College+"}),
    ("Smoking status",    "smk_num",    {0:"Never",        1:"Former",            2:"Current"}),
    ("Drinking",          "drink_num",  {0:"No",           1:"Yes"}),
    ("Physical activity", "pa_num",     {0:"No MVPA",      1:"MVPA >=2/wk"}),
    ("BMI, kg/m2",        "bmi_cat3",   {1:"<25",          2:"25-<30",            3:">=30"}),
]

def fit_within(sub):
    cols = ["ecrf_sd"] + [c for c in M3 if c in sub.columns]
    dfm = sub[["followup_years","mobility_event"] + cols].dropna()
    keep = [c for c in cols if dfm[c].nunique() > 1]
    dfm = dfm[["followup_years","mobility_event"] + keep].dropna()
    if len(dfm) < 20 or dfm["mobility_event"].sum() < 5:
        return None, dfm
    cph = CoxPHFitter(penalizer=0)
    cph.fit(dfm, duration_col="followup_years", event_col="mobility_event")
    return cph, dfm

rows = []
for gname, gvar, levels in SUBGROUPS:
    inter_p = np.nan
    # interaction on full cohort M3 (numeric subgroup var, ecrf_sd * var)
    sub0 = d.dropna(subset=["ecrf_sd","followup_years","mobility_event", gvar] + M3).copy()
    sub0[gvar] = pd.to_numeric(sub0[gvar], errors="coerce")
    sub0 = sub0.dropna(subset=["ecrf_sd"] + M3 + [gvar]).copy()
    sub0["inter"] = sub0["ecrf_sd"] * sub0[gvar]
    icols = list(dict.fromkeys(["ecrf_sd"] + M3 + [gvar, "inter"]))
    dfm_i = sub0[["followup_years","mobility_event"] + icols].dropna()
    dfm_i = dfm_i[[c for c in dfm_i.columns if dfm_i[c].nunique() > 1]]
    if len(dfm_i) > 40:
        try:
            cph_i = CoxPHFitter(penalizer=0.01)
            cph_i.fit(dfm_i, duration_col="followup_years", event_col="mobility_event")
            if "inter" in cph_i.params_:
                cc = cph_i.params_["inter"]; se = cph_i.standard_errors_["inter"]
                inter_p = 2*(1 - st.norm.cdf(abs(cc/se)))
        except Exception:
            pass

    for val, lab in levels.items():
        sub = d[d[gvar] == val].copy()
        cph, dfm = fit_within(sub)
        if cph is None:
            rows.append({"subgroup": gname, "stratum": lab,
                         "events": np.nan, "n": np.nan,
                         "HR": np.nan, "lo": np.nan, "hi": np.nan, "p": np.nan,
                         "p_interaction": inter_p})
            continue
        ev = int(dfm["mobility_event"].sum()); n = len(dfm)
        cc = cph.params_["ecrf_sd"]; se = cph.standard_errors_["ecrf_sd"]
        hr = np.exp(cc); lo = np.exp(cc-1.96*se); hi = np.exp(cc+1.96*se)
        p = 2*(1-st.norm.cdf(abs(cc/se)))
        rows.append({"subgroup": gname, "stratum": lab, "events": ev, "n": n,
                     "HR": hr, "lo": lo, "hi": hi, "p": p, "p_interaction": inter_p})

res = pd.DataFrame(rows)
res["P-interaction display"] = ""
seen = set()
for i, r in res.iterrows():
    g = r["subgroup"]
    if g not in seen:
        seen.add(g)
        val = r["p_interaction"]
        res.at[i, "P-interaction display"] = (
            "<0.001" if (pd.notna(val) and val < 0.001) else (f"{val:.3f}" if pd.notna(val) else "-")
        )
    else:
        res.at[i, "P-interaction display"] = ""

outfile = OUT + rf"\an12_{COHORT}_subgroup.csv"
res.to_csv(outfile, index=False, encoding="utf-8-sig")
pd.set_option("display.width", 220)
print(f"=== {COHORT} ===")
print(res.drop(columns=["p_interaction"]).to_string())